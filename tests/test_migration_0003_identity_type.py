"""Migration 0003 (identity_type on users) -- additive column, backfill, and
reversibility (TDS Epic 2, Section 11)."""
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


def test_0003_adds_identity_type_with_backfilled_default():
    with temp_database_url("migration_0003") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url

        _alembic(env, "upgrade", "0002")
        engine = create_engine(database_url)

        # A user created on the pre-0003 schema (organizations/users already
        # exist from 0002's seed) must be backfilled to "standard" by 0003.
        with engine.begin() as conn:
            org_id = conn.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
            conn.execute(
                text(
                    "INSERT INTO users (organization_id, email, display_name, created_at) "
                    "VALUES (:o, 'pre-existing@example.com', 'Pre Existing', CURRENT_TIMESTAMP)"
                ),
                {"o": org_id},
            )

        _alembic(env, "upgrade", "0003")

        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("users")}
        assert "identity_type" in columns
        assert not columns["identity_type"]["nullable"]

        with engine.connect() as conn:
            value = conn.execute(
                text(
                    "SELECT identity_type FROM users WHERE email = 'pre-existing@example.com'"
                )
            ).scalar()
        assert value == "standard"


def test_0003_downgrade_removes_the_column_and_is_lossless_otherwise():
    with temp_database_url("migration_0003_downgrade") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url

        _alembic(env, "upgrade", "head")
        engine = create_engine(database_url)

        with engine.begin() as conn:
            org_id = conn.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
            conn.execute(
                text(
                    "INSERT INTO users "
                    "(organization_id, email, display_name, identity_type, created_at) "
                    "VALUES (:o, 'someone@example.com', 'Someone', 'demo', CURRENT_TIMESTAMP)"
                ),
                {"o": org_id},
            )

        _alembic(env, "downgrade", "0002")

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        assert "identity_type" not in columns

        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE email = 'someone@example.com'")
            ).scalar()
        assert count == 1  # the row itself survives; only the column is gone

        _alembic(env, "upgrade", "head")  # full round trip works
