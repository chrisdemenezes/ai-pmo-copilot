"""Enterprise Domain API -- Portfolio routes (Wave 2, Sprint 2 + Sprint 3 RBAC).

Auth (verify_api_key/enforce_rate_limit) is bypassed by the autouse
conftest fixture, same as every other API test in this suite --
`get_request_context` and RBAC (`require_permission`) are NOT bypassed,
so every request below supplies the 3 institutional headers directly and
uses a real user with a real role, exercising org-scoping and permission
enforcement end to end, against the real migration 0006 permission
catalog (not a hand-rolled seed).
"""
import os
import subprocess
import sys

import pytest

from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import portfolio as portfolio_routes
from src.api.security import verify_api_key
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.domain_service import DomainService

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


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


@pytest.fixture()
def client():
    with temp_database_url("portfolio_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")  # seeds roles + the migration 0006 permission catalog

        repo = AnalysisRepository(database_url=database_url)
        app.dependency_overrides[portfolio_routes.build_domain_service] = lambda: DomainService(repo)
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo
        app.dependency_overrides.pop(portfolio_routes.build_domain_service, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    """Creates a real User in the given organization and assigns it a real
    role from the migration 0002 seed, so permission checks run against
    the actual catalog, not a fixture-only shortcut."""
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


def test_list_portfolios_is_empty_for_a_fresh_organization(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "viewer")

    response = test_client.get("/api/portfolios", headers=_headers(org_id, user_id))

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_portfolio_round_trip(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    admin_id = _actor(repo, org_id, "organization_admin")

    create_response = test_client.post(
        "/api/portfolios",
        headers=_headers(org_id, admin_id),
        json={"name": "Portfólio Corporativo", "code": "PF-001", "sponsor": "CIO"},
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["name"] == "Portfólio Corporativo"
    assert body["code"] == "PF-001"
    assert body["sponsor"] == "CIO"
    assert body["status"] == "Ativo"  # column default applied, not overridden by None
    assert body["health"] == "green"
    assert body["organization_id"] == org_id

    list_response = test_client.get("/api/portfolios", headers=_headers(org_id, admin_id))
    assert list_response.status_code == 200
    assert [p["code"] for p in list_response.json()] == ["PF-001"]


def test_get_portfolio_by_id(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "viewer")
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")

    response = test_client.get(f"/api/portfolios/{portfolio_id}", headers=_headers(org_id, user_id))

    assert response.status_code == 200
    assert response.json()["code"] == "PF-A"


def test_get_portfolio_not_found_returns_404(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "viewer")

    response = test_client.get("/api/portfolios/999999", headers=_headers(org_id, user_id))

    assert response.status_code == 404


class TestOrganizationScoping:
    def test_portfolio_from_another_organization_is_invisible(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")

        # Org A must never see Org B's portfolio, in the list or by direct id.
        list_response = test_client.get("/api/portfolios", headers=_headers(org_a, user_a))
        assert list_response.json() == []

        get_response = test_client.get(
            f"/api/portfolios/{portfolio_b}", headers=_headers(org_a, user_a)
        )
        assert get_response.status_code == 404  # not 403 -- never confirms the id exists


class TestRequestContextRequired:
    def test_missing_institutional_headers_returns_400(self, client):
        test_client, _repo = client
        response = test_client.get("/api/portfolios")
        assert response.status_code == 400


def test_list_portfolios_requires_api_key(client, monkeypatch):
    """The autouse conftest fixture bypasses verify_api_key by default for
    every test in this suite -- this test restores it to prove the
    auth stack is really wired on this router, same check already used
    for /api/risks/latest."""
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "viewer")
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)

    response = test_client.get("/api/portfolios", headers=_headers(org_id, user_id))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


class TestRbacEnforcement:
    def test_viewer_can_read_but_not_write(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        read_response = test_client.get("/api/portfolios", headers=_headers(org_id, viewer_id))
        assert read_response.status_code == 200

        write_response = test_client.post(
            "/api/portfolios",
            headers=_headers(org_id, viewer_id),
            json={"name": "X", "code": "PF-X"},
        )
        assert write_response.status_code == 403
        assert write_response.json()["detail"] == "missing permission: portfolio.write"

    def test_user_with_no_role_is_denied_read(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.get("/api/portfolios", headers=_headers(org_id, user_id))

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: portfolio.read"
