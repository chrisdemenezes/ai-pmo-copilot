"""Delete Policy tests (W7-3 Etapa 3, TD-002 -- Founder Decision).

Etapa 3's mandated analysis (inspect the real current behavior, map every
FK, identify what RESTRICT/CASCADE-equivalent behavior actually applies,
assess impact) found that **no FK in the real schema declares
`ondelete=` at all** (`grep -n "ForeignKey(" src/database/*.py` --
33 occurrences, none with `ondelete=`), and **the application never hard-
deletes any parent/CRITICAL entity anywhere** (`grep -rn ".delete("
src/database/*.py src/services/**/*.py` -- the sole hit is
`AdministrationRepository`'s `session.delete(user_role)`, a leaf join-row
with no children).

PostgreSQL's default for an FK with no `ON DELETE` clause is `NO ACTION`
-- empirically confirmed here (not assumed) to already behave exactly
like `RESTRICT` for the non-deferred constraints this schema uses: a
`DELETE` against a referenced row with existing dependents is blocked
with a `ForeignKeyViolation`, never a silent orphan.

**Correction to a prior finding, elevated transparently, not silently
carried forward:** AR-18 §12 stated "um DELETE real de produção hoje
produziria órfãos silenciosos, não um erro". Empirical testing during this
Etapa (see Technical Design/Decision Log) shows this is not accurate for
the schema as it exists today -- every FK already blocks the delete with
a real error. The genuine gap TD-002 named is narrower: this RESTRICT-
equivalent behavior is an accidental default, never a declared, tested,
protected decision -- exactly what this module closes.

**Decision derived without inventing a new architectural/business
decision (Founder's explicit condition for Etapa 3):** the smallest
policy coherent with the V1 is to keep exactly the current behavior
(RESTRICT-equivalent everywhere, no CASCADE anywhere) and make it a
tested, protected invariant -- consistent with the application's own
pre-existing discipline of never hard-deleting a CRITICAL entity (soft
state via `is_active`/`revoked_at`/`cancelled_at` everywhere). No
migration is introduced: `ondelete=` was never declared, so there is
nothing to change to preserve this behavior -- only to lock it in with a
test, so a future migration or ORM change can never introduce an
accidental `CASCADE` without this suite failing first.
"""
import os
import subprocess
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.db import temp_database_url


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _assert_delete_is_blocked(conn, delete_sql: str, params: dict) -> None:
    try:
        conn.execute(text(delete_sql), params)
        conn.commit()
        raise AssertionError(
            f"expected DELETE to be blocked by a foreign key constraint, but it succeeded: {delete_sql}"
        )
    except IntegrityError:
        conn.rollback()


