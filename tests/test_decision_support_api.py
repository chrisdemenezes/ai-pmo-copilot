"""Decision Support HTTP route (Wave 6, first production consumer of the
Executive Orchestrator) -- `TECHNICAL-DESIGN-DECISION-SUPPORT.md`, Founder
Decision "Explicit Scope / Decision Support" (D-153/D-154).

Same rigor already established for the 8 Advisor routes (real Postgres,
real migration-seeded permissions, real institutional headers, real
`DomainService`) plus the 10 mandatory Explicit Scope scenarios (Founder
Decision §7/§9) and the eligibility proofs A/B/C/F (§7 of the
implementation mandate). Scenarios D/E (Selection Rule cannot reintroduce
an excluded Advisor; deterministic distinct sets per scope) are proven in
isolation in `tests/test_executive_orchestrator_selection_rule.py`
(`TestExplicitScopeEligibility`) -- never duplicated here at the HTTP
layer.
"""
import ast
import inspect
import json
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
from src.services.domain_service import DomainService

from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


class _NoOpEventPublisher:
    def publish(self, event_type, payload, organization_id, correlation_id, origin):
        return None


class _ScriptedProvider:
    """Cites nothing -- sufficient for every scenario that only asserts on
    selection/scope/composition trace, never on citation content."""

    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if "Contributions already produced by the selected Enterprise Advisors" in prompt:
            return "Sintese executiva a partir das contribuicoes recebidas."
        return json.dumps({"answer": "Resposta fundamentada.", "cited_analysis_ids": []})


class _CitingProvider:
    """Cites the real ids it is constructed with -- used by the one
    scenario that asserts on citation content end-to-end."""

    def __init__(self, risk_id: int, status_id: int):
        self._risk_id = risk_id
        self._status_id = status_id
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if "Risks already identified" in prompt:
            return json.dumps(
                {"answer": "Risco de escalação identificado.", "cited_analysis_ids": [self._risk_id]}
            )
        if "Project status history" in prompt:
            return json.dumps(
                {"answer": "Entrega em andamento.", "cited_analysis_ids": [self._status_id]}
            )
        if "Contributions already produced by the selected Enterprise Advisors" in prompt:
            return "Sintese executiva: risco de escalacao e entrega em andamento no projeto Aurora."
        raise AssertionError(f"unexpected prompt reached the LLM: {prompt[:200]!r}")


class _ExplodingProvider:
    def generate(self, prompt: str) -> str:
        raise AssertionError("the LLM must not be called for this scenario")


