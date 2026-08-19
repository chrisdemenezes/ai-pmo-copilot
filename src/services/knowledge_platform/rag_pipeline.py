"""RAG Pipeline (Wave 3 Fase 2, Knowledge Services), per
`DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`.

Stops exactly where Advisor-specific logic would begin (Founder directive,
this Fase): retrieves and ranks evidence, and hands back a
`RagContext` that is deterministic, auditable, and traceable to its
sources. It never composes a prompt, never calls an `LLMProvider`, and
never knows about a specific Advisor -- that composition belongs to the
Advisor Framework (Fase 3) and the Advisors themselves (Fase 4).

Only ever calls `KnowledgeRepository` -- never `VectorRepository` or
`EmbeddingProvider` directly (Founder directives 3-4, this Fase).
"""
import logging
from dataclasses import dataclass

from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.types import ScoredChunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RagContext:
    """The result of one context-resolution call -- deterministic given the
    same query and database state, and fully traceable: every chunk in
    `chunks` carries its real `chunk_id`/`document_id`, and `chunk_ids` is
    the authoritative set a future Advisor must validate any citation
    against (the same anti-hallucination discipline `RecommendationEngine`
    already applies to `analysis_id`, extended to chunk citations)."""

    query: str
    organization_id: int
    chunks: list[ScoredChunk]

    @property
    def chunk_ids(self) -> frozenset[int]:
        return frozenset(chunk.chunk_id for chunk in self.chunks)


class RagPipeline:
    def __init__(self, knowledge_repository: KnowledgeRepository):
        self._knowledge_repository = knowledge_repository

    def retrieve(self, organization_id: int, query: str, top_k: int = 5) -> RagContext:
        """Query Embedding + Semantic Search (via `KnowledgeRepository`) ->
        Ranking -> an auditable `RagContext`."""
        candidates = self._knowledge_repository.search(organization_id, query, top_k=top_k)
        ranked = self._rank(candidates)
        logger.info(
            "RAG retrieval organization_id=%s query=%r results=%d chunk_ids=%s",
            organization_id,
            query,
            len(ranked),
            [chunk.chunk_id for chunk in ranked],
        )
        return RagContext(query=query, organization_id=organization_id, chunks=ranked)

    @staticmethod
    def _rank(chunks: list[ScoredChunk]) -> list[ScoredChunk]:
        """Ranking (Blueprint §3): similarity score is the primary key --
        there is no real consumer yet to justify weighting it against
        anything else -- and document version recency breaks ties between
        chunks of otherwise equal relevance."""
        return sorted(
            chunks,
            key=lambda chunk: (chunk.score, chunk.document_version_created_at),
            reverse=True,
        )
