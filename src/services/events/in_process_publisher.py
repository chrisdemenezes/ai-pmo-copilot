"""`InProcessEventPublisher` -- the sole `EventPublisher` implementation
in the STRATECH (Wave 4, Enterprise Operations, Epic W4-1). Replaces
`NoOpEventEmitter` (Wave 1, D-049), migrated atomically in this same
Epic -- no period where both abstractions coexist (Founder, D-076).

Persists the full envelope to `events` (Event Audit) before dispatching,
so the envelope is durable even if no handler is registered yet.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from src.database.models import EventRecord
from src.services.events.dispatcher import EventDispatcher
from src.services.events.interfaces import DomainEvent

logger = logging.getLogger(__name__)

PAYLOAD_VERSION = 1


class InProcessEventPublisher:
    def __init__(self, session_factory: sessionmaker, dispatcher: EventDispatcher):
        self._session_factory = session_factory
        self._dispatcher = dispatcher

    def publish(
        self,
        event_type: str,
        payload: dict,
        organization_id: int,
        correlation_id: str,
        origin: str,
    ) -> DomainEvent:
        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
            organization_id=organization_id,
            origin=origin,
            payload_version=PAYLOAD_VERSION,
            payload=payload,
        )
        self._persist(event)
        logger.info(
            "event published: event_id=%s event_type=%s correlation_id=%s org=%s",
            event.event_id,
            event.event_type,
            event.correlation_id,
            event.organization_id,
        )
        self._dispatcher.dispatch(event)
        return event

    def _persist(self, event: DomainEvent) -> None:
        with self._session_factory() as session:
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
