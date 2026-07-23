"""Intelligence API -- meeting/risk/status analysis + read endpoints.

Security Hardening Gate (C-1 RBAC / C-2 tenant isolation; Repository Audit
Wave 3): every route now carries `get_request_context` + `require_permission`,
same convention as `test_portfolio_api.py` -- real Postgres, real migration
0010 permission catalog, real users/roles, institutional headers on every
request. `verify_api_key`/`enforce_rate_limit` stay bypassed by the autouse
conftest fixture; RBAC and organization scope are exercised for real.
"""
import json
import os
import subprocess
import sys

import pytest

from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import intelligence
from src.api.security import verify_api_key
from src.database.repository import AnalysisRepository
from src.llm.providers.base import ProviderConfigError, ProviderUnavailableError
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
    return result


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        if agent_name == "meeting_intelligence":
            return "Project: $project_name\nInput: $transcript"
        if agent_name == "risk_review":
            return "Project: $project_name\nInput: $project_context"
        if agent_name == "project_status":
            return "Project: $project_name\nInput: $project_context"
        if agent_name == "risk_advisor":
            return "Question: $question\nRisks: $risks_json"
        raise AssertionError(f"Unexpected agent: {agent_name}")


class FakeProvider:
    def generate(self, prompt):
        # Not valid JSON, so every agent's structured output parser falls
        # back to raw_output -- same fixture behavior as before this Gate.
        return "api analysis generated"


class RaisingProvider:
    def __init__(self, exc):
        self.exc = exc

    def generate(self, prompt):
        raise self.exc


