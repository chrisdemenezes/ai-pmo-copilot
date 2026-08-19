"""Event Dispatcher (Wave 4, Enterprise Operations, Epic W4-1 --
`docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md`
§5.1/§4). In-process pub/sub only -- a fixed dispatch table keyed by
`event_type`, never a dynamic/generic registry, never a broker or queue.

No handler is registered by any production code in this Epic (the
Workflow Runtime that would register one belongs to Epic W4-4, which
does not exist yet) -- dispatch to zero handlers trivially succeeds.
The retry/dead-letter mechanism exists and is exercised by
`tests/test_events_dispatcher.py`, proving the seam works before any
real consumer registers a handler -- same "seam now, mechanism later"
discipline as `NoOpEventEmitter`/`NoOpNotificationProvider`.
"""
import logging
from collections import defaultdict
from collections.abc import Callable

from sqlalchemy.orm import sessionmaker

from src.database.models import DeadLetterEvent
from src.services.events.interfaces import DomainEvent

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


class EventDispatcher:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory
        self._handlers: dict[str, list[Callable[[DomainEvent], None]]] = defaultdict(list)

    def register(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        self._handlers[event_type].append(handler)

    def dispatch(self, event: DomainEvent) -> None:
        """Calls every handler registered for `event.event_type`. A
        failing handler is retried up to MAX_ATTEMPTS times, synchronously
        and immediately (no backoff, no queue) -- on exhaustion, the
        failure is recorded to `dead_letter_events` and dispatch continues
        to the next handler. A dispatch failure never propagates to the
        caller (the publisher/producer's own write already succeeded)."""
        for handler in self._handlers[event.event_type]:
            self._dispatch_to_handler(event, handler)

    def _dispatch_to_handler(self, event: DomainEvent, handler: Callable[[DomainEvent], None]) -> None:
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                handler(event)
                return
            except Exception as exc:  # noqa: BLE001 -- any handler failure is retried identically
                last_error = exc
                logger.warning(
                    "event dispatch attempt %s/%s failed event_id=%s event_type=%s: %s",
                    attempt,
                    MAX_ATTEMPTS,
                    event.event_id,
                    event.event_type,
                    exc,
                )
        self._record_dead_letter(event, MAX_ATTEMPTS, last_error)

    def _record_dead_letter(self, event: DomainEvent, attempts: int, error: Exception | None) -> None:
        with self._session_factory() as session:
            session.add(
                DeadLetterEvent(
                    event_id=event.event_id,
                    organization_id=event.organization_id,
                    correlation_id=event.correlation_id,
                    attempts=attempts,
                    last_error=str(error)[:2000],
                )
            )
            session.commit()
