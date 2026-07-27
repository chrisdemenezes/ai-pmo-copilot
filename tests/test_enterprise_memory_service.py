"""EnterpriseMemoryService (Wave 3 Fase 2) -- classification and
category-scoped retrieval of already-ingested Knowledge Platform
documents, on real PostgreSQL (`tests/db.py`).
"""
import pytest

from src.database.repository import AnalysisRepository
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.enterprise_memory_service import (
    EnterpriseMemoryService,
    MemoryCategory,
)
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from tests.db import temp_database_url


@pytest.fixture()
def repo():
    with temp_database_url("enterprise_memory") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def knowledge_repository(repo):
    vector_repository = PgVectorRepository(repo.SessionLocal)
    return KnowledgeRepository(repo.SessionLocal, MockEmbeddingProvider(), vector_repository)


@pytest.fixture()
def memory_service(repo, knowledge_repository):
    return EnterpriseMemoryService(repo.SessionLocal, knowledge_repository)


class TestClassify:
    def test_classifies_an_ingested_document(self, repo, knowledge_repository, memory_service):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(org_id, "decision-log.md", "D-065 approved")

        record = memory_service.classify(org_id, document.id, MemoryCategory.DECISOES)

        assert record.document_id == document.id
        assert record.organization_id == org_id
        assert record.category == MemoryCategory.DECISOES.value

    def test_raises_for_unknown_document(self, memory_service):
        with pytest.raises(ValueError):
            memory_service.classify(1, 999999, MemoryCategory.DOCUMENTAL)

    def test_raises_when_document_belongs_to_another_organization(
        self, repo, knowledge_repository, memory_service
    ):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        document = knowledge_repository.ingest(org_a, "notes.md", "hello")

        with pytest.raises(ValueError):
            memory_service.classify(org_b, document.id, MemoryCategory.DOCUMENTAL)


class TestListByCategory:
    def test_lists_only_the_requested_category(self, repo, knowledge_repository, memory_service):
        org_id = repo.enterprise.create_organization("Org A")
        decision_doc = knowledge_repository.ingest(org_id, "decision-log.md", "D-065 approved")
        lesson_doc = knowledge_repository.ingest(org_id, "lessons.md", "retro insight")

        memory_service.classify(org_id, decision_doc.id, MemoryCategory.DECISOES)
        memory_service.classify(org_id, lesson_doc.id, MemoryCategory.APRENDIZADOS)

        decisions = memory_service.list_by_category(org_id, MemoryCategory.DECISOES)
        assert [r.document_id for r in decisions] == [decision_doc.id]

    def test_scoped_by_organization(self, repo, knowledge_repository, memory_service):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        doc_a = knowledge_repository.ingest(org_a, "decision-a.md", "decision in org A")
        doc_b = knowledge_repository.ingest(org_b, "decision-b.md", "decision in org B")
        memory_service.classify(org_a, doc_a.id, MemoryCategory.DECISOES)
        memory_service.classify(org_b, doc_b.id, MemoryCategory.DECISOES)

        records_a = memory_service.list_by_category(org_a, MemoryCategory.DECISOES)
        assert [r.document_id for r in records_a] == [doc_a.id]

    def test_a_document_may_carry_multiple_classifications(
        self, repo, knowledge_repository, memory_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(org_id, "policy.md", "governance policy update")
        memory_service.classify(org_id, document.id, MemoryCategory.DOCUMENTAL)
        memory_service.classify(org_id, document.id, MemoryCategory.ORGANIZACIONAL)

        assert len(memory_service.list_by_category(org_id, MemoryCategory.DOCUMENTAL)) == 1
        assert len(memory_service.list_by_category(org_id, MemoryCategory.ORGANIZACIONAL)) == 1