@pytest.fixture()
def client():
    with temp_database_url("intelligence_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")  # seeds roles + migration 0010 permission catalog

        repo = AnalysisRepository(database_url=database_url)
        app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
        app.dependency_overrides[intelligence.build_provider] = lambda: FakeProvider()
        app.dependency_overrides[intelligence.build_repository] = lambda: repo
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo
        app.dependency_overrides.pop(intelligence.build_prompt_registry, None)
        app.dependency_overrides.pop(intelligence.build_provider, None)
        app.dependency_overrides.pop(intelligence.build_repository, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    """Creates a real User in the given organization and assigns it a real
    role from the migration 0002/0010 seed, so permission checks run
    against the actual catalog, not a fixture-only shortcut."""
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


def test_meeting_and_risk_endpoints_with_dependency_overrides(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")

    meeting_response = test_client.post(
        "/api/meetings/analyze",
        headers=_headers(org_id, user_id),
        json={"project_name": "Multilift", "transcript": "Client approved the handover plan."},
    )
    assert meeting_response.status_code == 200
    assert meeting_response.json()["agent"] == "meeting_intelligence"

    risk_response = test_client.post(
        "/api/risks/analyze",
        headers=_headers(org_id, user_id),
        json={"project_name": "Medlog", "project_context": "Timeline has relevant constraints."},
    )
    assert risk_response.status_code == 200
    assert risk_response.json()["agent"] == "risk_review"


def test_project_status_endpoint_with_dependency_overrides(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")

    response = test_client.post(
        "/api/projects/analyze",
        headers=_headers(org_id, user_id),
        json={"project_name": "Medlog", "project_context": "Schedule slipping two weeks."},
    )
    assert response.status_code == 200
    assert response.json()["agent"] == "project_status"


def test_meeting_endpoint_rejects_whitespace_only_transcript(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")

    response = test_client.post(
        "/api/meetings/analyze",
        headers=_headers(org_id, user_id),
        json={"project_name": "Multilift", "transcript": "                    "},
    )

    assert response.status_code == 422


def test_meeting_endpoint_rejects_transcript_over_max_length(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")

    response = test_client.post(
        "/api/meetings/analyze",
        headers=_headers(org_id, user_id),
        json={"project_name": "Multilift", "transcript": "a" * 20001},
    )

    assert response.status_code == 422


def test_risk_endpoint_rejects_whitespace_only_project_context(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")

    response = test_client.post(
        "/api/risks/analyze",
        headers=_headers(org_id, user_id),
        json={"project_name": "Medlog", "project_context": "                    "},
    )

    assert response.status_code == 422


def test_meeting_endpoint_returns_503_on_provider_config_error(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")
    app.dependency_overrides[intelligence.build_provider] = lambda: RaisingProvider(
        ProviderConfigError("ANTHROPIC_API_KEY is required")
    )

    response = test_client.post(
        "/api/meetings/analyze",
        headers=_headers(org_id, user_id),
        json={"project_name": "Multilift", "transcript": "Client approved the handover plan."},
    )

    assert response.status_code == 503
    assert response.json()["error"] == "provider_config_error"


def test_risk_endpoint_returns_502_on_provider_unavailable_error(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")
    app.dependency_overrides[intelligence.build_provider] = lambda: RaisingProvider(
        ProviderUnavailableError("Anthropic API call failed")
    )

    response = test_client.post(
        "/api/risks/analyze",
        headers=_headers(org_id, user_id),
        json={"project_name": "Medlog", "project_context": "Timeline has relevant constraints."},
    )

    assert response.status_code == 502
    assert response.json()["error"] == "provider_unavailable"


def test_list_analyses_endpoint_returns_summaries(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")
    id1 = repo.save_analysis(
        kind="meeting", payload={}, organization_id=org_id, project_name="Multilift"
    )
    id2 = repo.save_analysis(
        kind="risk", payload={}, organization_id=org_id, project_name="Multilift"
    )

    response = test_client.get(
        "/api/analyses", headers=_headers(org_id, user_id), params={"project_name": "Multilift"}
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [id2, id1]


def test_list_analyses_endpoint_passes_kind_and_period_filters(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")
    repo.save_analysis(kind="meeting", payload={}, organization_id=org_id, project_name="Multilift")
    repo.save_analysis(kind="risk", payload={}, organization_id=org_id, project_name="Multilift")

    response = test_client.get(
        "/api/analyses",
        headers=_headers(org_id, user_id),
        params={"project_name": "Multilift", "kind": "meeting"},
    )

    assert response.status_code == 200
    assert [item["kind"] for item in response.json()] == ["meeting"]


def test_list_analyses_endpoint_with_no_results_returns_empty_list(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")

    response = test_client.get(
        "/api/analyses", headers=_headers(org_id, user_id), params={"project_name": "Unknown"}
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_analysis_endpoint_returns_full_payload(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")
    analysis_id = repo.save_analysis(
        kind="meeting",
        payload={"model_output": "summary generated"},
        organization_id=org_id,
        project_name="Multilift",
    )

    response = test_client.get(f"/api/analyses/{analysis_id}", headers=_headers(org_id, user_id))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == analysis_id
    assert body["payload"] == {"model_output": "summary generated"}


def test_get_analysis_endpoint_returns_404_when_not_found(client):
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")

    response = test_client.get("/api/analyses/999", headers=_headers(org_id, user_id))

    assert response.status_code == 404


class TestOrganizationScoping:
    def test_get_analysis_from_another_organization_returns_404(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        analysis_b = repo.save_analysis(
            kind="meeting", payload={}, organization_id=org_b, project_name="Multilift"
        )

        response = test_client.get(
            f"/api/analyses/{analysis_b}", headers=_headers(org_a, user_a)
        )

        assert response.status_code == 404  # not 403 -- never confirms the id exists

    def test_list_analyses_never_returns_another_organizations_records(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        repo.save_analysis(
            kind="meeting", payload={}, organization_id=org_b, project_name="Multilift"
        )

        response = test_client.get("/api/analyses", headers=_headers(org_a, user_a))

        assert response.json() == []

    def test_meeting_analyzed_by_org_a_is_invisible_to_org_b(self, client):
        # End-to-end: the real live cross-tenant leak the Repository Audit
        # found (C-2) -- confirms it can't come back through the write path.
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        user_b = _actor(repo, org_b, "organization_admin")

        analyze_response = test_client.post(
            "/api/meetings/analyze",
            headers=_headers(org_a, user_a),
            json={"project_name": "Multilift", "transcript": "Client approved the handover plan."},
        )
        assert analyze_response.status_code == 200

        response = test_client.get(
            "/api/analyses", headers=_headers(org_b, user_b), params={"project_name": "Multilift"}
        )
        assert response.json() == []

        portfolio_response = test_client.get(
            "/api/portfolio/summary", headers=_headers(org_b, user_b)
        )
        assert portfolio_response.json() == []


class TestRbacEnforcement:
    @pytest.mark.parametrize(
        "path,json_body",
        [
            ("/api/meetings/analyze", {"project_name": "X", "transcript": "abcdefghij"}),
            ("/api/risks/analyze", {"project_name": "X", "project_context": "abcdefghij"}),
            ("/api/projects/analyze", {"project_name": "X", "project_context": "abcdefghij"}),
        ],
    )
    def test_viewer_cannot_call_write_routes(self, client, path, json_body):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.post(path, headers=_headers(org_id, viewer_id), json=json_body)

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: intelligence.write"

    @pytest.mark.parametrize(
        "path",
        ["/api/analyses", "/api/action-items", "/api/risks/latest", "/api/portfolio/summary"],
    )
    def test_user_with_no_role_is_denied_read(self, client, path):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.get(path, headers=_headers(org_id, user_id))

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: intelligence.read"

    def test_user_with_no_role_is_denied_get_analysis_by_id(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")
        analysis_id = repo.save_analysis(kind="meeting", payload={}, organization_id=org_id)

        response = test_client.get(
            f"/api/analyses/{analysis_id}", headers=_headers(org_id, user_id)
        )

        assert response.status_code == 403

    def test_user_with_no_role_is_denied_project_summary(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.get(
            "/api/projects/summary",
            headers=_headers(org_id, user_id),
            params={"project_name": "Multilift"},
        )

        assert response.status_code == 403

    def test_viewer_can_read_but_not_write(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.get("/api/analyses", headers=_headers(org_id, viewer_id))

        assert response.status_code == 200


class TestRequestContextRequired:
    def test_missing_institutional_headers_returns_400(self, client):
        test_client, _repo = client
        response = test_client.get("/api/analyses")
        assert response.status_code == 400


def test_list_analyses_requires_api_key(client, monkeypatch):
    """The autouse conftest fixture bypasses verify_api_key by default for
    every test in this suite -- this test restores it to prove the auth
    stack is really wired on this router."""
    test_client, repo = client
    org_id = repo.enterprise.create_organization("Org A")
    user_id = _actor(repo, org_id, "organization_admin")
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)

    response = test_client.get("/api/analyses", headers=_headers(org_id, user_id))

    assert response.status_code == 401


class TestRiskAdvisor:
    def test_returns_a_canned_answer_without_calling_the_llm_when_no_risks_exist(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("LLM must not be called when there is nothing to synthesize")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/risk-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Multilift", "question": "Qual o risco mais crítico?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Nenhum risco identificado ainda para este projeto."
        assert body["cited_analyses"] == []

    def test_answers_from_the_latest_risk_analysis_with_citations(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        analysis_id = repo.save_analysis(
            kind="risk",
            payload={
                "model_output": {
                    "structured": True,
                    "risks": [
                        {
                            "description": "Atraso no fornecedor de middleware",
                            "probability": "high",
                            "impact": "high",
                            "mitigation": "Escalar ao patrocinador",
                        }
                    ],
                    "escalation_recommendation": "Escalar ao comitê executivo",
                }
            },
            organization_id=org_id,
            project_name="Multilift",
        )

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {
                        "answer": "O risco mais crítico é o atraso no fornecedor de middleware.",
                        "cited_analysis_ids": [analysis_id],
                    }
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/risk-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Multilift", "question": "Qual o risco mais crítico?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "O risco mais crítico é o atraso no fornecedor de middleware."
        assert body["cited_analyses"] == [
            {"source_analysis_id": analysis_id, "source_created_at": response.json()["cited_analyses"][0]["source_created_at"]}
        ]

    def test_user_with_no_role_is_denied(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.post(
            "/api/risk-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Multilift", "question": "Qual o risco mais crítico?"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: intelligence.read"

    def test_viewer_can_ask(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.post(
            "/api/risk-advisor/ask",
            headers=_headers(org_id, viewer_id),
            json={"project_name": "Multilift", "question": "Qual o risco mais crítico?"},
        )

        assert response.status_code == 200

    def test_never_sees_risks_from_another_organization(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        repo.save_analysis(
            kind="risk",
            payload={
                "model_output": {
                    "structured": True,
                    "risks": [{"description": "Risco de Org B", "probability": "high", "impact": "high", "mitigation": "x"}],
                    "escalation_recommendation": None,
                }
            },
            organization_id=org_b,
            project_name="Multilift",
        )

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("must not synthesize over another organization's risks")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/risk-advisor/ask",
            headers=_headers(org_a, user_a),
            json={"project_name": "Multilift", "question": "Qual o risco mais crítico?"},
        )

        assert response.status_code == 200
        assert response.json()["answer"] == "Nenhum risco identificado ainda para este projeto."

    def test_records_an_audit_entry_without_the_llm_answer(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = test_client.post(
            "/api/risk-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Multilift", "question": "Qual o risco mais crítico?"},
        )
        assert response.status_code == 200

        entries = repo.administration.list_audit_log(org_id)
        matching = [e for e in entries if e.action == "risk_advisor.question_asked"]
        assert len(matching) == 1
        assert matching[0].actor_user_id == user_id
        assert matching[0].organization_id == org_id
        assert matching[0].details["question"] == "Qual o risco mais crítico?"
        assert "answer" not in matching[0].details


class TestAuditTrail:
    @pytest.mark.parametrize(
        "path,json_body,action",
        [
            (
                "/api/meetings/analyze",
                {"project_name": "Multilift", "transcript": "Client approved the handover plan."},
                "analysis.meeting_created",
            ),
            (
                "/api/risks/analyze",
                {"project_name": "Multilift", "project_context": "Timeline has constraints."},
                "analysis.risk_created",
            ),
            (
                "/api/projects/analyze",
                {"project_name": "Multilift", "project_context": "Schedule slipping."},
                "analysis.status_created",
            ),
        ],
    )
    def test_analyze_route_records_an_audit_entry(self, client, path, json_body, action):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = test_client.post(path, headers=_headers(org_id, user_id), json=json_body)
        assert response.status_code == 200

        entries = repo.administration.list_audit_log(org_id)
        matching = [e for e in entries if e.action == action]
        assert len(matching) == 1
        assert matching[0].actor_user_id == user_id
        assert matching[0].organization_id == org_id
        assert matching[0].entity_id is not None
