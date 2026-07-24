"""Item 5 (resolves TD-010) -- proves that revoking a session actually
blocks its next request through `require_permission`, on an existing,
unmodified route (`GET /admin/organization`).

conftest's autouse fixture defaults `build_session_revocation_checker` to
"never revoked" for the whole suite (the other ~12 API test modules use
fabricated session ids that were never in any store). This module is the
one that overrides it with the real DB-backed checker, bound to the same
temp database its sessions live in, to exercise the enforcement path end to
end.
"""
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import administration as administration_routes
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.administration_service import AdministrationService
from src.services.authorization.checker import SqlPermissionChecker

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


def _headers(organization_id: int, user_id: int, session_id: str) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": session_id,
    }


@pytest.fixture()
def client():
    with temp_database_url("session_revocation") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

        repo = AnalysisRepository(database_url=database_url)
        app.dependency_overrides[administration_routes.build_administration_service] = (
            lambda: AdministrationService(repo)
        )
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        # Override conftest's "never revoked" default with the real checker
        # bound to this temp DB, so revocation is genuinely enforced here.
        app.dependency_overrides[authorization_module.build_session_revocation_checker] = (
            lambda: repo.administration.is_session_revoked
        )
        try:
            yield TestClient(app), repo
        finally:
            app.dependency_overrides.pop(
                administration_routes.build_administration_service, None
            )
            app.dependency_overrides.pop(authorization_module.build_permission_checker, None)
            app.dependency_overrides.pop(
                authorization_module.build_session_revocation_checker, None
            )


def _admin(repo, organization_id: int) -> int:
    user_id = repo.enterprise.create_user(organization_id, "admin@example.com", "Admin")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, "organization_admin")
        session.commit()
    return user_id


def test_active_session_is_allowed(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    admin_id = _admin(repo, org_id)
    repo.administration.create_session("sess-1", admin_id, org_id)

    response = test_client.get(
        "/api/admin/organization", headers=_headers(org_id, admin_id, "sess-1")
    )

    assert response.status_code == 200


def test_revoked_session_is_rejected_with_401_on_its_next_request(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    admin_id = _admin(repo, org_id)
    repo.administration.create_session("sess-1", admin_id, org_id)

    ok = test_client.get(
        "/api/admin/organization", headers=_headers(org_id, admin_id, "sess-1")
    )
    assert ok.status_code == 200

    repo.administration.revoke_session("sess-1")

    after = test_client.get(
        "/api/admin/organization", headers=_headers(org_id, admin_id, "sess-1")
    )
    assert after.status_code == 401
    assert after.json()["detail"] == "Session has been revoked"


def test_an_untracked_session_id_is_treated_as_active(client):
    """A fabricated / pre-store session id (no row at all) must never be
    treated as revoked -- otherwise every session predating this store would
    break the moment enforcement shipped."""
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    admin_id = _admin(repo, org_id)

    response = test_client.get(
        "/api/admin/organization",
        headers=_headers(org_id, admin_id, "never-created-in-store"),
    )

    assert response.status_code == 200
