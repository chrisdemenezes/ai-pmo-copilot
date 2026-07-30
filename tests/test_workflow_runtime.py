"""WorkflowRuntime + ExecutionTracker (Wave 4, Enterprise Operations,
Epic W4-4) -- the running/completed/failed lifecycle in
`workflow_executions`, the idempotent upsert keyed by
(event_id, workflow_name), and sanitized error messages. `EventDispatcher`
is never imported here -- these are Runtime-only unit tests; the full
publish -> dispatch -> execute chain (including Retry/Dead Letter) is
covered by `test_document_indexed_workflow.py`.
"""
from datetime import datetime, timezone

import pytest

from src.database.models import EventRecord, WorkflowExecution
from src.database.repository import AnalysisRepository
from src.services.events.interfaces import DomainEvent
from src.workflows.execution_tracking import ExecutionTracker, sanitize_error
from src.workflows.runtime import WorkflowRuntime
from tests.db import temp_database_url

WORKFLOW_NAME = "wf-example"


@pytest.fixture()
def repository():
    with temp_database_url("workflow_runtime") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


@pytest.fixture()
def execution_tracker(repository):
    return ExecutionTracker(repository.SessionLocal)


@pytest.fixture()
def runtime(execution_tracker):
    return WorkflowRuntime(execution_tracker)


def _event(repository, org_id: int, event_id: str = "event-1") -> DomainEvent:
    """Persists a matching EventRecord first -- workflow_executions.event_id
    has a real FK to events.event_id, mirroring InProcessEventPublisher's own
    invariant (same pattern already used by test_events_dispatcher.py)."""
    event = DomainEvent(
        event_id=event_id,
        event_type="document.indexed",
        correlation_id="corr-1",
        timestamp=datetime.now(timezone.utc),
        organization_id=org_id,
        origin="test",
        payload_version=1,
        payload={"document_id": 42, "version_id": 7, "chunk_count": 3},
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


def _executions(repository, event_id: str, workflow_name: str) -> list[WorkflowExecution]:
    with repository.SessionLocal() as session:
        return (
            session.query(WorkflowExecution)
            .filter(
                WorkflowExecution.event_id == event_id,
                WorkflowExecution.workflow_name == workflow_name,
            )
            .all()
        )


def _always_fails(context):
    raise RuntimeError("step exploded")


class TestSuccessfulExecution:
    def test_run_records_completed_with_correlation_id_inherited(self, runtime, repository, org_id):
        event = _event(repository, org_id)

        context = runtime.run(WORKFLOW_NAME, [lambda c: c], event)

        assert context.correlation_id == event.correlation_id
        assert context.organization_id == event.organization_id
        assert context.payload == event.payload

        rows = _executions(repository, event.event_id, WORKFLOW_NAME)
        assert len(rows) == 1
        assert rows[0].status == "completed"
        assert rows[0].finished_at is not None
        assert rows[0].error is None
        assert rows[0].correlation_id == event.correlation_id
        assert rows[0].organization_id == event.organization_id


class TestFailedExecution:
    def test_run_records_failed_and_reraises_the_original_exception(self, runtime, repository, org_id):
        event = _event(repository, org_id)

        with pytest.raises(RuntimeError, match="step exploded"):
            runtime.run(WORKFLOW_NAME, [_always_fails], event)

        rows = _executions(repository, event.event_id, WORKFLOW_NAME)
        assert len(rows) == 1
        assert rows[0].status == "failed"
        assert rows[0].finished_at is not None
        assert "RuntimeError" in rows[0].error
        assert "step exploded" in rows[0].error

    def test_failure_error_never_leaks_the_event_payload(self, runtime, repository, org_id):
        event = _event(repository, org_id)  # payload has document_id=42, chunk_count=3

        with pytest.raises(RuntimeError):
            runtime.run(WORKFLOW_NAME, [_always_fails], event)

        rows = _executions(repository, event.event_id, WORKFLOW_NAME)
        assert "document_id" not in rows[0].error
        assert "chunk_count" not in rows[0].error
        assert "42" not in rows[0].error


class TestRetryReusesTheSameRow:
    """Mirrors EventDispatcher's own synchronous retry (W4-1): the same
    DomainEvent is redispatched to the same handler, which calls
    WorkflowRuntime.run() again for the same (event_id, workflow_name)."""

    def test_second_attempt_reuses_the_row_instead_of_inserting_a_second_one(
        self, runtime, repository, org_id
    ):
        event = _event(repository, org_id)

        with pytest.raises(RuntimeError):
            runtime.run(WORKFLOW_NAME, [_always_fails], event)  # attempt 1: running -> failed

        runtime.run(WORKFLOW_NAME, [lambda c: c], event)  # attempt 2: failed -> running -> completed

        rows = _executions(repository, event.event_id, WORKFLOW_NAME)
        assert len(rows) == 1
        assert rows[0].status == "completed"

    def test_error_is_cleared_when_a_later_attempt_succeeds(self, runtime, repository, org_id):
        event = _event(repository, org_id)

        with pytest.raises(RuntimeError):
            runtime.run(WORKFLOW_NAME, [_always_fails], event)

        runtime.run(WORKFLOW_NAME, [lambda c: c], event)

        rows = _executions(repository, event.event_id, WORKFLOW_NAME)
        assert rows[0].error is None


class TestNoDuplicateRows:
    def test_three_consecutive_failing_attempts_never_produce_more_than_one_row(
        self, runtime, repository, org_id
    ):
        event = _event(repository, org_id)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                runtime.run(WORKFLOW_NAME, [_always_fails], event)

        rows = _executions(repository, event.event_id, WORKFLOW_NAME)
        assert len(rows) == 1
        assert rows[0].status == "failed"

    def test_a_different_event_id_always_creates_a_new_execution_row(self, runtime, repository, org_id):
        first_event = _event(repository, org_id, event_id="event-a")
        second_event = _event(repository, org_id, event_id="event-b")

        runtime.run(WORKFLOW_NAME, [lambda c: c], first_event)
        runtime.run(WORKFLOW_NAME, [lambda c: c], second_event)

        assert len(_executions(repository, "event-a", WORKFLOW_NAME)) == 1
        assert len(_executions(repository, "event-b", WORKFLOW_NAME)) == 1


class TestSanitizeError:
    def test_only_exception_type_and_message_never_a_traceback(self):
        try:
            raise ValueError("boom")
        except ValueError as exc:
            message = sanitize_error(exc)

        assert message == "ValueError: boom"
        assert "Traceback" not in message
        assert "File \"" not in message

    def test_truncated_to_the_column_limit(self):
        try:
            raise RuntimeError("x" * 1000)
        except RuntimeError as exc:
            message = sanitize_error(exc)

        assert len(message) <= 500
