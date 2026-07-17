"""identity type on users -- distinguishes demo accounts from standard ones

STRATECH V2 Release 0.1, Épico 2 (Identity Foundation), TDS Rev. 2
Section 11 / AR-001 item 5.

Additive, backfillable column: every pre-existing user (if any, from the
Épico 1 baseline) receives "standard" via the column default, which is
also the application-level default in src/database/models.py. Reversible
by dropping the column.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "identity_type",
                sa.String(length=20),
                nullable=False,
                server_default="standard",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("identity_type")
