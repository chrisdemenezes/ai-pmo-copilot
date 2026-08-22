"""TD-016 (V1 Post-Completion Technical Closure): automated performance
snapshot capture. Two independent paths, tested at the layer each one
actually operates:

- Event-driven (`performance_snapshot_automation.register`) -- exercised
  directly against `EventDispatcher`/`InProcessEventPublisher`, same
  convention `test_document_indexed_workflow.py` already established.
- Read-triggered checkpoint (`_auto_capture_snapshot` inside
  `list_projects_delivery`/`get_project_delivery`) -- exercised through
  the real API, same convention `test_project_delivery_api.py` already
  established.
"""
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api import authorization as authorization_module
from src.api.routes import project_delivery as project_delivery_routes
from src.database.models import DeadLetterEvent
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.domain_service import DomainService
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.executive_analytics.performance_service import (
    ProjectPerformanceService,
)
from src.workflows import performance_snapshot_automation
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"
TODAY = datetime.now(tz=timezone.utc).date()


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


def _make_program(repo, org_id: int) -> int:
    portfolio_id = repo.domain.create_portfolio(org_id, "Portfólio A", "PF-A")
    return repo.domain.create_program(portfolio_id, "Programa A", "PG-A")


# -- Event-driven path: direct dispatcher/publisher wiring -------------------


@pytest.fixture()
def repository():
    with temp_database_url("performance_snapshot_automation") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


@pytest.fixture()
def actor_id(repository, org_id):
    return repository.enterprise.create_user(org_id, "actor@example.com", "Actor")


@pytest.fixture()
def wired_performance_service(repository):
    """Same composition `build_event_publisher()` performs in production --
    a dispatcher with the TD-016 handler registered, wrapped by a real
    publisher, used to build the ProjectPerformanceService under test."""
    dispatcher = EventDispatcher(repository.SessionLocal)
    publisher = InProcessEventPublisher(repository.SessionLocal, dispatcher)
    performance_snapshot_automation.register(dispatcher, repository, publisher)
    return ProjectPerformanceService(repository=repository, publisher=publisher)


@pytest.fixture()
def project(repository, org_id, actor_id):
    domain_service = DomainService(
        repository, InProcessEventPublisher(repository.SessionLocal, EventDispatcher(repository.SessionLocal))
    )
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


@pytest.fixture()
def bare_project(repository, org_id, actor_id):
    """No actual_cost/progress_percentage -- nothing real to capture yet."""
    domain_service = DomainService(
        repository, InProcessEventPublisher(repository.SessionLocal, EventDispatcher(repository.SessionLocal))
    )
    portfolio = domain_service.create_portfolio(
        org_id, "Portfolio B", "PF-B", actor_id, correlation_id=CORRELATION_ID
    )
    program = domain_service.create_program(
        org_id, portfolio.id, "Program B", "PG-B", actor_id, correlation_id=CORRELATION_ID
    )
    return domain_service.create_project(
        org_id, program.id, "Project B", actor_id, correlation_id=CORRELATION_ID
    )


