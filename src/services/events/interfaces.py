"""Event Model + Event Publisher contract (Wave 4, Enterprise Operations,
Epic W4-1 -- `docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md`
§1-2). Replaces `EventEmitter`/`NoOpEventEmitter` (Wave 1, D-049) --
migrated atomically in this same Epic, per the Founder's explicit
"no coexistence between the two abstractions" requirement (D-076).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class DomainEvent:
    """The platform's single event envelope. Every field is mandatory --
    this is the only official event contract, never one shape per
    producer."""

    event_id: str
    event_type: str
    correlation_id: str
    timestamp: datetime
    organization_id: int
    origin: str
    payload_version: int
    payload: dict


class EventPublisher(Protocol):
    def publish(
        self,
        event_type: str,
        payload: dict,
        organization_id: int,
        correlation_id: str,
        origin: str,
    ) -> DomainEvent: ...
