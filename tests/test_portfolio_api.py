"""Enterprise Domain API -- Portfolio routes (Wave 2, Sprint 2).

Auth (verify_api_key/enforce_rate_limit) is bypassed by the autouse
conftest fixture, same as every other API test in this suite --
`get_request_context` is NOT bypassed, so every request below supplies
the 3 institutional headers directly, exercising the real org-scoping
path end to end.
"""
import pytest
from fastapi.testclient import TestClient

from src.api.routes import portfolio as portfolio_routes
from src.api.security import verify_api_key
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.domain_service import DomainService


def _headers(organization_id: int, user_id: int = 1) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


@pytest.fixture()
def client(tmp_path):
    repo = AnalysisRepository(database_url=f"sqlite:///{tmp_path / 'portfolio_api.db'}")
    app.dependency_overrides[portfolio_routes.build_domain_service] = lambda: DomainService(repo)
    yield TestClient(app), repo
    app.dependency_overrides.pop(portfolio_routes.build_domain_service, None)


def test_list_portfolios_is_empty_for_a_fresh_organization(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")

    response = test_client.get("/api/portfolios", headers=_headers(org_id))

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_portfolio_round_trip(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")

    create_response = test_client.post(
        "/api/portfolios",
        headers=_headers(org_id),
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

    list_response = test_client.get("/api/portfolios", headers=_headers(org_id))
    assert list_response.status_code == 200
    assert [p["code"] for p in list_response.json()] == ["PF-001"]


def test_get_portfolio_by_id(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")

    response = test_client.get(f"/api/portfolios/{portfolio_id}", headers=_headers(org_id))

    assert response.status_code == 200
    assert response.json()["code"] == "PF-A"


def test_get_portfolio_not_found_returns_404(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")

    response = test_client.get("/api/portfolios/999999", headers=_headers(org_id))

    assert response.status_code == 404


class TestOrganizationScoping:
    def test_portfolio_from_another_organization_is_invisible(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")

        # Org A must never see Org B's portfolio, in the list or by direct id.
        list_response = test_client.get("/api/portfolios", headers=_headers(org_a))
        assert list_response.json() == []

        get_response = test_client.get(
            f"/api/portfolios/{portfolio_b}", headers=_headers(org_a)
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
    "estrutura de autenticação preparada para receber RBAC" is really
    wired on this router, same check already used for /api/risks/latest."""
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)

    response = test_client.get("/api/portfolios", headers=_headers(org_id))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
