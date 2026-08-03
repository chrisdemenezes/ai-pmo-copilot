from src.database.repository import AnalysisRepository
from src.services.ai_foundation.types import Evidence
from src.services.knowledge_platform.rag_pipeline import RagContext


class AIContextEngine:
    """Resolves the institutional data (already persisted AnalysisRecords)
    relevant to an Enterprise Analyst's question -- one implementation shared
    by every Analyst, instead of each one re-querying and re-filtering on
    its own (Domain Blueprint §4.1).

    D-086: also the single place that normalizes RAG evidence
    (`normalize_rag_evidence()`) for every Class D Advisor (Document,
    Governance) -- preparing context, never interpreting domain."""

    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def gather(self, organization_id: int, project_name: str | None, kind: str) -> list[Evidence]:
        # TD-008 Fase 3b, Etapa 4a: scope by project_id. The Analyst still
        # receives the project by name (the user informs a name); it is
        # resolved to an id before the query -- never used as a filter key. A
        # name with no Project yields no evidence (an unanalyzed project has
        # nothing to synthesize), same result the legacy name filter produced.
        scope_id, unmatched = self._repository.resolve_scope_id(
            organization_id, project_name=project_name
        )
        if unmatched:
            return []
        records = self._repository.list_analyses(
            organization_id=organization_id,
            project_id=scope_id,
            kind=kind,
            limit=None,
        )

        evidence: list[Evidence] = []
        for record in records:
            model_output = (record.payload or {}).get("model_output")
            if not isinstance(model_output, dict) or not model_output.get("structured"):
                continue
            evidence.append(
                Evidence(
                    source_type="analysis_record",
                    source_id=record.id,
                    source_label=f"AnalysisRecord#{record.id} ({kind})",
                    content=model_output,
                    metadata={"created_at": record.created_at, "kind": kind},
                )
            )
        return evidence

    def normalize_rag_evidence(self, rag_context: RagContext) -> list[Evidence]:
        """Mechanical envelope only (D-086/AR-9 §3): never interprets
        `chunk.text`, never decides relevance -- ranking/relevance is
        already `RagPipeline`'s responsibility (Fase 2). One `Evidence` per
        `ScoredChunk`, in the same order `RagContext.chunks` already
        provides."""
        return [
            Evidence(
                source_type="document_chunk",
                source_id=chunk.chunk_id,
                source_label=f"Document {chunk.document_id} / Chunk {chunk.chunk_id}",
                content={"text": chunk.text},
                metadata={
                    "document_id": chunk.document_id,
                    "score": chunk.score,
                    "created_at": chunk.document_version_created_at,
                },
            )
            for chunk in rag_context.chunks
        ]
