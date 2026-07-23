"""User Management -- is_active + case-insensitive email uniqueness

STRATECH V2 Wave 2, User Management Capability (Enterprise Administration,
Nível 1). Closes the last gap in `DOMAIN-BLUEPRINT-USER-MANAGEMENT.md`:

1. `users.is_active` (BOOLEAN NOT NULL DEFAULT TRUE) -- additive, every
   existing row becomes active by default, no behavior change for
   installs that predate this migration.
2. Replaces `uq_users_org_email` (case-sensitive, on the raw column) with
   a functional unique index `uq_users_org_email_lower` on
   `(organization_id, lower(email))`, so uniqueness is enforced by the
   database itself under concurrent inserts, not just by an
   application-level pre-check (Technical Design §2). Existing data (only
   the seeded demo user as of this migration) is already lowercase, so no
   backfill is required -- documented here rather than a silent
   assumption.

Downgrade recreates the original case-sensitive constraint. This is only
lossy if two rows with case-variant emails were inserted while this
migration was active (impossible: the functional index would have
rejected the second one), so the round trip is safe in practice.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_org_email", type_="unique")

    op.create_index(
        "uq_users_org_email_lower",
        "users",
        ["organization_id", sa.text("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_users_org_email_lower", table_name="users")

    with op.batch_alter_table("users") as batch_op:
        batch_op.create_unique_constraint(
            "uq_users_org_email", ["organization_id", "email"]
        )
        batch_op.drop_column("is_active")
