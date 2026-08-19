"""Executive Orchestrator, Etapa 3 -- ciclo completo (Selection -> Execution
-> Correlation -> Composition Trace -> Executive Intelligence Result), ainda
sem síntese (Founder Decision "Implementação do Executive Orchestrator").
Prova com Advisors reais (`RiskAdvisorAgent`/`DeliveryAdvisorAgent`) via
`AdvisorFramework`, nunca `_FakeAdvisor` -- mesmo padrão de
`test_risk_advisor_migration.py`. Runs on real PostgreSQL (`tests/db.py`).
"""
import ast
import inspect
import json
from datetime import datetime, timezone

import pytest

from src.database.repository import AnalysisRepository
from src.llm.providers.mock_provider import MockLLMProvider
from src.prompts.registry import PromptRegistry
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import SessionContext
from src.services.domain_service import DomainService
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.events.interfaces import DomainEvent
from src.services.executive_orchestrator import orchestrator as orchestrator_module
from src.services.executive_orchestrator import provisioning as provisioning_module
from src.services.executive_orchestrator.orchestrator import ExecutiveOrchestrator
from src.services.executive_orchestrator.selection_rule import SelectionSignals
from src.services.executive_orchestrator.types import (
    Capability,
    InsufficientBasisReason,
)
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.rag_pipeline import RagPipeline
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from tests.db import temp_database_url


class _ScriptedProvider:
    """Same convention as `test_risk_advisor_migration.py`'s
    `_ScriptedProvider` -- a fixed, valid JSON answer, deterministic, no
    network call."""

    def __init__(self, answer: str = "synthesized answer"):
        self.answer = answer
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return json.dumps({"answer": self.answer, "cited_analysis_ids": []})


class _AllCitingProvider:
    """Cites every id it is constructed with -- used to prove citation
    preservation end to end."""

    def __init__(self, cited_analysis_ids: list[int]):
        self.cited_analysis_ids = cited_analysis_ids
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return json.dumps({"answer": "synthesis citing everything", "cited_analysis_ids": self.cited_analysis_ids})


class _RecordingEventPublisher:
    def publish(self, event_type, payload, organization_id, correlation_id, origin) -> DomainEvent:
        return DomainEvent(
            event_id="fake-event-id",
            event_type=event_type,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
            organization_id=organization_id,
            origin=origin,
            payload_version=1,
            payload=payload,
        )


@pytest.fixture()
def repo():
    with temp_database_url("executive_orchestrator") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def knowledge_repository(repo):
    vector_repository = PgVectorRepository(repo.SessionLocal)
    event_publisher = InProcessEventPublisher(repo.SessionLocal, EventDispatcher(repo.SessionLocal))
    return KnowledgeRepository(repo.SessionLocal, MockEmbeddingProvider(), vector_repository, event_publisher)


@pytest.fixture()
def domain_service(repo):
    return DomainService(repository=repo, publisher=_RecordingEventPublisher())


def _framework(repo, knowledge_repository, provider):
    return AdvisorFramework(
        repository=repo,
        prompt_registry=PromptRegistry(base_path="src/agents"),
        llm_provider=provider,
        rag_pipeline=RagPipeline(knowledge_repository),
    )


def _orchestrator(repo, knowledge_repository, domain_service, provider):
    return ExecutiveOrchestrator(
        _framework(repo, knowledge_repository, provider),
        domain_service,
        provider,
        PromptRegistry(base_path="src/services"),
    )


def _session(repo, org_id: int, project_name: str = "Aurora") -> SessionContext:
    user_id = repo.enterprise.create_user(org_id, "founder@stratech.example", "Founder")
    return SessionContext(
        organization_id=org_id, user_id=user_id, session_id="s-1", project_name=project_name
    )


class TestSelectionEmpty:
    def test_no_advisor_is_invoked_and_no_evidence_is_gathered(self, repo, knowledge_repository, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        provider = _ScriptedProvider()
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            _session(repo, org_id),
            "Qual a previsão do tempo hoje?",
            SelectionSignals(question="Qual a previsão do tempo hoje?"),
        )

        assert result.is_insufficient_basis is True
        assert result.insufficient_basis_reason == InsufficientBasisReason.SELECTION_EMPTY
        assert result.advisor_identities == ()
        assert provider.calls == 0


