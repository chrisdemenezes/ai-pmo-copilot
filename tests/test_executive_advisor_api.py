"""Executive Advisor HTTP route (Wave 5), per
`TECHNICAL-DESIGN-EXECUTIVE-ADVISOR.md` §4.

Same rigor already established for `/pmo-advisor/ask`
(`test_pmo_advisor_api.py`) -- real Postgres, real migration-seeded
permissions, real institutional headers, real `DomainService`.

Covers HTTP-layer proof of the mandatory scenarios plus RBAC, audit trail,
malformed response, and the structural absence of a second/supplementary
source (RAG).
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import intelligence
from src.database.repository import AnalysisRecord, AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.domain_service import DomainService
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"
NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


class _NoOpEventPublisher:
    def publish(self, event_type, payload, organization_id, correlation_id, origin):
        return None


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "executive_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nRecords: $records_json"


class _ExplodingRagPipeline:
    def retrieve(self, organization_id, query, top_k=5):
        raise AssertionError("Executive Advisor must never consult RAG -- Classe B, status/risk only")


@pytest.fixture()
def client():
    with temp_database_url("executive_advisor_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=os.getcwd(),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

        repo = AnalysisRepository(database_url=database_url)
        domain_service = DomainService(repository=repo, publisher=_NoOpEventPublisher())
        app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
        app.dependency_overrides[intelligence.build_repository] = lambda: repo
        # Structurally proves the source is exclusively status/risk: if the
        # route ever called gather_rag_context(), this override blows up.
        app.dependency_overrides[intelligence.build_rag_pipeline] = lambda: _ExplodingRagPipeline()
        app.dependency_overrides[intelligence.build_domain_service] = lambda: domain_service
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo, domain_service
        app.dependency_overrides.pop(intelligence.build_prompt_registry, None)
        app.dependency_overrides.pop(intelligence.build_provider, None)
        app.dependency_overrides.pop(intelligence.build_repository, None)
        app.dependency_overrides.pop(intelligence.build_rag_pipeline, None)
        app.dependency_overrides.pop(intelligence.build_domain_service, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


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


def _save_analysis_at(repo, org_id, project_name, kind, model_output, created_at) -> int:
    analysis_id = repo.save_analysis(
        kind=kind,
        payload={"model_output": model_output},
        organization_id=org_id,
        project_name=project_name,
    )
    with repo.SessionLocal() as session:
        record = session.get(AnalysisRecord, analysis_id)
        record.created_at = created_at
        session.commit()
    return analysis_id


def _save_status_at(repo, org_id: int, project_name: str, health_status: str, created_at: datetime) -> int:
    return _save_analysis_at(
        repo,
        org_id,
        project_name,
        "status",
        {
            "structured": True,
            "health_status": health_status,
            "key_findings": [f"finding-{health_status}"],
            "recommendations": [f"recommendation-{health_status}"],
        },
        created_at,
    )


def _save_risk_at(repo, org_id: int, project_name: str, description: str, created_at: datetime) -> int:
    return _save_analysis_at(
        repo,
        org_id,
        project_name,
        "risk",
        {
            "structured": True,
            "risks": [{"description": description, "probability": "medium", "impact": "high", "mitigation": "m"}],
            "escalation_recommendation": None,
        },
        created_at,
    )


def _org_with_program(domain_service, repo, name="Org A"):
    org_id = repo.enterprise.create_organization(name)
    user_id = _actor(repo, org_id, "organization_admin")
    portfolio = domain_service.create_portfolio(org_id, "Portfolio", "PF-A", user_id, correlation_id=CORRELATION_ID)
    program = domain_service.create_program(org_id, portfolio.id, "Program", "PRG", user_id, correlation_id=CORRELATION_ID)
    return org_id, user_id, program.id


class TestScenarioE_CoberturaCompleta:
    def test_all_projects_covered(self, client):
        test_client, repo, domain_service = client
        org_id, user_id, program_id = _org_with_program(domain_service, repo)
        domain_service.create_project(org_id, program_id, "Aurora", user_id, correlation_id=CORRELATION_ID)
        domain_service.create_project(org_id, program_id, "Boreal", user_id, correlation_id=CORRELATION_ID)
        id_status = _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        id_risk = _save_risk_at(repo, org_id, "Boreal", "risco de escopo", NOW - timedelta(days=1))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {"answer": "Aurora esta green, Boreal com risco.", "cited_analysis_ids": [id_status, id_risk]}
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "O que exige atencao da lideranca agora?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total_projects"] == 2
        assert body["projects_with_status"] == 1
        assert body["projects_with_risk"] == 1
        assert body["projects_with_status_and_risk"] == 0
        assert body["projects_without_any_evidence"] == 0
        assert body["projects_with_status"] + body["projects_without_status"] == body["total_projects"]
        assert body["projects_with_risk"] + body["projects_without_risk"] == body["total_projects"]
        assert {c["source_analysis_id"] for c in body["cited_evidence"]} == {id_status, id_risk}


class TestScenarioF_CoberturaParcial:
    def test_some_projects_without_any_evidence(self, client):
        test_client, repo, domain_service = client
        org_id, user_id, program_id = _org_with_program(domain_service, repo)
        domain_service.create_project(org_id, program_id, "Aurora", user_id, correlation_id=CORRELATION_ID)
        domain_service.create_project(org_id, program_id, "Boreal", user_id, correlation_id=CORRELATION_ID)
        id_status = _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {
                        "answer": "Apenas Aurora possui evidencia registrada; Boreal nao possui nenhuma.",
                        "cited_analysis_ids": [id_status],
                    }
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "O que exige atencao?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total_projects"] == 2
        assert body["projects_without_any_evidence"] == 1
        assert len(body["cited_evidence"]) == 1


class TestScenarioG_AusenciaTotal:
    def test_no_evidence_returns_canned_answer_without_calling_the_llm(self, client):
        test_client, repo, domain_service = client
        org_id, user_id, program_id = _org_with_program(domain_service, repo)
        domain_service.create_project(org_id, program_id, "Aurora", user_id, correlation_id=CORRELATION_ID)

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("LLM must not be called when there is nothing to synthesize")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "O que exige atencao agora?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Nenhuma análise de status ou risco registrada para os projetos desta organização."
        assert body["total_projects"] == 1
        assert body["projects_without_any_evidence"] == 1
        assert body["cited_evidence"] == []


class TestScenarioH_DuasCitacoesMesmoProjectKindsDiferentes:
    def test_cited_evidence_distinguishes_status_from_risk_for_the_same_project(self, client):
        test_client, repo, domain_service = client
        org_id, user_id, program_id = _org_with_program(domain_service, repo)
        domain_service.create_project(org_id, program_id, "Aurora", user_id, correlation_id=CORRELATION_ID)
        id_status = _save_status_at(repo, org_id, "Aurora", "red", NOW - timedelta(days=1))
        id_risk = _save_risk_at(repo, org_id, "Aurora", "atraso critico", NOW - timedelta(days=1))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {"answer": "Aurora exige decisao agora.", "cited_analysis_ids": [id_status, id_risk]}
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "O que exige decisao agora?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["cited_evidence"]) == 2
        kinds_by_source_id = {c["source_analysis_id"]: c["kind"] for c in body["cited_evidence"]}
        assert kinds_by_source_id == {id_status: "status", id_risk: "risk"}
        assert all(c["project_name"] == "Aurora" for c in body["cited_evidence"])


class TestScenarioJ_IsolamentoOrganizacional:
    def test_projects_of_another_organization_never_leak_in(self, client):
        test_client, repo, domain_service = client
        org_a, user_a, program_a = _org_with_program(domain_service, repo, "Org A")
        org_b, user_b, program_b = _org_with_program(domain_service, repo, "Org B")
        domain_service.create_project(org_a, program_a, "Aurora", user_a, correlation_id=CORRELATION_ID)
        domain_service.create_project(org_b, program_b, "Nebula", user_b, correlation_id=CORRELATION_ID)
        _save_status_at(repo, org_a, "Aurora", "green", NOW - timedelta(days=1))
        _save_risk_at(repo, org_b, "Nebula", "risco b", NOW - timedelta(days=1))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps({"answer": "Aurora esta green.", "cited_analysis_ids": []})

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_a, user_a),
            json={"question": "Como estao os projetos?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total_projects"] == 1


class TestRbac:
    def test_user_with_no_role_is_denied(self, client):
        test_client, repo, domain_service = client
        org_id, _user_id, _program_id = _org_with_program(domain_service, repo)
        no_role_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_id, no_role_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: intelligence.read"

    def test_viewer_can_ask(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org Viewer")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_id, viewer_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200


class TestMalformedResponse:
    def test_returns_502_for_a_malformed_advisor_response(self, client):
        test_client, repo, domain_service = client
        org_id, user_id, program_id = _org_with_program(domain_service, repo)
        domain_service.create_project(org_id, program_id, "Aurora", user_id, correlation_id=CORRELATION_ID)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        class NotJsonProvider:
            def generate(self, prompt):
                return "not json at all"

        app.dependency_overrides[intelligence.build_provider] = lambda: NotJsonProvider()

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Como estao os projetos?"},
        )

        assert response.status_code == 502


class TestAuditTrail:
    def test_records_an_audit_entry_without_the_llm_answer(self, client):
        test_client, repo, domain_service = client
        org_id, user_id, _program_id = _org_with_program(domain_service, repo)

        response = test_client.post(
            "/api/executive-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta sobre a organizacao?"},
        )
        assert response.status_code == 200

        entries = repo.administration.list_audit_log(org_id)
        matching = [e for e in entries if e.action == "executive_advisor.question_asked"]
        assert len(matching) == 1
        assert matching[0].actor_user_id == user_id
        assert matching[0].organization_id == org_id
        assert matching[0].details["question"] == "Alguma pergunta sobre a organizacao?"
        assert "answer" not in matching[0].details