class TestEventDrivenCapture:
    def test_creating_a_baseline_automatically_captures_a_snapshot(
        self, wired_performance_service, repository, org_id, actor_id, project
    ):
        wired_performance_service.create_baseline(
            org_id,
            project.id,
            actor_id,
            CORRELATION_ID,
            Decimal("100000.00"),
            [(date(2026, 1, 1), Decimal(0))],
        )

        snapshots = repository.performance.list_snapshots(project.id, org_id)

        assert len(snapshots) == 1
        assert snapshots[0].snapshot_date == TODAY
        assert snapshots[0].actual_cost == Decimal("20000.00")
        assert snapshots[0].progress_percentage == 20

    def test_missing_actual_cost_or_progress_is_a_silent_noop_not_a_failure(
        self, wired_performance_service, repository, org_id, actor_id, bare_project
    ):
        # Must not raise -- publish() never propagates a handler failure,
        # but a *silent no-op* additionally means: no dead letter recorded
        # either, since this isn't a real failure.
        wired_performance_service.create_baseline(
            org_id,
            bare_project.id,
            actor_id,
            CORRELATION_ID,
            Decimal("100000.00"),
            [(date(2026, 1, 1), Decimal(0))],
        )

        assert repository.performance.list_snapshots(bare_project.id, org_id) == []
        with repository.SessionLocal() as session:
            dead_letters = session.execute(select(DeadLetterEvent)).scalars().all()
        assert dead_letters == []

    def test_rebaseline_triggers_a_second_capture_attempt_idempotently(
        self, wired_performance_service, repository, org_id, actor_id, project
    ):
        wired_performance_service.create_baseline(
            org_id, project.id, actor_id, CORRELATION_ID, Decimal("100000.00"), [(date(2026, 1, 1), Decimal(0))]
        )
        wired_performance_service.create_baseline(
            org_id, project.id, actor_id, CORRELATION_ID, Decimal("120000.00"), [(date(2026, 1, 1), Decimal(0))]
        )

        # Same day both times -- idempotent, still exactly one snapshot row.
        snapshots = repository.performance.list_snapshots(project.id, org_id)
        assert len(snapshots) == 1

        # Baseline history itself is never rewritten: 2 distinct versions exist.
        with repository.SessionLocal() as session:
            from src.database.models import ProjectPerformanceBaseline

            versions = sorted(
                {
                    row.baseline_version
                    for row in session.execute(
                        select(ProjectPerformanceBaseline).where(
                            ProjectPerformanceBaseline.project_id == project.id
                        )
                    ).scalars()
                }
            )
        assert versions == [1, 2]

    def test_capture_is_scoped_to_the_correct_tenant(
        self, wired_performance_service, repository, org_id, actor_id, project
    ):
        other_org = repository.enterprise.create_organization("Org B")

        wired_performance_service.create_baseline(
            org_id, project.id, actor_id, CORRELATION_ID, Decimal("100000.00"), [(date(2026, 1, 1), Decimal(0))]
        )

        assert repository.performance.list_snapshots(project.id, other_org) == []
        assert len(repository.performance.list_snapshots(project.id, org_id)) == 1

    def test_manual_capture_endpoint_path_is_unaffected_by_automation(
        self, wired_performance_service, repository, org_id, actor_id, project
    ):
        """The manual/on-demand path (ProjectPerformanceService.capture_snapshot
        called directly, Section 16) still works exactly as before -- and
        composes correctly with the automated path (still just one row)."""
        wired_performance_service.capture_snapshot(org_id, project.id, actor_id, CORRELATION_ID)
        wired_performance_service.create_baseline(
            org_id, project.id, actor_id, CORRELATION_ID, Decimal("100000.00"), [(date(2026, 1, 1), Decimal(0))]
        )

        assert len(repository.performance.list_snapshots(project.id, org_id)) == 1


# -- Read-triggered checkpoint: through the real API -------------------------


