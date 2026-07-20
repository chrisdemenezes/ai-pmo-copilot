"""Enterprise Domain API -- Program routes (Wave 2, Sprint 2)."""
import pytest
from fastapi.testclient import TestClient

from src.api.routes import portfolio as portfolio_routes
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
    repo = AnalysisRepository(database_url=f"sqlite:///{tmp_path / 'program_api.db'}")
    app.dependency_overrides[portfolio_routes.build_domain_service] = lambda: DomainService(repo)
    yield TestClient(app), repo
    app.dependency_overrides.pop(portfolio_routes.build_domain_service, None)


def test_create_and_get_program(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")

    create_response = test_client.post(
        "/api/programs",
        headers=_headers(org_id),
        json={"portfolio_id": portfolio_id, "name": "Programa A", "code": "PG-A"},
    )
    assert create_response.status_code == 201
    program_id = create_response.json()["id"]
    assert create_response.json()["portfolio_id"] == portfolio_id

    get_response = test_client.get(f"/api/programs/{program_id}", headers=_headers(org_id))
    assert get_response.status_code == 200
    assert get_response.json()["code"] == "PG-A"


def test_create_program_under_a_portfolio_from_another_org_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")

    response = test_client.post(
        "/api/programs",
        headers=_headers(org_a),
        json={"portfolio_id": portfolio_b, "name": "X", "code": "PG-X"},
    )
    assert response.status_code == 404


def test_list_programs_filtered_by_portfolio(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    portfolio_1 = repo.domain.create_portfolio(org_id, "Portfólio 1", "PF-1")
    portfolio_2 = repo.domain.create_portfolio(org_id, "Portfólio 2", "PF-2")
    repo.domain.create_program(portfolio_1, "Programa 1", "PG-1")
    repo.domain.create_program(portfolio_2, "Programa 2", "PG-2")

    response = test_client.get(
        "/api/programs", headers=_headers(org_id), params={"portfolio_id": portfolio_1}
    )
    assert response.status_code == 200
    assert [p["code"] for p in response.json()] == ["PG-1"]


def test_list_programs_without_filter_returns_all_in_organization(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")
    repo.domain.create_program(portfolio_id, "Programa 1", "PG-1")
    repo.domain.create_program(portfolio_id, "Programa 2", "PG-2")

    response = test_client.get("/api/programs", headers=_headers(org_id))
    assert response.status_code == 200
    assert {p["code"] for p in response.json()} == {"PG-1", "PG-2"}


def test_list_programs_with_portfolio_from_another_org_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")

    response = test_client.get(
        "/api/programs", headers=_headers(org_a), params={"portfolio_id": portfolio_b}
    )
    assert response.status_code == 404


def test_get_program_from_another_organization_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")
    program_b = repo.domain.create_program(portfolio_b, "Programa B", "PG-B")

    response = test_client.get(f"/api/programs/{program_b}", headers=_headers(org_a))
    assert response.status_code == 404
