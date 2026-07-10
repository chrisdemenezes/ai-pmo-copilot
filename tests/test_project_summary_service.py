from src.database.repository import AnalysisRepository
from src.services.project_summary_service import ProjectSummaryService


def _repository() -> AnalysisRepository:
    return AnalysisRepository(database_url="sqlite:///:memory:")


def test_summarize_counts_risks_and_action_items_from_structured_payloads():
    repository = _repository()
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "risks": [{"description": "a"}, {"description": "b"}],
            }
        },
    )
    repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "action_items": [{"description": "x"}]}},
    )

    summary = ProjectSummaryService(repository).summarize("Multilift")

    assert summary == {
        "project_name": "Multilift",
        "total_analyses": 2,
        "open_risks": 2,
        "pending_action_items": 1,
        "latest_health_status": None,
    }


def test_summarize_uses_latest_status_analysis():
    repository = _repository()
    repository.save_analysis(
        kind="status",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "health_status": "red"}},
    )
    repository.save_analysis(
        kind="status",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "health_status": "green"}},
    )

    summary = ProjectSummaryService(repository).summarize("Multilift")

    assert summary["latest_health_status"] == "green"


def test_summarize_ignores_fallback_unstructured_payloads():
    repository = _repository()
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": False, "raw_output": "not json"}},
    )

    summary = ProjectSummaryService(repository).summarize("Multilift")

    assert summary["open_risks"] == 0
    assert summary["total_analyses"] == 1


def test_summarize_only_counts_analyses_for_the_requested_project():
    repository = _repository()
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "risks": [{"description": "a"}]}},
    )
    repository.save_analysis(
        kind="risk",
        project_name="Medlog",
        payload={"model_output": {"structured": True, "risks": [{"description": "b"}]}},
    )

    summary = ProjectSummaryService(repository).summarize("Multilift")

    assert summary["total_analyses"] == 1
    assert summary["open_risks"] == 1


def test_summarize_returns_zeros_for_project_with_no_analyses():
    repository = _repository()

    summary = ProjectSummaryService(repository).summarize("Unknown")

    assert summary == {
        "project_name": "Unknown",
        "total_analyses": 0,
        "open_risks": 0,
        "pending_action_items": 0,
        "latest_health_status": None,
    }
