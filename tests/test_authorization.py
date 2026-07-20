"""SqlPermissionChecker (Wave 2, Sprint 3; `DOMAIN-BLUEPRINT-RBAC.md`).

Seeds 2 users with different roles against the real migration 0006
permission catalog and asserts has_permission() per (user, permission)
pair -- same convention `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4.12
described.
"""
import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.authorization.checker import SqlPermissionChecker


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


@pytest.fixture()
def migrated_session_factory(tmp_path):
    db_path = tmp_path / "authorization.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    _alembic(env, "upgrade", "head")

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _create_user_with_role(session_factory, role_name: str) -> int:
    with session_factory() as session:
        from sqlalchemy import text

        org_id = session.execute(
            text(
                "INSERT INTO organizations (name, slug, created_at) "
                "VALUES ('Org', 'org', CURRENT_TIMESTAMP) RETURNING id"
            )
        ).scalar()
        user_id = session.execute(
            text(
                "INSERT INTO users (organization_id, email, display_name, identity_type, created_at) "
                "VALUES (:org_id, :email, 'User', 'standard', CURRENT_TIMESTAMP) RETURNING id"
            ),
            {"org_id": org_id, "email": f"{role_name}@example.com"},
        ).scalar()
        role_id = session.execute(
            text("SELECT id FROM roles WHERE name = :n"), {"n": role_name}
        ).scalar()
        session.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
            {"u": user_id, "r": role_id},
        )
        session.commit()
        return user_id


def test_viewer_has_read_but_not_write(migrated_session_factory):
    checker = SqlPermissionChecker(migrated_session_factory)
    viewer_id = _create_user_with_role(migrated_session_factory, "viewer")

    assert checker.has_permission(viewer_id, "portfolio.read") is True
    assert checker.has_permission(viewer_id, "portfolio.write") is False
    assert checker.has_permission(viewer_id, "program.read") is True
    assert checker.has_permission(viewer_id, "project_delivery.read") is True


def test_organization_admin_has_full_access(migrated_session_factory):
    checker = SqlPermissionChecker(migrated_session_factory)
    admin_id = _create_user_with_role(migrated_session_factory, "organization_admin")

    for permission in (
        "portfolio.read",
        "portfolio.write",
        "program.read",
        "program.write",
        "project_delivery.read",
        "project_delivery.write",
    ):
        assert checker.has_permission(admin_id, permission) is True


def test_project_manager_cannot_write_portfolio(migrated_session_factory):
    """project_manager governs Program/Project execution, not
    Portfolio-level strategy (migration 0006's role assignment)."""
    checker = SqlPermissionChecker(migrated_session_factory)
    pm_id = _create_user_with_role(migrated_session_factory, "project_manager")

    assert checker.has_permission(pm_id, "portfolio.read") is True
    assert checker.has_permission(pm_id, "portfolio.write") is False
    assert checker.has_permission(pm_id, "program.write") is True
    assert checker.has_permission(pm_id, "project_delivery.write") is True


def test_user_with_no_role_has_no_permissions(migrated_session_factory):
    checker = SqlPermissionChecker(migrated_session_factory)
    with migrated_session_factory() as session:
        from sqlalchemy import text

        org_id = session.execute(
            text(
                "INSERT INTO organizations (name, slug, created_at) "
                "VALUES ('Org2', 'org2', CURRENT_TIMESTAMP) RETURNING id"
            )
        ).scalar()
        user_id = session.execute(
            text(
                "INSERT INTO users (organization_id, email, display_name, identity_type, created_at) "
                "VALUES (:org_id, 'norole@example.com', 'No Role', 'standard', CURRENT_TIMESTAMP) "
                "RETURNING id"
            ),
            {"org_id": org_id},
        ).scalar()
        session.commit()

    assert checker.has_permission(user_id, "portfolio.read") is False


def test_unknown_user_id_has_no_permissions(migrated_session_factory):
    checker = SqlPermissionChecker(migrated_session_factory)
    assert checker.has_permission(999999, "portfolio.read") is False
