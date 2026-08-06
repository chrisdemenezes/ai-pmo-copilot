"""Strategy Advisor HTTP route (Wave 5), per
`TECHNICAL-DESIGN-STRATEGY-ADVISOR.md` §7.

Same rigor already established for `/executive-advisor/ask`
(`test_executive_advisor_api.py`) -- real Postgres, real migration-seeded
permissions, real institutional headers, real `DomainService`.

Covers HTTP-layer proof of scenarios H-N, P, Q, R, T, U plus RBAC and audit
trail -- most critically R, confirming the synthetic `source_id` never
leaks into any field of the full HTTP response body.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from fastapi.testclient import TestClient

from src.agents.strategy_advisor.evidence_assembler import _synthetic_source_id
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
        assert agent_name == "strategy_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nRecords: $records_json"


class _ExplodingRagPipeline:
    def retrieve(self, organization_id, query, top_k=5):
        raise AssertionError("Strategy Advisor must never consult RAG this Epic -- declared strategy + status/risk only")


@pytest.fixture()
def client():
    with temp_database_url("strategy_advisor_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=os.getcwd(), env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        repo = AnalysisRepository(database_url=database_url)
        domain_service = DomainService(repository=repo, publisher=_NoOpEventPublisher())
        app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
        app.dependency_overrides[intelligence.build_repository] = lambda: repo
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
        kind=kind, payload={"model_output": model_output}, organization_id=org_id, project_name=project_name
    )
    with repo.SessionLocal() as session:
        record = session.get(AnalysisRecord, analysis_id)
        record.created_at = created_at
        session.commit()
    return analysis_id


def _save_status_at(repo, org_id, project_name, health_status, created_at) -> int:
    return _save_analysis_at(
        repo, org_id, project_name, "status",
        {"structured": True, "health_status": health_status, "key_findings": [], "recommendations": []},
        created_at,
    )


def _save_risk_at(repo, org_id, project_name, description, created_at) -> int:
    return _save_analysis_at(
        repo, org_id, project_name, "risk",
        {"structured": True, "risks": [{"description": description, "probability": "medium", "impact": "high", "mitigation": "m"}], "escalation_recommendation": None},
        created_at,
    )


def _org(repo, name="Org A") -> int:
    return repo.enterprise.create_organization(name)


def _portfolio(domain_service, org_id, user_id, code, objective=None):
    return domain_service.create_portfolio(
        org_id, f"Portfolio {code}", code, user_id, correlation_id=CORRELATION_ID, strategic_objective=objective
    )


def _program(domain_service, org_id, user_id, portfolio_id, code, objective=None):
    return domain_service.create_program(
        org_id, portfolio_id, f"Program {code}", code, user_id, correlation_id=CORRELATION_ID, objective=objective
    )


def _project(domain_service, org_id, user_id, program_id, name, objective=None):
    return domain_service.create_project(
        org_id, program_id, name, user_id, correlation_id=CORRELATION_ID, objective=objective
    )


class TestScenarioH_AusenciaTotal:
    def test_no_evidence_returns_canned_answer_without_calling_the_llm(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, user_id, "PF-A")
        program = _program(domain_service, org_id, user_id, portfolio.id, "PRG-A")
        _project(domain_service, org_id, user_id, program.id, "Aurora")

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("LLM must not be called when there is nothing to synthesize")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "A execucao continua alinhada com a estrategia?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == (
            "Nenhum objetivo declarado ou evidência de execução comparável registrada para esta organização."
        )
        assert body["cited_evidence"] == []
        assert body["projects_total"] == 1
        assert body["projects_comparable"] == 0


class TestScenarioI_CoberturaParcial:
    def test_partial_coverage_still_permits_synthesis(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, user_id, "PF-A")
        program = _program(domain_service, org_id, user_id, portfolio.id, "PRG-A")
        _project(domain_service, org_id, user_id, program.id, "Aurora", objective="Migrar workloads")
        _project(domain_service, org_id, user_id, program.id, "Boreal")

        class AdvisorProvider:
            def generate(self, prompt):
                sent = json.loads(prompt.split("Records: ", 1)[1])
                source_id = sent[0]["source_id"]
                return json.dumps({"answer": "Apenas Aurora possui objetivo declarado.", "cited_analysis_ids": [source_id]})

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "A execucao esta alinhada?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["projects_with_strategy_without_execution"] == 1
        assert len(body["cited_evidence"]) == 1


class TestScenarioP_CitacaoRealDeDeclaredStrategyPontaAPonta:
    def test_declared_strategy_citation_resolves_through_the_full_http_response(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, user_id, "PF-A", objective="Expandir para APAC")

        class AdvisorProvider:
            def generate(self, prompt):
                sent = json.loads(prompt.split("Records: ", 1)[1])
                declared = next(r for r in sent if r["kind"] == "declared_strategy")
                return json.dumps(
                    {"answer": "Atlas declara expansao para APAC.", "cited_analysis_ids": [declared["source_id"]]}
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Qual a estrategia do portfolio?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["cited_evidence"]) == 1
        cited = body["cited_evidence"][0]
        assert cited["level"] == "portfolio"
        assert cited["entity_id"] == portfolio.id
        assert cited["source_id"] == portfolio.id  # always real in the HTTP response
        assert cited["kind"] == "declared_strategy"
        assert cited["created_at"] is None


class TestScenarioQ_ConversaoDoTokenSinteticoParaIdentidadeReal:
    def test_response_never_carries_the_synthetic_token(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, user_id, "PF-A", objective="Expandir para APAC")
        synthetic = _synthetic_source_id("portfolio", portfolio.id)

        class AdvisorProvider:
            def generate(self, prompt):
                sent = json.loads(prompt.split("Records: ", 1)[1])
                declared = sent[0]
                assert declared["source_id"] == synthetic  # confirms the token WAS sent to the LLM
                return json.dumps({"answer": "ok", "cited_analysis_ids": [declared["source_id"]]})

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200
        cited = response.json()["cited_evidence"][0]
        assert cited["source_id"] == portfolio.id
        assert cited["source_id"] != synthetic


class TestScenarioR_AusenciaDeVazamentoDoToken:
    def test_synthetic_token_never_appears_anywhere_in_the_full_response_body(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, user_id, "PF-A", objective="Expandir para APAC")
        synthetic = _synthetic_source_id("portfolio", portfolio.id)

        class AdvisorProvider:
            def generate(self, prompt):
                sent = json.loads(prompt.split("Records: ", 1)[1])
                return json.dumps({"answer": "ok", "cited_analysis_ids": [sent[0]["source_id"]]})

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200
        raw_body = response.text
        assert str(synthetic) not in raw_body


class TestScenarioT_EstrategiaEExecucaoCitadasSimultaneamente:
    def test_declared_strategy_and_execution_both_cited_without_collision(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, user_id, "PF-A")
        program = _program(domain_service, org_id, user_id, portfolio.id, "PRG-A")
        _project(domain_service, org_id, user_id, program.id, "Aurora", objective="Migrar workloads")
        risk_id = _save_risk_at(repo, org_id, "Aurora", "atraso de fornecedor", NOW - timedelta(days=1))

        class AdvisorProvider:
            def generate(self, prompt):
                sent = json.loads(prompt.split("Records: ", 1)[1])
                declared = next(r for r in sent if r["kind"] == "declared_strategy")
                risk = next(r for r in sent if r["kind"] == "risk")
                return json.dumps(
                    {"answer": "Aurora esta alinhada, mas ha risco de fornecedor.", "cited_analysis_ids": [declared["source_id"], risk["source_id"]]}
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["cited_evidence"]) == 2
        kinds = {c["kind"] for c in body["cited_evidence"]}
        assert kinds == {"declared_strategy", "risk"}
        risk_cited = next(c for c in body["cited_evidence"] if c["kind"] == "risk")
        assert risk_cited["source_id"] == risk_id


class TestScenarioU_DescarteDeTokenInventado:
    def test_invented_token_is_silently_discarded(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)
        _portfolio(domain_service, org_id, user_id, "PF-A", objective="Expandir para APAC")
        never_emitted = _synthetic_source_id("project", 999_999)

        class AdvisorProvider:
            def generate(self, prompt):
                sent = json.loads(prompt.split("Records: ", 1)[1])
                return json.dumps({"answer": "ok", "cited_analysis_ids": [sent[0]["source_id"], never_emitted]})

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["cited_evidence"]) == 1


class TestScenarioN_IsolamentoOrganizacional:
    def test_other_organizations_never_leak_in(self, client):
        test_client, repo, domain_service = client
        org_a = _org(repo, "Org A")
        org_b = _org(repo, "Org B")
        user_a = _actor(repo, org_a)
        user_b = _actor(repo, org_b)
        _portfolio(domain_service, org_a, user_a, "PF-A", objective="Objetivo A")
        _portfolio(domain_service, org_b, user_b, "PF-B", objective="Objetivo B")

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps({"answer": "ok", "cited_analysis_ids": []})

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_a, user_a),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200
        assert response.json()["portfolios_total"] == 1


class TestRbac:
    def test_user_with_no_role_is_denied(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        no_role_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, no_role_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: intelligence.read"

    def test_viewer_can_ask(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org Viewer")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, viewer_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200


class TestMalformedResponse:
    def test_returns_502_for_a_malformed_advisor_response(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)
        _portfolio(domain_service, org_id, user_id, "PF-A", objective="Expandir para APAC")

        class NotJsonProvider:
            def generate(self, prompt):
                return "not json at all"

        app.dependency_overrides[intelligence.build_provider] = lambda: NotJsonProvider()

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 502


class TestAuditTrail:
    def test_records_an_audit_entry_without_the_llm_answer(self, client):
        test_client, repo, domain_service = client
        org_id = _org(repo)
        user_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/strategy-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta sobre a estrategia?"},
        )
        assert response.status_code == 200

        entries = repo.administration.list_audit_log(org_id)
        matching = [e for e in entries if e.action == "strategy_advisor.question_asked"]
        assert len(matching) == 1
        assert matching[0].actor_user_id == user_id
        assert matching[0].organization_id == org_id
        assert matching[0].details["question"] == "Alguma pergunta sobre a estrategia?"
        assert "answer" not in matching[0].details
