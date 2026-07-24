"""Migration 0012 (Sessions, item 5 -- resolves TD-010) -- table shape +
sessions.manage permission seeded to organization_admin only."""
import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text

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
    return result


def test_0012_creates_sessions_table_and_seeds_permission():
    with temp_database_url("migration_0012") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url

        _alembic(env, "upgrade", "head")
        engine = create_engine(database_url)

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("sessions")}
        assert columns == {
            "id",
            "user_id",
            "organization_id",
            "created_at",
            "last_seen_at",
            "revoked_at",
        }

        with engine.connect() as conn:
            permission_id = conn.execute(
                text("SELECT id FROM permissions WHERE name = 'sessions.manage'")
            ).scalar()
            assert permission_id is not None

            role_names = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT r.name FROM roles r "
                        "JOIN role_permissions rp ON rp.role_id = r.id "
                        "WHERE rp.permission_id = :p"
                    ),
                    {"p": permission_id},
                )
            }
            assert role_names == {"organization_admin"}


def test_0012_downgrade_removes_table_and_permission():
    with temp_database_url("migration_0012_downgrade") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url

        _alembic(env, "upgrade", "head")
        _alembic(env, "downgrade", "0011")

        engine = create_engine(database_url)
        inspector = inspect(engine)
        assert "sessions" not in inspector.get_table_names()

        with engine.connect() as conn:
            permission_id = conn.execute(
                text("SELECT id FROM permissions WHERE name = 'sessions.manage'")
            ).scalar()
            assert permission_id is None
