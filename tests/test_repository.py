from datetime import datetime, timedelta, timezone

import pytest

from src.api.dependencies import build_repository
from src.database.repository import AnalysisRepository
from tests.db import temp_database_url


@pytest.fixture()
def repository():
    with temp_database_url("analysis_repo") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Organização Única")


def test_repository_saves_analysis(repository, org_id):
    record_id = repository.save_analysis(
        kind="meeting",
        payload={"result": "ok"},
        organization_id=org_id,
    )

    assert isinstance(record_id, int)
    assert record_id > 0


def test_build_repository_returns_the_same_cached_instance(monkeypatch):
    with temp_database_url("analysis_repo_cache") as database_url:
        monkeypatch.setenv("DATABASE_URL", database_url)
        build_repository.cache_clear()
        try:
            first = build_repository()
            second = build_repository()
            assert first is second
        finally:
            build_repository.cache_clear()


def test_save_analysis_stores_project_name(repository, org_id):
    repository.save_analysis(
        kind="meeting", payload={"result": "ok"}, organization_id=org_id, project_name="Multilift"
    )

    records = repository.list_analyses(organization_id=org_id, project_name="Multilift")
    assert len(records) == 1
    assert records[0].project_name == "Multilift"
    assert records[0].kind == "meeting"


def test_list_analyses_filters_by_project_name(repository, org_id):
    repository.save_analysis(
        kind="meeting", payload={"result": "a"}, organization_id=org_id, project_name="Multilift"
    )
    repository.save_analysis(
        kind="risk", payload={"result": "b"}, organization_id=org_id, project_name="Medlog"
    )

    multilift_records = repository.list_analyses(organization_id=org_id, project_name="Multilift")
    assert [r.project_name for r in multilift_records] == ["Multilift"]

    all_records = repository.list_analyses(organization_id=org_id)
    assert len(all_records) == 2


def test_list_analyses_returns_empty_list_when_no_match(repository, org_id):
    repository.save_analysis(
        kind="meeting", payload={"result": "a"}, organization_id=org_id, project_name="Multilift"
    )

    assert repository.list_analyses(organization_id=org_id, project_name="Unknown") == []


def test_list_analyses_respects_limit_and_offset(repository, org_id):
    for i in range(5):
        repository.save_analysis(
            kind="meeting", payload={"i": i}, organization_id=org_id, project_name="Multilift"
        )

    first_page = repository.list_analyses(
        organization_id=org_id, project_name="Multilift", limit=2, offset=0
    )
    second_page = repository.list_analyses(
        organization_id=org_id, project_name="Multilift", limit=2, offset=2
    )

    assert len(first_page) == 2
    assert len(second_page) == 2
    assert {r.id for r in first_page}.isdisjoint({r.id for r in second_page})


def test_list_analyses_orders_newest_first(repository, org_id):
    first_id = repository.save_analysis(
        kind="meeting", payload={"i": 1}, organization_id=org_id, project_name="Multilift"
    )
    second_id = repository.save_analysis(
        kind="meeting", payload={"i": 2}, organization_id=org_id, project_name="Multilift"
    )

    records = repository.list_analyses(organization_id=org_id, project_name="Multilift")
    assert [r.id for r in records] == [second_id, first_id]


def test_get_analysis_returns_matching_record(repository, org_id):
    record_id = repository.save_analysis(
        kind="meeting", payload={"result": "ok"}, organization_id=org_id, project_name="Multilift"
    )

    record = repository.get_analysis(record_id, org_id)
    assert record is not None
    assert record.id == record_id
    assert record.payload == {"result": "ok"}


def test_get_analysis_returns_none_when_not_found(repository, org_id):
    assert repository.get_analysis(999, org_id) is None


def test_get_analysis_returns_none_for_a_record_from_another_organization(repository, org_id):
    other_org_id = repository.enterprise.create_organization("Outra Organização")
    record_id = repository.save_analysis(
        kind="meeting", payload={"result": "ok"}, organization_id=org_id, project_name="Multilift"
    )

    assert repository.get_analysis(record_id, other_org_id) is None


def test_list_analyses_never_returns_another_organizations_records(repository, org_id):
    other_org_id = repository.enterprise.create_organization("Outra Organização")
    repository.save_analysis(
        kind="meeting", payload={"result": "a"}, organization_id=org_id, project_name="Multilift"
    )
    repository.save_analysis(
        kind="meeting",
        payload={"result": "b"},
        organization_id=other_org_id,
        project_name="Multilift",
    )

    records = repository.list_analyses(organization_id=org_id)
    assert len(records) == 1
    assert records[0].payload == {"result": "a"}


def test_list_analyses_filters_by_kind(repository, org_id):
    repository.save_analysis(
        kind="meeting", payload={"result": "a"}, organization_id=org_id, project_name="Multilift"
    )
    repository.save_analysis(
        kind="risk", payload={"result": "b"}, organization_id=org_id, project_name="Multilift"
    )

    meeting_only = repository.list_analyses(organization_id=org_id, kind="meeting")
    assert [r.kind for r in meeting_only] == ["meeting"]


def test_list_analyses_filters_by_period(repository, org_id):
    repository.save_analysis(
        kind="meeting", payload={"result": "a"}, organization_id=org_id, project_name="Multilift"
    )

    now = datetime.now(timezone.utc)
    future_only = repository.list_analyses(
        organization_id=org_id, created_from=now + timedelta(days=1)
    )
    assert future_only == []

    past_to_now = repository.list_analyses(
        organization_id=org_id,
        created_from=now - timedelta(days=1),
        created_to=now + timedelta(days=1),
    )
    assert len(past_to_now) == 1


def test_list_analyses_combines_project_kind_and_period_filters(repository, org_id):
    repository.save_analysis(
        kind="meeting", payload={"result": "a"}, organization_id=org_id, project_name="Multilift"
    )
    repository.save_analysis(
        kind="risk", payload={"result": "b"}, organization_id=org_id, project_name="Multilift"
    )
    repository.save_analysis(
        kind="meeting", payload={"result": "c"}, organization_id=org_id, project_name="Medlog"
    )

    now = datetime.now(timezone.utc)
    records = repository.list_analyses(
        organization_id=org_id,
        project_name="Multilift",
        kind="meeting",
        created_from=now - timedelta(days=1),
        created_to=now + timedelta(days=1),
    )
    assert len(records) == 1
    assert records[0].payload == {"result": "a"}
