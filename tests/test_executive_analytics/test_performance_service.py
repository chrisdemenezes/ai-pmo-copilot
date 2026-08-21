"""ProjectPerformanceService (Wave 8, Founder Decision "EVM Temporal
Baseline") -- baseline authoring, snapshot capture, and EVM summary
computation against a real project, using the same
`RecordingEventPublisher`/`temp_database_url` convention already
established by `test_domain_service.py`.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.database.repository import AnalysisRepository
from src.services.domain_service import DomainService
from src.services.events.interfaces import DomainEvent
from src.services.executive_analytics.performance_service import (
    ProjectPerformanceService,
)
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


class RecordingEventPublisher:
    def __init__(self):
        self.events: list[tuple[str, dict, int]] = []

    def publish(self, event_type, payload, organization_id, correlation_id, origin) -> DomainEvent:
        self.events.append((event_type, payload, organization_id))
        return DomainEvent(
            event_id="fake-event-id",
            event_type=event_type,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
            organization_id=organization_id,
            origin=origin,
            payload_version=1,
            payload=payload,
        )


@pytest.fixture()
def repository():
    with temp_database_url("performance_service") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def publisher():
    return RecordingEventPublisher()


@pytest.fixture()
def domain_service(repository, publisher):
    return DomainService(repository=repository, publisher=publisher)


@pytest.fixture()
def performance_service(repository, publisher):
    return ProjectPerformanceService(repository=repository, publisher=publisher)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


@pytest.fixture()
def actor_id(repository, org_id):
    return repository.enterprise.create_user(org_id, "actor@example.com", "Actor")


@pytest.fixture()
def project(domain_service, org_id, actor_id):
    portfolio = domain_service.create_portfolio(
        org_id, "Portfolio A", "PF-A", actor_id, correlation_id=CORRELATION_ID
    )
    program = domain_service.create_program(
        org_id, portfolio.id, "Program A", "PG-A", actor_id, correlation_id=CORRELATION_ID
    )
    return domain_service.create_project(
        org_id,
        program.id,
        "Project A",
        actor_id,
        correlation_id=CORRELATION_ID,
        approved_budget=Decimal("100000.00"),
        actual_cost=Decimal("20000.00"),
        progress_percentage=20,
    )


class TestCreateBaseline:
    def test_returns_none_for_a_project_outside_the_caller_organization(
        self, performance_service, repository, actor_id
    ):
        other_org = repository.enterprise.create_organization("Org B")

        result = performance_service.create_baseline(
            other_org, 999999, actor_id, CORRELATION_ID, Decimal("100000.00"), []
        )

        assert result is None

    def test_first_baseline_is_version_1_and_rebaseline_increments(
        self, performance_service, org_id, actor_id, project
    ):
        points = [(date(2026, 1, 1), Decimal(0)), (date(2026, 2, 1), Decimal(25))]

        first = performance_service.create_baseline(
            org_id, project.id, actor_id, CORRELATION_ID, Decimal("100000.00"), points
        )
        second = performance_service.create_baseline(
            org_id, project.id, actor_id, CORRELATION_ID, Decimal("100000.00"), points
        )

        assert first == 1
        assert second == 2

    def test_publishes_baseline_created_event(
        self, performance_service, publisher, org_id, actor_id, project
    ):
        # `project` fixture itself publishes portfolio/program/project
        # events (same pattern as test_domain_service.py) -- clear those
        # before asserting only on this call's own event.
        publisher.events.clear()
        performance_service.create_baseline(
            org_id,
            project.id,
            actor_id,
            CORRELATION_ID,
            Decimal("100000.00"),
            [(date(2026, 1, 1), Decimal(0))],
        )

        assert publisher.events == [
            (
                "project_performance_baseline.created",
                {"project_id": project.id, "baseline_version": 1},
                org_id,
            )
        ]


class TestCaptureSnapshot:
    def test_returns_none_for_a_project_outside_the_caller_organization(
        self, performance_service, repository, actor_id
    ):
        other_org = repository.enterprise.create_organization("Org B")

        result = performance_service.capture_snapshot(
            other_org, 999999, actor_id, CORRELATION_ID
        )

        assert result is None

    def test_copies_actual_cost_and_progress_percentage_from_the_project(
        self, performance_service, org_id, actor_id, project
    ):
        snapshot = performance_service.capture_snapshot(org_id, project.id, actor_id, CORRELATION_ID)

        assert snapshot.actual_cost == Decimal("20000.00")
        assert snapshot.progress_percentage == 20

    def test_second_capture_same_day_returns_the_same_row_never_overwrites(
        self, performance_service, org_id, actor_id, project
    ):
        first = performance_service.capture_snapshot(org_id, project.id, actor_id, CORRELATION_ID)
        second = performance_service.capture_snapshot(org_id, project.id, actor_id, CORRELATION_ID)

        assert first.id == second.id

    def test_raises_value_error_when_project_has_no_actual_cost_recorded(
        self, performance_service, domain_service, org_id, actor_id
    ):
        portfolio = domain_service.create_portfolio(
            org_id, "Portfolio B", "PF-B", actor_id, correlation_id=CORRELATION_ID
        )
        program = domain_service.create_program(
            org_id, portfolio.id, "Program B", "PG-B", actor_id, correlation_id=CORRELATION_ID
        )
        bare_project = domain_service.create_project(
            org_id, program.id, "Project B", actor_id, correlation_id=CORRELATION_ID
        )

        with pytest.raises(ValueError, match="actual_cost_missing"):
            performance_service.capture_snapshot(org_id, bare_project.id, actor_id, CORRELATION_ID)


class TestGetEvmSummary:
    def test_returns_none_for_a_project_outside_the_caller_organization(
        self, performance_service, repository, actor_id
    ):
        other_org = repository.enterprise.create_organization("Org B")

        result = performance_service.get_evm_summary(999999, other_org, date(2026, 2, 1))

        assert result is None

    def test_project_with_no_baseline_and_no_snapshot_is_all_na(
        self, performance_service, org_id, project
    ):
        summary = performance_service.get_evm_summary(project.id, org_id, date(2026, 2, 1))

        assert summary.bac.value is None
        assert summary.pv.value is None
        assert summary.ac.value is None

    def test_full_data_available_computes_real_evm_metrics(
        self, performance_service, org_id, actor_id, project
    ):
        performance_service.create_baseline(
            org_id,
            project.id,
            actor_id,
            CORRELATION_ID,
            Decimal("100000.00"),
            [(date(2026, 1, 1), Decimal(0)), (date(2026, 2, 1), Decimal(25))],
        )
        performance_service.capture_snapshot(
            org_id, project.id, actor_id, CORRELATION_ID, snapshot_date=date(2026, 2, 1)
        )

        summary = performance_service.get_evm_summary(project.id, org_id, date(2026, 2, 1))

        assert summary.bac.value == Decimal("100000.00")
        assert summary.pv.value == Decimal("25000.00")
        assert summary.ev.value == Decimal("20000.00")
        assert summary.ac.value == Decimal("20000.00")


class TestGetPerformanceHistory:
    def test_returns_none_for_a_project_outside_the_caller_organization(
        self, performance_service, repository, actor_id
    ):
        other_org = repository.enterprise.create_organization("Org B")

        result = performance_service.get_performance_history(999999, other_org)

        assert result is None

    def test_empty_when_no_snapshot_has_ever_been_captured(
        self, performance_service, org_id, project
    ):
        history = performance_service.get_performance_history(project.id, org_id)

        assert history == []

    def test_one_point_per_captured_snapshot(
        self, performance_service, org_id, actor_id, project
    ):
        performance_service.create_baseline(
            org_id,
            project.id,
            actor_id,
            CORRELATION_ID,
            Decimal("100000.00"),
            [(date(2026, 1, 1), Decimal(0)), (date(2026, 2, 1), Decimal(25))],
        )
        performance_service.capture_snapshot(
            org_id, project.id, actor_id, CORRELATION_ID, snapshot_date=date(2026, 2, 1)
        )

        history = performance_service.get_performance_history(project.id, org_id)

        assert len(history) == 1
        assert history[0].as_of == date(2026, 2, 1)
        assert history[0].ac.value == Decimal("20000.00")