class TestCollectionEmpty:
    def test_selected_advisors_with_no_evidence_declare_base_insuficiente(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        provider = _ScriptedProvider()
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            _session(repo, org_id),
            "Existe algum risco de escalação neste projeto?",
            SelectionSignals(explicit=frozenset({"risco"})),
        )

        assert result.is_insufficient_basis is True
        assert result.insufficient_basis_reason == InsufficientBasisReason.COLLECTION_EMPTY
        assert [identity.name for identity in result.advisor_identities] == ["risk_advisor"]
        assert result.explanations[0].explanation.recommendation.cited_evidence == []
        assert provider.calls == 0  # no_evidence() never calls the LLM


class TestSingleAdvisor:
    def test_a_single_selected_advisor_produces_a_complete_result(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        analysis_id = repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _ScriptedProvider(answer="one risk identified")
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            _session(repo, org_id),
            "Existe risco neste projeto?",
            SelectionSignals(explicit=frozenset({"risco"})),
        )

        assert result.is_insufficient_basis is False
        assert [identity.name for identity in result.advisor_identities] == ["risk_advisor"]
        assert len(result.explanations) == 1
        assert result.explanations[0].advisor_name == "risk_advisor"
        assert result.explanations[0].explanation.recommendation.answer == "one risk identified"
        # No structural pair with only one Advisor -- no correlation possible.
        assert result.correlation == ()
        assert analysis_id  # the evidence gathered really exists


