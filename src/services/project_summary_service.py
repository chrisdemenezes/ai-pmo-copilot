import logging
from collections import defaultdict

from src.database.repository import (
    AnalysisRecord,
    AnalysisRepository,
    analysis_display_name,
)

logger = logging.getLogger(__name__)


class ProjectSummaryService:
    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def summarize(
        self,
        organization_id: int,
        project_name: str | None = None,
        project_id: int | None = None,
        display_name: str | None = None,
    ) -> dict:
        # TD-008 Fase 3b, Etapa 4a: scope strictly by project_id. A name is
        # resolved to its id first (resolve_scope_id) -- never used as a
        # filter key. A name that resolves to no Project yields a zero summary
        # echoing the requested name, exactly as the never-analyzed case did.
        scope_id, unmatched = self._repository.resolve_scope_id(
            organization_id, project_name=project_name, project_id=project_id
        )
        if unmatched:
            return self._aggregate(display_name or project_name, None, [])

        # Relies on the repository's list_analyses ordering records newest-first.
        records = self._repository.list_analyses(
            organization_id=organization_id,
            project_id=scope_id,
            limit=None,
        )
        resolved_id = scope_id if scope_id is not None else (
            records[0].project_id if records else None
        )
        # Display name derives from Project.name (via the record's project
        # relationship), never from the legacy project_name column. When the
        # project has no analyses yet, echo the name the caller informed
        # (display_name, else project_name) so an empty project still shows a
        # sensible label.
        if records:
            name = analysis_display_name(records[0])
        else:
            name = display_name or project_name
        return self._aggregate(name, resolved_id, records)

    def summarize_portfolio(self, organization_id: int) -> list[dict]:
        # One fetch of everything, grouped in memory, instead of one query per
        # project — MVP data volume doesn't justify N+1 queries here.
        records = self._repository.list_analyses(organization_id=organization_id, limit=None)

        # Grouped by project_id (the sole identity key, TD-008 Fase 3b): two
        # analyses saved under names that differ only by incidental whitespace
        # resolve to the same Project and must appear as one portfolio entry.
        # Analyses without an identifiable project (the fallback Project, whose
        # display name is None) are excluded from the executive portfolio, the
        # same behavior the legacy "project_name is not None" guard produced --
        # now expressed by identity, not by reading the project_name column.
        by_project: dict[int, list[AnalysisRecord]] = defaultdict(list)
        for record in records:
            if record.project_id is not None and analysis_display_name(record) is not None:
                # Partitioning a stream that's already newest-first preserves
                # that order within each project's bucket.
                by_project[record.project_id].append(record)

        summaries = [
            self._aggregate(analysis_display_name(project_records[0]), project_id, project_records)
            for project_id, project_records in by_project.items()
        ]
        summaries.sort(key=lambda summary: summary["project_name"])
        logger.info("Summarized portfolio: %d projects", len(summaries))
        return summaries

    def list_action_items(
        self,
        organization_id: int,
        project_name: str | None = None,
        project_id: int | None = None,
    ) -> list[dict]:
        # Same call already used by summarize()/summarize_portfolio() -- zero
        # new query, zero new table (FS-007 §2.1). One fetch, flattened in
        # memory, never one query per meeting. Scope strictly by project_id
        # (TD-008 Fase 3b, Etapa 4a).
        scope_id, unmatched = self._repository.resolve_scope_id(
            organization_id, project_name=project_name, project_id=project_id
        )
        if unmatched:
            return []
        records = self._repository.list_analyses(
            organization_id=organization_id,
            project_id=scope_id,
            kind="meeting",
            limit=None,
        )

        items: list[dict] = []
        for record in records:
            model_output = (record.payload or {}).get("model_output")
            if not isinstance(model_output, dict) or not model_output.get("structured"):
                continue

            for item in model_output.get("action_items") or []:
                # A malformed item from one specific meeting is excluded from
                # the rollup, never allowed to break it -- same schema-robustness
                # discipline as _aggregate.
                if not isinstance(item, dict) or not isinstance(item.get("description"), str):
                    continue
                owner = item.get("owner")
                due_date = item.get("due_date")
                items.append(
                    {
                        "project_name": analysis_display_name(record),
                        "project_id": record.project_id,
                        "description": item["description"],
                        "owner": owner if isinstance(owner, str) else None,
                        "due_date": due_date if isinstance(due_date, str) else None,
                        "source_analysis_id": record.id,
                        "source_created_at": record.created_at,
                    }
                )

        logger.info(
            "Listed %d action items project_id=%s from %d meeting analyses",
            len(items),
            scope_id,
            len(records),
        )
        return items

    def list_latest_risks(
        self,
        organization_id: int,
        project_name: str | None = None,
        project_id: int | None = None,
    ) -> list[dict]:
        # Same call already used by list_action_items() -- zero new query.
        # Difference: keeps only the MOST RECENT risk analysis per project
        # (same principle as latest_health_status in _aggregate), not the
        # whole history -- the attention zone is always about the current
        # analysis, matching what the Riscos Brief already shows today.
        scope_id, unmatched = self._repository.resolve_scope_id(
            organization_id, project_name=project_name, project_id=project_id
        )
        if unmatched:
            return []
        records = self._repository.list_analyses(
            organization_id=organization_id,
            project_id=scope_id,
            kind="risk",
            limit=None,
        )

        # Dedup by project_id (identity), TD-008 Fase 3b, Etapa 4a -- never by
        # the project_name string.
        seen_projects: set[int | None] = set()
        items: list[dict] = []
        for record in records:  # already newest-first
            if record.project_id in seen_projects:
                continue

            model_output = (record.payload or {}).get("model_output")
            if not isinstance(model_output, dict) or not model_output.get("structured"):
                # Not marked as seen -- an older, structured risk analysis
                # for this project may still count as "the most recent".
                continue

            seen_projects.add(record.project_id)
            escalation_recommendation = model_output.get("escalation_recommendation")
            for risk in model_output.get("risks") or []:
                if not isinstance(risk, dict) or not isinstance(risk.get("description"), str):
                    continue
                items.append(
                    {
                        "project_name": analysis_display_name(record),
                        "project_id": record.project_id,
                        "description": risk["description"],
                        "probability": risk.get("probability"),
                        "impact": risk.get("impact"),
                        "mitigation": risk.get("mitigation"),
                        "escalation_recommendation": escalation_recommendation
                        if isinstance(escalation_recommendation, str)
                        else None,
                        "source_analysis_id": record.id,
                        "source_created_at": record.created_at,
                    }
                )

        logger.info(
            "Listed %d latest risks project_id=%s from %d risk analyses",
            len(items),
            scope_id,
            len(records),
        )
        return items

    @staticmethod
    def _aggregate(project_name: str, project_id: int | None, records: list[AnalysisRecord]) -> dict:
        open_risks = 0
        pending_action_items = 0
        latest_health_status: str | None = None

        for record in records:
            model_output = (record.payload or {}).get("model_output")
            if not isinstance(model_output, dict) or not model_output.get("structured"):
                continue

            if record.kind == "risk":
                open_risks += len(model_output.get("risks") or [])
            elif record.kind == "meeting":
                pending_action_items += len(model_output.get("action_items") or [])
            elif record.kind == "status" and latest_health_status is None:
                latest_health_status = model_output.get("health_status")

        summary = {
            "project_name": project_name,
            "project_id": project_id,
            "total_analyses": len(records),
            "open_risks": open_risks,
            "pending_action_items": pending_action_items,
            "latest_health_status": latest_health_status,
        }
        logger.info(
            "Summarized project_name=%s total_analyses=%d open_risks=%d pending_action_items=%d",
            project_name,
            summary["total_analyses"],
            open_risks,
            pending_action_items,
        )
        return summary
