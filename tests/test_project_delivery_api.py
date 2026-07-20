"""Enterprise Domain API -- Project Delivery routes (Wave 2, Sprint 2)."""
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
    repo = AnalysisRepository(database_url=f"sqlite:///{tmp_path / 'project_delivery_api.db'}")
    app.dependency_overrides[portfolio_routes.build_domain_service] = lambda: DomainService(repo)
    yield TestClient(app), repo
    app.dependency_overrides.pop(portfolio_routes.build_domain_service, None)


def _make_program(repo, org_id: int) -> int:
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")
    return repo.domain.create_program(portfolio_id, "Programa A", "PG-A")


def test_create_project_delivery_with_value_objects(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    program_id = _make_program(repo, org_id)

    response = test_client.post(
        "/api/projects-delivery",
        headers=_headers(org_id),
        json={
            "program_id": program_id,
            "name": "Multilift",
            "code": "PJ-001",
            "health": "red",
            "owner": {"name": "Bruno Castro", "role": "Product Owner"},
            "milestones": [{"name": "Diagnóstico concluído", "dueDate": "2025-11-01", "status": "Concluído"}],
            "team": {"size": 8, "leadName": "Fernanda Lima"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Multilift"
    assert body["program_id"] == program_id
    assert body["health"] == "red"
    assert body["owner"] == {"name": "Bruno Castro", "role": "Product Owner"}
    assert body["milestones"] == [
        {"name": "Diagnóstico concluído", "dueDate": "2025-11-01", "status": "Concluído"}
    ]
    assert body["team"] == {"size": 8, "leadName": "Fernanda Lima"}


def test_create_project_under_program_from_another_org_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    program_b = _make_program(repo, org_b)

    response = test_client.post(
        "/api/projects-delivery",
        headers=_headers(org_a),
        json={"program_id": program_b, "name": "X"},
    )
    assert response.status_code == 404


def test_list_projects_delivery_filtered_by_program(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")
    program_1 = repo.domain.create_program(portfolio_id, "Programa 1", "PG-1")
    program_2 = repo.domain.create_program(portfolio_id, "Programa 2", "PG-2")
    repo.domain.create_project_with_domain(org_id, program_1, "Projeto 1")
    repo.domain.create_project_with_domain(org_id, program_2, "Projeto 2")

    response = test_client.get(
        "/api/projects-delivery", headers=_headers(org_id), params={"program_id": program_1}
    )
    assert response.status_code == 200
    assert [p["name"] for p in response.json()] == ["Projeto 1"]


def test_list_projects_delivery_excludes_legacy_projects_without_a_program(client):
    """A plain Épico-1 Project (no program_id) is not part of this API's
    surface until attach_project_to_program() links it (TD-008, Fase 2)."""
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    program_id = _make_program(repo, org_id)
    repo.domain.create_project_with_domain(org_id, program_id, "Projeto Domain")
    repo.enterprise.create_project(org_id, "Projeto Legado")  # no program_id

    response = test_client.get("/api/projects-delivery", headers=_headers(org_id))

    assert response.status_code == 200
    assert [p["name"] for p in response.json()] == ["Projeto Domain"]


def test_list_projects_delivery_with_program_from_another_org_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    program_b = _make_program(repo, org_b)

    response = test_client.get(
        "/api/projects-delivery", headers=_headers(org_a), params={"program_id": program_b}
    )
    assert response.status_code == 404


def test_get_project_delivery_from_another_organization_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    program_b = _make_program(repo, org_b)
    project_b = repo.domain.create_project_with_domain(org_b, program_b, "Projeto B")

    response = test_client.get(f"/api/projects-delivery/{project_b}", headers=_headers(org_a))
    assert response.status_code == 404


def test_attach_legacy_project_makes_it_visible_in_the_api(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    program_id = _make_program(repo, org_id)
    legacy_id = repo.enterprise.create_project(org_id, "Projeto Legado")

    repo.domain.attach_project_to_program(legacy_id, program_id, code="PJ-LEGACY")

    response = test_client.get(f"/api/projects-delivery/{legacy_id}", headers=_headers(org_id))
    assert response.status_code == 200
    assert response.json()["code"] == "PJ-LEGACY"
