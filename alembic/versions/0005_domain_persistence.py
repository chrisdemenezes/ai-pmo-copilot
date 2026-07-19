"""domain persistence -- portfolios, programs, and Project domain fields

STRATECH V2 Wave 2 (Enterprise Master Execution Program), Enterprise
Domain epic. Persists Portfolio and Program as new tables (organization_id
on Portfolio only -- Program/Project derive their organization
transitively, per Foundation Technical Design §3/§3.10), and extends the
existing Épico-1 `projects` table with domain fields instead of creating a
separate `projects_delivery` table (Domain Blueprint
`DOMAIN-BLUEPRINT-PROJECT.md`, Opção A Fase 1) -- so the historical
"3 Project concepts" (TD-008) collapse toward one instead of becoming a
fourth.

All new `projects` columns are nullable: pre-existing rows (migrated from
legacy `project_name`) never populate them; only Projects going through
the Enterprise Domain from here on do, via `program_id`.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("executive_owner", sa.String(length=255), nullable=True),
        sa.Column("strategic_objective", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
        sa.Column("health", sa.String(length=10), nullable=False, server_default="green"),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="Média"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("program_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("project_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_demands", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_risks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_decisions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sponsor", sa.String(length=255), nullable=True),
        sa.Column("pmo_owner", sa.String(length=255), nullable=True),
        sa.Column("last_updated", sa.Date(), nullable=True),
        sa.Column("next_review", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("organization_id", "code", name="uq_portfolios_org_code"),
    )
    op.create_index(op.f("ix_portfolios_id"), "portfolios", ["id"], unique=False)
    op.create_index(
        op.f("ix_portfolios_organization_id"), "portfolios", ["organization_id"], unique=False
    )

    op.create_table(
        "programs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("sponsor", sa.String(length=255), nullable=True),
        sa.Column("program_manager", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
        sa.Column("health", sa.String(length=10), nullable=False, server_default="green"),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="Média"),
        sa.Column("objective", sa.String(length=1000), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("project_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_demands", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_risks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_decisions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_actions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pmo_owner", sa.String(length=255), nullable=True),
        sa.Column("last_updated", sa.Date(), nullable=True),
        sa.Column("next_review", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.UniqueConstraint("portfolio_id", "code", name="uq_programs_portfolio_code"),
    )
    op.create_index(op.f("ix_programs_id"), "programs", ["id"], unique=False)
    op.create_index(
        op.f("ix_programs_portfolio_id"), "programs", ["portfolio_id"], unique=False
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("program_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("code", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("description", sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column("objective", sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column("sponsor", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("project_manager", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("health", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("priority", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("start_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("planned_end_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("actual_end_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("progress_percentage", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_updated", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("next_review", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("owner_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("milestones_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("team_json", sa.JSON(), nullable=True))
        batch_op.create_index(
            op.f("ix_projects_program_id"), ["program_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_projects_program_id", "programs", ["program_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_program_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_projects_program_id"))
        batch_op.drop_column("team_json")
        batch_op.drop_column("milestones_json")
        batch_op.drop_column("owner_json")
        batch_op.drop_column("next_review")
        batch_op.drop_column("last_updated")
        batch_op.drop_column("progress_percentage")
        batch_op.drop_column("actual_end_date")
        batch_op.drop_column("planned_end_date")
        batch_op.drop_column("start_date")
        batch_op.drop_column("priority")
        batch_op.drop_column("health")
        batch_op.drop_column("status")
        batch_op.drop_column("project_manager")
        batch_op.drop_column("sponsor")
        batch_op.drop_column("objective")
        batch_op.drop_column("description")
        batch_op.drop_column("code")
        batch_op.drop_column("program_id")

    op.drop_index(op.f("ix_programs_portfolio_id"), table_name="programs")
    op.drop_index(op.f("ix_programs_id"), table_name="programs")
    op.drop_table("programs")

    op.drop_index(op.f("ix_portfolios_organization_id"), table_name="portfolios")
    op.drop_index(op.f("ix_portfolios_id"), table_name="portfolios")
    op.drop_table("portfolios")