class TestMultipleAdvisors:
    def test_two_selected_advisors_are_both_invoked_independently(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        repo.save_analysis(
            kind="status",
            payload={"model_output": {"structured": True}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _ScriptedProvider(answer="grounded synthesis")
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        # Cross Advisor Correlation never includes Síntese (AR-17 §2) --
        # keeps this test's "one call per Advisor" assertion exclusively
        # about Execução, unaffected by Etapa 4.
        result = orchestrator.run(
            Capability.CROSS_ADVISOR_CORRELATION,
            _session(repo, org_id),
            "Quais os riscos e o status de entrega deste projeto?",
            SelectionSignals(explicit=frozenset({"risco", "entrega"})),
        )

        assert result.is_insufficient_basis is False
        assert {identity.name for identity in result.advisor_identities} == {"risk_advisor", "delivery_advisor"}
        assert {item.advisor_name for item in result.explanations} == {"risk_advisor", "delivery_advisor"}
        assert provider.calls == 2  # one independent LLM call per Advisor

    def test_two_grounded_advisors_produce_a_structural_correlation_finding(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        risk_id = repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        status_id = repo.save_analysis(
            kind="status",
            payload={"model_output": {"structured": True}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _AllCitingProvider([risk_id, status_id])
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.CROSS_ADVISOR_CORRELATION,
            _session(repo, org_id),
            "Quais os riscos e o status de entrega deste projeto?",
            SelectionSignals(explicit=frozenset({"risco", "entrega"})),
        )

        assert len(result.correlation) == 1
        finding = result.correlation[0]
        assert finding.advisor_names == ("delivery_advisor", "risk_advisor")
        assert finding.is_structural_pair is True

    def test_conflict_analysis_keeps_only_structural_pair_findings(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        risk_id = repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        status_id = repo.save_analysis(
            kind="status",
            payload={"model_output": {"structured": True}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _AllCitingProvider([risk_id, status_id])
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.CONFLICT_ANALYSIS,
            _session(repo, org_id),
            "Quais os riscos e o status de entrega deste projeto?",
            SelectionSignals(explicit=frozenset({"risco", "entrega"})),
        )

        assert all(finding.is_structural_pair for finding in result.correlation)


class TestCompositionTrace:
    def test_trace_records_selection_and_every_execution(self, repo, knowledge_repository, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _ScriptedProvider()
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            _session(repo, org_id),
            "Existe risco neste projeto?",
            SelectionSignals(explicit=frozenset({"risco"})),
        )

        trace = result.composition_trace
        assert trace.selection is not None
        assert trace.selection.selected_advisor_names == ("risk_advisor",)
        assert len(trace.executions) == 1
        assert trace.executions[0].advisor_name == "risk_advisor"
        assert trace.executions[0].had_evidence is True

    def test_trace_is_produced_even_when_selection_is_empty(self, repo, knowledge_repository, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        provider = _ScriptedProvider()
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            _session(repo, org_id),
            "irrelevante",
            SelectionSignals(question="irrelevante"),
        )

        assert result.composition_trace.selection is not None
        assert result.composition_trace.executions == ()


class TestCitationPreservation:
    def test_cited_evidence_traces_back_to_the_real_analysis_record(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        analysis_id = repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = MockLLMProvider(
            response=json.dumps({"answer": "grounded", "cited_analysis_ids": [analysis_id]})
        )
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            _session(repo, org_id),
            "Existe risco neste projeto?",
            SelectionSignals(explicit=frozenset({"risco"})),
        )

        cited = result.explanations[0].explanation.recommendation.cited_evidence
        assert [item.source_id for item in cited] == [analysis_id]


class TestRequestScoped:
    def test_two_sequential_calls_never_leak_state_between_them(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _ScriptedProvider()
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)
        session = _session(repo, org_id)

        first = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            session,
            "Existe risco neste projeto?",
            SelectionSignals(explicit=frozenset({"risco"})),
        )
        second = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            session,
            "Qual a previsão do tempo hoje?",
            SelectionSignals(question="Qual a previsão do tempo hoje?"),
        )

        assert first.is_insufficient_basis is False
        assert second.is_insufficient_basis is True
        assert second.insufficient_basis_reason == InsufficientBasisReason.SELECTION_EMPTY

    def test_orchestrator_instance_holds_no_state_beyond_its_injected_dependencies(
        self, repo, knowledge_repository, domain_service
    ):
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, _ScriptedProvider())

        assert set(vars(orchestrator).keys()) == {
            "_framework",
            "_domain_service",
            "_llm_provider",
            "_prompt_registry",
        }


class TestNoDirectInfrastructureAccess:
    def test_orchestrator_never_imports_a_repository_or_domain_access_class_directly(self):
        source = inspect.getsource(orchestrator_module)
        tree = ast.parse(source)
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        forbidden = {"AnalysisRepository", "PgVectorRepository", "KnowledgeRepository", "DomainRepository"}
        assert not (imported_names & forbidden)

    def test_provisioning_never_imports_a_repository_class_directly(self):
        source = inspect.getsource(provisioning_module)
        tree = ast.parse(source)
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        forbidden = {"AnalysisRepository", "PgVectorRepository", "KnowledgeRepository", "DomainRepository"}
        assert not (imported_names & forbidden)


class TestSynthesis:
    """Etapa 4 -- Selection -> Execution -> Correlation -> Synthesis ->
    Composition Trace -> Executive Intelligence Result."""

    def test_a_capability_with_synthesis_produces_one(self, repo, knowledge_repository, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        risk_id = repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _AllCitingProvider([risk_id])
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            _session(repo, org_id),
            "Existe risco neste projeto?",
            SelectionSignals(explicit=frozenset({"risco"})),
        )

        assert result.synthesis is not None
        assert result.composition_trace.synthesis is not None
        assert result.composition_trace.synthesis.source_advisor_names == ("risk_advisor",)
        # one LLM call for the Advisor's own analysis, a second for the Síntese
        assert provider.calls == 2

    def test_cross_advisor_correlation_never_produces_a_synthesis(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _ScriptedProvider()
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.CROSS_ADVISOR_CORRELATION,
            _session(repo, org_id),
            "Existe risco neste projeto?",
            SelectionSignals(explicit=frozenset({"risco"})),
        )

        assert result.synthesis is None
        assert result.composition_trace.synthesis is None
        assert provider.calls == 1  # only the Advisor's own call, never a Síntese call

    def test_conflict_analysis_never_produces_a_synthesis(self, repo, knowledge_repository, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        provider = _ScriptedProvider()
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.CONFLICT_ANALYSIS,
            _session(repo, org_id),
            "Existe risco neste projeto?",
            SelectionSignals(explicit=frozenset({"risco"})),
        )

        assert result.synthesis is None
        assert result.composition_trace.synthesis is None

    def test_synthesis_source_advisor_names_excludes_ungrounded_advisors(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        risk_id = repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        # delivery_advisor is selected (explicit signal) but has zero evidence
        # for this project -- partial coverage (Domain Blueprint §4) --
        # never invoked via the LLM, so it can never be cited.
        provider = _AllCitingProvider([risk_id])
        orchestrator = _orchestrator(repo, knowledge_repository, domain_service, provider)

        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE,
            _session(repo, org_id),
            "Existe risco ou status de entrega neste projeto?",
            SelectionSignals(explicit=frozenset({"risco", "entrega"})),
        )

        assert result.is_insufficient_basis is False
        assert {identity.name for identity in result.advisor_identities} == {"risk_advisor", "delivery_advisor"}
        assert result.composition_trace.synthesis.source_advisor_names == ("risk_advisor",)
