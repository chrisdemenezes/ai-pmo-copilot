import logging

from src.database.repository import AnalysisRepository

logger = logging.getLogger(__name__)


class ProjectSummaryService:
    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def summarize(self, project_name: str) -> dict:
        # Relies on the repository's list_analyses ordering records newest-first,
        # so the first "status" kind record encountered below is the latest one.
        records = self._repository.list_analyses(project_name=project_name, limit=None)

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
