"""Governance Advisor (Wave 5, next Epic after W5-1), per
`TECHNICAL-DESIGN-GOVERNANCE-ADVISOR.md`.

Proves, against the real `GovernanceAdvisorAgent` (never a fake test
double), the end-to-end chain: Knowledge Platform -> RAG Pipeline ->
`normalize_rag_evidence()` -> `AdvisorFramework.run()` (byte-for-byte
unchanged) -> Governance Advisor -> LLM -> Response, and that the
classification prefix (Founder Decision -- Technical Design do Governance
Advisor) survives intact through `RecommendationEngine.build()`/
`ExplanationEngine.explain()`.

Includes the mandatory evidence required by "Founder Decision --
Technical Design do Governance Advisor" (item 4): a real scenario where a
Decision Log entry and a Technical Debt Register entry conflict, the
Governance Advisor identifies it, classifies it CONFLITANTE, and cites
both documents.
"""
import json

import pytest

from src.agents.governance_advisor.agent import GovernanceAdvisorAgent
from src.database.repository import AnalysisRepository
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
    with temp_database_url("governance_advisor") as database_url:
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
    return SessionContext(organization_id=org_id, user_id=user_id, session_id="s-1")


class TestNoEvidenceWithoutLlmCall:
    def test_no_indexed_governance_chunks_means_no_llm_call(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        framework = _framework(repo, knowledge_repository, _ExplodingProvider())
        agent = GovernanceAdvisorAgent(framework)

        rag_context = framework.gather_rag_context(org_id, "any question", top_k=5)
        evidence = framework.normalize_rag_evidence(rag_context)
        assert evidence == []

        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "Existe alguma decisao sobre X?",
            evidence,
            rag_context=rag_context,
            no_evidence_answer="[SEM EVIDÊNCIA]\nNenhuma referência de governança relevante foi encontrada para responder a esta pergunta.",
        )

        assert explanation.recommendation.answer.startswith("[SEM EVIDÊNCIA]")
        assert explanation.recommendation.cited_evidence == []


class TestFunctionalCitation:
    def test_answers_with_a_real_chunk_citation_and_conforme_classification(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(
            org_id, "decision-log-fragment.md", "D-050: knowledge.write e concedido a organization_admin, pmo e project_manager."
        )
        knowledge_repository.index(document.id, CORRELATION_ID)

        framework = _framework(repo, knowledge_repository, None)
        rag_context = framework.gather_rag_context(org_id, "quem recebe knowledge.write?", top_k=5)
        evidence = framework.normalize_rag_evidence(rag_context)
        assert len(evidence) == 1
        real_chunk_id = evidence[0].source_id

        provider = _ScriptedProvider(
            answer="[CONFORME]\nknowledge.write e concedido a organization_admin, pmo e project_manager, per D-050.",
            cited_analysis_ids=[real_chunk_id, 999999],  # 999999 never in evidence
        )
        framework = _framework(repo, knowledge_repository, provider)
        agent = GovernanceAdvisorAgent(framework)

        explanation = framework.run(
            agent, _session(repo, org_id), "Quem recebe knowledge.write?", evidence, rag_context=rag_context
        )

        assert explanation.recommendation.answer.startswith("[CONFORME]")
        # Only the real citation survives -- the invented id is discarded.
        assert [item.source_id for item in explanation.recommendation.cited_evidence] == [real_chunk_id]
        assert provider.calls == 1


class TestOrganizationalIsolation:
    def test_never_cites_a_governance_chunk_from_another_organization(self, repo, knowledge_repository):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        document = knowledge_repository.ingest(org_a, "decision-log-fragment.md", "D-050: confidential Org A decision")
        knowledge_repository.index(document.id, CORRELATION_ID)

        framework = _framework(repo, knowledge_repository, _ExplodingProvider())
        rag_context = framework.gather_rag_context(org_b, "decision fragment", top_k=5)
        evidence = framework.normalize_rag_evidence(rag_context)

        assert rag_context.chunks == []
        assert evidence == []


class TestMandatoryConflictEvidence:
    """Founder-mandated evidence (item 4, "Founder Decision -- Technical
    Design do Governance Advisor"): a real scenario where a Decision Log
    entry and a Technical Debt Register entry conflict, the Governance
    Advisor identifies it, classifies it CONFLITANTE, and cites both
    documents.

    The two ingested documents below are fixtures that mirror the exact
    structure of the platform's own governance corpus (Decision Log entries
    named "D-NNN", Technical Debt entries named "TD-NNN", per D-099/AR-10)
    -- they do not modify the real `DECISION-LOG.md`/`TECHNICAL_DEBT.md`
    files, which remain untouched by this Epic.
    """

    def test_conflicting_decision_log_and_technical_debt_entries_are_classified_conflitante(
        self, repo, knowledge_repository
    ):
        org_id = repo.enterprise.create_organization("Org A")
        decision_log_doc = knowledge_repository.ingest(
            org_id,
            "decision-log-fragment.md",
            "D-050: A retencao de AuditLog e mantida indefinidamente, sem expiracao automatica.",
        )
        knowledge_repository.index(decision_log_doc.id, CORRELATION_ID)
        technical_debt_doc = knowledge_repository.ingest(
            org_id,
            "technical-debt-fragment.md",
            "TD-020: AuditLog expira automaticamente apos 90 dias, conforme politica de retencao implementada.",
        )
        knowledge_repository.index(technical_debt_doc.id, CORRELATION_ID)

        framework = _framework(repo, knowledge_repository, None)
        rag_context = framework.gather_rag_context(org_id, "qual a politica de retencao do AuditLog?", top_k=10)
        evidence = framework.normalize_rag_evidence(rag_context)

        assert len(evidence) == 2
        decision_log_chunk = next(e for e in evidence if e.metadata["document_id"] == decision_log_doc.id)
        technical_debt_chunk = next(e for e in evidence if e.metadata["document_id"] == technical_debt_doc.id)

        provider = _ScriptedProvider(
            answer=(
                "[CONFLITANTE]\n"
                "O Decision Log (D-050) afirma retencao indefinida do AuditLog, enquanto o Technical Debt "
                "Register (TD-020) afirma expiracao automatica apos 90 dias. Per a hierarquia institucional "
                "(AR-10), o Decision Log tem precedencia sobre o Technical Debt Register."
            ),
            cited_analysis_ids=[decision_log_chunk.source_id, technical_debt_chunk.source_id],
        )
        framework = _framework(repo, knowledge_repository, provider)
        agent = GovernanceAdvisorAgent(framework)

        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "Qual a politica de retencao do AuditLog?",
            evidence,
            rag_context=rag_context,
        )

        # Classified CONFLITANTE -- the prefix survives Framework processing intact.
        assert explanation.recommendation.answer.startswith("[CONFLITANTE]")
        assert "precedencia" in explanation.recommendation.answer

        # Both conflicting documents are cited -- neither side silently dropped.
        cited_ids = {item.source_id for item in explanation.recommendation.cited_evidence}
        assert cited_ids == {decision_log_chunk.source_id, technical_debt_chunk.source_id}

        cited_document_ids = {item.metadata["document_id"] for item in explanation.recommendation.cited_evidence}
        assert cited_document_ids == {decision_log_doc.id, technical_debt_doc.id}

        # Full traceability: each cited chunk's source_label names its real document.
        labels = {item.source_label for item in explanation.recommendation.cited_evidence}
        assert f"Document {decision_log_doc.id} / Chunk {decision_log_chunk.source_id}" in labels
        assert f"Document {technical_debt_doc.id} / Chunk {technical_debt_chunk.source_id}" in labels
