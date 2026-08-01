"""Migration 0020 -- Wave 5, Epic W5-0 (Document Ingestion). Purely
additive: seeds `knowledge.read`/`knowledge.write` permissions (no new
table -- `documents`/`document_versions`/`chunks` already exist since
migration 0016). Proven on real PostgreSQL -- upgrade seeds the
permissions for the 4 roles per the Technical Design, downgrade removes
them, and a re-upgrade round-trips cleanly.
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


def _permission_role_names(conn, permission_name: str) -> set[str]:
    rows = conn.execute(
        text(
            "SELECT r.name FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE p.name = :n"
        ),
        {"n": permission_name},
    ).all()
    return {row[0] for row in rows}


def test_0020_upgrade_seeds_permissions_and_downgrade_removes_them():
    with temp_database_url("migration_0020") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        engine = create_engine(database_url)

        _alembic(env, "upgrade", "0019")
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM permissions WHERE name IN ('knowledge.read', 'knowledge.write')")
            ).first()
            assert exists is None

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _permission_role_names(conn, "knowledge.read") == {
                "organization_admin",
                "pmo",
                "project_manager",
                "viewer",
            }
            assert _permission_role_names(conn, "knowledge.write") == {
                "organization_admin",
                "pmo",
                "project_manager",
            }

        _alembic(env, "downgrade", "0019")
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM permissions WHERE name IN ('knowledge.read', 'knowledge.write')")
            ).first()
            assert exists is None

        # Re-upgrade round-trips cleanly, no duplicate rows.
        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM permissions WHERE name IN ('knowledge.read', 'knowledge.write')")
            ).scalar()
            assert count == 2
