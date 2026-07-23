"""Migration 0009 (User Management) -- is_active column and case-insensitive
email uniqueness enforced at the database."""
import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

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


def test_0009_adds_is_active_defaulting_true_for_existing_rows():
    with temp_database_url("migration_0009") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url

        _alembic(env, "upgrade", "0008")
        engine = create_engine(database_url)

        with engine.begin() as conn:
            org_id = conn.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
            conn.execute(
                text(
                    "INSERT INTO users (organization_id, email, display_name, "
                    "identity_type, created_at) VALUES "
                    "(:o, 'pre-existing@example.com', 'Pre Existing', 'standard', "
                    "CURRENT_TIMESTAMP)"
                ),
                {"o": org_id},
            )

        _alembic(env, "upgrade", "0009")

        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("users")}
        assert "is_active" in columns
        assert not columns["is_active"]["nullable"]

        with engine.connect() as conn:
            value = conn.execute(
                text("SELECT is_active FROM users WHERE email = 'pre-existing@example.com'")
            ).scalar()
        assert value is True


def test_0009_enforces_case_insensitive_email_uniqueness_per_organization():
    with temp_database_url("migration_0009_email") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")
        engine = create_engine(database_url)

        with engine.begin() as conn:
            org_id = conn.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
            conn.execute(
                text(
                    "INSERT INTO users (organization_id, email, display_name, "
                    "identity_type, created_at) VALUES "
                    "(:o, 'Ana@Example.com', 'Ana', 'standard', CURRENT_TIMESTAMP)"
                ),
                {"o": org_id},
            )

        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO users (organization_id, email, display_name, "
                        "identity_type, created_at) VALUES "
                        "(:o, 'ana@example.com', 'Ana Duplicate', 'standard', "
                        "CURRENT_TIMESTAMP)"
                    ),
                    {"o": org_id},
                )
            raised = False
        except IntegrityError:
            raised = True
        assert raised, "case-variant duplicate email should violate the unique index"

        # A different organization may reuse the same email (organization-scoped).
        with engine.begin() as conn:
            other_org_id = conn.execute(
                text(
                    "INSERT INTO organizations (name, slug, created_at) VALUES "
                    "('Org B', 'org-b', CURRENT_TIMESTAMP) RETURNING id"
                )
            ).scalar()
            conn.execute(
                text(
                    "INSERT INTO users (organization_id, email, display_name, "
                    "identity_type, created_at) VALUES "
                    "(:o, 'ana@example.com', 'Ana Org B', 'standard', CURRENT_TIMESTAMP)"
                ),
                {"o": other_org_id},
            )
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE lower(email) = 'ana@example.com'")
            ).scalar()
        assert count == 2


def test_0009_downgrade_removes_is_active_and_restores_case_sensitive_constraint():
    with temp_database_url("migration_0009_downgrade") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")
        engine = create_engine(database_url)

        _alembic(env, "downgrade", "0008")

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        assert "is_active" not in columns

        # The original case-sensitive constraint is back -- case-variant
        # emails are no longer rejected by the database. Cleaned up before
        # re-upgrading: a functional unique index cannot be created over
        # data that already violates it, which is the correct, documented
        # behavior (this migration's own docstring), not tested here.
        with engine.begin() as conn:
            org_id = conn.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
            conn.execute(
                text(
                    "INSERT INTO users (organization_id, email, display_name, "
                    "identity_type, created_at) VALUES "
                    "(:o, 'Case@Example.com', 'Case', 'standard', CURRENT_TIMESTAMP)"
                ),
                {"o": org_id},
            )
            conn.execute(
                text(
                    "INSERT INTO users (organization_id, email, display_name, "
                    "identity_type, created_at) VALUES "
                    "(:o, 'case@example.com', 'Case Variant', 'standard', "
                    "CURRENT_TIMESTAMP)"
                ),
                {"o": org_id},
            )
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM users WHERE email = 'case@example.com'"))

        _alembic(env, "upgrade", "head")  # full round trip works on clean data
