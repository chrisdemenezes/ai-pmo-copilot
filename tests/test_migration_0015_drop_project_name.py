"""Migration 0015 (TD-008 Fase 3b, Etapa 4b) -- destructive drop of
analysis_records.project_name + NOT NULL on project_id, with an integral
downgrade (Founder Condição 2).

Proven on real PostgreSQL:
- upgrade: the column is dropped and project_id becomes NOT NULL;
- downgrade: the column is recreated AND repopulated from projects.name via
  project_id (never an empty column), so a prior application version that
  reads analysis_records.project_name operates over real display names.
"""
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
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _column_exists(conn) -> bool:
    return conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'analysis_records' AND column_name = 'project_name'"
        )
    ).scalar() is not None


def _project_id_nullable(conn) -> bool:
    return conn.execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'analysis_records' AND column_name = 'project_id'"
        )
    ).scalar() == "YES"


def test_0015_upgrade_drops_column_and_downgrade_restores_data():
    with temp_database_url("migration_0015") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        engine = create_engine(database_url)

        # Bring the DB to 0014 (column present, project_id nullable) and seed a
        # real row: an organization, a Project named "Aurora", and an analysis
        # linked to it (project_id set; the raw project_name is irrelevant --
        # it is dropped and repopulated from projects.name on downgrade).
        _alembic(env, "upgrade", "0014")
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
            analysis_id = conn.execute(
                text(
                    "INSERT INTO analysis_records "
                    "(kind, project_name, project_id, organization_id, payload, created_at) "
                    "VALUES ('meeting', 'raw-input-name', :p, :o, '{}', now()) RETURNING id"
                ),
                {"p": project_id, "o": org_id},
            ).scalar()

        with engine.connect() as conn:
            assert _column_exists(conn) is True
            assert _project_id_nullable(conn) is True

        # Upgrade to 0015 (head): column dropped, project_id NOT NULL.
        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _column_exists(conn) is False
            assert _project_id_nullable(conn) is False
            # Data preserved by identity: the row and its Project link survive.
            linked = conn.execute(
                text("SELECT project_id FROM analysis_records WHERE id = :i"),
                {"i": analysis_id},
            ).scalar()
            assert linked == project_id

        # Downgrade to 0014: integral rollback -- the column returns AND is
        # repopulated from projects.name (Founder Condição 2), so a prior app
        # version reading the column gets the real display name.
        _alembic(env, "downgrade", "0014")
        with engine.connect() as conn:
            assert _column_exists(conn) is True
            assert _project_id_nullable(conn) is True
            restored = conn.execute(
                text("SELECT project_name FROM analysis_records WHERE id = :i"),
                {"i": analysis_id},
            ).scalar()
            # NOT the empty column, NOT the raw input -- the Project's real name.
            assert restored == "Aurora"

        engine.dispose()
