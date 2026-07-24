"""Dual-key API contract for the intelligence read routes (TD-008 Phase 3b,
Etapa 1). Exercises the Founder-mandated validations end to end through the
real routes: nonexistent id, id/name divergence, cross-organization id, plus
the additive guarantees (name-only unchanged; project_id is exact)."""
import os
import subprocess
import sys

import pytest

from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import intelligence
from src.database.repository import AnalysisRepository
from src.main import app
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


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


@pytest.fixture()
def client():
    with temp_database_url("intelligence_dual_key") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

        repo = AnalysisRepository(database_url=database_url)
        app.dependency_overrides[intelligence.build_repository] = lambda: repo
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        try:
            yield TestClient(app), repo
        finally:
            app.dependency_overrides.pop(intelligence.build_repository, None)
            app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


def _seed_project_with_analysis(repo, organization_id, name):
    """Saves one analysis for `name`; returns the linked project_id."""
    repo.save_analysis(
        kind="meeting",
        payload={"model_output": {"structured": False, "raw_output": "x"}},
        organization_id=organization_id,
        project_name=name,
    )
    project = repo.enterprise.resolve_project_reference(organization_id, project_name=name)
    return project.id


class TestProjectIdFiltering:
    def test_project_id_scopes_analyses_exactly(self, client):
        test_client, repo = client
        org = repo.enterprise.create_organization("Org A")
        admin = _actor(repo, org)
        aurora_id = _seed_project_with_analysis(repo, org, "Aurora")
        _seed_project_with_analysis(repo, org, "Multilift")

        response = test_client.get(
            "/api/analyses", params={"project_id": aurora_id}, headers=_headers(org, admin)
        )
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["project_name"] == "Aurora"

    def test_name_only_still_works_unchanged(self, client):
        test_client, repo = client
        org = repo.enterprise.create_organization("Org A")
        admin = _actor(repo, org)
        _seed_project_with_analysis(repo, org, "Aurora")

        response = test_client.get(
            "/api/analyses", params={"project_name": "Aurora"}, headers=_headers(org, admin)
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_never_analyzed_name_returns_empty_not_404(self, client):
        # Additive guarantee: a genuinely nonexistent project (no Project row,
        # no analyses) keeps returning an empty list, never a 404.
        test_client, repo = client
        org = repo.enterprise.create_organization("Org A")
        admin = _actor(repo, org)

        response = test_client.get(
            "/api/analyses", params={"project_name": "Ghost"}, headers=_headers(org, admin)
        )
        assert response.status_code == 200
        assert response.json() == []


class TestDualKeyValidation:
    def test_nonexistent_id_is_404(self, client):
        test_client, repo = client
        org = repo.enterprise.create_organization("Org A")
        admin = _actor(repo, org)

        response = test_client.get(
            "/api/analyses", params={"project_id": 999999}, headers=_headers(org, admin)
        )
        assert response.status_code == 404

    def test_divergent_id_and_name_is_409(self, client):
        test_client, repo = client
        org = repo.enterprise.create_organization("Org A")
        admin = _actor(repo, org)
        aurora_id = _seed_project_with_analysis(repo, org, "Aurora")
        _seed_project_with_analysis(repo, org, "Multilift")

        response = test_client.get(
            "/api/analyses",
            params={"project_id": aurora_id, "project_name": "Multilift"},
            headers=_headers(org, admin),
        )
        assert response.status_code == 409

    def test_matching_id_and_name_is_ok(self, client):
        test_client, repo = client
        org = repo.enterprise.create_organization("Org A")
        admin = _actor(repo, org)
        aurora_id = _seed_project_with_analysis(repo, org, "Aurora")

        response = test_client.get(
            "/api/analyses",
            params={"project_id": aurora_id, "project_name": "Aurora"},
            headers=_headers(org, admin),
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_cross_organization_id_is_404(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        admin_a = _actor(repo, org_a)
        org_b = repo.enterprise.create_organization("Org B")
        secret_id = _seed_project_with_analysis(repo, org_b, "Secret")

        # Org A asks for Org B's project id -> 404, never confirmed.
        response = test_client.get(
            "/api/analyses", params={"project_id": secret_id}, headers=_headers(org_a, admin_a)
        )
        assert response.status_code == 404

    def test_project_summary_accepts_project_id(self, client):
        test_client, repo = client
        org = repo.enterprise.create_organization("Org A")
        admin = _actor(repo, org)
        aurora_id = _seed_project_with_analysis(repo, org, "Aurora")

        response = test_client.get(
            "/api/projects/summary",
            params={"project_id": aurora_id},
            headers=_headers(org, admin),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == aurora_id
        assert body["project_name"] == "Aurora"

    def test_action_items_and_risks_accept_project_id(self, client):
        test_client, repo = client
        org = repo.enterprise.create_organization("Org A")
        admin = _actor(repo, org)
        aurora_id = _seed_project_with_analysis(repo, org, "Aurora")

        for path in ("/api/action-items", "/api/risks/latest"):
            response = test_client.get(
                path, params={"project_id": aurora_id}, headers=_headers(org, admin)
            )
            assert response.status_code == 200
