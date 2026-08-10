"""Executive Narrative HTTP route (Wave 6, second production consumer of
the Executive Orchestrator) -- `TECHNICAL-DESIGN-EXECUTIVE-NARRATIVE.md`,
Founder Decision "Technical Design Executive Narrative" (D-160/D-161).

Same rigor already established for Decision Support (`test_decision_
support_api.py`): real Postgres, real migration-seeded permissions, real
institutional headers, real `DomainService`. Covers the 11 mandatory
scenarios of the implementation mandate: scope eligibility (1-3),
insufficient basis (4), partial coverage (5), non-aliasing against Decision
Support (6), absence of `question` in the contract (7), no direct
infrastructure access (8), plus RBAC and malformed-response rigor already
standard for every Executive Intelligence route. Items 9/10 (Executive
Orchestrator and Selection Rules remain unchanged) are proven by `git diff`
in the Etapa 3 Executive Evidence, never by a pytest assertion here -- an
unchanged file is not a runtime behavior to test.
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
from src.api import dependencies as dependencies_module
from src.api.routes import intelligence
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.domain_service import DomainService
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.vector_repository import PgVectorRepository

from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"

# The 7 Advisor Identities eligible under scope=organization, per
# `ADVISOR_ELIGIBLE_SCOPES` (catalog.py) -- portfolio_advisor is excluded
# because its structural precondition (a real `portfolio_id`) is never met
# under a bare organization scope, exactly the same behavior already proven
# for Decision Support (D-154).
ORGANIZATION_ELIGIBLE_ADVISORS = {
    "risk_advisor",
    "delivery_advisor",
    "pmo_advisor",
    "executive_advisor",
    "strategy_advisor",
    "document_advisor",
    "governance_advisor",
}


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
            return "Síntese executiva a partir das contribuições recebidas."
        return json.dumps({"answer": "Resposta fundamentada.", "cited_analysis_ids": []})


class _CitingProvider:
    """Cites the real id it is constructed with -- used by the partial-
    coverage scenario that asserts citations are traceable to real
    evidence."""

    def __init__(self, risk_id: int):
        self._risk_id = risk_id

    def generate(self, prompt: str) -> str:
        if "Risks already identified" in prompt:
            return json.dumps(
                {"answer": "Risco de escalação identificado.", "cited_analysis_ids": [self._risk_id]}
            )
        if "Contributions already produced by the selected Enterprise Advisors" in prompt:
            return "Síntese executiva: risco de escalação identificado no projeto Aurora."
        return json.dumps({"answer": "Resposta fundamentada.", "cited_analysis_ids": []})


class _ExplodingProvider:
    def generate(self, prompt: str) -> str:
        raise AssertionError("the LLM must not be called for this scenario")


class _DualRagCitingProvider:
    """Cites the same evidence id from both RAG-based Advisors
    (document_advisor, governance_advisor) -- the real duplication scenario
    diagnosed in the Wave 6 Consolidation Review (D-164): both call
    `gather_rag_context()` with identical arguments (same organization,
    same question), so both receive the exact same chunk pool and may cite
    the same chunk independently."""

    def __init__(self, chunk_id: int):
        self._chunk_id = chunk_id

    def generate(self, prompt: str) -> str:
        if "Indexed document chunks" in prompt or "Governance document chunks" in prompt:
            return json.dumps(
                {
                    "answer": "Resposta fundamentada no documento indexado.",
                    "cited_analysis_ids": [self._chunk_id],
                }
            )
        if "Contributions already produced by the selected Enterprise Advisors" in prompt:
            return "Síntese executiva a partir das contribuições recebidas."
        return json.dumps({"answer": "Resposta fundamentada.", "cited_analysis_ids": []})


@pytest.fixture()
def client():
    with temp_database_url("executive_narrative_api") as database_url:
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


class TestScopeEligibility:
    """Founder mandate items 1-3: the set of `advisors_used` for each scope
    matches exactly what `ADVISOR_ELIGIBLE_SCOPES` (catalog.py, unmodified)
    already declares -- proving `explicit`=all 8 catalog names plus the
    existing eligibility table is sufficient, no new selection logic."""

    def test_scope_project_selects_only_risk_and_delivery_advisors(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _portfolio, _program, project = _build_project(domain_service, org_id, user_id)
        _save_risk(repo, org_id, "Aurora")

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()

        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "project", "project_id": project.id}},
        )

        assert response.status_code == 200
        body = response.json()
        assert set(body["advisors_used"]) == {"risk_advisor", "delivery_advisor"}
        assert body["scope"] == {"type": "project", "project_id": project.id, "portfolio_id": None}

    def test_scope_portfolio_selects_only_portfolio_advisor(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        portfolio, _program, _project = _build_project(domain_service, org_id, user_id)

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()

        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "portfolio", "portfolio_id": portfolio.id}},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["advisors_used"] == ["portfolio_advisor"]
        assert body["scope"]["type"] == "portfolio"

    def test_scope_organization_selects_the_full_eligible_set_per_catalog(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _build_project(domain_service, org_id, user_id)
        _save_risk(repo, org_id, "Aurora")

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()

        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "organization"}},
        )

        assert response.status_code == 200
        body = response.json()
        assert set(body["advisors_used"]) == ORGANIZATION_ELIGIBLE_ADVISORS
        assert "portfolio_advisor" not in body["advisors_used"]


class TestInsufficientBasis:
    def test_zero_evidence_declares_insufficient_basis_with_no_synthesis(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _portfolio, _program, project = _build_project(domain_service, org_id, user_id)
        # No analyses saved at all -- both risk_advisor and delivery_advisor
        # gather zero evidence, so AdvisorFramework.run() short-circuits to
        # its own no-evidence answer for each, never reaching the LLM.
        app.dependency_overrides[intelligence.build_provider] = lambda: _ExplodingProvider()

        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "project", "project_id": project.id}},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["insufficient_basis"] is True
        # Selection Empty structurally never occurs for a validly resolved
        # scope (Technical Design §5.4) -- the real, exhaustive reason here
        # is Collection Empty (Advisors selected, none produced evidence).
        assert body["insufficient_basis_reason"] == "collection_empty"
        assert body["narrative"] is None
        assert body["citations"] == []


class TestPartialCoverage:
    def test_partial_evidence_still_produces_a_narrative_with_traceable_citations(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _portfolio, _program, project = _build_project(domain_service, org_id, user_id)
        # Only risk_advisor has evidence -- delivery_advisor is selected
        # (same scope) but gathers none, exercising the partial-coverage
        # path: overall result is still `.complete()` (any_had_evidence is
        # True), never insufficient_basis, but the composition trace
        # preserves which Advisor actually contributed.
        risk_id = _save_risk(repo, org_id, "Aurora")

        app.dependency_overrides[intelligence.build_provider] = lambda: _CitingProvider(risk_id)

        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "project", "project_id": project.id}},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["insufficient_basis"] is False
        assert body["narrative"] is not None
        assert {c["source_id"] for c in body["citations"]} == {risk_id}
        assert all(c["advisor_names"] == ["risk_advisor"] for c in body["citations"])
        trace_by_advisor = {e["advisor_name"]: e["had_evidence"] for e in body["composition_trace"]["advisors_used"]}
        assert trace_by_advisor["risk_advisor"] is True
        assert trace_by_advisor["delivery_advisor"] is False


class TestNonAliasing:
    def test_decision_support_and_executive_narrative_select_structurally_different_advisor_sets(
        self, client
    ):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _build_project(domain_service, org_id, user_id)
        _save_risk(repo, org_id, "Aurora")

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()

        # A narrow, lexically specific question -- Decision Support selects
        # only risk_advisor via vocabulary matching.
        decision_support_response = test_client.post(
            "/api/decision-support/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe algum risco relevante?", "scope": {"type": "organization"}},
        )
        narrative_response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "organization"}},
        )

        assert decision_support_response.status_code == 200
        assert narrative_response.status_code == 200
        decision_support_advisors = set(decision_support_response.json()["advisors_used"])
        narrative_advisors = set(narrative_response.json()["advisors_used"])
        assert decision_support_advisors == {"risk_advisor"}
        assert narrative_advisors == ORGANIZATION_ELIGIBLE_ADVISORS
        assert decision_support_advisors != narrative_advisors


class TestContractShape:
    def test_request_contract_has_no_question_field(self):
        assert "question" not in intelligence.ExecutiveNarrativeRequest.model_fields

    def test_a_question_field_sent_by_a_misbehaving_client_is_silently_ignored(self, client):
        test_client, repo, domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)
        _build_project(domain_service, org_id, user_id)
        _save_risk(repo, org_id, "Aurora")

        app.dependency_overrides[intelligence.build_provider] = lambda: _ScriptedProvider()

        # A `question` field narrow enough to select a single Advisor under
        # Decision Support's lexical matching -- if Executive Narrative ever
        # consumed it, the selection would narrow too.
        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "organization"}, "question": "documentos"},
        )

        assert response.status_code == 200
        assert set(response.json()["advisors_used"]) == ORGANIZATION_ELIGIBLE_ADVISORS


class TestNoDirectInfrastructureAccess:
    def test_generate_executive_narrative_function_never_calls_domain_service_beyond_scope_resolution(self):
        source = inspect.getsource(intelligence.generate_executive_narrative)
        tree = ast.parse(source)
        called_names = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert "gather_context" not in called_names
        assert "gather_rag_context" not in called_names


class TestRbac:
    def test_user_with_no_role_is_denied(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "organization"}},
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
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "project", "project_id": project.id}},
        )

        assert response.status_code == 502


class TestExplicitScope:
    """Founder mandate item 11: scope remains obrigatório, same guarantee
    already proven for Decision Support, reused unmodified (`ExplicitScope`)."""

    def test_request_without_scope_is_rejected(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/executive-narrative/generate", headers=_headers(org_id, user_id), json={}
        )

        assert response.status_code == 422

    def test_scope_project_without_project_id_is_rejected(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_id, user_id),
            json={"scope": {"type": "project"}},
        )

        assert response.status_code == 422

    def test_project_id_of_another_organization_is_rejected(self, client):
        test_client, repo, domain_service = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a)
        user_b = _actor(repo, org_b, "organization_admin")
        _portfolio_b, _program_b, project_b = _build_project(domain_service, org_b, user_b)

        response = test_client.post(
            "/api/executive-narrative/generate",
            headers=_headers(org_a, user_a),
            json={"scope": {"type": "project", "project_id": project_b.id}},
        )

        assert response.status_code == 404


class TestCitationConsolidation:
    """Founder Decision -- Wave 6 Final Consolidation Actions (D-165): the
    real duplication scenario diagnosed in the Wave 6 Consolidation Review
    (D-164) -- `document_advisor`/`governance_advisor` both query the same
    RAG pool under `scope=organization` -- proven end to end here, through
    the real HTTP route, a real ingested/indexed document, and a real
    Postgres-backed `KnowledgeRepository`/`RagPipeline`. The pure-function
    scenarios A-G are covered in isolation by
    `tests/test_executive_intelligence_citation_consolidation.py`."""

    def test_two_rag_advisors_citing_the_same_chunk_consolidate_into_one_source(self, client):
        test_client, repo, _domain_service = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id)

        dispatcher = EventDispatcher(repo.SessionLocal)
        event_publisher = InProcessEventPublisher(repo.SessionLocal, dispatcher)
        knowledge_repository = KnowledgeRepository(
            repo.SessionLocal, MockEmbeddingProvider(), PgVectorRepository(repo.SessionLocal), event_publisher
        )
        document = knowledge_repository.ingest(org_id, "runbook.md", "conteudo indexado relevante")
        knowledge_repository.index(document.id, CORRELATION_ID)

        app.dependency_overrides[dependencies_module.build_event_publisher] = lambda: event_publisher
        app.dependency_overrides[intelligence.build_provider] = lambda: _DualRagCitingProvider(chunk_id=1)

        try:
            response = test_client.post(
                "/api/executive-narrative/generate",
                headers=_headers(org_id, user_id),
                json={"scope": {"type": "organization"}},
            )
        finally:
            app.dependency_overrides.pop(dependencies_module.build_event_publisher, None)

        assert response.status_code == 200
        body = response.json()
        assert body["insufficient_basis"] is False
        # Both document_advisor and governance_advisor cited the exact same
        # chunk -- the only one indexed for this organization -- consolidated
        # into a single citation, never presented as two independent
        # confirmations of the same primary source.
        document_chunk_citations = [c for c in body["citations"] if c["source_type"] == "document_chunk"]
        assert len(document_chunk_citations) == 1
        assert document_chunk_citations[0]["source_id"] == 1
        assert set(document_chunk_citations[0]["advisor_names"]) == {"document_advisor", "governance_advisor"}
        # Composition Trace still attributes each Advisor's own execution
        # individually -- consolidation touches only `citations`, never
        # `composition_trace.advisors_used`.
        trace_by_advisor = {
            e["advisor_name"]: e["had_evidence"] for e in body["composition_trace"]["advisors_used"]
        }
        assert trace_by_advisor["document_advisor"] is True
        assert trace_by_advisor["governance_advisor"] is True
