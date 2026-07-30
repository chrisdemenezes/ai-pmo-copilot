"""DomainService's event publication (Wave 1, Event Foundation, D-048;
promoted to EventPublisher in Wave 4, Enterprise Operations, Epic W4-1,
D-076). Uses a fake EventPublisher test double, same convention
`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §5.12 prescribes and
`test_identity_auth_service.py` already established for other Protocol
dependencies (fake instead of hitting a real bus/DB in unit scope).
"""
from datetime import datetime, timezone

import pytest

from src.database.repository import AnalysisRepository
from src.services.domain_service import DomainService
from src.services.events.interfaces import DomainEvent
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


class RecordingEventPublisher:
    def __init__(self):
        self.events: list[tuple[str, dict, int]] = []

    def publish(
        self,
        event_type: str,
        payload: dict,
        organization_id: int,
        correlation_id: str,
        origin: str,
    ) -> DomainEvent:
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
    with temp_database_url("domain_service_events") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def publisher():
    return RecordingEventPublisher()


@pytest.fixture()
def service(repository, publisher):
    return DomainService(repository=repository, publisher=publisher)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


@pytest.fixture()
def actor_id(repository, org_id):
    return repository.enterprise.create_user(org_id, "actor@example.com", "Actor")


def test_create_portfolio_publishes_portfolio_created_after_the_write_succeeds(
    service, publisher, org_id, actor_id
):
    portfolio = service.create_portfolio(
        org_id, "Portfólio A", "PF-A", actor_id, correlation_id=CORRELATION_ID
    )

    assert publisher.events == [
        ("portfolio.created", {"portfolio_id": portfolio.id}, org_id),
    ]


def test_create_program_publishes_created_and_linked_to_portfolio(
    service, publisher, org_id, actor_id
):
    portfolio = service.create_portfolio(
        org_id, "Portfólio A", "PF-A", actor_id, correlation_id=CORRELATION_ID
    )
    publisher.events.clear()

    program = service.create_program(
        org_id, portfolio.id, "Programa A", "PG-A", actor_id, correlation_id=CORRELATION_ID
    )

    payload = {"program_id": program.id, "portfolio_id": portfolio.id}
    assert publisher.events == [
        ("program.created", payload, org_id),
        ("program.linked_to_portfolio", payload, org_id),
    ]


def test_create_project_publishes_created_and_linked_to_program(
    service, publisher, org_id, actor_id
):
    portfolio = service.create_portfolio(
        org_id, "Portfólio A", "PF-A", actor_id, correlation_id=CORRELATION_ID
    )
    program = service.create_program(
        org_id, portfolio.id, "Programa A", "PG-A", actor_id, correlation_id=CORRELATION_ID
    )
    publisher.events.clear()

    project = service.create_project(
        org_id, program.id, "Projeto A", actor_id, correlation_id=CORRELATION_ID
    )

    payload = {"project_id": project.id, "program_id": program.id}
    assert publisher.events == [
        ("project_delivery.created", payload, org_id),
        ("project_delivery.linked_to_program", payload, org_id),
    ]


def test_create_program_never_publishes_when_the_portfolio_does_not_resolve(
    service, publisher, org_id, actor_id
):
    result = service.create_program(
        org_id, 999, "Programa A", "PG-A", actor_id, correlation_id=CORRELATION_ID
    )

    assert result is None
    assert publisher.events == []


def test_create_project_never_publishes_when_the_program_does_not_resolve(
    service, publisher, org_id, actor_id
):
    result = service.create_project(
        org_id, 999, "Projeto A", actor_id, correlation_id=CORRELATION_ID
    )

    assert result is None
    assert publisher.events == []


def test_create_portfolio_propagates_the_given_correlation_id_into_the_published_event(
    repository, org_id, actor_id
):
    """Confirms DomainService never mints its own correlation_id -- it
    only ever forwards whatever the caller (the API route) already
    resolved (D-076, Condição 2)."""

    class CapturingEventPublisher:
        def __init__(self):
            self.last_correlation_id = None

        def publish(self, event_type, payload, organization_id, correlation_id, origin):
            self.last_correlation_id = correlation_id
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

    publisher = CapturingEventPublisher()
    service = DomainService(repository=repository, publisher=publisher)

    service.create_portfolio(org_id, "Portfólio A", "PF-A", actor_id, correlation_id="req-abc-123")

    assert publisher.last_correlation_id == "req-abc-123"
