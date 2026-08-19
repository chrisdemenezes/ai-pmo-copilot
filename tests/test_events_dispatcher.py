"""EventDispatcher (Wave 4, Enterprise Operations, Epic W4-1) -- in-process
pub/sub with the minimal Retry/Dead Letter behavior approved in D-076:
up to 3 attempts, synchronous and immediate, no backoff, no queue,
dead-letter recorded only after the 3rd failure, no automatic
reprocessing.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from src.database.models import DeadLetterEvent, EventRecord
from src.database.repository import AnalysisRepository
from src.services.events.dispatcher import MAX_ATTEMPTS, EventDispatcher
from src.services.events.interfaces import DomainEvent
from tests.db import temp_database_url


@pytest.fixture()
def repository():
    with temp_database_url("events_dispatcher") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def dispatcher(repository):
    return EventDispatcher(repository.SessionLocal)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


def _event(repository, org_id: int, event_type: str = "document.indexed") -> DomainEvent:
    """Builds a DomainEvent AND persists its envelope to `events` first --
    dead_letter_events.event_id has a real FK to events.event_id (per the
    Technical Design), which InProcessEventPublisher always satisfies in
    production (it persists before dispatching); this test helper mirrors
    that same invariant instead of exercising the dispatcher against a
    dangling event_id."""
    event = DomainEvent(
        event_id="event-1",
        event_type=event_type,
        correlation_id="corr-1",
        timestamp=datetime.now(timezone.utc),
        organization_id=org_id,
        origin="test",
        payload_version=1,
        payload={},
    )
    with repository.SessionLocal() as session:
        session.add(
            EventRecord(
                event_id=event.event_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                timestamp=event.timestamp,
                organization_id=event.organization_id,
                origin=event.origin,
                payload_version=event.payload_version,
                payload=event.payload,
            )
        )
        session.commit()
    return event


def test_dispatch_with_no_registered_handler_is_a_no_op(dispatcher, repository, org_id):
    dispatcher.dispatch(_event(repository, org_id))  # must not raise


def test_dispatch_calls_the_registered_handler_exactly_once_on_success(dispatcher, repository, org_id):
    calls = []
    dispatcher.register("document.indexed", lambda event: calls.append(event))

    dispatcher.dispatch(_event(repository, org_id))

    assert len(calls) == 1


def test_handler_failing_fewer_than_max_attempts_eventually_succeeds_without_dead_letter(
    dispatcher, repository, org_id
):
    attempts = {"count": 0}

    def flaky_handler(event):
        attempts["count"] += 1
        if attempts["count"] < MAX_ATTEMPTS:
            raise RuntimeError("transient failure")

    dispatcher.register("document.indexed", flaky_handler)

    dispatcher.dispatch(_event(repository, org_id))

    assert attempts["count"] == MAX_ATTEMPTS
    with repository.SessionLocal() as session:
        assert session.execute(select(DeadLetterEvent)).scalars().all() == []


def test_handler_failing_every_attempt_is_recorded_to_dead_letter_after_the_third_failure(
    dispatcher, repository, org_id
):
    attempts = {"count": 0}

    def always_failing_handler(event):
        attempts["count"] += 1
        raise RuntimeError(f"failure #{attempts['count']}")

    dispatcher.register("document.indexed", always_failing_handler)

    dispatcher.dispatch(_event(repository, org_id, "document.indexed"))

    assert attempts["count"] == MAX_ATTEMPTS
    with repository.SessionLocal() as session:
        dead_letters = session.execute(select(DeadLetterEvent)).scalars().all()

    assert len(dead_letters) == 1
    assert dead_letters[0].event_id == "event-1"
    assert dead_letters[0].organization_id == org_id
    assert dead_letters[0].correlation_id == "corr-1"
    assert dead_letters[0].attempts == MAX_ATTEMPTS
    assert "failure #3" in dead_letters[0].last_error


def test_a_failing_handler_never_raises_back_to_the_caller(dispatcher, repository, org_id):
    def always_failing_handler(event):
        raise RuntimeError("boom")

    dispatcher.register("document.indexed", always_failing_handler)

    dispatcher.dispatch(_event(repository, org_id))  # must not raise -- dispatch failures never propagate