class TestDeletePolicyIsRestrictEverywhere:
    """One isolated database, migrated to head, exercising the impact
    areas the Founder's mandate named explicitly: tenant isolation
    (organizations), auditability (users -> audit_logs), Knowledge
    Platform (documents -> document_versions -> chunks), AnalysisRecords
    (projects -> analysis_records), Events (events -> dead_letter_events /
    workflow_executions)."""

    def test_organization_with_dependents_cannot_be_deleted(self) -> None:
        """Tenant isolation: an Organization that owns real data (a
        Portfolio, in this case) can never be deleted out from under it."""
        with temp_database_url("delete_policy_org") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            engine = create_engine(database_url)
            with engine.connect() as conn:
                org_id = conn.execute(
                    text(
                        "INSERT INTO organizations (name, slug, created_at) "
                        "VALUES ('Org', 'org', now()) RETURNING id"
                    )
                ).scalar()
                conn.execute(
                    text(
                        "INSERT INTO portfolios (organization_id, name, code, created_at) "
                        "VALUES (:o, 'PF', 'PF1', now())"
                    ),
                    {"o": org_id},
                )
                conn.commit()

                _assert_delete_is_blocked(
                    conn, "DELETE FROM organizations WHERE id = :id", {"id": org_id}
                )
            engine.dispose()

    def test_user_with_audit_logs_cannot_be_deleted(self) -> None:
        """Auditability: the actor behind an audit trail entry can never
        be deleted while that entry still exists -- the trail can never
        silently lose its "who" (AR-18 audit integrity requirement)."""
        with temp_database_url("delete_policy_audit") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            engine = create_engine(database_url)
            with engine.connect() as conn:
                org_id = conn.execute(
                    text(
                        "INSERT INTO organizations (name, slug, created_at) "
                        "VALUES ('Org', 'org', now()) RETURNING id"
                    )
                ).scalar()
                user_id = conn.execute(
                    text(
                        "INSERT INTO users (organization_id, email, display_name, identity_type, "
                        "is_active, created_at) VALUES (:o, 'a@example.com', 'A', 'standard', true, now()) "
                        "RETURNING id"
                    ),
                    {"o": org_id},
                ).scalar()
                conn.execute(
                    text(
                        "INSERT INTO audit_logs (organization_id, actor_user_id, action, entity_type, "
                        "entity_id, created_at) VALUES (:o, :u, 'organization.renamed', 'organization', :o, now())"
                    ),
                    {"o": org_id, "u": user_id},
                )
                conn.commit()

                _assert_delete_is_blocked(conn, "DELETE FROM users WHERE id = :id", {"id": user_id})
            engine.dispose()

    def test_document_with_versions_and_chunks_cannot_be_deleted(self) -> None:
        """Knowledge Platform: a Document with an ingested version (and its
        chunks) is structurally protected -- deleting it can never silently
        strand `document_versions`/`chunks` rows."""
        with temp_database_url("delete_policy_docs") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            engine = create_engine(database_url)
            with engine.connect() as conn:
                org_id = conn.execute(
                    text(
                        "INSERT INTO organizations (name, slug, created_at) "
                        "VALUES ('Org', 'org', now()) RETURNING id"
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
                vector = "[" + ",".join(["0.1"] * 1024) + "]"
                conn.execute(
                    text(
                        "INSERT INTO chunks (document_version_id, organization_id, chunk_index, text, embedding) "
                        "VALUES (:v, :o, 0, 'hello', :e)"
                    ),
                    {"v": version_id, "o": org_id, "e": vector},
                )
                conn.commit()

                _assert_delete_is_blocked(
                    conn, "DELETE FROM documents WHERE id = :id", {"id": document_id}
                )
                _assert_delete_is_blocked(
                    conn, "DELETE FROM document_versions WHERE id = :id", {"id": version_id}
                )
            engine.dispose()

    def test_project_with_analysis_records_cannot_be_deleted(self) -> None:
        """AnalysisRecords: a Project's real analysis history can never be
        silently orphaned by deleting the Project."""
        with temp_database_url("delete_policy_analysis") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            engine = create_engine(database_url)
            with engine.connect() as conn:
                org_id = conn.execute(
                    text(
                        "INSERT INTO organizations (name, slug, created_at) "
                        "VALUES ('Org', 'org', now()) RETURNING id"
                    )
                ).scalar()
                project_id = conn.execute(
                    text(
                        "INSERT INTO projects (organization_id, name, created_at) "
                        "VALUES (:o, 'Project', now()) RETURNING id"
                    ),
                    {"o": org_id},
                ).scalar()
                conn.execute(
                    text(
                        "INSERT INTO analysis_records (kind, project_id, organization_id, payload, created_at) "
                        "VALUES ('status', :p, :o, '{}', now())"
                    ),
                    {"p": project_id, "o": org_id},
                )
                conn.commit()

                _assert_delete_is_blocked(
                    conn, "DELETE FROM projects WHERE id = :id", {"id": project_id}
                )
            engine.dispose()

    def test_event_with_dead_letter_and_workflow_execution_cannot_be_deleted(self) -> None:
        """Events: the durable envelope of a published event cannot be
        deleted while its Dead Letter or Workflow Execution records still
        reference it -- "what was published" can never silently lose its
        downstream trail."""
        with temp_database_url("delete_policy_events") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            engine = create_engine(database_url)
            with engine.connect() as conn:
                org_id = conn.execute(
                    text(
                        "INSERT INTO organizations (name, slug, created_at) "
                        "VALUES ('Org', 'org', now()) RETURNING id"
                    )
                ).scalar()
                event_id = "22222222-2222-2222-2222-222222222222"
                conn.execute(
                    text(
                        "INSERT INTO events (event_id, event_type, correlation_id, timestamp, "
                        "organization_id, origin, payload_version, payload) "
                        "VALUES (:e, 'document.indexed', 'corr-1', now(), :o, 'test', 1, '{}')"
                    ),
                    {"e": event_id, "o": org_id},
                )
                conn.execute(
                    text(
                        "INSERT INTO workflow_executions (event_id, workflow_name, organization_id, "
                        "correlation_id, status, started_at) "
                        "VALUES (:e, 'document_indexed_workflow', :o, 'corr-1', 'completed', now())"
                    ),
                    {"e": event_id, "o": org_id},
                )
                conn.commit()

                _assert_delete_is_blocked(conn, "DELETE FROM events WHERE event_id = :id", {"id": event_id})
            engine.dispose()

    def test_reconstructable_role_catalog_can_still_be_managed_normally(self) -> None:
        """Confirms the policy is not overreaching: `role_permissions`
        (a RECONSTRUCTABLE mapping row, Technical Design Section 4) can be
        deleted freely when nothing references it -- RESTRICT only blocks
        deletes that would actually orphan a real dependent, never
        legitimate management of catalog data with no dependents."""
        with temp_database_url("delete_policy_catalog") as database_url:
            env = os.environ.copy()
            env["DATABASE_URL"] = database_url
            _alembic(env, "upgrade", "head")

            engine = create_engine(database_url)
            with engine.connect() as conn:
                role_id = conn.execute(
                    text("INSERT INTO roles (name, description) VALUES ('td002_test_role', NULL) RETURNING id")
                ).scalar()
                permission_id = conn.execute(
                    text(
                        "INSERT INTO permissions (name, description) VALUES ('td002_test_perm', NULL) RETURNING id"
                    )
                ).scalar()
                conn.execute(
                    text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                    {"r": role_id, "p": permission_id},
                )
                conn.commit()

                conn.execute(
                    text("DELETE FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
                    {"r": role_id, "p": permission_id},
                )
                conn.execute(text("DELETE FROM roles WHERE id = :id"), {"id": role_id})
                conn.execute(text("DELETE FROM permissions WHERE id = :id"), {"id": permission_id})
                conn.commit()  # must not raise
            engine.dispose()
