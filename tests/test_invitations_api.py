"""Convites (Invitations) API (item 6 -- D-054): admin CRUD under
`invitations.manage`, plus the public token-authenticated preview/accept
flow that requires no session."""
import os
import subprocess
import sys

import pytest

from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import invitations as invitations_routes
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.administration_service import AdministrationService
from src.services.authorization.checker import SqlPermissionChecker
from src.services.notifications.noop_provider import NoOpNotificationProvider

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


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


@pytest.fixture()
def client():
    with temp_database_url("invitations_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

        repo = AnalysisRepository(database_url=database_url)
        app.dependency_overrides[invitations_routes.build_invitation_service] = (
            lambda: AdministrationService(repo, notification_provider=NoOpNotificationProvider())
        )
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        try:
            yield TestClient(app), repo
        finally:
            app.dependency_overrides.pop(invitations_routes.build_invitation_service, None)
            app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


class TestAdminManagement:
    def test_create_returns_201_with_plaintext_token_once(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/admin/invitations",
            headers=_headers(org_id, admin_id),
            json={"email": "invitee@example.com", "role_name": "viewer"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["plaintext_token"].startswith("inv_")
        assert body["status"] == "pending"
        assert body["email"] == "invitee@example.com"

    def test_create_with_unknown_role_is_400(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/admin/invitations",
            headers=_headers(org_id, admin_id),
            json={"email": "a@b.com", "role_name": "not_a_role"},
        )
        assert response.status_code == 400

    def test_list_never_exposes_hashed_token(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        test_client.post(
            "/api/admin/invitations",
            headers=_headers(org_id, admin_id),
            json={"email": "a@b.com", "role_name": "viewer"},
        )

        response = test_client.get("/api/admin/invitations", headers=_headers(org_id, admin_id))
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 1
        assert "hashed_token" not in rows[0]
        assert "plaintext_token" not in rows[0]

    def test_cancel_returns_200_with_body(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        created = test_client.post(
            "/api/admin/invitations",
            headers=_headers(org_id, admin_id),
            json={"email": "a@b.com", "role_name": "viewer"},
        ).json()

        response = test_client.delete(
            f"/api/admin/invitations/{created['id']}", headers=_headers(org_id, admin_id)
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_unknown_is_404(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        response = test_client.delete(
            "/api/admin/invitations/999999", headers=_headers(org_id, admin_id)
        )
        assert response.status_code == 404

    def test_viewer_without_permission_gets_403(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, role="viewer")

        response = test_client.post(
            "/api/admin/invitations",
            headers=_headers(org_id, viewer_id),
            json={"email": "a@b.com", "role_name": "viewer"},
        )
        assert response.status_code == 403

    def test_list_is_scoped_to_organization(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        admin_a = _actor(repo, org_a)
        org_b = repo.enterprise.create_organization("Org B")
        admin_b = _actor(repo, org_b)
        test_client.post(
            "/api/admin/invitations",
            headers=_headers(org_a, admin_a),
            json={"email": "a@b.com", "role_name": "viewer"},
        )

        response_b = test_client.get("/api/admin/invitations", headers=_headers(org_b, admin_b))
        assert response_b.json() == []


class TestPublicFlow:
    def _create(self, test_client, repo, org_id, admin_id, email="new@example.com"):
        return test_client.post(
            "/api/admin/invitations",
            headers=_headers(org_id, admin_id),
            json={"email": email, "role_name": "viewer"},
        ).json()

    def test_preview_requires_no_session(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Acme")
        admin_id = _actor(repo, org_id)
        created = self._create(test_client, repo, org_id, admin_id)

        # No X-Stratech-* headers at all -- the token is the authorization.
        response = test_client.get(f"/api/invitations/{created['plaintext_token']}")
        assert response.status_code == 200
        body = response.json()
        assert body["organization_name"] == "Acme"
        assert body["role_name"] == "viewer"
        assert body["status"] == "pending"

    def test_preview_invalid_token_is_404(self, client):
        test_client, _ = client
        assert test_client.get("/api/invitations/inv_bogus").status_code == 404

    def test_accept_creates_account_without_a_session(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Acme")
        admin_id = _actor(repo, org_id)
        created = self._create(test_client, repo, org_id, admin_id)

        response = test_client.post(
            "/api/invitations/accept",
            json={
                "token": created["plaintext_token"],
                "display_name": "New Person",
                "password": "a-strong-password",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["organization_id"] == org_id
        assert isinstance(body["user_id"], int)

    def test_accept_invalid_token_is_404(self, client):
        test_client, _ = client
        response = test_client.post(
            "/api/invitations/accept",
            json={"token": "inv_bogus", "display_name": "X", "password": "pw-123456"},
        )
        assert response.status_code == 404

    def test_accept_twice_is_404_the_second_time(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Acme")
        admin_id = _actor(repo, org_id)
        created = self._create(test_client, repo, org_id, admin_id)
        payload = {
            "token": created["plaintext_token"],
            "display_name": "First",
            "password": "pw-123456",
        }
        assert test_client.post("/api/invitations/accept", json=payload).status_code == 200
        assert test_client.post("/api/invitations/accept", json=payload).status_code == 404
