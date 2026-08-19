"""`DocumentIngestionService` (Wave 5, Epic W5-0), per
`TECHNICAL-DESIGN-W5-0-DOCUMENT-INGESTION.md`. Exercises the exact
composition the `/documents` HTTP routes call -- `KnowledgeRepository`
(unchanged) + the Enterprise Administration audit mechanism (unchanged).
"""
import pytest
from sqlalchemy import select

from src.database.models import WorkflowExecution
from src.database.repository import AnalysisRepository
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.document_ingestion_service import (
    STATUS_FAILED,
    STATUS_INDEXED,
    DocumentIndexingError,
    DocumentIngestionService,
)
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from src.workflows import document_indexed_workflow
from src.workflows.execution_tracking import ExecutionTracker
from src.workflows.runtime import WorkflowRuntime
from tests.db import temp_database_url

CORRELATION_ID = "w5-0-test-correlation"


@pytest.fixture()
def repo():
    with temp_database_url("document_ingestion_service") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def event_publisher(repo):
    dispatcher = EventDispatcher(repo.SessionLocal)
    runtime = WorkflowRuntime(ExecutionTracker(repo.SessionLocal))
    document_indexed_workflow.register(dispatcher, runtime)
    return InProcessEventPublisher(repo.SessionLocal, dispatcher)


@pytest.fixture()
def knowledge_repository(repo, event_publisher):
    return KnowledgeRepository(
        repo.SessionLocal,
        MockEmbeddingProvider(),
        PgVectorRepository(repo.SessionLocal),
        event_publisher,
    )


@pytest.fixture()
def service(knowledge_repository, repo):
    return DocumentIngestionService(knowledge_repository, repo)


@pytest.fixture()
def org_and_user(repo):
    org_id = repo.enterprise.create_organization("Org A")
    user_id = repo.enterprise.create_user(org_id, "admin@org-a.test", "Admin")
    return org_id, user_id


class TestUpload:
    def test_upload_ingests_indexes_and_returns_indexed_document(self, service, org_and_user):
        org_id, user_id = org_and_user
        document = service.upload(
            org_id, user_id, "runbook.md", "hello world rollback procedure", CORRELATION_ID
        )

        assert document.chunk_count == 1
        assert service.get_status(org_id, document.id) == STATUS_INDEXED

    def test_upload_records_audit_trail(self, service, org_and_user, repo):
        org_id, user_id = org_and_user
        document = service.upload(org_id, user_id, "notes.md", "hello", CORRELATION_ID)

        entries = repo.administration.list_audit_log(
            org_id, entity_type="document", entity_id=document.id
        )
        actions = [e.action for e in entries]
        assert "document.uploaded" in actions
        assert "document.indexed" in actions

    def test_get_status_returns_none_for_unknown_document(self, service, org_and_user):
        org_id, _user_id = org_and_user
        assert service.get_status(org_id, 999999) is None


class TestIndexingFailure:
    def test_index_failure_preserves_document_and_audits_sanitized_error(
        self, service, org_and_user, repo, monkeypatch
    ):
        org_id, user_id = org_and_user

        def _boom(*_args, **_kwargs):
            raise RuntimeError("embedding backend unavailable")

        monkeypatch.setattr(
            service._knowledge_repository._embedding_provider, "embed", _boom
        )

        with pytest.raises(DocumentIndexingError) as excinfo:
            service.upload(org_id, user_id, "broken.md", "hello world", CORRELATION_ID)

        document_id = excinfo.value.document_id
        document = service.get_document(org_id, document_id)
        assert document is not None  # ingest() already committed, independent of index()
        assert document.chunk_count == 0
        assert service.get_status(org_id, document_id) == STATUS_FAILED

        entries = repo.administration.list_audit_log(
            org_id, entity_type="document", entity_id=document_id
        )
        failed_entry = next(e for e in entries if e.action == "document.index_failed")
        assert failed_entry.details["error"] == "RuntimeError: embedding backend unavailable"
        assert "Traceback" not in failed_entry.details["error"]

    def test_reindex_after_transient_failure_succeeds(self, service, org_and_user, monkeypatch):
        org_id, user_id = org_and_user
        real_embed = service._knowledge_repository._embedding_provider.embed
        calls = {"count": 0}

        def _fail_once(text):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("transient failure")
            return real_embed(text)

        monkeypatch.setattr(
            service._knowledge_repository._embedding_provider, "embed", _fail_once
        )

        with pytest.raises(DocumentIndexingError) as excinfo:
            service.upload(org_id, user_id, "retry.md", "hello world", CORRELATION_ID)
        document_id = excinfo.value.document_id

        document = service.reindex(org_id, user_id, document_id, CORRELATION_ID)
        assert document.chunk_count == 1
        assert service.get_status(org_id, document_id) == STATUS_INDEXED


class TestOrganizationalIsolation:
    """Teste A (Founder Decision -- Technical Design W5-0, D-090), at the
    service layer: an organization never sees another's document."""

    def test_get_document_scoped_by_organization(self, service, org_and_user, repo):
        org_a, user_a = org_and_user
        org_b = repo.enterprise.create_organization("Org B")
        document = service.upload(org_a, user_a, "confidential-a.md", "hello", CORRELATION_ID)

        assert service.get_document(org_a, document.id) is not None
        assert service.get_document(org_b, document.id) is None
        assert service.get_status(org_b, document.id) is None
        assert all(doc.id != document.id for doc in service.list_documents(org_b))


class TestEndToEndChain:
    def test_upload_flows_through_event_pipeline_to_workflow_execution_tracking(
        self, service, org_and_user, repo
    ):
        """Teste B (Founder Decision -- Technical Design W5-0, D-090):
        upload -> ingest -> index -> document.indexed -> Workflow Runtime ->
        Execution Tracking, sem intervencao manual -- this test never calls
        EventDispatcher/WorkflowRuntime directly, only service.upload(),
        exactly what the HTTP route calls."""
        org_id, user_id = org_and_user
        service.upload(org_id, user_id, "runbook.md", "hello world rollback procedure", CORRELATION_ID)

        with repo.SessionLocal() as session:
            execution = session.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.workflow_name == document_indexed_workflow.WORKFLOW_NAME,
                    WorkflowExecution.organization_id == org_id,
                )
            ).scalar_one()

        assert execution.status == "completed"
        assert execution.correlation_id == CORRELATION_ID
        assert execution.error is None
