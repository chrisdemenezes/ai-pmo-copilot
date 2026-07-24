"""Migration 0014 (TD-008 Phase 3b, Etapa 1) -- defensive re-backfill of
analysis_records.project_id. Idempotent, non-destructive, no NOT NULL."""
import os
import subprocess
import sys

from sqlalchemy import create_engine, text

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


def test_0014_backfills_null_project_id_from_matching_project():
    with temp_database_url("migration_0014") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        # Migrate up to 0013 (before the backfill), then seed a NULL-linked row.
        _alembic(env, "upgrade", "0013")
        engine = create_engine(database_url)
        with engine.begin() as conn:
            org_id = conn.execute(
                text(
                    "INSERT INTO organizations (name, slug, created_at) "
                    "VALUES ('Org A', 'org-a', now()) RETURNING id"
                )
            ).scalar()
            project_id = conn.execute(
                text(
                    "INSERT INTO projects (organization_id, name, created_at) "
                    "VALUES (:o, 'Aurora', now()) RETURNING id"
                ),
                {"o": org_id},
            ).scalar()
            # An analysis row deliberately left with project_id NULL.
            analysis_id = conn.execute(
                text(
                    "INSERT INTO analysis_records "
                    "(kind, project_name, project_id, organization_id, payload, created_at) "
                    "VALUES ('meeting', 'Aurora', NULL, :o, '{}', now()) RETURNING id"
                ),
                {"o": org_id},
            ).scalar()

        # Apply 0014 -- the defensive backfill.
        _alembic(env, "upgrade", "head")

        with engine.connect() as conn:
            linked = conn.execute(
                text("SELECT project_id FROM analysis_records WHERE id = :i"),
                {"i": analysis_id},
            ).scalar()
            assert linked == project_id

        # Idempotent: a second run changes nothing (already linked).
        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            still = conn.execute(
                text("SELECT project_id FROM analysis_records WHERE id = :i"),
                {"i": analysis_id},
            ).scalar()
            assert still == project_id


def test_0014_downgrade_is_a_noop_and_reversible():
    with temp_database_url("migration_0014_down") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")
        # Downgrade to 0013 and back up -- no schema change, must not error.
        _alembic(env, "downgrade", "0013")
        _alembic(env, "upgrade", "head")
