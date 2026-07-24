"""Defensive backfill of analysis_records.project_id (TD-008 Phase 3b, Etapa 1)

STRATECH V2 Wave 2 -- item 8 of the Wave Completion Review retrospective,
first (additive) stage of the project_name -> project_id migration.

`analysis_records.project_id` was already added and backfilled by migration
0002, and every write since links it at save time
(`get_or_create_project_for_name`). This migration is a **belt-and-suspenders
re-backfill**: it links any remaining `project_id IS NULL` row to the
matching Project in the same organization, using the same resolution rule as
the application (strip whitespace on the name; empty/None -> the fallback
project "(sem projeto)"). It does NOT set NOT NULL and does NOT drop any
column -- those destructive steps are Etapa 4, gated on a separate Founder
approval.

Idempotent (a second run finds nothing to update) and non-destructive (only
fills NULLs, never overwrites an existing id). Downgrade is a documented
no-op: the backfilled links are correct and harmless; there is nothing to
reverse without losing valid data.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014"
down_revision: Union[str, Sequence[str], None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FALLBACK_PROJECT_NAME = "(sem projeto)"


def upgrade() -> None:
    conn = op.get_bind()
    # Link every still-unlinked analysis to the Project that shares its
    # organization and (normalized) name. Rows whose name matches no Project
    # stay NULL -- in practice none exist, since save_analysis always
    # get_or_creates the Project; Etapa 4 will handle any residual explicitly
    # before promoting the column to NOT NULL.
    conn.execute(
        sa.text(
            """
            UPDATE analysis_records AS a
            SET project_id = p.id
            FROM projects AS p
            WHERE a.project_id IS NULL
              AND p.organization_id = a.organization_id
              AND p.name = COALESCE(NULLIF(TRIM(a.project_name), ''), :fallback)
            """
        ),
        {"fallback": FALLBACK_PROJECT_NAME},
    )


def downgrade() -> None:
    # No-op by design: this migration only fills NULL project_id links with
    # correct values. Reversing it would re-introduce NULLs and lose valid
    # data, with no schema change to undo.
    pass
