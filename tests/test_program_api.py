"""Enterprise Domain API -- Program routes (Wave 2, Sprint 2 + Sprint 3 RBAC)."""
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import portfolio as portfolio_routes
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.domain_service import DomainService


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
def client(tmp_path):
    db_path = tmp_path / "program_api.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    _alembic(env, "upgrade", "head")

    repo = AnalysisRepository(database_url=database_url)
    app.dependency_overrides[portfolio_routes.build_domain_service] = lambda: DomainService(repo)
    app.dependency_overrides[authorization_module.build_permission_checker] = (
        lambda: SqlPermissionChecker(repo.SessionLocal)
    )
    yield TestClient(app), repo
    app.dependency_overrides.pop(portfolio_routes.build_domain_service, None)
    app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


def test_create_and_get_program(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    admin_id = _actor(repo, org_id, "organization_admin")
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")

    create_response = test_client.post(
        "/api/programs",
        headers=_headers(org_id, admin_id),
        json={"portfolio_id": portfolio_id, "name": "Programa A", "code": "PG-A"},
    )
    assert create_response.status_code == 201
    program_id = create_response.json()["id"]
    assert create_response.json()["portfolio_id"] == portfolio_id

    get_response = test_client.get(
        f"/api/programs/{program_id}", headers=_headers(org_id, admin_id)
    )
    assert get_response.status_code == 200
    assert get_response.json()["code"] == "PG-A"


def test_create_program_under_a_portfolio_from_another_org_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    admin_a = _actor(repo, org_a, "organization_admin")
    portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")

    response = test_client.post(
        "/api/programs",
        headers=_headers(org_a, admin_a),
        json={"portfolio_id": portfolio_b, "name": "X", "code": "PG-X"},
    )
    assert response.status_code == 404


def test_list_programs_filtered_by_portfolio(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "viewer")
    portfolio_1 = repo.domain.create_portfolio(org_id, "Portfólio 1", "PF-1")
    portfolio_2 = repo.domain.create_portfolio(org_id, "Portfólio 2", "PF-2")
    repo.domain.create_program(portfolio_1, "Programa 1", "PG-1")
    repo.domain.create_program(portfolio_2, "Programa 2", "PG-2")

    response = test_client.get(
        "/api/programs", headers=_headers(org_id, user_id), params={"portfolio_id": portfolio_1}
    )
    assert response.status_code == 200
    assert [p["code"] for p in response.json()] == ["PG-1"]


def test_list_programs_without_filter_returns_all_in_organization(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "viewer")
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")
    repo.domain.create_program(portfolio_id, "Programa 1", "PG-1")
    repo.domain.create_program(portfolio_id, "Programa 2", "PG-2")

    response = test_client.get("/api/programs", headers=_headers(org_id, user_id))
    assert response.status_code == 200
    assert {p["code"] for p in response.json()} == {"PG-1", "PG-2"}


def test_list_programs_with_portfolio_from_another_org_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    user_a = _actor(repo, org_a, "viewer")
    portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")

    response = test_client.get(
        "/api/programs", headers=_headers(org_a, user_a), params={"portfolio_id": portfolio_b}
    )
    assert response.status_code == 404


def test_get_program_from_another_organization_returns_404(client):
    test_client, repo = client
    org_a = repo.enterprise.create_organization("Org A")
    org_b = repo.enterprise.create_organization("Org B")
    user_a = _actor(repo, org_a, "viewer")
    portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")
    program_b = repo.domain.create_program(portfolio_b, "Programa B", "PG-B")

    response = test_client.get(f"/api/programs/{program_b}", headers=_headers(org_a, user_a))
    assert response.status_code == 404


class TestRbacEnforcement:
    def test_viewer_cannot_create_program(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")
        portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")

        response = test_client.post(
            "/api/programs",
            headers=_headers(org_id, viewer_id),
            json={"portfolio_id": portfolio_id, "name": "X", "code": "PG-X"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: program.write"

    def test_project_manager_can_create_program(self, client):
        """migration 0006 grants program.write to project_manager (operational
        role), unlike portfolio.write which stays admin/pmo-only."""
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        pm_id = _actor(repo, org_id, "project_manager")
        portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")

        response = test_client.post(
            "/api/programs",
            headers=_headers(org_id, pm_id),
            json={"portfolio_id": portfolio_id, "name": "Programa PM", "code": "PG-PM"},
        )
        assert response.status_code == 201
