"""pgvector-backed storage for Chunk embeddings (Fase 1).

The only class in the project aware of `pgvector` -- every other component
(the domain, a future Advisor) reaches vector storage exclusively through
`KnowledgeRepository`, which composes this class internally
(Princípio 2, `WAVE-3-DOMAIN-BLUEPRINT.md`).
"""
import logging
from typing import Protocol

from sqlalchemy.orm import sessionmaker

from src.database.models import Chunk, DocumentVersion
from src.services.knowledge_platform.types import ScoredChunk

logger = logging.getLogger(__name__)


class VectorRepositoryError(Exception):
    """Raised when a vector operation references a chunk that does not exist."""


class VectorRepository(Protocol):
    def upsert_vector(self, chunk_id: int, embedding: list[float]) -> None:
        ...

    def similarity_search(
        self, organization_id: int, query_embedding: list[float], top_k: int
    ) -> list[ScoredChunk]:
        ...


class PgVectorRepository:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def upsert_vector(self, chunk_id: int, embedding: list[float]) -> None:
        with self._session_factory() as session:
            chunk = session.get(Chunk, chunk_id)
            if chunk is None:
                raise VectorRepositoryError(f"Chunk {chunk_id} does not exist")
            chunk.embedding = embedding
            session.commit()

    def similarity_search(
        self, organization_id: int, query_embedding: list[float], top_k: int = 5
    ) -> list[ScoredChunk]:
        with self._session_factory() as session:
            distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
            rows = (
                session.query(Chunk, DocumentVersion.document_id, DocumentVersion.created_at, distance)
                .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
                # Tenant isolation: no similarity search ever crosses
                # organization_id, same discipline as every other
                # organization-scoped read in the platform.
                .filter(Chunk.organization_id == organization_id)
                .order_by(distance)
                .limit(top_k)
                .all()
            )
            return [
                ScoredChunk(
                    chunk_id=chunk.id,
                    document_id=document_id,
                    text=chunk.text,
                    score=1.0 - float(distance_value),
                    document_version_created_at=version_created_at,
                )
                for chunk, document_id, version_created_at, distance_value in rows
            ]
