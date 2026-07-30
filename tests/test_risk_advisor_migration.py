"""Wave 3 Fase 4 -- Risk Advisor migration onto `AdvisorFramework`.

Proves, against the REAL `RiskAdvisorAgent` (never `_FakeAdvisor`), the
end-to-end chain the Founder mandated:

    Risk Advisor -> Advisor Framework -> Gather Context -> RagPipeline ->
    KnowledgeRepository -> traceable context -> LLMProvider -> Response ->
    Audit

Covers exactly the Founder's mandatory evidence points: chunk_id
traceability, `no_evidence()` without an LLM call, absence of direct
infrastructure access, functional preservation (identical answer/citation
behavior to the pre-migration Agent), and organization isolation. Runs
against real PostgreSQL (`tests/db.py`).
"""
import json

import pytest

from src.agents.risk_advisor.agent import RiskAdvisorAgent
from src.database.repository import AnalysisRepository
from src.llm.providers.mock_provider import MockLLMProvider
from src.prompts.registry import PromptRegistry
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import SessionContext
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.rag_pipeline import RagPipeline
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


class _ScriptedProvider:
    """Returns a fixed, valid JSON answer -- deterministic, no network call."""

    def __init__(self, answer: str, cited_analysis_ids: list[int]):
        self.answer = answer
        self.cited_analysis_ids = cited_analysis_ids
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return json.dumps({"answer": self.answer, "cited_analysis_ids": self.cited_analysis_ids})


class _ExplodingProvider:
    def generate(self, prompt: str) -> str:
        raise AssertionError("LLM must not be called when there is nothing to synthesize")


@pytest.fixture()
def repo():
    with temp_database_url("risk_advisor_migration") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def knowledge_repository(repo):
    vector_repository = PgVectorRepository(repo.SessionLocal)
    event_publisher = InProcessEventPublisher(repo.SessionLocal, EventDispatcher(repo.SessionLocal))
    return KnowledgeRepository(repo.SessionLocal, MockEmbeddingProvider(), vector_repository, event_publisher)


def _framework(repo, knowledge_repository, provider):
    return AdvisorFramework(
        repository=repo,
        prompt_registry=PromptRegistry(base_path="src/agents"),
        llm_provider=provider,
        rag_pipeline=RagPipeline(knowledge_repository),
    )


def _session(repo, org_id: int) -> SessionContext:
    user_id = repo.enterprise.create_user(org_id, "founder@stratech.example", "Founder")
    return SessionContext(
        organization_id=org_id, user_id=user_id, session_id="s-1", project_name="Multilift"
    )


class TestNoEvidenceWithoutLlmCall:
    """Founder's mandatory criterion: no_evidence() executes without
    calling the LLM -- identical to the pre-migration behavior."""

    def test_no_risks_means_no_llm_call(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        provider = _ExplodingProvider()
        framework = _framework(repo, knowledge_repository, provider)
        agent = RiskAdvisorAgent(framework)

        evidence = framework.gather_context(org_id, "Multilift", kind="risk")
        assert evidence == []

        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "Qual o risco mais crítico?",
            evidence,
            no_evidence_answer="Nenhum risco identificado ainda para este projeto.",
        )

        assert explanation.recommendation.answer == "Nenhum risco identificado ainda para este projeto."
        assert explanation.recommendation.cited_evidence == []


