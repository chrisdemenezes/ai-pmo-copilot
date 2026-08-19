"""InProcessEventPublisher (Wave 4, Enterprise Operations, Epic W4-1) --
the sole EventPublisher implementation. Confirms the Event Envelope is
persisted (Event Audit, traceability) and that publish() returns the
full DomainEvent, per the Founder's evidence requirements (D-076).
"""
import uuid

import pytest
from sqlalchemy import select

from src.database.models import EventRecord
from src.database.repository import AnalysisRepository
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from tests.db import temp_database_url


@pytest.fixture()
def repository():
    with temp_database_url("events_publisher") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def publisher(repository):
    return InProcessEventPublisher(repository.SessionLocal, EventDispatcher(repository.SessionLocal))


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


def test_publish_returns_a_fully_populated_envelope(publisher, org_id):
    event = publisher.publish(
        "portfolio.created",
        {"portfolio_id": 1},
        org_id,
        correlation_id="corr-1",
        origin="domain_service",
    )

    assert event.event_type == "portfolio.created"
    assert event.correlation_id == "corr-1"
    assert event.organization_id == org_id
    assert event.origin == "domain_service"
    assert event.payload_version == 1
    assert event.payload == {"portfolio_id": 1}
    uuid.UUID(event.event_id)  # a real UUID, not a placeholder
    assert event.timestamp is not None


def test_publish_persists_the_envelope_for_traceability(publisher, repository, org_id):
    event = publisher.publish(
        "portfolio.created",
        {"portfolio_id": 1},
        org_id,
        correlation_id="corr-2",
        origin="domain_service",
    )

    with repository.SessionLocal() as session:
        record = session.execute(
            select(EventRecord).where(EventRecord.event_id == event.event_id)
        ).scalar_one()

    assert record.event_type == "portfolio.created"
    assert record.correlation_id == "corr-2"
    assert record.organization_id == org_id
    assert record.origin == "domain_service"
    assert record.payload_version == 1
    assert record.payload == {"portfolio_id": 1}


def test_publish_with_zero_registered_handlers_succeeds_trivially(publisher, org_id):
    """No Workflow Runtime exists yet (Epic W4-4) -- dispatching to zero
    handlers must never fail or block the publisher's caller."""
    event = publisher.publish(
        "document.indexed", {}, org_id, correlation_id="corr-3", origin="knowledge_repository"
    )

    assert event.event_type == "document.indexed"
