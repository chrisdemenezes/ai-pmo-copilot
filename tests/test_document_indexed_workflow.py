"""Full chain (Wave 4, Enterprise Operations, Epic W4-4): `document.indexed`
published via `InProcessEventPublisher` -> `EventDispatcher` (W4-1,
untouched) -> the single authorized example workflow
(`document_indexed_workflow.register`) -> `WorkflowRuntime` -> Execution
Tracking. Also proves the two independent failure owners (§12.2): after
3 exhausted attempts, `EventDispatcher` records its own `dead_letter_events`
row while `WorkflowRuntime` independently records
`workflow_executions.status="failed"` -- neither reads the other's table.
"""
import pytest
from sqlalchemy import select

from src.database.models import DeadLetterEvent, WorkflowExecution
from src.database.repository import AnalysisRepository
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.workflows import document_indexed_workflow
from src.workflows.execution_tracking import ExecutionTracker
from src.workflows.runtime import WorkflowRuntime
from tests.db import temp_database_url

CORRELATION_ID = "corr-doc-indexed"


@pytest.fixture()
def repository():
    with temp_database_url("document_indexed_workflow") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


class TestSuccessfulChain:
    def test_publishing_document_indexed_runs_the_workflow_and_records_completed(
        self, repository, org_id
    ):
        dispatcher = EventDispatcher(repository.SessionLocal)
        runtime = WorkflowRuntime(ExecutionTracker(repository.SessionLocal))
        document_indexed_workflow.register(dispatcher, runtime)
        publisher = InProcessEventPublisher(repository.SessionLocal, dispatcher)

        event = publisher.publish(
            "document.indexed",
            {"document_id": 1, "version_id": 1, "chunk_count": 2},
            org_id,
            correlation_id=CORRELATION_ID,
            origin="knowledge_repository",
        )

        with repository.SessionLocal() as session:
            execution = session.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.event_id == event.event_id,
                    WorkflowExecution.workflow_name == document_indexed_workflow.WORKFLOW_NAME,
                )
            ).scalar_one()

        assert execution.status == "completed"
        assert execution.correlation_id == CORRELATION_ID
        assert execution.event_id == event.event_id
        assert execution.organization_id == org_id
        assert execution.error is None


class TestDeadLetterAfterThreeAttempts:
    def test_permanent_failure_produces_two_independent_records(self, repository, org_id):
        """The Dispatcher's own dead_letter_events (W4-1, unmodified) and
        the Runtime's own workflow_executions.status="failed" (W4-4) are
        both populated -- neither component reads or writes the other's
        table (Founder's separation principle, §12.2)."""
        dispatcher = EventDispatcher(repository.SessionLocal)
        runtime = WorkflowRuntime(ExecutionTracker(repository.SessionLocal))
        workflow_name = "always_failing_example"

        def _always_fails(context):
            raise RuntimeError("simulated permanent failure")

        def _handle(event):
            runtime.run(workflow_name, [_always_fails], event)

        dispatcher.register("document.indexed", _handle)
        publisher = InProcessEventPublisher(repository.SessionLocal, dispatcher)

        event = publisher.publish(
            "document.indexed",
            {"document_id": 2, "version_id": 1, "chunk_count": 1},
            org_id,
            correlation_id=CORRELATION_ID,
            origin="knowledge_repository",
        )  # dispatch never raises to the caller -- W4-1 policy, unchanged

        with repository.SessionLocal() as session:
            dead_letters = session.execute(
                select(DeadLetterEvent).where(DeadLetterEvent.event_id == event.event_id)
            ).scalars().all()
            execution = session.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.event_id == event.event_id,
                    WorkflowExecution.workflow_name == workflow_name,
                )
            ).scalar_one()

        assert len(dead_letters) == 1  # Dispatcher's own record, owned by W4-1
        assert dead_letters[0].attempts == 3

        assert execution.status == "failed"  # Runtime's own record, owned by W4-4
        assert "RuntimeError" in execution.error
        assert "simulated permanent failure" in execution.error

        # A single upsert row, never duplicated across the 3 Dispatcher attempts.
        with repository.SessionLocal() as session:
            count = session.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.event_id == event.event_id,
                    WorkflowExecution.workflow_name == workflow_name,
                )
            ).scalars().all()
        assert len(count) == 1
