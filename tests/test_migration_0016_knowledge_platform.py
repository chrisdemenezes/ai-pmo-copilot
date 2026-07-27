"""Migration 0016 -- Enterprise Knowledge Platform Fase 1 (Foundation).

Purely additive: enables the `vector` (pgvector) extension and creates
`documents`, `document_versions`, `chunks`. Proven on real PostgreSQL --
upgrade creates the 3 tables with a working `vector` column, downgrade
removes them (leaving the shared `vector` extension installed), and a
re-upgrade round-trips cleanly.
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


def test_0016_upgrade_creates_tables_and_downgrade_removes_them():
    with temp_database_url("migration_0016") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        engine = create_engine(database_url)

        _alembic(env, "upgrade", "0015")
        with engine.connect() as conn:
            assert _table_exists(conn, "documents") is False
            assert _table_exists(conn, "document_versions") is False
            assert _table_exists(conn, "chunks") is False

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _table_exists(conn, "documents") is True
            assert _table_exists(conn, "document_versions") is True
            assert _table_exists(conn, "chunks") is True
            extension_installed = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            assert extension_installed == 1

            org_id = conn.execute(
                text(
                    "INSERT INTO organizations (name, slug, created_at) "
                    "VALUES ('Org A', 'org-a', now()) RETURNING id"
                )
            ).scalar()
            document_id = conn.execute(
                text(
                    "INSERT INTO documents (organization_id, source_name, created_at) "
                    "VALUES (:o, 'runbook.md', now()) RETURNING id"
                ),
                {"o": org_id},
            ).scalar()
            version_id = conn.execute(
                text(
                    "INSERT INTO document_versions (document_id, content, created_at) "
                    "VALUES (:d, 'hello world', now()) RETURNING id"
                ),
                {"d": document_id},
            ).scalar()
            zero_vector = "[" + ",".join(["0"] * 16) + "]"
            chunk_id = conn.execute(
                text(
                    "INSERT INTO chunks "
                    "(document_version_id, organization_id, chunk_index, text, embedding) "
                    "VALUES (:v, :o, 0, 'hello world', :e) RETURNING id"
                ),
                {"v": version_id, "o": org_id, "e": zero_vector},
            ).scalar()
            assert chunk_id is not None

        _alembic(env, "downgrade", "0015")
        with engine.connect() as conn:
            assert _table_exists(conn, "documents") is False
            assert _table_exists(conn, "document_versions") is False
            assert _table_exists(conn, "chunks") is False
            # The shared extension is never dropped on downgrade.
            extension_installed = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            assert extension_installed == 1

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _table_exists(conn, "chunks") is True

        engine.dispose()
