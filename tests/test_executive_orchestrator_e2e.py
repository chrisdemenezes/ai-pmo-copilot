"""Executive Orchestrator, Etapa 5 -- validação ponta a ponta (Founder
Decision "Implementação do Executive Orchestrator"). Proves the full chain
mandated:

    Pergunta -> Selection Rule -> Advisor Identities -> AdvisorFramework
    .run() -> Explanations -> Correlation -> Composition Trace ->
    Executive Intelligence Result -> Resposta Executiva

against real Advisors (`RiskAdvisorAgent`/`DeliveryAdvisorAgent`) and real
PostgreSQL (`tests/db.py`) -- never `_FakeAdvisor`, never a mock domain.
"""
import json
from datetime import datetime, timezone

import pytest

from src.database.repository import AnalysisRepository
from src.prompts.registry import PromptRegistry
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import SessionContext
from src.services.domain_service import DomainService
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.events.interfaces import DomainEvent
from src.services.executive_orchestrator.orchestrator import ExecutiveOrchestrator
from src.services.executive_orchestrator.selection_rule import SelectionSignals
from src.services.executive_orchestrator.types import Capability
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.rag_pipeline import RagPipeline
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from tests.db import temp_database_url


class _EndToEndProvider:
    """Deterministic, no network call. Cites the real `AnalysisRecord` ids
    it is constructed with for every per-Advisor call; returns a plain-text
    executive narrative (never JSON) for the Síntese call -- proving
    `synthesize()`'s raw-text fallback survives the full chain too."""

    def __init__(self, risk_id: int, status_id: int):
        self._risk_id = risk_id
        self._status_id = status_id
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        # Each Advisor's own template (and the Síntese template) has a
        # fixed, unique phrase never shared with the others -- the $question
        # substitution alone (e.g. the word "Aurora") is never a reliable
        # discriminator, since it is echoed verbatim into every prompt.
        if "Risks already identified" in prompt:
            return json.dumps(
                {"answer": "Um risco de escalação foi identificado.", "cited_analysis_ids": [self._risk_id]}
            )
        if "Project status history" in prompt:
            return json.dumps(
                {"answer": "A entrega está em andamento.", "cited_analysis_ids": [self._status_id]}
            )
        if "Contributions already produced by the selected Enterprise Advisors" in prompt:
            return (
                "Síntese executiva: o projeto Aurora tem um risco de escalação identificado e "
                "a entrega segue em andamento, segundo o Risk Advisor e o Delivery Advisor."
            )
        raise AssertionError(f"unexpected prompt reached the LLM: {prompt[:200]!r}")


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
    with temp_database_url("executive_orchestrator_e2e") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def knowledge_repository(repo):
    vector_repository = PgVectorRepository(repo.SessionLocal)
    event_publisher = InProcessEventPublisher(repo.SessionLocal, EventDispatcher(repo.SessionLocal))
    return KnowledgeRepository(repo.SessionLocal, MockEmbeddingProvider(), vector_repository, event_publisher)


@pytest.fixture()
def domain_service(repo):
    return DomainService(repository=repo, publisher=_RecordingEventPublisher())


