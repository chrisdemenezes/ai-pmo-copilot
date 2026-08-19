"""Shared FastAPI DI factories used by more than one route module.

Extracted from `intelligence.py` (Security Hardening Gate, C-1): once
`intelligence.py` itself needed `require_permission` (defined in
`src.api.authorization`, which in turn depended on `build_repository`
living in `intelligence.py`), leaving it there would have created a
circular import. Moved here instead of duplicated -- no new registry,
same single `AnalysisRepository` instance shared by every route module
via `@lru_cache`.
"""
from functools import lru_cache

from src.database.repository import AnalysisRepository
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.events.interfaces import EventPublisher
from src.services.notifications.interfaces import NotificationProvider
from src.services.notifications.noop_provider import NoOpNotificationProvider
from src.workflows import document_indexed_workflow
from src.workflows.execution_tracking import ExecutionTracker
from src.workflows.runtime import WorkflowRuntime


@lru_cache
def build_repository() -> AnalysisRepository:
    return AnalysisRepository()


@lru_cache
def build_event_publisher() -> EventPublisher:
    # Wave 4, Enterprise Operations, Epic W4-1 (D-076): the platform's sole
    # event publishing infrastructure -- replaces EventEmitter/
    # NoOpEventEmitter (Wave 1, D-049), migrated atomically, never
    # coexisting with it.
    repository = build_repository()
    dispatcher = EventDispatcher(repository.SessionLocal)
    # Epic W4-4: the single authorized example workflow, registered as an
    # ordinary handler -- the Dispatcher above is never modified to know
    # about it. WorkflowRuntime/ExecutionTracker own the workflow_executions
    # lifecycle entirely on their own.
    runtime = WorkflowRuntime(ExecutionTracker(repository.SessionLocal))
    document_indexed_workflow.register(dispatcher, runtime)
    return InProcessEventPublisher(repository.SessionLocal, dispatcher)


@lru_cache
def build_notification_provider() -> NotificationProvider:
    # Item 6 (Convites, D-054): the delivery seam. NoOp today -- no concrete
    # SMTP/SES provider is chosen; the invitation token is returned once at
    # creation for manual delivery. Same pattern as build_event_publisher.
    return NoOpNotificationProvider()
