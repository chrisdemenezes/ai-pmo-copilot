"""Wave 4 Enterprise Operations, Epic W4-1 -- events, dead_letter_events

STRATECH V2, Wave 4 (Enterprise Operations), Epic W4-1 -- Event Model +
Event Publisher.

Purely additive: adds `events` (Event Audit -- the durable envelope of
every event published via `EventPublisher`) and `dead_letter_events`
(minimal Dead Letter Strategy -- an event whose dispatch failed 3 times).
`workflow_executions` (Execution Tracking) is deliberately NOT created
here -- it belongs to the Workflow Runtime, Epic W4-4, which does not
exist yet (`docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md`
§5.3).

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018"
down_revision: Union[str, Sequence[str], None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=100), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_events_id"), "events", ["id"], unique=False)
    op.create_index(op.f("ix_events_event_id"), "events", ["event_id"], unique=True)
    op.create_index(op.f("ix_events_event_type"), "events", ["event_type"], unique=False)
    op.create_index(op.f("ix_events_correlation_id"), "events", ["correlation_id"], unique=False)
    op.create_index(op.f("ix_events_organization_id"), "events", ["organization_id"], unique=False)

    op.create_table(
        "dead_letter_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )
    op.create_index(
        op.f("ix_dead_letter_events_id"), "dead_letter_events", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_dead_letter_events_event_id"),
        "dead_letter_events",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dead_letter_events_organization_id"),
        "dead_letter_events",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dead_letter_events_correlation_id"),
        "dead_letter_events",
        ["correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_dead_letter_events_correlation_id"), table_name="dead_letter_events")
    op.drop_index(op.f("ix_dead_letter_events_organization_id"), table_name="dead_letter_events")
    op.drop_index(op.f("ix_dead_letter_events_event_id"), table_name="dead_letter_events")
    op.drop_index(op.f("ix_dead_letter_events_id"), table_name="dead_letter_events")
    op.drop_table("dead_letter_events")

    op.drop_index(op.f("ix_events_organization_id"), table_name="events")
    op.drop_index(op.f("ix_events_correlation_id"), table_name="events")
    op.drop_index(op.f("ix_events_event_type"), table_name="events")
    op.drop_index(op.f("ix_events_event_id"), table_name="events")
    op.drop_index(op.f("ix_events_id"), table_name="events")
    op.drop_table("events")