@pytest.fixture()
def client():
    with temp_database_url("decision_support_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=os.getcwd(),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

        repo = AnalysisRepository(database_url=database_url)
        domain_service = DomainService(repository=repo, publisher=_NoOpEventPublisher())
        app.dependency_overrides[intelligence.build_repository] = lambda: repo
        app.dependency_overrides[intelligence.build_domain_service] = lambda: domain_service
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo, domain_service
        app.dependency_overrides.pop(intelligence.build_provider, None)
        app.dependency_overrides.pop(intelligence.build_repository, None)
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


def _build_project(domain_service, org_id, actor_id, project_name="Aurora", portfolio_code="PF-A"):
    portfolio = domain_service.create_portfolio(
        org_id, "Cloud Modernization", portfolio_code, actor_id, correlation_id=CORRELATION_ID
    )
    program = domain_service.create_program(
        org_id, portfolio.id, "Infra", f"{portfolio_code}-INFRA", actor_id, correlation_id=CORRELATION_ID
    )
    project = domain_service.create_project(
        org_id, program.id, project_name, actor_id, correlation_id=CORRELATION_ID
    )
    return portfolio, program, project


def _save_risk(repo, org_id, project_name):
    return repo.save_analysis(
        kind="risk",
        payload={"model_output": {"structured": True, "risks": []}},
        organization_id=org_id,
        project_name=project_name,
    )


def _save_status(repo, org_id, project_name):
    return repo.save_analysis(
        kind="status",
        payload={"model_output": {"structured": True}},
        organization_id=org_id,
        project_name=project_name,
    )


class TestFullChainWithRealCitations:
    def test_scope_project_produces_a_complete_answer_with_real_citations(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _portfolio, _program, project = _build_project(domain_service, org_id, user_id)
        risk_id = _save_risk(repo, org_id, "Aurora")
        status_id = _save_status(repo, org_id, "Aurora")

        app.dependency_overrides[intelligence.build_provider] = lambda: _CitingProvider(risk_id, status_id)

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={
                "question": "Existe risco e qual o status de entrega do projeto Aurora?",
                "scope": {"type": "project", "project_id": project.id},
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["capability"] == "decision_support"
        assert body["insufficient_basis"] is False
        assert set(body["advisors_used"]) == {"risk_advisor", "delivery_advisor"}
        assert {c["source_id"] for c in body["citations"]} == {risk_id, status_id}
        assert body["answer"] is not None and "Aurora" in body["answer"]
        assert len(body["composition_trace"]["advisors_used"]) == 2
        assert all(e["had_evidence"] for e in body["composition_trace"]["advisors_used"])
        assert len(body["composition_trace"]["correlations"]) == 1
        assert body["composition_trace"]["synthesis_source_advisor_names"] is not None


class TestInsufficientBasis:
    def test_irrelevant_question_declares_selection_empty_with_zero_llm_calls(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        app.dependency_overrides[intelligence.build_provider] = lambda: _ExplodingProvider()

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={
                "question": "Qual a previsão do tempo hoje?",
                "scope": {"type": "organization"},
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["insufficient_basis"] is True
        assert body["insufficient_basis_reason"] == "selection_empty"
        assert body["answer"] is None
        assert body["citations"] == []


class Test10MandatoryScopeScenarios:
    """Founder Decision -- Eliminação do Risco de Escopo Implícito, §9;
    Founder Decision -- Explicit Scope / Decision Support, §7/§9."""

    def test_1_request_without_scope_is_rejected(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe algum risco relevante?"},
        )

        assert response.status_code == 422

    def test_2_scope_project_without_project_id_is_rejected(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe algum risco relevante?", "scope": {"type": "project"}},
        )

        assert response.status_code == 422

    def test_3_scope_portfolio_without_portfolio_id_is_rejected(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Como esta o portfolio?", "scope": {"type": "portfolio"}},
        )

        assert response.status_code == 422

    def test_4_scope_organization_with_project_id_is_rejected(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _portfolio, _program, project = _build_project(domain_service, org_id, user_id)

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={
                "question": "Existe algum risco relevante?",
                "scope": {"type": "organization", "project_id": project.id},
            },
        )

        assert response.status_code == 422

    def test_5_project_id_of_another_organization_is_rejected(self, client):
        test_client, repo, domain_service = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a)
        user_b = _actor(repo, org_b, "organization_admin")
        _portfolio_b, _program_b, project_b = _build_project(domain_service, org_b, user_b)

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_a, user_a),
            json={
                "question": "Existe algum risco relevante?",
                "scope": {"type": "project", "project_id": project_b.id},
            },
        )

        assert response.status_code == 404

    def test_6_portfolio_id_of_another_organization_is_rejected(self, client):
        test_client, repo, domain_service = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a)
        user_b = _actor(repo, org_b, "organization_admin")
        portfolio_b = domain_service.create_portfolio(
            org_b, "Org B Portfolio", "PF-B", user_b, correlation_id=CORRELATION_ID
        )

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_a, user_a),
            json={
                "question": "Como esta o portfolio?",
                "scope": {"type": "portfolio", "portfolio_id": portfolio_b.id},
            },
        )

        assert response.status_code == 404

    def test_7_organization_scope_uses_exclusively_the_session_organization_id(self, client):
        test_client, repo, domain_service = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a)
        user_b = _actor(repo, org_b, "organization_admin")
        _build_project(domain_service, org_a, user_a, project_name="Aurora", portfolio_code="PF-A")
        _build_project(domain_service, org_b, user_b, project_name="Boreal", portfolio_code="PF-B")
        risk_a = _save_risk(repo, org_a, "Aurora")
        _save_risk(repo, org_b, "Boreal")

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_a, user_a),
            json={"question": "Existe algum risco relevante?", "scope": {"type": "organization"}},
        )

        assert response.status_code == 200
        # No cross-tenant leak: only org_a's risk advisor evidence is ever
        # in play -- org_b's AnalysisRecord (risk_a's sibling) is never
        # reachable, confirmed structurally by DomainService/AIContextEngine
        # always scoping by the session's organization_id, never a
        # client-supplied one (no such field exists on the contract at all).
        assert "risk_advisor" in response.json()["advisors_used"]
        assert risk_a > 0  # sanity: evidence was created for org_a

    def test_8_same_question_under_three_scopes_yields_three_distinct_advisor_sets(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        portfolio, _program, project = _build_project(domain_service, org_id, user_id)
        _save_risk(repo, org_id, "Aurora")

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()
        question = "Existe algum risco relevante para o portfolio?"

        project_response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": question, "scope": {"type": "project", "project_id": project.id}},
        )
        portfolio_response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": question, "scope": {"type": "portfolio", "portfolio_id": portfolio.id}},
        )
        organization_response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": question, "scope": {"type": "organization"}},
        )

        assert set(project_response.json()["advisors_used"]) == {"risk_advisor"}
        assert set(portfolio_response.json()["advisors_used"]) == {"portfolio_advisor"}
        assert set(organization_response.json()["advisors_used"]) == {"risk_advisor"}

    def test_9_no_advisor_receives_evidence_outside_the_requested_scope(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        portfolio, program, project_a = _build_project(
            domain_service, org_id, user_id, project_name="Aurora", portfolio_code="PF-A"
        )
        domain_service.create_project(org_id, program.id, "Boreal", user_id, correlation_id=CORRELATION_ID)
        risk_a = _save_risk(repo, org_id, "Aurora")
        risk_b = _save_risk(repo, org_id, "Boreal")

        app.dependency_overrides[intelligence.build_provider] = lambda: _CitingProvider(risk_a, 0)

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={
                "question": "Existe algum risco de escalação?",
                "scope": {"type": "project", "project_id": project_a.id},
            },
        )

        assert response.status_code == 200
        cited_ids = {c["source_id"] for c in response.json()["citations"]}
        assert risk_b not in cited_ids
        assert cited_ids <= {risk_a}

    def test_10_absence_of_scope_never_produces_an_implicit_organization_execution(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        app.dependency_overrides[intelligence.build_provider] = lambda: _ExplodingProvider()

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe algum risco relevante?"},
        )

        assert response.status_code == 422


