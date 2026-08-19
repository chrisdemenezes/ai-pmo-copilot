"""`KnowledgeRepository` -- the single domain-facing entry point of the
Enterprise Knowledge Platform (Fase 1), per
`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §2. Composes
`EmbeddingProvider` + `VectorRepository` + Document/DocumentVersion/Chunk
persistence -- no caller sees those three pieces separately.
"""
import logging

from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from src.database.models import Chunk, Document, DocumentVersion
from src.services.events.interfaces import EventPublisher
from src.services.knowledge_platform.embedding_provider import EmbeddingProvider
from src.services.knowledge_platform.types import (
    DocumentVersionInfo,
    IngestedDocument,
    ScoredChunk,
)
from src.services.knowledge_platform.vector_repository import VectorRepository

logger = logging.getLogger(__name__)

# Fase 1 minimal chunking strategy (Blueprint §1.3): fixed-size windows with
# a small overlap, preserving enough locality that a citation always points
# at a real, boundable slice of the source text. Refined per
# DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md if a real RAG consumer needs it
# (Fase 2) -- out of scope here.
CHUNK_SIZE_CHARS = 500
CHUNK_OVERLAP_CHARS = 50


def _chunk_text(text: str) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    step = CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS
    length = len(normalized)
    chunks = []
    start = 0
    while start < length:
        end = min(start + CHUNK_SIZE_CHARS, length)
        chunks.append(normalized[start:end])
        if end == length:
            break
        start += step
    return chunks


