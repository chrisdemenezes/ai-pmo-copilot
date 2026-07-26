"""Drop analysis_records.project_name + NOT NULL on project_id (TD-008 Fase 3b, Etapa 4b)

STRATECH V2 -- item 8 of the Wave Completion Review retrospective, the ONLY
**irreversible** stage of the project_name -> project_id migration.

STATUS: **STAGED, NOT ACTIVATED.** This revision lives in
`alembic/versions_pending/` (NOT on alembic's `version_locations`), so
`alembic upgrade head` for the application and the test suite stops at 0014
and the `analysis_records.project_name` column is preserved -- exactly as
Etapa 4a requires. Activating it (moving this file into `alembic/versions/`
so it becomes head) is the Etapa 4b act, which the Founder has explicitly
blocked pending a separate, explicit approval.

Its upgrade AND downgrade are proven reversible on real PostgreSQL by
`tests/test_migration_0015_drop_project_name.py` (run against a throwaway
database, at raw-connection level so the still-mapped ORM column never
conflicts). Backup/restore before activation follows RB-002 (Production
Backup & Restore Runbook).

Prerequisite already satisfied by Etapa 4a: no behavior reads or writes the
`project_name` column, and migration 0014 backfilled `project_id` on every
row, so `SET NOT NULL` cannot fail on legacy data.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015"
down_revision: Union[str, Sequence[str], None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # project_id becomes the sole, mandatory identity key.
    op.alter_column(
        "analysis_records",
        "project_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    # The legacy display/key column and its index are removed for good.
    op.drop_index(op.f("ix_analysis_records_project_name"), table_name="analysis_records")
    op.drop_column("analysis_records", "project_name")


def downgrade() -> None:
    # Fully reversible: re-add the column (nullable, as it always was) and its
    # index, and relax project_id back to nullable. Historical project_name
    # values are NOT restored (they were already unused since Etapa 4a and are
    # not recoverable post-drop); the column comes back empty, which is exactly
    # its state for every row written during Etapa 4a.
    op.add_column(
        "analysis_records",
        sa.Column("project_name", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_analysis_records_project_name"),
        "analysis_records",
        ["project_name"],
        unique=False,
    )
    op.alter_column(
        "analysis_records",
        "project_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
