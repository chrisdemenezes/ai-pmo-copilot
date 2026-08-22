from datetime import datetime, timezone

from src.database.repository import AnalysisRepository
from src.services.ai_foundation.organizational_learning import (
    build_recurring_actions,
    build_recurring_risks,
    select_top_learnings,
)
from src.services.ai_foundation.types import Evidence
from src.services.executive_analytics.executive_signal_engine import (
    ExecutiveSignal,
    derive_cost_performance_signal,
    derive_forecast_deviation_signal,
    derive_schedule_performance_signal,
)
from src.services.executive_analytics.metrics_engine import (
    BaselinePoint,
    PerformanceSnapshotPoint,
    build_history_series,
    compute_evm_summary,
)
from src.services.knowledge_platform.rag_pipeline import RagContext
from src.services.project_summary_service import ProjectSummaryService

MAX_EXECUTIVE_ANALYTICS_SIGNALS = 5
_SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}


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

    def gather_executive_analytics_context(self, organization_id: int) -> list[Evidence]:
        """TD-017 (V1 Post-Completion Technical Closure): deterministic
        Executive Signals (cost/schedule performance trend, forecast
        deviation) across every Project in the organization with real EVM
        history, as controlled, capped-at-5 supporting context -- same
        discipline as `gather_organizational_learnings()`: never enters
        `evidence`/`cited_evidence`, so the Evidence Gate and every
        Advisor's own no-evidence behavior stay exactly as before this
        method existed. All arithmetic already happened in
        `executive_signal_engine.py`/`metrics_engine.py` -- this method
        only collects and caps, never computes a metric itself."""
        as_of = datetime.now(tz=timezone.utc).date()
        signals: list[ExecutiveSignal] = []
        for project in self._repository.domain.list_projects_by_organization(organization_id):
            baseline_rows = self._repository.performance.get_active_baseline(
                project.id, organization_id
            )
            snapshot_rows = self._repository.performance.list_snapshots(project.id, organization_id)
            if not baseline_rows and not snapshot_rows:
                continue
            baseline = [
                BaselinePoint(row.period_date, row.planned_value, row.bac_reference)
                for row in baseline_rows
            ]
            snapshots = [
                PerformanceSnapshotPoint(row.snapshot_date, row.actual_cost, row.progress_percentage)
                for row in snapshot_rows
            ]
            history = build_history_series(baseline, snapshots)
            summary = compute_evm_summary(baseline, snapshots, as_of)
            for signal in (
                derive_cost_performance_signal(history, project.name),
                derive_schedule_performance_signal(history, project.name),
                derive_forecast_deviation_signal(summary, project.name, as_of),
            ):
                if signal is not None:
                    signals.append(signal)

        top = sorted(signals, key=lambda s: (_SEVERITY_RANK[s.severity], s.scope))[
            :MAX_EXECUTIVE_ANALYTICS_SIGNALS
        ]

        return [
            Evidence(
                source_type="executive_signal",
                # Negative and unique per call, same convention as
                # gather_organizational_learnings() -- never collides with a
                # real AnalysisRecord.id (always positive).
                source_id=-(index + 1),
                source_label=f"Sinal executivo determinístico ({signal.signal_type})",
                content={
                    "signal_type": signal.signal_type,
                    "severity": signal.severity,
                    "scope": signal.scope,
                    "metric": signal.metric,
                    "current_value": float(signal.current_value),
                    "baseline_or_threshold": float(signal.baseline_or_threshold),
                    "trend": signal.trend,
                    "period": signal.period.isoformat(),
                    "evidence_reference": signal.evidence_reference,
                    "provenance": signal.provenance,
                },
                metadata={},
            )
            for index, signal in enumerate(top)
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