class TestEndToEnd:
    def test_full_chain_from_question_to_executive_response(
        self, repo, knowledge_repository, domain_service
    ):
        # Pergunta: an organization with real, independently-produced
        # execution evidence for the same project (Aurora) -- exactly the
        # shape a real question about "risks and delivery status" arrives
        # against in production.
        org_id = repo.enterprise.create_organization("Aurora Org")
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
        user_id = repo.enterprise.create_user(org_id, "founder@stratech.example", "Founder")
        session = SessionContext(
            organization_id=org_id, user_id=user_id, session_id="s-e2e", project_name="Aurora"
        )

        provider = _EndToEndProvider(risk_id, status_id)
        framework = AdvisorFramework(
            repository=repo,
            prompt_registry=PromptRegistry(base_path="src/agents"),
            llm_provider=provider,
            rag_pipeline=RagPipeline(knowledge_repository),
        )
        orchestrator = ExecutiveOrchestrator(
            framework, domain_service, provider, PromptRegistry(base_path="src/services")
        )

        # Selection Rule -> Advisor Identities: explicit signals identify
        # both Risk Advisor and Delivery Advisor, deterministically.
        signals = SelectionSignals(explicit=frozenset({"risco", "entrega"}))

        # AdvisorFramework.run() -> Explanations -> Correlation ->
        # Composition Trace -> Executive Intelligence Result -> Resposta
        # Executiva, all through one call to ExecutiveOrchestrator.run().
        result = orchestrator.run(
            Capability.DECISION_SUPPORT,
            session,
            "Existe risco e qual o status de entrega do projeto Aurora?",
            signals,
        )

        # -- Selection Rule / Advisor Identities --
        assert result.is_insufficient_basis is False
        assert {identity.name for identity in result.advisor_identities} == {
            "risk_advisor",
            "delivery_advisor",
        }
        assert result.composition_trace.selection.selected_advisor_names == (
            "risk_advisor",
            "delivery_advisor",
        )

        # -- AdvisorFramework.run() / Explanations --
        assert len(result.explanations) == 2
        by_advisor = {item.advisor_name: item.explanation for item in result.explanations}
        assert by_advisor["risk_advisor"].recommendation.answer == "Um risco de escalação foi identificado."
        assert [e.source_id for e in by_advisor["risk_advisor"].recommendation.cited_evidence] == [risk_id]
        assert by_advisor["delivery_advisor"].recommendation.answer == "A entrega está em andamento."
        assert [e.source_id for e in by_advisor["delivery_advisor"].recommendation.cited_evidence] == [
            status_id
        ]
        assert len(result.composition_trace.executions) == 2
        assert all(entry.had_evidence for entry in result.composition_trace.executions)

        # -- Correlation --
        assert len(result.correlation) == 1
        finding = result.correlation[0]
        assert finding.advisor_names == ("delivery_advisor", "risk_advisor")
        assert finding.is_structural_pair is True  # Delivery+Risk, AR-17 §3
        assert len(result.composition_trace.correlations) == 1

        # -- Composition Trace: full chain accounted for --
        trace = result.composition_trace
        assert trace.selection is not None
        assert len(trace.executions) == 2
        assert len(trace.correlations) == 1
        assert trace.synthesis is not None
        assert set(trace.synthesis.source_advisor_names) == {"risk_advisor", "delivery_advisor"}

        # -- Executive Intelligence Result / Resposta Executiva --
        assert result.capability == Capability.DECISION_SUPPORT
        assert result.synthesis is not None
        assert "Aurora" in result.synthesis
        assert "Risk Advisor" in result.synthesis or "risco" in result.synthesis.lower()

        # Exactly three LLM calls: one per Advisor, one for the Síntese --
        # never more, never a call the chain didn't account for.
        assert provider.calls == 3

    def test_full_chain_declares_base_insuficiente_when_nothing_matches(
        self, repo, knowledge_repository, domain_service
    ):
        org_id = repo.enterprise.create_organization("Empty Org")
        user_id = repo.enterprise.create_user(org_id, "founder@stratech.example", "Founder")
        session = SessionContext(organization_id=org_id, user_id=user_id, session_id="s-e2e-empty")

        provider = _EndToEndProvider(risk_id=0, status_id=0)
        framework = AdvisorFramework(
            repository=repo,
            prompt_registry=PromptRegistry(base_path="src/agents"),
            llm_provider=provider,
            rag_pipeline=RagPipeline(knowledge_repository),
        )
        orchestrator = ExecutiveOrchestrator(
            framework, domain_service, provider, PromptRegistry(base_path="src/services")
        )

        result = orchestrator.run(
            Capability.DECISION_SUPPORT,
            session,
            "Qual a previsão do tempo hoje?",
            SelectionSignals(question="Qual a previsão do tempo hoje?"),
        )

        assert result.is_insufficient_basis is True
        assert result.synthesis is None
        assert result.correlation == ()
        assert provider.calls == 0
