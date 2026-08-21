"""Wave 8 Executive Analytics -- project_performance_baselines, project_performance_snapshots

STRATECH V2, Wave 8 (Executive Analytics & Experience Completion). Founder
Decision "EVM Temporal Baseline" (docs/architecture/TECHNICAL-DESIGN-WAVE-8-EXECUTIVE-ANALYTICS.md
Section 2): the STRATECH domain today only carries a current snapshot per
Project (approved_budget/actual_cost/progress_percentage), never a
time-phased baseline -- so EVM (CPI/SPI/EAC/S-Curve) has no real data to
compute against. Rather than infer or fabricate historical Planned Value
from the current snapshot, this migration adds two purely additive tables
so the domain can start accumulating a real, human-authored planned curve
(project_performance_baselines) and a real, prospectively-captured actual
history (project_performance_snapshots) going forward.

Purely additive: no existing table or column is touched. No existing row
is affected. Both new tables start empty for every current Project --
EVM-family metrics remain N/A until a baseline is authored and at least one
snapshot is captured, exactly as designed.

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0023"
down_revision: Union[str, Sequence[str], None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_performance_baselines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("baseline_version", sa.Integer(), nullable=False),
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("planned_progress_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("planned_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("bac_reference", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "project_id",
            "baseline_version",
            "period_date",
            name="uq_performance_baseline_project_version_period",
        ),
    )
    op.create_index(
        op.f("ix_project_performance_baselines_id"),
        "project_performance_baselines",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_performance_baselines_organization_id"),
        "project_performance_baselines",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_performance_baselines_project_id"),
        "project_performance_baselines",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "project_performance_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("actual_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("progress_percentage", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "project_id", "snapshot_date", name="uq_performance_snapshot_project_date"
        ),
    )
    op.create_index(
        op.f("ix_project_performance_snapshots_id"),
        "project_performance_snapshots",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_performance_snapshots_organization_id"),
        "project_performance_snapshots",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_performance_snapshots_project_id"),
        "project_performance_snapshots",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_project_performance_snapshots_project_id"),
        table_name="project_performance_snapshots",
    )
    op.drop_index(
        op.f("ix_project_performance_snapshots_organization_id"),
        table_name="project_performance_snapshots",
    )
    op.drop_index(
        op.f("ix_project_performance_snapshots_id"), table_name="project_performance_snapshots"
    )
    op.drop_table("project_performance_snapshots")

    op.drop_index(
        op.f("ix_project_performance_baselines_project_id"),
        table_name="project_performance_baselines",
    )
    op.drop_index(
        op.f("ix_project_performance_baselines_organization_id"),
        table_name="project_performance_baselines",
    )
    op.drop_index(
        op.f("ix_project_performance_baselines_id"), table_name="project_performance_baselines"
    )
    op.drop_table("project_performance_baselines")
