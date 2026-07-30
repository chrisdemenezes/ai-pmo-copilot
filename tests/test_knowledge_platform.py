"""Enterprise Knowledge Platform Fase 1 -- MockEmbeddingProvider,
PgVectorRepository, and the KnowledgeRepository facade end to end, on real
PostgreSQL with pgvector (`tests/db.py`).
"""
import pytest

from src.database.models import EventRecord
from src.database.repository import AnalysisRepository
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.embedding_provider import (
    EmbeddingProviderConfigError,
    MockEmbeddingProvider,
    get_embedding_provider,
)
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.vector_repository import PgVectorRepository, VectorRepositoryError
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


class TestMockEmbeddingProvider:
    def test_same_text_yields_same_vector(self):
        provider = MockEmbeddingProvider()
        assert provider.embed("hello world") == provider.embed("hello world")

    def test_normalizes_whitespace_and_case(self):
        provider = MockEmbeddingProvider()
        assert provider.embed("Hello   World") == provider.embed("hello world")

    def test_different_text_yields_different_vector(self):
        provider = MockEmbeddingProvider()
        assert provider.embed("hello world") != provider.embed("goodbye world")

    def test_vector_has_expected_dimension(self):
        provider = MockEmbeddingProvider()
        assert len(provider.embed("hello world")) == 16


class TestGetEmbeddingProvider:
    def test_defaults_to_mock(self, monkeypatch):
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        assert isinstance(get_embedding_provider(), MockEmbeddingProvider)

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "some-future-real-backend")
        with pytest.raises(EmbeddingProviderConfigError):
            get_embedding_provider()


@pytest.fixture()
def repo():
    with temp_database_url("knowledge_platform") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def vector_repository(repo):
    return PgVectorRepository(repo.SessionLocal)


@pytest.fixture()
def event_publisher(repo):
    return InProcessEventPublisher(repo.SessionLocal, EventDispatcher(repo.SessionLocal))


@pytest.fixture()
def knowledge_repository(repo, vector_repository, event_publisher):
    return KnowledgeRepository(repo.SessionLocal, MockEmbeddingProvider(), vector_repository, event_publisher)


class TestPgVectorRepository:
    def test_upsert_and_similarity_search(self, repo, vector_repository, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(org_id, "notes.md", "hello world")
        knowledge_repository.index(document.id, CORRELATION_ID)

        results = vector_repository.similarity_search(org_id, MockEmbeddingProvider().embed("hello world"), top_k=5)
        assert len(results) >= 1
        assert results[0].text == "hello world"

    def test_upsert_vector_raises_for_unknown_chunk(self, vector_repository):
        with pytest.raises(VectorRepositoryError):
            vector_repository.upsert_vector(999999, [0.0] * 16)

    def test_similarity_search_never_crosses_organizations(self, repo, knowledge_repository):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")

        doc_a = knowledge_repository.ingest(org_a, "notes-a.md", "risk of delay on project alfa")
        knowledge_repository.index(doc_a.id, CORRELATION_ID)
        doc_b = knowledge_repository.ingest(org_b, "notes-b.md", "risk of delay on project alfa")
        knowledge_repository.index(doc_b.id, CORRELATION_ID)

        results_a = knowledge_repository.search(org_a, "risk of delay", top_k=10)
        assert all(r.document_id == doc_a.id for r in results_a)

        results_b = knowledge_repository.search(org_b, "risk of delay", top_k=10)
        assert all(r.document_id == doc_b.id for r in results_b)


class TestKnowledgeRepository:
    def test_ingest_index_search_round_trip(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(
            org_id, "runbook.md", "the deployment runbook explains the rollback procedure"
        )
        knowledge_repository.index(document.id, CORRELATION_ID)

        results = knowledge_repository.search(org_id, "rollback procedure", top_k=3)
        assert len(results) == 1
        assert results[0].document_id == document.id
        assert "rollback" in results[0].text

    def test_reingestion_creates_a_new_version_not_an_overwrite(self, repo, knowledge_repository):
        org_id = repo.enterprise.create_organization("Org A")
        first = knowledge_repository.ingest(org_id, "policy.md", "version one content")
        second = knowledge_repository.ingest(org_id, "policy.md", "version two content")

        assert first.id == second.id  # same Document
        assert first.version_id != second.version_id  # new version, not overwritten

        versions = knowledge_repository.list_versions(org_id, first.id)
        assert len(versions) == 2
        assert {v.id for v in versions} == {first.version_id, second.version_id}

    def test_get_document_scoped_by_organization(self, repo, knowledge_repository):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        document = knowledge_repository.ingest(org_a, "notes.md", "hello")

        assert knowledge_repository.get_document(org_a, document.id) is not None
        assert knowledge_repository.get_document(org_b, document.id) is None

    def test_index_raises_for_unknown_document(self, knowledge_repository):
        with pytest.raises(ValueError):
            knowledge_repository.index(999999, CORRELATION_ID)

    def test_list_versions_scoped_by_organization(self, repo, knowledge_repository):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        document = knowledge_repository.ingest(org_a, "notes.md", "hello")

        assert len(knowledge_repository.list_versions(org_a, document.id)) == 1
        assert knowledge_repository.list_versions(org_b, document.id) == []

    def test_index_publishes_document_indexed_with_full_envelope(self, repo, knowledge_repository):
        """Wave 4, Epic W4-3 (D-080): document.indexed carries the full
        envelope, the propagated correlation_id, and the strict payload
        {document_id, version_id, chunk_count} -- nothing else."""
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(org_id, "notes.md", "hello world")
        knowledge_repository.index(document.id, CORRELATION_ID)

        with repo.SessionLocal() as session:
            records = (
                session.query(EventRecord)
                .filter(EventRecord.event_type == "document.indexed")
                .all()
            )
        assert len(records) == 1
        record = records[0]
        assert record.correlation_id == CORRELATION_ID
        assert record.organization_id == org_id
        assert record.origin == "knowledge_repository"
        assert set(record.payload.keys()) == {"document_id", "version_id", "chunk_count"}
        assert record.payload["document_id"] == document.id
        assert record.payload["chunk_count"] == 1

    def test_index_does_not_publish_when_the_document_does_not_exist(self, repo, knowledge_repository):
        with repo.SessionLocal() as session:
            before = session.query(EventRecord).count()
        with pytest.raises(ValueError):
            knowledge_repository.index(999999, CORRELATION_ID)
        with repo.SessionLocal() as session:
            after = session.query(EventRecord).count()
        assert after == before
