"""RAG Pipeline (Wave 3 Fase 2) -- ranking, determinism, and traceability of
`RagContext`, on real PostgreSQL with pgvector (`tests/db.py`).
"""
import time

import pytest

from src.database.repository import AnalysisRepository
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.rag_pipeline import RagPipeline
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


@pytest.fixture()
def repo():
    with temp_database_url("rag_pipeline") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def knowledge_repository(repo):
    vector_repository = PgVectorRepository(repo.SessionLocal)
    event_publisher = InProcessEventPublisher(repo.SessionLocal, EventDispatcher(repo.SessionLocal))
    return KnowledgeRepository(repo.SessionLocal, MockEmbeddingProvider(), vector_repository, event_publisher)


@pytest.fixture()
def rag_pipeline(knowledge_repository):
    return RagPipeline(knowledge_repository)


class TestRagContext:
    def test_chunk_ids_reflects_retrieved_chunks(self, repo, knowledge_repository, rag_pipeline):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(org_id, "runbook.md", "the rollback procedure is documented here")
        knowledge_repository.index(document.id, CORRELATION_ID)

        context = rag_pipeline.retrieve(org_id, "rollback procedure", top_k=5)
        assert len(context.chunk_ids) == len(context.chunks)
        assert context.chunk_ids == {c.chunk_id for c in context.chunks}


class TestRagPipelineDeterminism:
    def test_same_query_yields_same_context(self, repo, knowledge_repository, rag_pipeline):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(org_id, "runbook.md", "the rollback procedure is documented here")
        knowledge_repository.index(document.id, CORRELATION_ID)

        first = rag_pipeline.retrieve(org_id, "rollback procedure", top_k=5)
        second = rag_pipeline.retrieve(org_id, "rollback procedure", top_k=5)
        assert [c.chunk_id for c in first.chunks] == [c.chunk_id for c in second.chunks]
        assert [c.score for c in first.chunks] == [c.score for c in second.chunks]


class TestRagPipelineRanking:
    def test_higher_score_ranks_first(self, repo, knowledge_repository, rag_pipeline):
        org_id = repo.enterprise.create_organization("Org A")
        # An exact match to the query text scores strictly higher (cosine
        # distance 0) than an unrelated chunk under the deterministic mock
        # embedding, so this is a real (not tautological) ranking check.
        exact = knowledge_repository.ingest(org_id, "exact.md", "rollback procedure")
        knowledge_repository.index(exact.id, CORRELATION_ID)
        unrelated = knowledge_repository.ingest(org_id, "unrelated.md", "quarterly budget forecast summary")
        knowledge_repository.index(unrelated.id, CORRELATION_ID)

        context = rag_pipeline.retrieve(org_id, "rollback procedure", top_k=5)
        assert context.chunks[0].document_id == exact.id

    def test_recency_breaks_ties_on_equal_score(self, repo, knowledge_repository, rag_pipeline):
        org_id = repo.enterprise.create_organization("Org A")
        older = knowledge_repository.ingest(org_id, "older.md", "identical content for tie break")
        knowledge_repository.index(older.id, CORRELATION_ID)
        time.sleep(1)  # DB timestamp resolution -- ensure a strictly later created_at
        newer = knowledge_repository.ingest(org_id, "newer.md", "identical content for tie break")
        knowledge_repository.index(newer.id, CORRELATION_ID)

        context = rag_pipeline.retrieve(org_id, "identical content for tie break", top_k=5)
        # Both chunks are identical text -> identical (deterministic) score;
        # the more recently ingested document must win the tie.
        assert context.chunks[0].document_id == newer.id


class TestRagPipelineIsolation:
    def test_never_crosses_organizations(self, repo, knowledge_repository, rag_pipeline):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        doc_a = knowledge_repository.ingest(org_a, "notes-a.md", "risk of delay on project alfa")
        knowledge_repository.index(doc_a.id, CORRELATION_ID)
        doc_b = knowledge_repository.ingest(org_b, "notes-b.md", "risk of delay on project alfa")
        knowledge_repository.index(doc_b.id, CORRELATION_ID)

        context_a = rag_pipeline.retrieve(org_a, "risk of delay", top_k=10)
        assert all(c.document_id == doc_a.id for c in context_a.chunks)
