"""Enterprise Memory Model (Wave 3 Fase 2), per
`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md`.

Collision checklist (§0) revalidated for this implementation: this service
is backend, persisted, classifies `Document`s already ingested by the
Knowledge Platform, and is meant to be consumed by a future Advisor via the
Advisor Framework. `Executive Memory` (`web/lib/executive-memory/`)
remains frontend-only, stateless, and consumed directly by the
Workspace/Dashboard UI. No overlap in layer, persistence, mechanism, or
consumer -- no file under `web/lib/executive-memory/` is touched by this
Fase.

Scope for this Fase (Captura + Classificação + Consulta only): promoting a
record to organizational memory ("Consolidação") and automatic expiration
are explicitly out of scope -- there is no real consumer yet to ground
that design, the same discipline already applied to deferring a production
embedding backend in Fase 1.
"""
import logging
from enum import Enum

from sqlalchemy.orm import sessionmaker

from src.database.models import MemoryRecord
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.types import MemoryRecordInfo

logger = logging.getLogger(__name__)


class MemoryCategory(str, Enum):
    DOCUMENTAL = "documental"
    OPERACIONAL = "operacional"
    DECISOES = "decisoes"
    APRENDIZADOS = "aprendizados"
    ORGANIZACIONAL = "organizacional"


class EnterpriseMemoryService:
    def __init__(self, session_factory: sessionmaker, knowledge_repository: KnowledgeRepository):
        self._session_factory = session_factory
        self._knowledge_repository = knowledge_repository

    def classify(
        self, organization_id: int, document_id: int, category: MemoryCategory
    ) -> MemoryRecordInfo:
        """Classifies a Document that must already exist in the Knowledge
        Platform -- resolved via `KnowledgeRepository`, never a direct
        table read, so this service never bypasses the platform's single
        entry point."""
        document = self._knowledge_repository.get_document(organization_id, document_id)
        if document is None:
            raise ValueError(
                f"Document {document_id} does not exist for organization {organization_id}"
            )
        with self._session_factory() as session:
            record = MemoryRecord(
                organization_id=organization_id,
                document_id=document_id,
                category=category.value,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(
                "Classified document_id=%s organization_id=%s category=%s",
                document_id,
                organization_id,
                category.value,
            )
            return MemoryRecordInfo(
                id=record.id,
                organization_id=record.organization_id,
                document_id=record.document_id,
                category=record.category,
                created_at=record.created_at,
            )

    def list_by_category(
        self, organization_id: int, category: MemoryCategory
    ) -> list[MemoryRecordInfo]:
        with self._session_factory() as session:
            records = (
                session.query(MemoryRecord)
                .filter(
                    MemoryRecord.organization_id == organization_id,
                    MemoryRecord.category == category.value,
                )
                .order_by(MemoryRecord.created_at.desc())
                .all()
            )
            return [
                MemoryRecordInfo(
                    id=r.id,
                    organization_id=r.organization_id,
                    document_id=r.document_id,
                    category=r.category,
                    created_at=r.created_at,
                )
                for r in records
            ]
