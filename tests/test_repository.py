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
