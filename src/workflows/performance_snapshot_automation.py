"""TD-016 (V1 Post-Completion Technical Closure): automated performance
snapshot capture, event-driven side.

Registers a plain handler on `EventDispatcher` -- deliberately NOT routed
through `WorkflowRuntime` (that machinery is reserved for
`document_indexed_workflow`, "the single minimal example workflow
authorized for Epic W4-4"; this is a second, independent, generic pub/sub
consumer, exactly the kind `EventDispatcher.register()` already supports
for any future handler). No new dispatch mechanism is introduced -- retry
(up to 3 attempts) and dead-letter recording on a genuine failure are
inherited from `EventDispatcher` unchanged.

Reacts to `project_performance_baseline.created` -- a real, already-published
event (Wave 8) marking "a relevant planning change just happened" -- by
capturing one snapshot immediately, anchoring the newly-authored planned
curve to a real actual/earned data point. A Project with no
`actual_cost`/`progress_percentage` yet (nothing real to capture) is an
expected, normal state, not a failure: `capture_snapshot()`'s `ValueError`
for that case is caught here and treated as a no-op, never retried or
dead-lettered (retrying would never fix a permanently-missing field).
"""
import logging

from src.database.repository import AnalysisRepository
from src.services.events.dispatcher import EventDispatcher
from src.services.events.interfaces import DomainEvent, EventPublisher
from src.services.executive_analytics.performance_service import (
    ProjectPerformanceService,
)

logger = logging.getLogger(__name__)


def register(
    dispatcher: EventDispatcher, repository: AnalysisRepository, publisher: EventPublisher
) -> None:
    service = ProjectPerformanceService(repository=repository, publisher=publisher)

    def _handle(event: DomainEvent) -> None:
        project_id = event.payload["project_id"]
        actor_user_id = event.payload["actor_user_id"]
        try:
            snapshot = service.capture_snapshot(
                event.organization_id, project_id, actor_user_id, event.correlation_id
            )
        except ValueError as error:
            logger.info(
                "Skipped automated snapshot capture project_id=%s: %s", project_id, error
            )
            return
        if snapshot is None:
            logger.warning(
                "Automated snapshot capture found no project_id=%s organization_id=%s "
                "(baseline event referenced a project that no longer resolves)",
                project_id,
                event.organization_id,
            )
            return
        logger.info(
            "Automated snapshot capture (baseline event) project_id=%s snapshot_id=%s",
            project_id,
            snapshot.id,
        )

    dispatcher.register("project_performance_baseline.created", _handle)
