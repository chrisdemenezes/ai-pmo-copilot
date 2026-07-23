from src.database.repository import AnalysisRepository
from src.services.ai_foundation.types import Evidence


class AIContextEngine:
    """Resolves the institutional data (already persisted AnalysisRecords)
    relevant to an Enterprise Analyst's question -- one implementation shared
    by every Analyst, instead of each one re-querying and re-filtering on
    its own (Domain Blueprint §4.1)."""

    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def gather(self, organization_id: int, project_name: str | None, kind: str) -> list[Evidence]:
        records = self._repository.list_analyses(
            organization_id=organization_id,
            project_name=project_name,
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
                    source_analysis_id=record.id,
                    source_created_at=record.created_at,
                    kind=kind,
                    summary=model_output,
                )
            )
        return evidence
