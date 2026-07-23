import pytest

from src.database.repository import AnalysisRepository
from src.services.project_summary_service import ProjectSummaryService
from tests.db import temp_database_url


@pytest.fixture()
def repository():
    with temp_database_url("project_summary") as database_url:
        yield AnalysisRepository(database_url=database_url)


def test_summarize_counts_risks_and_action_items_from_structured_payloads(repository):
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

    project_id = summary.pop("project_id")
    assert isinstance(project_id, int)
    assert summary == {
        "project_name": "Multilift",
        "total_analyses": 2,
        "open_risks": 2,
        "pending_action_items": 1,
        "latest_health_status": None,
    }


def test_summarize_uses_latest_status_analysis(repository):
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


def test_summarize_ignores_fallback_unstructured_payloads(repository):
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": False, "raw_output": "not json"}},
    )

    summary = ProjectSummaryService(repository).summarize("Multilift")

    assert summary["open_risks"] == 0
    assert summary["total_analyses"] == 1


def test_summarize_only_counts_analyses_for_the_requested_project(repository):
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


def test_summarize_returns_zeros_for_project_with_no_analyses(repository):

    summary = ProjectSummaryService(repository).summarize("Unknown")

    assert summary == {
        "project_name": "Unknown",
        "project_id": None,
        "total_analyses": 0,
        "open_risks": 0,
        "pending_action_items": 0,
        "latest_health_status": None,
    }


def test_summarize_portfolio_groups_by_project_and_sorts_by_name(repository):
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "risks": [{"description": "a"}]}},
    )
    repository.save_analysis(
        kind="meeting",
        project_name="Medlog",
        payload={"model_output": {"structured": True, "action_items": [{"description": "x"}]}},
    )

    portfolio = ProjectSummaryService(repository).summarize_portfolio()

    assert [entry["project_name"] for entry in portfolio] == ["Medlog", "Multilift"]
    medlog, multilift = portfolio
    assert medlog["pending_action_items"] == 1
    assert medlog["open_risks"] == 0
    assert multilift["open_risks"] == 1
    assert multilift["pending_action_items"] == 0


def test_summarize_portfolio_excludes_analyses_without_a_project_name(repository):
    repository.save_analysis(
        kind="risk",
        project_name=None,
        payload={"model_output": {"structured": True, "risks": [{"description": "a"}]}},
    )
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "risks": [{"description": "b"}]}},
    )

    portfolio = ProjectSummaryService(repository).summarize_portfolio()

    assert [entry["project_name"] for entry in portfolio] == ["Multilift"]


def test_summarize_portfolio_groups_whitespace_variant_names_under_one_project(repository):
    # get_or_create_project_for_name() strips whitespace before resolving the
    # Project, so "Multilift" and "Multilift " (trailing space) already share
    # the same project_id at write time. summarize_portfolio() must group by
    # that project_id, not the raw string, or these appear as 2 entries
    # instead of 1 (TD-008 Fase 3 bug, fixed by Epic W3-1 Fase 3a).
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "risks": [{"description": "a"}]}},
    )
    repository.save_analysis(
        kind="meeting",
        project_name="Multilift ",
        payload={"model_output": {"structured": True, "action_items": [{"description": "x"}]}},
    )

    portfolio = ProjectSummaryService(repository).summarize_portfolio()

    assert len(portfolio) == 1
    entry = portfolio[0]
    assert entry["total_analyses"] == 2
    assert entry["open_risks"] == 1
    assert entry["pending_action_items"] == 1
    assert entry["project_id"] is not None


def test_summarize_portfolio_returns_empty_list_when_no_analyses_exist(repository):

    assert ProjectSummaryService(repository).summarize_portfolio() == []


def test_list_action_items_flattens_items_from_meeting_analyses(repository):
    analysis_id = repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "action_items": [
                    {"description": "Atualizar cronograma", "owner": "Ana", "due_date": "2026-07-20"},
                    {"description": "Cobrar fornecedor", "owner": None, "due_date": None},
                ],
            }
        },
    )

    items = ProjectSummaryService(repository).list_action_items("Multilift")

    assert len(items) == 2
    first, second = items
    assert first["description"] == "Atualizar cronograma"
    assert first["owner"] == "Ana"
    assert first["due_date"] == "2026-07-20"
    assert first["project_name"] == "Multilift"
    assert first["source_analysis_id"] == analysis_id
    assert first["source_created_at"] is not None
    assert second["description"] == "Cobrar fornecedor"
    assert second["owner"] is None
    assert second["due_date"] is None


def test_list_action_items_without_project_name_spans_the_portfolio(repository):
    repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "action_items": [{"description": "a"}]}},
    )
    repository.save_analysis(
        kind="meeting",
        project_name="Medlog",
        payload={"model_output": {"structured": True, "action_items": [{"description": "b"}]}},
    )

    items = ProjectSummaryService(repository).list_action_items()

    assert sorted(item["project_name"] for item in items) == ["Medlog", "Multilift"]


