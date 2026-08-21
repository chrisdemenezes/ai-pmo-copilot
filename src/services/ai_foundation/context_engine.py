from src.database.repository import AnalysisRepository
from src.services.ai_foundation.organizational_learning import (
    build_recurring_actions,
    build_recurring_risks,
    select_top_learnings,
)
from src.services.ai_foundation.types import Evidence
from src.services.knowledge_platform.rag_pipeline import RagContext
from src.services.project_summary_service import ProjectSummaryService


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

    def gather_organizational_learnings(self, organization_id: int) -> list[Evidence]:
        """Package M (V1 Product & Capability Completion): recurring
        risks/actions across 3+ distinct projects, as controlled,
        capped-at-5 supporting context -- never a primary evidentiary
        basis (see `PMOAdvisorAgent`/`ExecutiveAdvisorAgent`: this never
        enters `evidence`/`cited_evidence`, so the Evidence Gate and every
        Advisor's own no-evidence behavior stay exactly as before this
        method existed). Reuses `ProjectSummaryService`'s already-tested
        accessors verbatim -- zero new query, zero new repository method,
        same tenant scoping (`organization_id`) as every other read here.
        """
        service = ProjectSummaryService(self._repository)
        risk_learnings = build_recurring_risks(service.list_latest_risks(organization_id))
        action_learnings = build_recurring_actions(service.list_action_items(organization_id))
        top = select_top_learnings(risk_learnings, action_learnings)

        return [
            Evidence(
                source_type="organizational_learning",
                # Negative and unique per call: guaranteed to never collide
                # with a real AnalysisRecord.id (always positive) -- this
                # Evidence has no single underlying row, so it can never be
                # confused with one (RecommendationEngine.build()'s by_id
                # dict keys on source_type="analysis_record" ids only in
                # every advisor that consumes this).
                source_id=-(index + 1),
                source_label=f"Aprendizado organizacional recorrente ({learning.category})",
                content={
                    "category": learning.category,
                    "description": learning.description,
                    "occurrences": learning.occurrences,
                    "project_names": list(learning.project_names),
                },
                metadata={},
            )
            for index, learning in enumerate(top)
        ]

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
