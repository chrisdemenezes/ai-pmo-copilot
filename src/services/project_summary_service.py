import logging
from collections import defaultdict

from src.database.repository import AnalysisRecord, AnalysisRepository

logger = logging.getLogger(__name__)


class ProjectSummaryService:
    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def summarize(self, project_name: str) -> dict:
        # Relies on the repository's list_analyses ordering records newest-first.
        records = self._repository.list_analyses(project_name=project_name, limit=None)
        return self._aggregate(project_name, records)

    def summarize_portfolio(self) -> list[dict]:
        # One fetch of everything, grouped in memory, instead of one query per
        # project — MVP data volume doesn't justify N+1 queries here.
        records = self._repository.list_analyses(limit=None)

        by_project: dict[str, list[AnalysisRecord]] = defaultdict(list)
        for record in records:
            if record.project_name is not None:
                # Partitioning a stream that's already newest-first preserves
                # that order within each project's bucket.
                by_project[record.project_name].append(record)

        summaries = [
            self._aggregate(project_name, project_records)
            for project_name, project_records in sorted(by_project.items())
        ]
        logger.info("Summarized portfolio: %d projects", len(summaries))
        return summaries

    def list_action_items(self, project_name: str | None = None) -> list[dict]:
        # Same call already used by summarize()/summarize_portfolio() -- zero
        # new query, zero new table (FS-007 §2.1). One fetch, flattened in
        # memory, never one query per meeting.
        records = self._repository.list_analyses(
            project_name=project_name,
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
                        "project_name": record.project_name,
                        "description": item["description"],
                        "owner": owner if isinstance(owner, str) else None,
                        "due_date": due_date if isinstance(due_date, str) else None,
                        "source_analysis_id": record.id,
                        "source_created_at": record.created_at,
                    }
                )

        logger.info(
            "Listed %d action items project_name=%s from %d meeting analyses",
            len(items),
            project_name,
            len(records),
        )
        return items

    @staticmethod
    def _aggregate(project_name: str, records: list[AnalysisRecord]) -> dict:
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
