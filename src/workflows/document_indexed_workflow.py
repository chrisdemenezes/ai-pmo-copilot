"""The single minimal example workflow authorized for Epic W4-4
(Founder Decision — Epic W4-4 Scope Approval): `document.indexed` ->
`WorkflowRuntime` -> Execution Tracking. One step, no business logic, no
metric -- its only purpose is to prove the publish -> dispatch -> execute
-> track chain end to end (the Founder's own Success Metric, D-073/D-076).
"""
from src.services.events.dispatcher import EventDispatcher
from src.services.events.interfaces import DomainEvent
from src.workflows.runtime import WorkflowContext, WorkflowRuntime

WORKFLOW_NAME = "document_indexed_example"


def _record_execution_step(context: WorkflowContext) -> WorkflowContext:
    """No-op -- `WorkflowRuntime.run()` already records the execution
    (§12.4); this step exists only to prove a real step is executed."""
    return context


def register(dispatcher: EventDispatcher, runtime: WorkflowRuntime) -> None:
    def _handle(event: DomainEvent) -> None:
        runtime.run(WORKFLOW_NAME, [_record_execution_step], event)

    dispatcher.register("document.indexed", _handle)
