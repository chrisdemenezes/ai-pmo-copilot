"""`ExecutionTracker` -- the only component aware of `workflow_executions`
(Wave 4, Enterprise Operations, Epic W4-4 --
`docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md` §12).
Same single-facade discipline already used by `KnowledgeRepository`/
`IntegrationGateway` -- `WorkflowRuntime` never writes SQL directly.

`EventDispatcher` (Epic W4-1) never imports this module and never reads
or writes `workflow_executions` -- that separation is a fixed
architectural principle of this Wave, not an implementation detail.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from src.database.models import WorkflowExecution

logger = logging.getLogger(__name__)

# The error column must never carry a stack trace, a token, a credential,
# or the full event payload (Founder's explicit restriction) -- only the
# exception's own type and message, truncated defensively even though the
# column itself already caps at 500 chars.
_MAX_ERROR_LENGTH = 500


def sanitize_error(exc: Exception) -> str:
    """`type(exc).__name__: str(exc)`, truncated -- never a traceback,
    never the workflow payload, never re-derived from anything but the
    exception's own message."""
    return f"{type(exc).__name__}: {exc}"[:_MAX_ERROR_LENGTH]


class ExecutionTracker:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def start(
        self,
        event_id: str,
        workflow_name: str,
        organization_id: int,
        correlation_id: str,
    ) -> None:
        """Upsert keyed by `(event_id, workflow_name)` -- the idempotency
        key (§12.4). Insert a fresh `running` row, or, if `EventDispatcher`
        is redispatching the same event on its own synchronous retry,
        reuse the existing row: reset it to `running`, clearing any prior
        `finished_at`/`error`. Atomic `INSERT ... ON CONFLICT DO UPDATE`
        against the database's own `UNIQUE(event_id, workflow_name)`
        constraint -- never a SELECT-then-INSERT race."""
        started_at = datetime.now(timezone.utc)
        stmt = insert(WorkflowExecution).values(
            event_id=event_id,
            workflow_name=workflow_name,
            organization_id=organization_id,
            correlation_id=correlation_id,
            status="running",
            started_at=started_at,
            finished_at=None,
            error=None,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_workflow_executions_event_workflow",
            set_={
                "status": "running",
                "started_at": started_at,
                "finished_at": None,
                "error": None,
            },
        )
        with self._session_factory() as session:
            session.execute(stmt)
            session.commit()
        logger.info(
            "workflow execution started: event_id=%s workflow_name=%s", event_id, workflow_name
        )

    def complete(self, event_id: str, workflow_name: str) -> None:
        with self._session_factory() as session:
            execution = (
                session.query(WorkflowExecution)
                .filter(
                    WorkflowExecution.event_id == event_id,
                    WorkflowExecution.workflow_name == workflow_name,
                )
                .one()
            )
            execution.status = "completed"
            execution.finished_at = datetime.now(timezone.utc)
            execution.error = None
            session.commit()
        logger.info(
            "workflow execution completed: event_id=%s workflow_name=%s", event_id, workflow_name
        )

    def fail(self, event_id: str, workflow_name: str, exc: Exception) -> None:
        error_message = sanitize_error(exc)
        with self._session_factory() as session:
            execution = (
                session.query(WorkflowExecution)
                .filter(
                    WorkflowExecution.event_id == event_id,
                    WorkflowExecution.workflow_name == workflow_name,
                )
                .one()
            )
            execution.status = "failed"
            execution.finished_at = datetime.now(timezone.utc)
            execution.error = error_message
            session.commit()
        logger.warning(
            "workflow execution failed: event_id=%s workflow_name=%s error=%s",
            event_id,
            workflow_name,
            error_message,
        )
