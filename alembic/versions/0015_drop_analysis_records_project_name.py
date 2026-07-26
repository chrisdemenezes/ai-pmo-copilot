"""Drop analysis_records.project_name + NOT NULL on project_id (TD-008 Fase 3b, Etapa 4b)

STRATECH V2 -- item 8 of the Wave Completion Review retrospective, the ONLY
**irreversible** stage of the project_name -> project_id migration.

STATUS: **ACTIVE** (Etapa 4b autorizada pelo Founder, D-060). `project_id`
torna-se a única chave de acesso interno ao Project (NOT NULL) e a coluna
legada `analysis_records.project_name` é removida do banco e do ORM.

Prerequisite satisfied by Etapa 4a: no behavior reads or writes the
`project_name` column, and migration 0014 backfilled `project_id` on every
row, so `SET NOT NULL` cannot fail on legacy data.

Downgrade (Founder Condição 2 -- rollback íntegro): re-adds the column and
**repopulates `project_name` from `projects.name` via `project_id`**, so a
prior application version that reads the column operates over real display
names (never an empty column). Proven reversible on real PostgreSQL by
`tests/test_migration_0015_drop_project_name.py`. Backup/restore before
activation follows RB-002 (Production Backup & Restore Runbook).

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
    # Reversible with data restoration (Founder Condição 2): re-add the column
    # and its index, relax project_id back to nullable, and REPOPULATE
    # project_name from projects.name via the project_id link -- so a prior app
    # version reading the column sees real display names, not an empty column.
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
    # Restore the display name from the Project (the source of truth since
    # Fase 3b). The fallback Project keeps its "(sem projeto)" name; a prior
    # version already treated that as "no project" for display.
    op.execute(
        "UPDATE analysis_records ar "
        "SET project_name = p.name "
        "FROM projects p "
        "WHERE ar.project_id = p.id"
    )
