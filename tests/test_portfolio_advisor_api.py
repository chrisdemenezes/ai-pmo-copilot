"""Portfolio Advisor HTTP route (Wave 5), per
`TECHNICAL-DESIGN-PORTFOLIO-ADVISOR.md` §6.

Same rigor already established for `/delivery-advisor/ask`
(`test_delivery_advisor_api.py`) -- real Postgres, real migration-seeded
permissions, real institutional headers, real `DomainService`.

Covers HTTP-layer proof of the mandatory scenarios (Founder Decision --
Technical Design do Portfolio Advisor, item 6), plus RBAC, audit trail,
malformed response, and the structural absence of a second/supplementary
source (RAG).
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
from src.services.domain_service import DomainService
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


class _NoOpEventPublisher:
    def publish(self, event_type, payload, organization_id, correlation_id, origin):
        return None


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "portfolio_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nProjects: $projects_json"


class _ExplodingRagPipeline:
    def retrieve(self, organization_id, query, top_k=5):
        raise AssertionError("Portfolio Advisor must never consult RAG -- Classe B, status-only source")


@pytest.fixture()
def client():
    with temp_database_url("portfolio_advisor_api") as database_url:
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
        # Structurally proves item 2/6 of "Technical Design do Delivery
        # Advisor" applied identically here: if the route ever called
        # gather_rag_context(), this override would blow up every test.
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


def _build_portfolio(domain_service, org_id, actor_id, code="PF-A"):
    portfolio = domain_service.create_portfolio(org_id, "Cloud Modernization", code, actor_id, correlation_id=CORRELATION_ID)
    program = domain_service.create_program(org_id, portfolio.id, "Infra", "INFRA", actor_id, correlation_id=CORRELATION_ID)
    return portfolio, program


class TestScenarioA_CoberturaCompleta:
    def test_all_projects_covered(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        portfolio, program = _build_portfolio(domain_service, org_id, user_id)
        domain_service.create_project(org_id, program.id, "Aurora", user_id, correlation_id=CORRELATION_ID)
        domain_service.create_project(org_id, program.id, "Boreal", user_id, correlation_id=CORRELATION_ID)
        id_a = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
        id_b = _save_status_at(repo, org_id, "Boreal", "red", datetime(2026, 8, 1, tzinfo=timezone.utc))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {"answer": "Aurora esta green, Boreal esta red.", "cited_analysis_ids": [id_a, id_b]}
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": portfolio.id, "question": "Como esta o portfolio?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total_projects"] == 2
        assert body["projects_with_evidence"] == 2
        assert body["projects_without_evidence"] == 0
        assert {c["source_analysis_id"] for c in body["cited_projects"]} == {id_a, id_b}


class TestScenarioB_CoberturaParcial:
    def test_some_projects_without_evidence(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        portfolio, program = _build_portfolio(domain_service, org_id, user_id)
        domain_service.create_project(org_id, program.id, "Aurora", user_id, correlation_id=CORRELATION_ID)
        domain_service.create_project(org_id, program.id, "Boreal", user_id, correlation_id=CORRELATION_ID)
        id_a = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {
                        "answer": "Apenas Aurora possui dados de status; Boreal nao possui analise registrada.",
                        "cited_analysis_ids": [id_a],
                    }
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": portfolio.id, "question": "Como esta o portfolio?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total_projects"] == 2
        assert body["projects_with_evidence"] == 1
        assert body["projects_without_evidence"] == 1
        assert len(body["cited_projects"]) == 1


class TestScenarioC_CoberturaZero:
    def test_no_evidence_returns_canned_answer_without_calling_the_llm(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        portfolio, program = _build_portfolio(domain_service, org_id, user_id)
        domain_service.create_project(org_id, program.id, "Aurora", user_id, correlation_id=CORRELATION_ID)

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("LLM must not be called when there is nothing to synthesize")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": portfolio.id, "question": "Como esta o portfolio?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Nenhuma análise de status registrada para os projetos deste portfólio."
        assert body["total_projects"] == 1
        assert body["projects_with_evidence"] == 0
        assert body["projects_without_evidence"] == 1
        assert body["cited_projects"] == []


class TestScenarioD_PortfolioSemProgramsOuProjects:
    def test_portfolio_without_any_program(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        portfolio = domain_service.create_portfolio(org_id, "Empty", "PF-EMPTY", user_id, correlation_id=CORRELATION_ID)

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("LLM must not be called")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": portfolio.id, "question": "Como esta o portfolio?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total_projects"] == 0
        assert body["projects_with_evidence"] == 0
        assert body["projects_without_evidence"] == 0


class TestScenarioE_PortfolioInexistente:
    def test_returns_404_for_a_nonexistent_portfolio(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": 999999, "question": "Como esta o portfolio?"},
        )

        assert response.status_code == 404


class TestScenarioF_PortfolioDeOutraOrganizacao:
    def test_returns_404_for_a_portfolio_belonging_to_another_organization(self, client):
        test_client, repo, domain_service = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        user_b = repo.enterprise.create_user(org_b, "actorb@example.com", "Actor B")
        portfolio_b = domain_service.create_portfolio(org_b, "Org B Portfolio", "PF-B", user_b, correlation_id=CORRELATION_ID)

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_a, user_a),
            json={"portfolio_id": portfolio_b.id, "question": "Como esta o portfolio?"},
        )

        assert response.status_code == 404


class TestScenarioG_ApenasOStatusMaisRecente:
    def test_only_the_most_recent_status_is_used(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        portfolio, program = _build_portfolio(domain_service, org_id, user_id)
        domain_service.create_project(org_id, program.id, "Aurora", user_id, correlation_id=CORRELATION_ID)
        _save_status_at(repo, org_id, "Aurora", "red", datetime(2026, 7, 1, tzinfo=timezone.utc))
        recent_id = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps({"answer": "Aurora esta green.", "cited_analysis_ids": [recent_id]})

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": portfolio.id, "question": "Como esta Aurora?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["cited_projects"] == [
            {
                "project_id": body["cited_projects"][0]["project_id"],
                "project_name": "Aurora",
                "source_analysis_id": recent_id,
                "source_created_at": body["cited_projects"][0]["source_created_at"],
            }
        ]


class TestRbac:
    def test_user_with_no_role_is_denied(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")
        actor_id = _actor(repo, org_id, "organization_admin")
        portfolio, _program = _build_portfolio(domain_service, org_id, actor_id)

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": portfolio.id, "question": "Alguma pergunta?"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: intelligence.read"

    def test_viewer_can_ask(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")
        portfolio = domain_service.create_portfolio(org_id, "Empty", "PF-V", viewer_id, correlation_id=CORRELATION_ID)

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, viewer_id),
            json={"portfolio_id": portfolio.id, "question": "Alguma pergunta?"},
        )

        assert response.status_code == 200


class TestMalformedResponse:
    def test_returns_502_for_a_malformed_advisor_response(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        portfolio, program = _build_portfolio(domain_service, org_id, user_id)
        domain_service.create_project(org_id, program.id, "Aurora", user_id, correlation_id=CORRELATION_ID)
        _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))

        class NotJsonProvider:
            def generate(self, prompt):
                return "not json at all"

        app.dependency_overrides[intelligence.build_provider] = lambda: NotJsonProvider()

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": portfolio.id, "question": "Como esta o portfolio?"},
        )

        assert response.status_code == 502


class TestAuditTrail:
    def test_records_an_audit_entry_without_the_llm_answer(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        portfolio, _program = _build_portfolio(domain_service, org_id, user_id)

        response = test_client.post(
            "/api/portfolio-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"portfolio_id": portfolio.id, "question": "Alguma pergunta sobre o portfolio?"},
        )
        assert response.status_code == 200

        entries = repo.administration.list_audit_log(org_id)
        matching = [e for e in entries if e.action == "portfolio_advisor.question_asked"]
        assert len(matching) == 1
        assert matching[0].actor_user_id == user_id
        assert matching[0].organization_id == org_id
        assert matching[0].details["question"] == "Alguma pergunta sobre o portfolio?"
        assert "answer" not in matching[0].details