def test_list_action_items_scopes_to_the_requested_project(repository):
    repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "action_items": [{"description": "a"}]}},
    )
    repository.save_analysis(
        kind="meeting",
        project_name="Medlog",
        payload={"model_output": {"structured": True, "action_items": [{"description": "b"}]}},
    )

    items = ProjectSummaryService(repository).list_action_items("Medlog")

    assert [item["description"] for item in items] == ["b"]


def test_list_action_items_ignores_non_meeting_and_unstructured_analyses(repository):
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "risks": [{"description": "r"}]}},
    )
    repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={"model_output": {"structured": False, "raw_output": "not json"}},
    )

    assert ProjectSummaryService(repository).list_action_items("Multilift") == []


def test_list_action_items_excludes_a_malformed_item_without_dropping_the_rest(repository):
    repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "action_items": [
                    "not a dict",
                    {"owner": "Ana"},
                    {"description": "Item válido", "owner": 42, "due_date": ["not", "a", "string"]},
                ],
            }
        },
    )

    items = ProjectSummaryService(repository).list_action_items("Multilift")

    # Only the item with a real description survives; its non-string
    # owner/due_date degrade to None instead of breaking the rollup.
    assert len(items) == 1
    assert items[0]["description"] == "Item válido"
    assert items[0]["owner"] is None
    assert items[0]["due_date"] is None


def test_list_action_items_orders_newest_meeting_first_preserving_item_order(repository):
    first_id = repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "action_items": [{"description": "antiga-1"}, {"description": "antiga-2"}],
            }
        },
    )
    second_id = repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "action_items": [{"description": "recente"}]}},
    )
    assert second_id > first_id

    items = ProjectSummaryService(repository).list_action_items("Multilift")

    # Repository streams analyses newest-first; within one meeting, the
    # items keep the order the agent extracted them in.
    assert [item["description"] for item in items] == ["recente", "antiga-1", "antiga-2"]


def test_list_latest_risks_returns_risks_from_the_most_recent_analysis_only(repository):
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "risks": [{"description": "risco antigo", "probability": "low", "impact": "low", "mitigation": "m1"}],
                "escalation_recommendation": None,
            }
        },
    )
    second_id = repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "risks": [
                    {"description": "risco recente", "probability": "high", "impact": "high", "mitigation": "m2"},
                ],
                "escalation_recommendation": "Escalar ao comitê",
            }
        },
    )

    items = ProjectSummaryService(repository).list_latest_risks("Multilift")

    assert len(items) == 1
    assert items[0]["description"] == "risco recente"
    assert items[0]["probability"] == "high"
    assert items[0]["impact"] == "high"
    assert items[0]["mitigation"] == "m2"
    assert items[0]["escalation_recommendation"] == "Escalar ao comitê"
    assert items[0]["source_analysis_id"] == second_id


def test_list_latest_risks_falls_back_to_an_older_structured_analysis(repository):
    first_id = repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "risks": [{"description": "risco válido", "probability": "medium", "impact": "medium", "mitigation": "m"}],
                "escalation_recommendation": None,
            }
        },
    )
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": False, "raw_output": "not json"}},
    )

    items = ProjectSummaryService(repository).list_latest_risks("Multilift")

    assert len(items) == 1
    assert items[0]["description"] == "risco válido"
    assert items[0]["source_analysis_id"] == first_id


def test_list_latest_risks_without_project_name_spans_the_portfolio(repository):
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "risks": [{"description": "a", "probability": "high", "impact": "high", "mitigation": "m"}],
                "escalation_recommendation": None,
            }
        },
    )
    repository.save_analysis(
        kind="risk",
        project_name="Medlog",
        payload={
            "model_output": {
                "structured": True,
                "risks": [{"description": "b", "probability": "low", "impact": "low", "mitigation": "m"}],
                "escalation_recommendation": None,
            }
        },
    )

    items = ProjectSummaryService(repository).list_latest_risks()

    assert sorted(item["project_name"] for item in items) == ["Medlog", "Multilift"]


def test_list_latest_risks_ignores_non_risk_and_unstructured_analyses(repository):
    repository.save_analysis(
        kind="meeting",
        project_name="Multilift",
        payload={"model_output": {"structured": True, "action_items": [{"description": "x"}]}},
    )
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={"model_output": {"structured": False, "raw_output": "not json"}},
    )

    assert ProjectSummaryService(repository).list_latest_risks("Multilift") == []


def test_list_latest_risks_excludes_a_malformed_risk_without_dropping_the_rest(repository):
    repository.save_analysis(
        kind="risk",
        project_name="Multilift",
        payload={
            "model_output": {
                "structured": True,
                "risks": [
                    "not a dict",
                    {"probability": "high"},
                    {"description": "risco válido", "probability": "high", "impact": "high", "mitigation": "m"},
                ],
                "escalation_recommendation": None,
            }
        },
    )

    items = ProjectSummaryService(repository).list_latest_risks("Multilift")

    assert len(items) == 1
    assert items[0]["description"] == "risco válido"


def test_list_latest_risks_returns_empty_list_when_there_are_no_risk_analyses(repository):
    assert ProjectSummaryService(repository).list_latest_risks("Multilift") == []