class TestFunctionalEquivalence:
    """Founder's mandatory criterion: functional behavior equivalent to
    the pre-migration Agent -- same answer, same citation filtering."""

    def test_answers_from_evidence_with_real_citations(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
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

        provider = _ScriptedProvider(
            answer="O risco mais crítico é o atraso no fornecedor de middleware.",
            cited_analysis_ids=[analysis_id, 999999],  # 999999 never in evidence
        )
        framework = _framework(repo, knowledge_repository, provider)
        agent = RiskAdvisorAgent(framework)

        evidence = framework.gather_context(org_id, "Multilift", kind="risk")
        explanation = framework.run(
            agent, _session(repo, org_id), "Qual o risco mais crítico?", evidence
        )

        assert explanation.recommendation.answer == "O risco mais crítico é o atraso no fornecedor de middleware."
        # Only the real citation survives -- the invented id is discarded,
        # exactly the guard the pre-migration Agent already enforced.
        assert [e.source_analysis_id for e in explanation.recommendation.cited_evidence] == [analysis_id]
        assert provider.calls == 1


class TestChunkIdTraceability:
    """Founder's mandatory criterion: chunk_id traceability, demonstrated
    through the real Advisor Framework's gather_rag_context, exercised as
    part of the same real production code path the migrated route uses."""

    def test_rag_context_traces_to_the_real_ingested_chunk(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(
            org_id, "middleware-runbook.md", "the middleware vendor has a history of delayed delivery"
        )
        knowledge_repository.index(document.id, CORRELATION_ID)

        framework = _framework(repo, knowledge_repository, MockLLMProvider())
        rag_context = framework.gather_rag_context(org_id, "middleware vendor delay", top_k=5)

        assert len(rag_context.chunks) == 1
        traced_chunk = rag_context.chunks[0]
        assert traced_chunk.document_id == document.id
        assert rag_context.chunk_ids == {traced_chunk.chunk_id}

    def test_rag_context_flows_into_the_migrated_agent_as_supplementary_material(
        self, repo, knowledge_repository
    ):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(
            org_id, "middleware-runbook.md", "the middleware vendor has a history of delayed delivery"
        )
        knowledge_repository.index(document.id, CORRELATION_ID)
        repo.save_analysis(
            kind="risk",
            payload={
                "model_output": {
                    "structured": True,
                    "risks": [{"description": "Atraso no fornecedor", "probability": "high", "impact": "high", "mitigation": "x"}],
                    "escalation_recommendation": None,
                }
            },
            organization_id=org_id,
            project_name="Multilift",
        )

        captured_prompts = []

        class CapturingProvider:
            def generate(self, prompt):
                captured_prompts.append(prompt)
                return json.dumps({"answer": "ok", "cited_analysis_ids": []})

        framework = _framework(repo, knowledge_repository, CapturingProvider())
        agent = RiskAdvisorAgent(framework)
        evidence = framework.gather_context(org_id, "Multilift", kind="risk")
        rag_context = framework.gather_rag_context(org_id, "middleware vendor delay", top_k=5)

        framework.run(agent, _session(repo, org_id), "Qual o risco?", evidence, rag_context=rag_context)

        assert len(captured_prompts) == 1
        assert "delayed delivery" in captured_prompts[0]


class TestOrganizationIsolation:
    """Founder's mandatory criterion: isolamento entre organizações,
    exercised across the whole migrated chain (AnalysisRecord evidence and
    RAG chunks alike)."""

    def test_never_synthesizes_over_another_organizations_data(self, repo, knowledge_repository):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
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
        doc_b = knowledge_repository.ingest(org_b, "notes-b.md", "org b confidential delay notes")
        knowledge_repository.index(doc_b.id, CORRELATION_ID)

        framework = _framework(repo, knowledge_repository, _ExplodingProvider())
        agent = RiskAdvisorAgent(framework)

        evidence_a = framework.gather_context(org_a, "Multilift", kind="risk")
        rag_context_a = framework.gather_rag_context(org_a, "org b confidential delay notes", top_k=5)

        assert evidence_a == []
        assert rag_context_a.chunks == []

        explanation = framework.run(
            agent,
            _session(repo, org_a),
            "Qual o risco mais crítico?",
            evidence_a,
            rag_context=rag_context_a,
            no_evidence_answer="Nenhum risco identificado ainda para este projeto.",
        )
        assert explanation.recommendation.answer == "Nenhum risco identificado ainda para este projeto."


class TestNoDirectInfrastructureAccess:
    """Founder's mandatory criterion: absence of direct infrastructure
    access -- confirmed statically (no import), verified here at runtime by
    checking the migrated Agent's module never references PgVectorRepository/
    EmbeddingProvider."""

    def test_agent_module_has_no_direct_infrastructure_import(self):
        import src.agents.risk_advisor.agent as agent_module

        source = agent_module.__file__
        with open(source, encoding="utf-8") as f:
            content = f.read()
        assert "PgVectorRepository" not in content
        assert "EmbeddingProvider" not in content
        assert "from src.database.models import" not in content
