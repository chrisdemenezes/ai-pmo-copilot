import logging

logger = logging.getLogger(__name__)


class NoOpEventEmitter:
    """Logs and does nothing else -- the seam exists, the bus doesn't yet
    (Wave 1, Event Foundation; PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md §5).

    Promoting this to a real emitter later changes zero call sites: every
    mutating service method already calls `emit()` at the same position a
    real event-sourcing emit would occupy.
    """

    def emit(self, event_name: str, payload: dict, organization_id: int) -> None:
        logger.info("event emitted (no-op): %s org=%s", event_name, organization_id)
