"""`WorkflowRuntime` -- minimal step executor (Wave 4, Enterprise
Operations, Epic W4-4 --
`docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md` §12).
Registered as an ordinary handler on `EventDispatcher` (Epic W4-1) --
from the Dispatcher's point of view, indistinguishable from any other
handler. `WorkflowRuntime` is the sole owner of the `running`/
`completed`/`failed` lifecycle recorded in `workflow_executions`
(`execution_tracking.py`) -- `EventDispatcher` never reads or writes it
(Founder's explicit separation principle, "Founder Decision — Epic W4-4
Technical Design Approval").

Never substitutes `AdvisorFramework.run()` -- a workflow step is a pure
function, never business logic, never Advisor intelligence.
"""
from dataclasses import dataclass
from typing import Protocol

from src.services.events.interfaces import DomainEvent
from src.workflows.execution_tracking import ExecutionTracker


@dataclass(frozen=True)
class WorkflowContext:
    correlation_id: str
    organization_id: int
    payload: dict


class WorkflowStep(Protocol):
    def __call__(self, context: WorkflowContext) -> WorkflowContext: ...


class WorkflowRuntime:
    def __init__(self, execution_tracker: ExecutionTracker):
        self._execution_tracker = execution_tracker

    def run(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        triggering_event: DomainEvent,
    ) -> WorkflowContext:
        """`WorkflowContext` is built here, exclusively from
        `triggering_event` -- there is no other constructor call site,
        making `correlation_id` inheritance structural rather than a
        convention a future caller could bypass. On step failure: records
        `status="failed"` with a sanitized error message, then re-raises
        the original exception unchanged -- `EventDispatcher`'s own
        retry/dead-letter policy (unmodified since Epic W4-1) reacts to
        it exactly as it would to any other handler failure."""
        context = WorkflowContext(
            correlation_id=triggering_event.correlation_id,
            organization_id=triggering_event.organization_id,
            payload=triggering_event.payload,
        )
        self._execution_tracker.start(
            event_id=triggering_event.event_id,
            workflow_name=workflow_name,
            organization_id=triggering_event.organization_id,
            correlation_id=triggering_event.correlation_id,
        )
        try:
            for step in steps:
                context = step(context)
        except Exception as exc:
            self._execution_tracker.fail(triggering_event.event_id, workflow_name, exc)
            raise
        self._execution_tracker.complete(triggering_event.event_id, workflow_name)
        return context
