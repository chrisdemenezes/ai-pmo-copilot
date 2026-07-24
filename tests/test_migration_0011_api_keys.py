"""Migration 0011 (API Keys, D-051) -- table shape + api_keys.manage
permission seeded to organization_admin only."""
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


def test_0011_creates_api_keys_table_and_seeds_permission():
    with temp_database_url("migration_0011") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url

        _alembic(env, "upgrade", "head")
        engine = create_engine(database_url)

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("api_keys")}
        assert columns == {
            "id",
            "organization_id",
            "created_by_user_id",
            "name",
            "key_prefix",
            "hashed_secret",
            "created_at",
            "last_used_at",
            "revoked_at",
        }

        with engine.connect() as conn:
            permission_id = conn.execute(
                text("SELECT id FROM permissions WHERE name = 'api_keys.manage'")
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


def test_0011_downgrade_removes_table_and_permission():
    with temp_database_url("migration_0011_downgrade") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url

        _alembic(env, "upgrade", "head")
        _alembic(env, "downgrade", "0010")

        engine = create_engine(database_url)
        inspector = inspect(engine)
        assert "api_keys" not in inspector.get_table_names()

        with engine.connect() as conn:
            permission_id = conn.execute(
                text("SELECT id FROM permissions WHERE name = 'api_keys.manage'")
            ).scalar()
            assert permission_id is None