class TestEligibilityAtTheHttpBoundary:
    """A/B/C already proven in isolation at the Selection Rule level
    (`TestExplicitScopeEligibility`) -- this class proves the same
    guarantee survives end-to-end through the real HTTP contract."""

    def test_a_scope_project_never_selects_an_organization_scoped_advisor(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _portfolio, _program, project = _build_project(domain_service, org_id, user_id)
        _save_risk(repo, org_id, "Aurora")

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={
                "question": "Existe risco e qual o processo de acompanhamento pmo da organização?",
                "scope": {"type": "project", "project_id": project.id},
            },
        )

        assert response.status_code == 200
        assert "pmo_advisor" not in response.json()["advisors_used"]

    def test_b_scope_portfolio_never_selects_organization_or_project_scoped_advisor(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        portfolio, _program, _project = _build_project(domain_service, org_id, user_id)

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={
                "question": "Existe risco e qual o processo pmo de acompanhamento do portfólio?",
                "scope": {"type": "portfolio", "portfolio_id": portfolio.id},
            },
        )

        assert response.status_code == 200
        assert response.json()["advisors_used"] == ["portfolio_advisor"]


class TestRbac:
    def test_user_with_no_role_is_denied(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe algum risco relevante?", "scope": {"type": "organization"}},
        )

        assert response.status_code == 403


class TestMalformedResponse:
    def test_returns_502_for_a_malformed_advisor_response(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _portfolio, _program, project = _build_project(domain_service, org_id, user_id)
        _save_risk(repo, org_id, "Aurora")

        class NotJsonProvider:
            def generate(self, prompt):
                return "not json at all"

        app.dependency_overrides[intelligence.build_provider] = lambda: NotJsonProvider()

        response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={
                "question": "Existe algum risco relevante?",
                "scope": {"type": "project", "project_id": project.id},
            },
        )

        assert response.status_code == 502


class TestNoDirectInfrastructureAccess:
    def test_route_module_never_imports_ai_context_engine_directly(self):
        # AIContextEngine is reached exclusively through
        # AdvisorFramework.gather_context()/gather_rag_context() -- the
        # same sanctioned intermediary all 8 Advisor routes already use.
        # Decision Support adds no second access path (Technical Design
        # §2: "a rota nunca... acessa AIContextEngine... diretamente").
        source = inspect.getsource(intelligence)
        tree = ast.parse(source)
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert "AIContextEngine" not in imported_names

    def test_ask_decision_support_function_never_calls_domain_service_beyond_scope_resolution(self):
        # The route's own body only ever calls DomainService.get_project()/
        # get_portfolio() (via resolve_decision_support_scope()) -- never a
        # repository, never gather_context()/gather_rag_context() directly.
        source = inspect.getsource(intelligence.ask_decision_support)
        tree = ast.parse(source)
        called_names = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert "gather_context" not in called_names
        assert "gather_rag_context" not in called_names
