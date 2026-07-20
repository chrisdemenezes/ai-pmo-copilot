"""Migration 0008 (domain seed) -- the Capability 01-03 seed data becomes
real rows in both organizations, legacy Projects are attached in place
(never duplicated), and the migration is idempotent and reversible."""
import os
import subprocess
import sys

from sqlalchemy import create_engine, text


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result


def _env(tmp_path, name):
    database_url = f"sqlite:///{tmp_path / name}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    return env, database_url


def test_0008_seeds_both_organizations(tmp_path):
    env, database_url = _env(tmp_path, "m0008.db")
    _alembic(env, "upgrade", "head")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        org_names = {row.name for row in conn.execute(text("SELECT name FROM organizations"))}
        assert {"Organização Principal", "Demo Organization"} <= org_names
        assert conn.execute(text("SELECT COUNT(*) FROM portfolios")).scalar() == 6  # 3 x 2 orgs
        assert conn.execute(text("SELECT COUNT(*) FROM programs")).scalar() == 8  # 4 x 2 orgs
        assert (
            conn.execute(
                text("SELECT COUNT(*) FROM projects WHERE program_id IS NOT NULL")
            ).scalar()
            == 14  # 7 x 2 orgs
        )


def test_0008_attaches_a_legacy_project_instead_of_duplicating(tmp_path):
    """DOMAIN-BLUEPRINT-PROJECT.md §3 Fase 2: a pre-existing legacy Project
    named like a seed one (e.g. Multilift, from migration 0002's
    analysis_records data migration) gains the domain fields in place."""
    env, database_url = _env(tmp_path, "m0008_legacy.db")
    _alembic(env, "upgrade", "0007")
    engine = create_engine(database_url)

    with engine.begin() as conn:
        org_id = conn.execute(
            text("SELECT id FROM organizations WHERE name = 'Organização Principal'")
        ).scalar()
        conn.execute(
            text(
                "INSERT INTO projects (organization_id, name, legacy_project_name, created_at) "
                "VALUES (:o, 'Multilift', 'Multilift', CURRENT_TIMESTAMP)"
            ),
            {"o": org_id},
        )

    _alembic(env, "upgrade", "head")

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT organization_id, code, program_id, legacy_project_name "
                "FROM projects WHERE name = 'Multilift'"
            )
        ).fetchall()
    assert len(rows) == 2  # one per organization -- the legacy row was reused, not tripled
    attached = next(row for row in rows if row.legacy_project_name == "Multilift")
    assert attached.code == "PJ-001"
    assert attached.program_id is not None


def test_0008_is_idempotent_and_downgrade_preserves_legacy_rows(tmp_path):
    env, database_url = _env(tmp_path, "m0008_roundtrip.db")
    _alembic(env, "upgrade", "0007")
    engine = create_engine(database_url)

    with engine.begin() as conn:
        org_id = conn.execute(
            text("SELECT id FROM organizations WHERE name = 'Organização Principal'")
        ).scalar()
        conn.execute(
            text(
                "INSERT INTO projects (organization_id, name, legacy_project_name, created_at) "
                "VALUES (:o, 'Aurora', 'Aurora', CURRENT_TIMESTAMP)"
            ),
            {"o": org_id},
        )

    _alembic(env, "upgrade", "head")
    _alembic(env, "downgrade", "0007")

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM portfolios")).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM programs")).scalar() == 0
        # The legacy Aurora row survives, stripped of its domain fields.
        rows = conn.execute(
            text("SELECT name, code, program_id FROM projects WHERE name = 'Aurora'")
        ).fetchall()
        assert len(rows) == 1
        assert rows[0].code is None
        assert rows[0].program_id is None

    _alembic(env, "upgrade", "head")  # re-upgrade after downgrade works (idempotency)
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT COUNT(*) FROM projects WHERE name = 'Aurora'")).scalar()
            == 2  # legacy row re-attached + demo-org copy, never a third
        )
