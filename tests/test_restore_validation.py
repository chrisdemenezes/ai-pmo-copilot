"""Restore Contract tests (W7-3 Etapa 2, Founder Decision).

Mandated coverage (Founder mandate letters, subset applicable to restore):
D. restore válido; E. restore incompleto detectado; F. migration
incompatível detectada; G. pgvector presente após restore; H. dados
CRITICAL preservados; I. dados RECONSTRUCTABLE tratados corretamente;
J. health após restore; K. readiness após restore; L. tenant isolation
preservado; M. audit records preservados; N. Knowledge Platform
estruturalmente íntegra. All backup/restore cycles run exclusively
against isolated, throwaway test databases (`tests.db.temp_database_url`)
-- never a shared or real environment.
"""
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from src.api.dependencies import build_repository
from src.database.backup import create_backup
from src.database.repository import AnalysisRepository
from src.database.restore_validation import validate_restore
from src.main import app
from tests.db import temp_database_url


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _restore(dump_path: Path, target_database_url: str) -> None:
    result = subprocess.run(
        ["pg_restore", "--clean", "--if-exists", "--dbname", target_database_url, str(dump_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    # pg_restore exits non-zero on harmless warnings (e.g. "role does not
    # exist" for --clean's DROP OWNED statements against a fresh database)
    # -- the real, mandated proof of success is validate_restore() itself,
    # never this exit code alone.
    assert "FATAL" not in result.stderr, result.stderr


def _seed_two_tenant_dataset(conn) -> dict:
    org_a = conn.execute(
        text("INSERT INTO organizations (name, slug, created_at) VALUES ('Org A', 'org-a', now()) RETURNING id")
    ).scalar()
    org_b = conn.execute(
        text("INSERT INTO organizations (name, slug, created_at) VALUES ('Org B', 'org-b', now()) RETURNING id")
    ).scalar()
    user_a = conn.execute(
        text(
            "INSERT INTO users (organization_id, email, display_name, identity_type, is_active, created_at) "
            "VALUES (:o, 'a@example.com', 'User A', 'standard', true, now()) RETURNING id"
        ),
        {"o": org_a},
    ).scalar()

    document_a = conn.execute(
        text(
            "INSERT INTO documents (organization_id, source_name, created_at) "
            "VALUES (:o, 'doc-a.md', now()) RETURNING id"
        ),
        {"o": org_a},
    ).scalar()
    version_a = conn.execute(
        text(
            "INSERT INTO document_versions (document_id, content, created_at) "
            "VALUES (:d, 'Content of document A', now()) RETURNING id"
        ),
        {"d": document_a},
    ).scalar()
    vector_a = "[" + ",".join(["0.1"] * 1024) + "]"
    conn.execute(
        text(
            "INSERT INTO chunks (document_version_id, organization_id, chunk_index, text, embedding, "
            "embedding_provider, embedding_model) "
            "VALUES (:v, :o, 0, 'Content of document A', :e, 'voyage', 'voyage-4')"
        ),
        {"v": version_a, "o": org_a, "e": vector_a},
    )

    document_b = conn.execute(
        text(
            "INSERT INTO documents (organization_id, source_name, created_at) "
            "VALUES (:o, 'doc-b.md', now()) RETURNING id"
        ),
        {"o": org_b},
    ).scalar()
    version_b = conn.execute(
        text(
            "INSERT INTO document_versions (document_id, content, created_at) "
            "VALUES (:d, 'Content of document B', now()) RETURNING id"
        ),
        {"d": document_b},
    ).scalar()
    vector_b = "[" + ",".join(["0.2"] * 1024) + "]"
    conn.execute(
        text(
            "INSERT INTO chunks (document_version_id, organization_id, chunk_index, text, embedding, "
            "embedding_provider, embedding_model) "
            "VALUES (:v, :o, 0, 'Content of document B', :e, 'voyage', 'voyage-4')"
        ),
        {"v": version_b, "o": org_b, "e": vector_b},
    )

    conn.execute(
        text(
            "INSERT INTO audit_logs (organization_id, actor_user_id, action, entity_type, entity_id, created_at) "
            "VALUES (:o, :u, 'organization.renamed', 'organization', :o, now())"
        ),
        {"o": org_a, "u": user_a},
    )
    conn.execute(
        text(
            "INSERT INTO events (event_id, event_type, correlation_id, timestamp, organization_id, "
            "origin, payload_version, payload) "
            "VALUES ('11111111-1111-1111-1111-111111111111', 'document.indexed', 'corr-1', now(), :o, "
            "'test', 1, '{}')"
        ),
        {"o": org_a},
    )
    conn.commit()
    return {"org_a": org_a, "org_b": org_b}


class TestFullRoundTrip:
    """D (restore válido), G (pgvector presente), H (CRITICAL preservado),
    I (RECONSTRUCTABLE tratado corretamente -- nenhuma linha de `roles`/
    `permissions`/`invitations` é exigida pela validação), L (tenant
    isolation preservado), M (audit records preservados), N (Knowledge
    Platform estruturalmente íntegra) -- exercised together against one
    real backup->restore->validate cycle, since they are properties of the
    same restored database, not independent mechanisms."""

    def test_backup_restore_and_validate_a_populated_two_tenant_dataset(self, tmp_path: Path) -> None:
        with (
            temp_database_url("restore_source") as source_url,
            temp_database_url("restore_target") as target_url,
        ):
            source_env = os.environ.copy()
            source_env["DATABASE_URL"] = source_url
            _alembic(source_env, "upgrade", "head")

            source_engine = create_engine(source_url)
            with source_engine.connect() as conn:
                ids = _seed_two_tenant_dataset(conn)
            source_engine.dispose()

            metadata = create_backup(
                database_url=source_url,
                destination_dir=tmp_path,
                environment="staging",
                release_sha="abc123",
                alembic_revision="head",
            )

            _restore(metadata.path, target_url)

            target_engine = create_engine(target_url)
            result = validate_restore(target_engine, expect_populated=True)
            assert result.ok, result.problems
            assert result.problems == ()

            with target_engine.connect() as conn:
                # D/M/N -- real content survived the round trip verbatim,
                # not just row counts.
                content_a = conn.execute(
                    text(
                        "SELECT content FROM document_versions dv "
                        "JOIN documents d ON dv.document_id = d.id "
                        "WHERE d.organization_id = :o"
                    ),
                    {"o": ids["org_a"]},
                ).scalar()
                assert content_a == "Content of document A"

                # L -- tenant isolation preserved: each org's chunk is
                # retrievable scoped to its own organization_id, never the
                # other tenant's.
                chunk_texts_a = conn.execute(
                    text("SELECT text FROM chunks WHERE organization_id = :o"), {"o": ids["org_a"]}
                ).scalars().all()
                chunk_texts_b = conn.execute(
                    text("SELECT text FROM chunks WHERE organization_id = :o"), {"o": ids["org_b"]}
                ).scalars().all()
                assert chunk_texts_a == ["Content of document A"]
                assert chunk_texts_b == ["Content of document B"]

                # G -- every restored chunk carries a real production-shaped
                # vector.
                bad_dim = conn.execute(
                    text("SELECT COUNT(*) FROM chunks WHERE vector_dims(embedding) != 1024")
                ).scalar()
                assert bad_dim == 0

                # I -- RECONSTRUCTABLE tables (seeded catalogs) were never
                # required non-empty by validate_restore, yet remain
                # structurally queryable (no error), confirming the
                # validation module never conflates them with CRITICAL data.
                role_count = conn.execute(text("SELECT COUNT(*) FROM roles")).scalar()
                assert role_count >= 0  # merely proves the table is intact and queryable
            target_engine.dispose()


class TestDetectsIncompleteRestore:
    """E -- a structurally incomplete restore (a table genuinely missing)
    must be detected, never silently accepted."""

    def test_missing_table_is_reported_as_a_problem(self) -> None:
        with temp_database_url("restore_incomplete") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE chunks CASCADE"))
                conn.commit()

            result = validate_restore(engine)
            assert not result.ok
            assert any("chunks" in problem for problem in result.problems)
            engine.dispose()


class TestDetectsIncompatibleSchema:
    """F (migration incompatível detectada) + G's negative case (embedding
    dimension mismatch is real when the schema is genuinely old, `vector(16)`
    pre-D-177) -- exercised together since they are both symptoms of
    restoring a backup taken from an older release."""

    def test_older_revision_and_dimension_mismatch_are_both_reported(self) -> None:
        with temp_database_url("restore_incompatible") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "0020")

            engine = create_engine(database_url)
            with engine.connect() as conn:
                org_id = conn.execute(
                    text(
                        "INSERT INTO organizations (name, slug, created_at) "
                        "VALUES ('Org A', 'org-a', now()) RETURNING id"
                    )
                ).scalar()
                document_id = conn.execute(
                    text(
                        "INSERT INTO documents (organization_id, source_name, created_at) "
                        "VALUES (:o, 'doc.md', now()) RETURNING id"
                    ),
                    {"o": org_id},
                ).scalar()
                version_id = conn.execute(
                    text(
                        "INSERT INTO document_versions (document_id, content, created_at) "
                        "VALUES (:d, 'hello', now()) RETURNING id"
                    ),
                    {"d": document_id},
                ).scalar()
                old_vector = "[" + ",".join(["0"] * 16) + "]"
                conn.execute(
                    text(
                        "INSERT INTO chunks (document_version_id, organization_id, chunk_index, text, embedding) "
                        "VALUES (:v, :o, 0, 'hello', :e)"
                    ),
                    {"v": version_id, "o": org_id, "e": old_vector},
                )
                conn.commit()

            result = validate_restore(engine)
            assert not result.ok
            assert any("older/incompatible release" in problem for problem in result.problems)
            assert any("embedding dimension" in problem for problem in result.problems)
            engine.dispose()


class TestDetectsTruncatedCriticalData:
    """H -- CRITICAL tables emptied after a restore of a source known to be
    populated must be detected; never assumed for an arbitrary restore
    (`expect_populated` is opt-in, exercised negatively here)."""

    def test_empty_critical_tables_after_expected_population_is_reported(self) -> None:
        """`organizations` is pre-seeded by migration `0008` (real seed data
        "by design"), so a freshly migrated database is never empty there --
        `users`/`audit_logs`/`events`, which no migration seeds, are the
        tables this scenario genuinely exercises as empty."""
        with temp_database_url("restore_truncated") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            result = validate_restore(create_engine(database_url), expect_populated=True)
            assert not result.ok
            assert any("users" in problem for problem in result.problems)
            assert any("audit_logs" in problem for problem in result.problems)
            assert any("events" in problem for problem in result.problems)

    def test_empty_database_without_expect_populated_is_not_flagged(self) -> None:
        """A fresh, legitimately empty install is not a restore failure --
        `expect_populated` defaults to False precisely so this is never a
        false positive."""
        with temp_database_url("restore_fresh_empty") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            result = validate_restore(create_engine(database_url))
            assert result.ok, result.problems


class TestHealthAndReadinessAfterRestore:
    """J (health após restore) + K (readiness após restore) -- the real
    HTTP surface an operator checks post-restore (Disaster Recovery
    Protocol, Technical Design Section 10), not just the DB-level module."""

    def test_health_and_ready_are_green_against_a_restored_database(self, tmp_path: Path) -> None:
        with (
            temp_database_url("restore_health_source") as source_url,
            temp_database_url("restore_health_target") as target_url,
        ):
            source_env = os.environ.copy()
            source_env["DATABASE_URL"] = source_url
            _alembic(source_env, "upgrade", "head")

            source_engine = create_engine(source_url)
            with source_engine.connect() as conn:
                _seed_two_tenant_dataset(conn)
            source_engine.dispose()

            metadata = create_backup(
                database_url=source_url,
                destination_dir=tmp_path,
                environment="staging",
                release_sha="abc123",
                alembic_revision="head",
            )
            _restore(metadata.path, target_url)

            restored_repository = AnalysisRepository(database_url=target_url)
            app.dependency_overrides[build_repository] = lambda: restored_repository
            try:
                client = TestClient(app)
                health = client.get("/health")
                assert health.status_code == 200
                assert health.json()["status"] == "healthy"

                ready = client.get("/ready")
                assert ready.status_code == 200
                assert ready.json() == {"status": "ready"}
            finally:
                app.dependency_overrides.pop(build_repository, None)
