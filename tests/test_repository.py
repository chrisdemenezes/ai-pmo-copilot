from src.api.routes import intelligence
from src.database.repository import AnalysisRepository


def test_repository_saves_analysis_in_sqlite_memory():
    repository = AnalysisRepository(database_url="sqlite:///:memory:")

    record_id = repository.save_analysis(
        kind="meeting",
        payload={"result": "ok"},
    )

    assert isinstance(record_id, int)
    assert record_id > 0


def test_build_repository_returns_the_same_cached_instance(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    intelligence.build_repository.cache_clear()
    try:
        first = intelligence.build_repository()
        second = intelligence.build_repository()
        assert first is second
    finally:
        intelligence.build_repository.cache_clear()


def test_save_analysis_stores_project_name():
    repository = AnalysisRepository(database_url="sqlite:///:memory:")

    repository.save_analysis(kind="meeting", payload={"result": "ok"}, project_name="Multilift")

    records = repository.list_analyses(project_name="Multilift")
    assert len(records) == 1
    assert records[0].project_name == "Multilift"
    assert records[0].kind == "meeting"


def test_list_analyses_filters_by_project_name():
    repository = AnalysisRepository(database_url="sqlite:///:memory:")

    repository.save_analysis(kind="meeting", payload={"result": "a"}, project_name="Multilift")
    repository.save_analysis(kind="risk", payload={"result": "b"}, project_name="Medlog")

    multilift_records = repository.list_analyses(project_name="Multilift")
    assert [r.project_name for r in multilift_records] == ["Multilift"]

    all_records = repository.list_analyses()
    assert len(all_records) == 2


def test_list_analyses_returns_empty_list_when_no_match():
    repository = AnalysisRepository(database_url="sqlite:///:memory:")

    repository.save_analysis(kind="meeting", payload={"result": "a"}, project_name="Multilift")

    assert repository.list_analyses(project_name="Unknown") == []


def test_list_analyses_respects_limit_and_offset():
    repository = AnalysisRepository(database_url="sqlite:///:memory:")

    for i in range(5):
        repository.save_analysis(kind="meeting", payload={"i": i}, project_name="Multilift")

    first_page = repository.list_analyses(project_name="Multilift", limit=2, offset=0)
    second_page = repository.list_analyses(project_name="Multilift", limit=2, offset=2)

    assert len(first_page) == 2
    assert len(second_page) == 2
    assert {r.id for r in first_page}.isdisjoint({r.id for r in second_page})


def test_list_analyses_orders_newest_first():
    repository = AnalysisRepository(database_url="sqlite:///:memory:")

    first_id = repository.save_analysis(kind="meeting", payload={"i": 1}, project_name="Multilift")
    second_id = repository.save_analysis(kind="meeting", payload={"i": 2}, project_name="Multilift")

    records = repository.list_analyses(project_name="Multilift")
    assert [r.id for r in records] == [second_id, first_id]
