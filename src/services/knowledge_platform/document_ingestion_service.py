"""Document Ingestion Service (Wave 5, Epic W5-0), per
`TECHNICAL-DESIGN-W5-0-DOCUMENT-INGESTION.md`.

Thin composition layer between the HTTP route and two already-existing
components -- `KnowledgeRepository` (Wave 3 Fase 1, `ingest()`/`index()`
unchanged) and the Enterprise Administration audit mechanism
(`AnalysisRepository.administration.record_audit()`/`list_audit_log()`,
same one `AIFoundationAudit.record_question()` already reuses). No new
audit mechanism, no new event, no Advisor responsibility (§1 of the
Technical Design -- this module never imports `Evidence`,
`AdvisorFramework`, or anything from `src.agents`).
"""
import logging

from src.database.repository import AnalysisRepository
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.types import DocumentVersionInfo, IngestedDocument
from src.workflows.execution_tracking import sanitize_error

logger = logging.getLogger(__name__)

STATUS_INDEXED = "indexed"
STATUS_INGESTED_PENDING_INDEX = "ingested_pending_index"
STATUS_FAILED = "failed"

ACTION_UPLOADED = "document.uploaded"
ACTION_INDEXED = "document.indexed"
ACTION_INDEX_FAILED = "document.index_failed"
ENTITY_TYPE = "document"


class DocumentIndexingError(Exception):
    """Raised when a document was ingested but indexing failed -- carries
    enough context for the route to respond with the partial state and a
    pointer to the retry path (`reindex`), instead of a bare 500 (Technical
    Design §6: the partial state is first-class, never hidden)."""

    def __init__(self, document_id: int, version_id: int, original: Exception):
        super().__init__(str(original))
        self.document_id = document_id
        self.version_id = version_id
        self.original = original


class DocumentIngestionService:
    def __init__(self, knowledge_repository: KnowledgeRepository, repository: AnalysisRepository):
        self._knowledge_repository = knowledge_repository
        self._repository = repository

    def upload(
        self,
        organization_id: int,
        user_id: int,
        source_name: str,
        text: str,
        correlation_id: str,
        project_id: int | None = None,
    ) -> IngestedDocument:
        """Upload -> Document -> DocumentVersion -> Chunks (Technical Design
        §2). `ingest()`/`index()` run with zero change to their signature."""
        ingested = self._knowledge_repository.ingest(organization_id, source_name, text, project_id)
        self._repository.administration.record_audit(
            organization_id,
            user_id,
            ACTION_UPLOADED,
            ENTITY_TYPE,
            ingested.id,
            {"source_name": source_name, "version_id": ingested.version_id},
        )
        return self._index(organization_id, user_id, ingested.id, correlation_id)

    def reindex(
        self, organization_id: int, user_id: int, document_id: int, correlation_id: str
    ) -> IngestedDocument:
        """Explicit retry path (§3.2) for a document left in
        `ingested_pending_index`/`failed` by a previous indexing failure."""
        return self._index(organization_id, user_id, document_id, correlation_id)

    def get_document(self, organization_id: int, document_id: int) -> IngestedDocument | None:
        return self._knowledge_repository.get_document(organization_id, document_id)

    def list_documents(
        self, organization_id: int, project_id: int | None = None
    ) -> list[IngestedDocument]:
        return self._knowledge_repository.list_documents(organization_id, project_id)

    def list_versions(self, organization_id: int, document_id: int) -> list[DocumentVersionInfo]:
        return self._knowledge_repository.list_versions(organization_id, document_id)

    def get_status(self, organization_id: int, document_id: int) -> str | None:
        """Derives `status` from `chunk_count` + the audit trail -- no new
        column (Technical Design §3.4)."""
        document = self._knowledge_repository.get_document(organization_id, document_id)
        if document is None:
            return None
        if document.chunk_count > 0:
            return STATUS_INDEXED
        recent = self._repository.administration.list_audit_log(
            organization_id, limit=1, entity_type=ENTITY_TYPE, entity_id=document_id
        )
        if recent and recent[0].action == ACTION_INDEX_FAILED:
            return STATUS_FAILED
        return STATUS_INGESTED_PENDING_INDEX

    def _index(
        self, organization_id: int, user_id: int, document_id: int, correlation_id: str
    ) -> IngestedDocument:
        document = self._knowledge_repository.get_document(organization_id, document_id)
        if document is None:
            raise ValueError(
                f"Document {document_id} does not exist for organization {organization_id}"
            )
        try:
            self._knowledge_repository.index(document_id, correlation_id)
        except Exception as exc:
            self._repository.administration.record_audit(
                organization_id,
                user_id,
                ACTION_INDEX_FAILED,
                ENTITY_TYPE,
                document_id,
                {"version_id": document.version_id, "error": sanitize_error(exc)},
            )
            logger.exception(
                "Indexing failed document_id=%s version_id=%s", document_id, document.version_id
            )
            raise DocumentIndexingError(document_id, document.version_id, exc) from exc

        indexed_document = self._knowledge_repository.get_document(organization_id, document_id)
        self._repository.administration.record_audit(
            organization_id,
            user_id,
            ACTION_INDEXED,
            ENTITY_TYPE,
            document_id,
            {"version_id": indexed_document.version_id, "chunk_count": indexed_document.chunk_count},
        )
        return indexed_document
