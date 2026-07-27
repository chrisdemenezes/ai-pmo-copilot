"""Migration 0017 -- Enterprise Memory Model (Wave 3 Fase 2). Purely
additive: creates `memory_records`, referencing an already-ingested
`documents` row. Proven on real PostgreSQL -- upgrade creates the table,
downgrade removes it, and a re-upgrade round-trips cleanly.
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
    )
    assert result.returncode == 0, result.stderr


def _table_exists(conn, table_name: str) -> bool:
    return conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table_name},
    ).scalar() is not None


def test_0017_upgrade_creates_table_and_downgrade_removes_it():
    with temp_database_url("migration_0017") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        engine = create_engine(database_url)

        _alembic(env, "upgrade", "0016")
        with engine.connect() as conn:
            assert _table_exists(conn, "memory_records") is False

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _table_exists(conn, "memory_records") is True

            org_id = conn.execute(
                text(
                    "INSERT INTO organizations (name, slug, created_at) "
                    "VALUES ('Org A', 'org-a', now()) RETURNING id"
                )
            ).scalar()
            document_id = conn.execute(
                text(
                    "INSERT INTO documents (organization_id, source_name, created_at) "
                    "VALUES (:o, 'decision-log.md', now()) RETURNING id"
                ),
                {"o": org_id},
            ).scalar()
            record_id = conn.execute(
                text(
                    "INSERT INTO memory_records (organization_id, document_id, category, created_at) "
                    "VALUES (:o, :d, 'decisoes', now()) RETURNING id"
                ),
                {"o": org_id, "d": document_id},
            ).scalar()
            assert record_id is not None

        _alembic(env, "downgrade", "0016")
        with engine.connect() as conn:
            assert _table_exists(conn, "memory_records") is False
            # Fase 1 tables untouched by this downgrade.
            assert _table_exists(conn, "documents") is True

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _table_exists(conn, "memory_records") is True

        engine.dispose()
