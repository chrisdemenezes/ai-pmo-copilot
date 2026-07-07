from src.database.repository import AnalysisRepository


def test_repository_saves_analysis_in_sqlite_memory():
    repository = AnalysisRepository(database_url="sqlite:///:memory:")

    record_id = repository.save_analysis(
        kind="meeting",
        payload={"result": "ok"},
    )

    assert isinstance(record_id, int)
    assert record_id > 0
