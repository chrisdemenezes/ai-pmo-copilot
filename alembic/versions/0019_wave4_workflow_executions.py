"""Wave 4 Enterprise Operations, Epic W4-4 -- workflow_executions

STRATECH V2, Wave 4 (Enterprise Operations), Epic W4-4 -- Workflow Runtime
+ Execution Tracking.

Purely additive: adds `workflow_executions` (Execution Tracking --
`docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md` §3/§12),
deliberately deferred from the W4-1 migration (0018) until the Workflow
Runtime that owns it existed. `UNIQUE(event_id, workflow_name)` is the
idempotency key (§12.4) -- enforced at the database, not only in
application code, per the Founder's explicit requirement.

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019"
down_revision: Union[str, Sequence[str], None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_name", sa.String(length=200), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("event_id", "workflow_name", name="uq_workflow_executions_event_workflow"),
    )
    op.create_index(
        op.f("ix_workflow_executions_id"), "workflow_executions", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_workflow_executions_event_id"),
        "workflow_executions",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_executions_organization_id"),
        "workflow_executions",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_executions_correlation_id"),
        "workflow_executions",
        ["correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_executions_correlation_id"), table_name="workflow_executions")
    op.drop_index(op.f("ix_workflow_executions_organization_id"), table_name="workflow_executions")
    op.drop_index(op.f("ix_workflow_executions_event_id"), table_name="workflow_executions")
    op.drop_index(op.f("ix_workflow_executions_id"), table_name="workflow_executions")
    op.drop_table("workflow_executions")