@pytest.fixture()
def api_client():
    with temp_database_url("performance_snapshot_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

        repo = AnalysisRepository(database_url=database_url)
        dispatcher = EventDispatcher(repo.SessionLocal)
        publisher = InProcessEventPublisher(repo.SessionLocal, dispatcher)
        performance_snapshot_automation.register(dispatcher, repo, publisher)
        performance_service = ProjectPerformanceService(repository=repo, publisher=publisher)
        domain_service = DomainService(repo, publisher)

        app.dependency_overrides[project_delivery_routes.build_domain_service] = (
            lambda: domain_service
        )
        app.dependency_overrides[project_delivery_routes.build_performance_service] = (
            lambda: performance_service
        )
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo
        app.dependency_overrides.clear()


class TestReadTriggeredCheckpoint:
    def test_getting_a_single_project_automatically_captures_a_snapshot(self, api_client):
        test_client, repo = api_client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        program_id = _make_program(repo, org_id)
        project_id = repo.domain.create_project_with_domain(
            org_id,
            program_id,
            "Project A",
            actual_cost=Decimal("5000.00"),
            progress_percentage=10,
        )

        response = test_client.get(
            f"/api/projects-delivery/{project_id}", headers=_headers(org_id, admin_id)
        )

        assert response.status_code == 200
        snapshots = repo.performance.list_snapshots(project_id, org_id)
        assert len(snapshots) == 1
        assert snapshots[0].actual_cost == Decimal("5000.00")

    def test_listing_projects_automatically_captures_a_snapshot_for_each(self, api_client):
        test_client, repo = api_client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        program_id = _make_program(repo, org_id)
        project_id = repo.domain.create_project_with_domain(
            org_id,
            program_id,
            "Project A",
            actual_cost=Decimal("5000.00"),
            progress_percentage=10,
        )

        response = test_client.get("/api/projects-delivery", headers=_headers(org_id, admin_id))

        assert response.status_code == 200
        assert len(repo.performance.list_snapshots(project_id, org_id)) == 1

    def test_reading_twice_the_same_day_never_duplicates_the_snapshot(self, api_client):
        test_client, repo = api_client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        program_id = _make_program(repo, org_id)
        project_id = repo.domain.create_project_with_domain(
            org_id,
            program_id,
            "Project A",
            actual_cost=Decimal("5000.00"),
            progress_percentage=10,
        )

        test_client.get(f"/api/projects-delivery/{project_id}", headers=_headers(org_id, admin_id))
        test_client.get(f"/api/projects-delivery/{project_id}", headers=_headers(org_id, admin_id))

        assert len(repo.performance.list_snapshots(project_id, org_id)) == 1

    def test_reading_a_project_with_no_financial_data_never_fails_and_captures_nothing(
        self, api_client
    ):
        test_client, repo = api_client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        program_id = _make_program(repo, org_id)
        project_id = repo.domain.create_project_with_domain(org_id, program_id, "Project A")

        response = test_client.get(
            f"/api/projects-delivery/{project_id}", headers=_headers(org_id, admin_id)
        )

        assert response.status_code == 200
        assert repo.performance.list_snapshots(project_id, org_id) == []

    def test_manual_snapshot_endpoint_still_works_unchanged(self, api_client):
        test_client, repo = api_client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        program_id = _make_program(repo, org_id)
        project_id = repo.domain.create_project_with_domain(
            org_id,
            program_id,
            "Project A",
            actual_cost=Decimal("5000.00"),
            progress_percentage=10,
        )

        response = test_client.post(
            f"/api/projects-delivery/{project_id}/performance-snapshots",
            headers=_headers(org_id, admin_id),
        )

        assert response.status_code == 201
        assert response.json()["actual_cost"] == 5000.00

    def test_all_four_wave_8_endpoints_remain_reachable(self, api_client):
        test_client, repo = api_client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        program_id = _make_program(repo, org_id)
        project_id = repo.domain.create_project_with_domain(
            org_id,
            program_id,
            "Project A",
            actual_cost=Decimal("5000.00"),
            progress_percentage=10,
        )
        headers = _headers(org_id, admin_id)

        baseline_response = test_client.post(
            f"/api/projects-delivery/{project_id}/performance-baselines",
            headers=headers,
            json={"bac_reference": "100000.00", "points": [{"period_date": "2026-01-01", "planned_progress_percentage": "0"}]},
        )
        snapshot_response = test_client.post(
            f"/api/projects-delivery/{project_id}/performance-snapshots", headers=headers
        )
        summary_response = test_client.get(
            f"/api/projects-delivery/{project_id}/performance-summary", headers=headers
        )
        history_response = test_client.get(
            f"/api/projects-delivery/{project_id}/performance-history", headers=headers
        )

        assert baseline_response.status_code == 201
        assert snapshot_response.status_code == 201
        assert summary_response.status_code == 200
        assert history_response.status_code == 200