class KnowledgeRepository:
    def __init__(
        self,
        session_factory: sessionmaker,
        embedding_provider: EmbeddingProvider,
        vector_repository: VectorRepository,
        event_publisher: EventPublisher,
    ):
        self._session_factory = session_factory
        self._embedding_provider = embedding_provider
        self._vector_repository = vector_repository
        self._event_publisher = event_publisher

    def ingest(
        self,
        organization_id: int,
        source_name: str,
        text: str,
        project_id: int | None = None,
    ) -> IngestedDocument:
        """Finds the Document by (organization_id, source_name) or creates
        one, then always adds a new DocumentVersion -- reingestion of a
        known source never overwrites a prior version (Blueprint §1.10)."""
        with self._session_factory() as session:
            document = (
                session.query(Document)
                .filter(
                    Document.organization_id == organization_id,
                    Document.source_name == source_name,
                )
                .one_or_none()
            )
            if document is None:
                document = Document(
                    organization_id=organization_id,
                    project_id=project_id,
                    source_name=source_name,
                )
                session.add(document)
                session.flush()

            version = DocumentVersion(document_id=document.id, content=text)
            session.add(version)
            session.commit()
            session.refresh(document)
            session.refresh(version)
            logger.info(
                "Ingested document id=%s organization_id=%s source_name=%s version_id=%s",
                document.id,
                organization_id,
                source_name,
                version.id,
            )
            return IngestedDocument(
                id=document.id,
                organization_id=document.organization_id,
                project_id=document.project_id,
                source_name=document.source_name,
                version_id=version.id,
                # A version just created by ingest() never has chunks yet --
                # index() runs strictly after (Technical Design W5-0 §3.1) --
                # deterministic, no query needed.
                chunk_count=0,
                created_at=document.created_at,
            )

    def index(self, document_id: int, correlation_id: str) -> None:
        """Chunks the latest DocumentVersion of a Document, embeds each
        chunk, and persists the resulting Chunk rows -- Parsing (Fase 1:
        already-normalized text) -> Chunking -> Embeddings -> Indexação.

        Wave 4 (Enterprise Operations, Epic W4-3): publishes `document.indexed`
        via `EventPublisher` only after the chunks are committed -- if this
        method raises before that point, no event is published. `correlation_id`
        is never minted here, exactly like `DomainService` (W4-1) -- it is
        supplied by the caller (today, only tests; a future route/pipeline
        would pass its own `context.request_id`)."""
        with self._session_factory() as session:
            document = session.get(Document, document_id)
            if document is None:
                raise ValueError(f"Document {document_id} does not exist")

            version = (
                session.query(DocumentVersion)
                .filter(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.id.desc())
                .first()
            )
            if version is None:
                raise ValueError(f"Document {document_id} has no version to index")

            chunks = _chunk_text(version.content)
            for chunk_index, chunk_text in enumerate(chunks):
                session.add(
                    Chunk(
                        document_version_id=version.id,
                        organization_id=document.organization_id,
                        chunk_index=chunk_index,
                        text=chunk_text,
                        embedding=self._embedding_provider.embed(chunk_text),
                        # Minimal provenance (Founder Decision D-175/D-177):
                        # every provider self-reports its own identity --
                        # no domain interpretation of "which provider" is
                        # added here, just a pass-through of what the
                        # injected EmbeddingProvider already exposes.
                        embedding_provider=self._embedding_provider.provider_name,
                        embedding_model=self._embedding_provider.model_name,
                    )
                )
            session.commit()
            logger.info("Indexed document_id=%s version_id=%s", document_id, version.id)
            organization_id = document.organization_id
            version_id = version.id
            chunk_count = len(chunks)

        self._event_publisher.publish(
            "document.indexed",
            {"document_id": document_id, "version_id": version_id, "chunk_count": chunk_count},
            organization_id,
            correlation_id=correlation_id,
            origin="knowledge_repository",
        )

    def search(self, organization_id: int, query: str, top_k: int = 5) -> list[ScoredChunk]:
        query_embedding = self._embedding_provider.embed(query)
        return self._vector_repository.similarity_search(organization_id, query_embedding, top_k)

    def get_document(self, organization_id: int, document_id: int) -> IngestedDocument | None:
        with self._session_factory() as session:
            document = session.get(Document, document_id)
            if document is None or document.organization_id != organization_id:
                return None
            latest_version = (
                session.query(DocumentVersion)
                .filter(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.id.desc())
                .first()
            )
            chunk_count = (
                session.query(func.count(Chunk.id))
                .filter(Chunk.document_version_id == latest_version.id)
                .scalar()
            )
            return IngestedDocument(
                id=document.id,
                organization_id=document.organization_id,
                project_id=document.project_id,
                source_name=document.source_name,
                version_id=latest_version.id,
                chunk_count=chunk_count,
                created_at=document.created_at,
            )

    def list_documents(
        self, organization_id: int, project_id: int | None = None
    ) -> list[IngestedDocument]:
        with self._session_factory() as session:
            query = session.query(Document).filter(Document.organization_id == organization_id)
            if project_id is not None:
                query = query.filter(Document.project_id == project_id)
            documents = query.order_by(Document.id.asc()).all()

            results: list[IngestedDocument] = []
            for document in documents:
                latest_version = (
                    session.query(DocumentVersion)
                    .filter(DocumentVersion.document_id == document.id)
                    .order_by(DocumentVersion.id.desc())
                    .first()
                )
                if latest_version is None:
                    continue
                chunk_count = (
                    session.query(func.count(Chunk.id))
                    .filter(Chunk.document_version_id == latest_version.id)
                    .scalar()
                )
                results.append(
                    IngestedDocument(
                        id=document.id,
                        organization_id=document.organization_id,
                        project_id=document.project_id,
                        source_name=document.source_name,
                        version_id=latest_version.id,
                        chunk_count=chunk_count,
                        created_at=document.created_at,
                    )
                )
            return results

    def list_versions(self, organization_id: int, document_id: int) -> list[DocumentVersionInfo]:
        with self._session_factory() as session:
            document = session.get(Document, document_id)
            if document is None or document.organization_id != organization_id:
                return []
            versions = (
                session.query(DocumentVersion)
                .filter(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.id.asc())
                .all()
            )
            counts_by_version_id = dict(
                session.query(Chunk.document_version_id, func.count(Chunk.id))
                .filter(Chunk.document_version_id.in_([v.id for v in versions]))
                .group_by(Chunk.document_version_id)
                .all()
            )
            return [
                DocumentVersionInfo(
                    id=v.id,
                    document_id=v.document_id,
                    created_at=v.created_at,
                    chunk_count=counts_by_version_id.get(v.id, 0),
                )
                for v in versions
            ]
