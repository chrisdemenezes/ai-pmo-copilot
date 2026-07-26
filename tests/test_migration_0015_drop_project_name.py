"""Migration 0015 (TD-008 Fase 3b, Etapa 4b) -- STAGED, destructive drop of
analysis_records.project_name + NOT NULL on project_id.

This proves the staged 0015 migration (in `alembic/versions_pending/`, NOT on
the live chain) upgrades AND downgrades reversibly on real PostgreSQL, so the
Founder can approve Etapa 4b with the irreversible step already validated. The
live `alembic upgrade head` stays at 0014 (the column is preserved); this test
opts the pending directory into `version_locations` only for its own run.
"""
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.db import temp_database_url


def _staged_config() -> Config:
    cfg = Config("alembic.ini")
    root = os.getcwd()
    versions = os.path.join(root, "alembic", "versions")
    pending = os.path.join(root, "alembic", "versions_pending")
    # Opt the pending directory in ONLY here, so 0015 becomes head for this
    # test alone; the app/other tests keep the default (versions/ -> 0014).
    cfg.set_main_option("path_separator", "space")
    cfg.set_main_option("version_locations", f"{versions} {pending}")
    return cfg


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


def test_0015_upgrade_drops_column_and_downgrade_restores_it():
    with temp_database_url("migration_0015") as database_url:
        previous = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = database_url  # env.py resolves the URL from here
        try:
            cfg = _staged_config()
            engine = create_engine(database_url)

            # Bring the DB to 0014 (live head): column present, project_id nullable.
            command.upgrade(cfg, "0014")
            with engine.connect() as conn:
                assert _column_exists(conn) is True
                assert _project_id_nullable(conn) is True

            # Upgrade to the staged 0015: column gone, project_id NOT NULL.
            command.upgrade(cfg, "0015")
            with engine.connect() as conn:
                assert _column_exists(conn) is False
                assert _project_id_nullable(conn) is False

            # Downgrade back to 0014: fully reversible -- column and its
            # nullable project_id return.
            command.downgrade(cfg, "0014")
            with engine.connect() as conn:
                assert _column_exists(conn) is True
                assert _project_id_nullable(conn) is True

            engine.dispose()
        finally:
            if previous is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous
