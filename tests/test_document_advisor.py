"""Document Advisor (Wave 5, Epic W5-1), per
`TECHNICAL-DESIGN-DOCUMENT-ADVISOR.md`.

Proves, against the real `DocumentAdvisorAgent` (never a fake test double),
the end-to-end chain: Knowledge Platform -> RAG Pipeline ->
`normalize_rag_evidence()` -> `AdvisorFramework.run()` -> Document Advisor ->
LLM -> Response. Mirrors the same rigor `test_risk_advisor_migration.py`
already established for the Risk Advisor.

Includes the mandatory evidence required by "Founder Decision — Technical
Design do Document Advisor" (item 3): a document with multiple chunks, where
the LLM cites only part of them, and the response traces exclusively to the
chunks actually cited -- chunk -> document -> version -> response.
"""
import json

import pytest

from src.agents.document_advisor.agent import DocumentAdvisorAgent
from src.database.models import Chunk
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
    with temp_database_url("document_advisor") as database_url:
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
    def test_no_indexed_chunks_means_no_llm_call(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        framework = _framework(repo, knowledge_repository, _ExplodingProvider())
        agent = DocumentAdvisorAgent(framework)

        rag_context = framework.gather_rag_context(org_id, "any question", top_k=5)
        evidence = framework.normalize_rag_evidence(rag_context)
        assert evidence == []

        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "O que os documentos dizem?",
            evidence,
            rag_context=rag_context,
            no_evidence_answer="Nenhum documento relevante foi encontrado para responder a esta pergunta.",
        )

        assert explanation.recommendation.answer == "Nenhum documento relevante foi encontrado para responder a esta pergunta."
        assert explanation.recommendation.cited_evidence == []


class TestFunctionalCitation:
    def test_answers_with_a_real_chunk_citation(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(
            org_id, "runbook.md", "the middleware vendor has a history of delayed delivery"
        )
        knowledge_repository.index(document.id, CORRELATION_ID)

        framework = _framework(repo, knowledge_repository, None)
        rag_context = framework.gather_rag_context(org_id, "middleware vendor delay", top_k=5)
        evidence = framework.normalize_rag_evidence(rag_context)
        assert len(evidence) == 1
        real_chunk_id = evidence[0].source_id

        provider = _ScriptedProvider(
            answer="O fornecedor de middleware tem histórico de atraso.",
            cited_analysis_ids=[real_chunk_id, 999999],  # 999999 never in evidence
        )
        framework = _framework(repo, knowledge_repository, provider)
        agent = DocumentAdvisorAgent(framework)

        explanation = framework.run(
            agent, _session(repo, org_id), "Há histórico de atraso?", evidence, rag_context=rag_context
        )

        assert explanation.recommendation.answer == "O fornecedor de middleware tem histórico de atraso."
        # Only the real citation survives -- the invented id is discarded.
        assert [item.source_id for item in explanation.recommendation.cited_evidence] == [real_chunk_id]
        assert provider.calls == 1


class TestOrganizationalIsolation:
    def test_never_cites_a_chunk_from_another_organization(self, repo, knowledge_repository):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        document = knowledge_repository.ingest(org_a, "confidential.md", "Org A's confidential rollback plan")
        knowledge_repository.index(document.id, CORRELATION_ID)

        framework = _framework(repo, knowledge_repository, _ExplodingProvider())
        rag_context = framework.gather_rag_context(org_b, "rollback plan", top_k=5)
        evidence = framework.normalize_rag_evidence(rag_context)

        assert rag_context.chunks == []
        assert evidence == []


class TestMultiChunkTraceability:
    """Founder-mandated evidence (item 3, "Founder Decision — Technical
    Design do Document Advisor"): a document with multiple chunks, the LLM
    citing only part of them, and the response tracing exclusively to the
    chunks actually cited -- chunk -> document -> version -> response."""

    def test_partial_citation_traces_chunk_to_document_version_and_response(
        self, repo, knowledge_repository
    ):
        org_id = repo.enterprise.create_organization("Org A")
        # Long enough to produce multiple 500-char chunks (50-char overlap,
        # KnowledgeRepository.CHUNK_SIZE_CHARS/CHUNK_OVERLAP_CHARS) --
        # three distinguishable sections, none artificially aligned to
        # chunk boundaries (the chunker is purely char-based).
        content = (
            "SECTION ONE: Budget approval requires CFO signoff before Q3 close. " * 8
            + "SECTION TWO: Vendor SLAs must include a 24 hour response window. " * 8
            + "SECTION THREE: Data retention policy mandates a 7 year archive. " * 8
        )
        document = knowledge_repository.ingest(org_id, "governance-policy.md", content)
        knowledge_repository.index(document.id, CORRELATION_ID)

        indexed = knowledge_repository.get_document(org_id, document.id)
        assert indexed.chunk_count >= 3, "fixture must produce multiple chunks, per Founder mandate"

        framework = _framework(repo, knowledge_repository, None)
        rag_context = framework.gather_rag_context(org_id, "budget vendor retention policy", top_k=10)
        assert len(rag_context.chunks) == indexed.chunk_count  # every chunk of this document is retrievable

        all_chunk_ids = sorted(chunk.chunk_id for chunk in rag_context.chunks)
        # The LLM uses only PART of the retrieved chunks -- exactly the
        # Founder-mandated scenario, not "all evidence handed in is cited".
        cited_ids = all_chunk_ids[:2]
        uncited_id = all_chunk_ids[-1]
        invented_id = max(all_chunk_ids) + 1000  # never real -- must be discarded

        evidence = framework.normalize_rag_evidence(rag_context)
        provider = _ScriptedProvider(
            answer="A politica exige aprovacao do CFO e SLA de 24 horas.",
            cited_analysis_ids=[*cited_ids, invented_id],
        )
        framework = _framework(repo, knowledge_repository, provider)
        agent = DocumentAdvisorAgent(framework)

        explanation = framework.run(
            agent, _session(repo, org_id), "Quais politicas se aplicam?", evidence, rag_context=rag_context
        )

        cited_evidence = explanation.recommendation.cited_evidence
        cited_result_ids = {item.source_id for item in cited_evidence}

        # The response references EXCLUSIVELY the chunks the LLM actually
        # cited -- never the unused chunk, never the invented one.
        assert cited_result_ids == set(cited_ids)
        assert uncited_id not in cited_result_ids
        assert invented_id not in cited_result_ids

        # Full traceability chunk -> document -> version -> response: every
        # cited Evidence traces back to this exact document and this exact
        # DocumentVersion, never a different one.
        for item in cited_evidence:
            assert item.source_type == "document_chunk"
            assert item.metadata["document_id"] == document.id
            assert item.source_label == f"Document {document.id} / Chunk {item.source_id}"

        with repo.SessionLocal() as session:
            chunk_rows = (
                session.query(Chunk).filter(Chunk.id.in_(cited_result_ids)).all()
            )
            assert len(chunk_rows) == len(cited_result_ids)
            assert {row.document_version_id for row in chunk_rows} == {document.version_id}
