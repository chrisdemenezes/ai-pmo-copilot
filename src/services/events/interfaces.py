from typing import Protocol


class EventEmitter(Protocol):
    def emit(self, event_name: str, payload: dict, organization_id: int) -> None: ...
