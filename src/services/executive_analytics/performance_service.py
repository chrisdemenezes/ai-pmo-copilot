"""Application layer for Wave 8 Executive Analytics -- baseline authoring,
snapshot capture, and EVM summary computation for a single Project.

Same split as `DomainService`: routes stay thin adapters; this service
enforces the one rule the repository doesn't -- that a Project is only
reachable when it belongs to the caller's organization -- and wires audit
+ event publication around the two write paths (baseline creation, snapshot
capture), matching the discipline every other Enterprise Domain write
already follows.
"""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from src.database.models import ProjectPerformanceSnapshot
from src.database.repository import AnalysisRepository
from src.services.events.interfaces import EventPublisher
from src.services.executive_analytics.metrics_engine import (
    BaselinePoint,
    EvmSummary,
    PerformanceSnapshotPoint,
    compute_evm_summary,
)

logger = logging.getLogger(__name__)


class ProjectPerformanceService:
    def __init__(self, repository: AnalysisRepository, publisher: EventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    def create_baseline(
        self,
        organization_id: int,
        project_id: int,
        actor_user_id: int,
        correlation_id: str,
        bac_reference: Decimal,
        points: list[tuple[date, Decimal]],
    ) -> int | None:
        """None means the project doesn't exist or isn't this
        organization's -- same not-found-not-yours discipline as
        `DomainService.create_project`."""
        if self._repository.domain.get_project(project_id, organization_id) is None:
            return None
        baseline_version = self._repository.performance.create_baseline(
            organization_id, project_id, bac_reference, points
        )
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "project_performance_baseline.created",
            "project",
            project_id,
            details={
                "baseline_version": baseline_version,
                "point_count": len(points),
                "bac_reference": str(bac_reference),
            },
        )
        self._publisher.publish(
            "project_performance_baseline.created",
            {"project_id": project_id, "baseline_version": baseline_version},
            organization_id,
            correlation_id=correlation_id,
            origin="performance_service",
        )
        return baseline_version

    def capture_snapshot(
        self,
        organization_id: int,
        project_id: int,
        actor_user_id: int,
        correlation_id: str,
        snapshot_date: date | None = None,
    ) -> ProjectPerformanceSnapshot | None:
        """Copies `Project.actual_cost`/`progress_percentage` as they stand
        right now -- the caller never supplies these values directly, so a
        snapshot can never diverge from the Project it was captured from
        (Section 2.B). Raises `ValueError` (mapped to 422 by the route) when
        either field is still null on the Project -- there is nothing real
        to capture yet."""
        project = self._repository.domain.get_project(project_id, organization_id)
        if project is None:
            return None
        if project.actual_cost is None:
            raise ValueError("actual_cost_missing")
        if project.progress_percentage is None:
            raise ValueError("progress_percentage_missing")
        resolved_date = snapshot_date or datetime.now(tz=timezone.utc).date()
        snapshot = self._repository.performance.capture_snapshot(
            organization_id,
            project_id,
            resolved_date,
            project.actual_cost,
            project.progress_percentage,
        )
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "project_performance_snapshot.captured",
            "project",
            project_id,
            details={
                "snapshot_date": resolved_date.isoformat(),
                "actual_cost": str(project.actual_cost),
                "progress_percentage": project.progress_percentage,
            },
        )
        self._publisher.publish(
            "project_performance_snapshot.captured",
            {"project_id": project_id, "snapshot_date": resolved_date.isoformat()},
            organization_id,
            correlation_id=correlation_id,
            origin="performance_service",
        )
        return snapshot

    def get_evm_summary(
        self, project_id: int, organization_id: int, as_of: date
    ) -> EvmSummary | None:
        """None means the project doesn't exist or isn't this
        organization's. Otherwise always returns a summary -- individual
        metrics inside it are `MetricValue.na(...)` when the underlying
        baseline/snapshot data doesn't exist, never raised as an error."""
        if self._repository.domain.get_project(project_id, organization_id) is None:
            return None
        baseline_rows = self._repository.performance.get_active_baseline(
            project_id, organization_id
        )
        snapshot_rows = self._repository.performance.list_snapshots(project_id, organization_id)
        baseline = [
            BaselinePoint(row.period_date, row.planned_value, row.bac_reference)
            for row in baseline_rows
        ]
        snapshots = [
            PerformanceSnapshotPoint(row.snapshot_date, row.actual_cost, row.progress_percentage)
            for row in snapshot_rows
        ]
        return compute_evm_summary(baseline, snapshots, as_of)
