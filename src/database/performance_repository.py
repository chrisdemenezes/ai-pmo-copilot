"""Write/read repository for Wave 8 Executive Analytics -- the EVM
temporal baseline and performance snapshot tables added by migration
`0023` (Founder Decision, `docs/architecture/TECHNICAL-DESIGN-WAVE-8-EXECUTIVE-ANALYTICS.md`
Section 2).

Same convention as `DomainRepository`: one class, constructed with the
shared `session_factory`, organization scoping enforced explicitly in
every query -- never implicitly, never checked only after the fact.

Both tables are append-only (Section 2.F/2.B): a baseline "version" or a
snapshot "day" is never updated or deleted here, only inserted.
"""
import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from src.database.models import ProjectPerformanceBaseline, ProjectPerformanceSnapshot

logger = logging.getLogger(__name__)


class PerformanceRepository:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    # -- Baselines (planned-value curve, human-authored) ------------------

    def create_baseline(
        self,
        organization_id: int,
        project_id: int,
        bac_reference: Decimal,
        points: list[tuple[date, Decimal]],
    ) -> int:
        """Inserts a brand new baseline version -- `points` is
        `[(period_date, planned_progress_percentage), ...]`, authored by a
        human (PM/PMO), never inferred. `planned_value` is derived
        deterministically as `bac_reference * planned_progress_percentage
        / 100` for each point. Returns the new `baseline_version`."""
        with self._session_factory() as session:
            current_max = (
                session.query(func.max(ProjectPerformanceBaseline.baseline_version))
                .filter(ProjectPerformanceBaseline.project_id == project_id)
                .scalar()
            )
            next_version = 1 if current_max is None else current_max + 1
            for period_date, planned_progress_percentage in points:
                planned_value = bac_reference * planned_progress_percentage / Decimal(100)
                session.add(
                    ProjectPerformanceBaseline(
                        organization_id=organization_id,
                        project_id=project_id,
                        baseline_version=next_version,
                        period_date=period_date,
                        planned_progress_percentage=planned_progress_percentage,
                        planned_value=planned_value,
                        bac_reference=bac_reference,
                    )
                )
            session.commit()
            logger.info(
                "Created baseline version=%s project_id=%s organization_id=%s points=%d",
                next_version,
                project_id,
                organization_id,
                len(points),
            )
            return next_version

    def get_active_baseline(
        self, project_id: int, organization_id: int
    ) -> list[ProjectPerformanceBaseline]:
        """Rows of the highest `baseline_version` for this project, ordered
        by `period_date`. Empty list means no baseline has ever been
        authored -- callers must treat this as "no data", never as zero."""
        with self._session_factory() as session:
            current_max = (
                session.query(func.max(ProjectPerformanceBaseline.baseline_version))
                .filter(
                    ProjectPerformanceBaseline.project_id == project_id,
                    ProjectPerformanceBaseline.organization_id == organization_id,
                )
                .scalar()
            )
            if current_max is None:
                return []
            return (
                session.query(ProjectPerformanceBaseline)
                .filter(
                    ProjectPerformanceBaseline.project_id == project_id,
                    ProjectPerformanceBaseline.organization_id == organization_id,
                    ProjectPerformanceBaseline.baseline_version == current_max,
                )
                .order_by(ProjectPerformanceBaseline.period_date)
                .all()
            )

    # -- Snapshots (actual/earned history, append-only) --------------------

    def capture_snapshot(
        self,
        organization_id: int,
        project_id: int,
        snapshot_date: date,
        actual_cost: Decimal,
        progress_percentage: int,
    ) -> ProjectPerformanceSnapshot:
        """Idempotent: a second capture on the same `snapshot_date` returns
        the existing row unchanged rather than overwriting it (Section
        2.B) -- the real history of what happened never gets silently
        replaced."""
        with self._session_factory() as session:
            existing = (
                session.query(ProjectPerformanceSnapshot)
                .filter(
                    ProjectPerformanceSnapshot.project_id == project_id,
                    ProjectPerformanceSnapshot.organization_id == organization_id,
                    ProjectPerformanceSnapshot.snapshot_date == snapshot_date,
                )
                .one_or_none()
            )
            if existing is not None:
                logger.info(
                    "Snapshot already captured project_id=%s date=%s -- returning existing row",
                    project_id,
                    snapshot_date,
                )
                return existing
            snapshot = ProjectPerformanceSnapshot(
                organization_id=organization_id,
                project_id=project_id,
                snapshot_date=snapshot_date,
                actual_cost=actual_cost,
                progress_percentage=progress_percentage,
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            logger.info(
                "Captured performance snapshot id=%s project_id=%s date=%s",
                snapshot.id,
                project_id,
                snapshot_date,
            )
            return snapshot

    def list_snapshots(
        self, project_id: int, organization_id: int
    ) -> list[ProjectPerformanceSnapshot]:
        with self._session_factory() as session:
            return (
                session.query(ProjectPerformanceSnapshot)
                .filter(
                    ProjectPerformanceSnapshot.project_id == project_id,
                    ProjectPerformanceSnapshot.organization_id == organization_id,
                )
                .order_by(ProjectPerformanceSnapshot.snapshot_date)
                .all()
            )
