"""Delivery Advisor HTTP route (Wave 5), per
`TECHNICAL-DESIGN-DELIVERY-ADVISOR.md` §5.

Same rigor already established for `/risk-advisor/ask`
(`test_intelligence_api.py::TestRiskAdvisor`) -- real Postgres, real
migration-seeded permissions, real institutional headers.

Includes, at the HTTP layer, the three mandatory temporal scenarios (item
4 of "Founder Decision -- Technical Design do Delivery Advisor") and the
proof that no second/supplementary source of evidence (RAG included) is
ever consulted by this route (item 2/6).
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import intelligence
from src.database.repository import AnalysisRecord, AnalysisRepository
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
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "delivery_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nHistory: $status_history_json"


class _ExplodingRagPipeline:
    def retrieve(self, organization_id, query, top_k=5):
        raise AssertionError("Delivery Advisor must never consult RAG -- Classe A, single source")


@pytest.fixture()
def client():
    with temp_database_url("delivery_advisor_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")  # seeds roles + migration 0010 permission catalog

        repo = AnalysisRepository(database_url=database_url)
        app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
        app.dependency_overrides[intelligence.build_repository] = lambda: repo
        # Structurally proves item 2/6 of the authorization: if the route
        # ever called gather_rag_context(), this override would blow up
        # every single test in this file -- a passing suite is the proof.
        app.dependency_overrides[intelligence.build_rag_pipeline] = lambda: _ExplodingRagPipeline()
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo
        app.dependency_overrides.pop(intelligence.build_prompt_registry, None)
        app.dependency_overrides.pop(intelligence.build_provider, None)
        app.dependency_overrides.pop(intelligence.build_repository, None)
        app.dependency_overrides.pop(intelligence.build_rag_pipeline, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


def _save_status_at(repo, org_id: int, project_name: str, health_status: str, created_at: datetime) -> int:
    analysis_id = repo.save_analysis(
        kind="status",
        payload={
            "model_output": {
                "structured": True,
                "health_status": health_status,
                "key_findings": [f"finding-{health_status}"],
                "recommendations": [f"recommendation-{health_status}"],
            }
        },
        organization_id=org_id,
        project_name=project_name,
    )
    with repo.SessionLocal() as session:
        record = session.get(AnalysisRecord, analysis_id)
        record.created_at = created_at
        session.commit()
    return analysis_id


class TestNoEvidence:
    def test_returns_a_canned_answer_without_calling_the_llm_when_no_status_exists(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("LLM must not be called when there is nothing to synthesize")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Aurora", "question": "Como esta o projeto?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Nenhuma análise de status registrada ainda para este projeto."
        assert body["cited_analyses"] == []


class TestTemporalScenarioA_Melhora:
    def test_old_red_intermediate_yellow_recent_green_yields_current_green_and_melhorando(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        red_id = _save_status_at(repo, org_id, "Aurora", "red", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc))
        yellow_id = _save_status_at(repo, org_id, "Aurora", "yellow", datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc))
        green_id = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {
                        "answer": (
                            "O estado atual do projeto Aurora e green. A tendencia e melhorando: "
                            "o projeto evoluiu de red para yellow e agora green."
                        ),
                        "cited_analysis_ids": [green_id, yellow_id, red_id],
                    }
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Aurora", "question": "Como esta o projeto Aurora?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "green" in body["answer"]
        assert "melhorando" in body["answer"]
        assert [c["source_analysis_id"] for c in body["cited_analyses"]] == [green_id, yellow_id, red_id]


class TestTemporalScenarioB_Deterioracao:
    def test_old_green_intermediate_yellow_recent_red_yields_current_red_and_deteriorando(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        green_id = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc))
        yellow_id = _save_status_at(repo, org_id, "Aurora", "yellow", datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc))
        red_id = _save_status_at(repo, org_id, "Aurora", "red", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {
                        "answer": (
                            "O estado atual do projeto Aurora e red. A tendencia e deteriorando: "
                            "o projeto evoluiu de green para yellow e agora red."
                        ),
                        "cited_analysis_ids": [red_id, yellow_id, green_id],
                    }
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Aurora", "question": "Como esta o projeto Aurora?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "red" in body["answer"]
        assert "deteriorando" in body["answer"]
        assert [c["source_analysis_id"] for c in body["cited_analyses"]] == [red_id, yellow_id, green_id]


class TestTemporalScenarioC_RegistroUnico:
    def test_single_record_reports_current_state_without_inventing_a_trend(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        yellow_id = _save_status_at(repo, org_id, "Aurora", "yellow", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {
                        "answer": (
                            "O estado atual do projeto Aurora e yellow. Nao ha historico suficiente "
                            "para avaliar uma tendencia de evolucao."
                        ),
                        "cited_analysis_ids": [yellow_id],
                    }
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Aurora", "question": "Como esta o projeto Aurora?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "yellow" in body["answer"]
        assert "Nao ha historico suficiente" in body["answer"]
        assert "melhorando" not in body["answer"]
        assert "deteriorando" not in body["answer"]
        assert [c["source_analysis_id"] for c in body["cited_analyses"]] == [yellow_id]


class TestRbac:
    def test_user_with_no_role_is_denied(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Aurora", "question": "Como esta o projeto?"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: intelligence.read"

    def test_viewer_can_ask(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_id, viewer_id),
            json={"project_name": "Aurora", "question": "Como esta o projeto?"},
        )

        assert response.status_code == 200


class TestOrganizationalIsolation:
    def test_never_cites_a_status_analysis_from_another_organization(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        _save_status_at(repo, org_b, "Aurora", "red", datetime(2026, 8, 1, tzinfo=timezone.utc))

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("must not synthesize over another organization's status analyses")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_a, user_a),
            json={"project_name": "Aurora", "question": "Como esta o projeto Aurora?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["cited_analyses"] == []


class TestMalformedResponse:
    def test_returns_502_for_a_malformed_advisor_response(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))

        class NotJsonProvider:
            def generate(self, prompt):
                return "not json at all"

        app.dependency_overrides[intelligence.build_provider] = lambda: NotJsonProvider()

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Aurora", "question": "Como esta o projeto?"},
        )

        assert response.status_code == 502


class TestAuditTrail:
    def test_records_an_audit_entry_without_the_llm_answer(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = test_client.post(
            "/api/delivery-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"project_name": "Aurora", "question": "Como esta o projeto Aurora?"},
        )
        assert response.status_code == 200

        entries = repo.administration.list_audit_log(org_id)
        matching = [e for e in entries if e.action == "delivery_advisor.question_asked"]
        assert len(matching) == 1
        assert matching[0].actor_user_id == user_id
        assert matching[0].organization_id == org_id
        assert matching[0].details["question"] == "Como esta o projeto Aurora?"
        assert "answer" not in matching[0].details
