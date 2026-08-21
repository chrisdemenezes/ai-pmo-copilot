"""Project financial fields: approved_budget/actual_cost/forecast_cost

STRATECH V1 Product & Capability Completion (Founder Mandate), Fase 3
(Package K -- Financial Management / Executive Financial KPIs). Per
`TECHNICAL-DESIGN-PACKAGE-K-FINANCIAL-MANAGEMENT.md`: the minimal financial
model lives only on `Project` -- Program/Portfolio never get a duplicate
column, their financial KPI is a runtime rollup over their own Projects
(same "derived, never stored" discipline `progress_percentage`/`health`
already use on the frontend, `web/lib/domain/shared.ts`).

Illustrative values are set only on the 7 Projects migration `0008_domain_seed`
itself seeds (matched the same way: `organization_id` + `code`, across both
fixed organizations) -- this migration never touches `0008`'s own INSERTs,
and never touches a Project created by a real user. Values are chosen to be
consistent with each seeded Project's already-seeded `health`/`progress_percentage`
(e.g. a `red` Project runs hot against its budget), for a truthful executive
demonstration -- never fabricated to look uniformly healthy.

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0022"
down_revision: Union[str, Sequence[str], None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_ORGANIZATION_NAMES = ["Organização Principal", "Demo Organization"]

# code -> (approved_budget, actual_cost, forecast_cost), same 7 Projects
# migration 0008 seeds (PJ-001..PJ-007).
PROJECT_FINANCIALS = {
    "PJ-001": (4_200_000.00, 3_100_000.00, 5_000_000.00),  # red, 30% progress -- over-pace
    "PJ-002": (1_800_000.00, 1_050_000.00, 1_900_000.00),  # yellow, 55%
    "PJ-003": (900_000.00, 560_000.00, 880_000.00),        # green, 70%
    "PJ-004": (12_000_000.00, 8_300_000.00, 12_600_000.00),  # yellow, 62%
    "PJ-005": (3_500_000.00, 3_050_000.00, 3_400_000.00),  # green, 88%
    "PJ-006": (2_200_000.00, 1_500_000.00, 2_150_000.00),  # green, 74%
    "PJ-007": (2_600_000.00, 1_900_000.00, 3_400_000.00),  # red, 22% -- over-pace
}


def upgrade() -> None:
    op.add_column("projects", sa.Column("approved_budget", sa.Numeric(14, 2), nullable=True))
    op.add_column("projects", sa.Column("actual_cost", sa.Numeric(14, 2), nullable=True))
    op.add_column("projects", sa.Column("forecast_cost", sa.Numeric(14, 2), nullable=True))

    conn = op.get_bind()
    for org_name in SEED_ORGANIZATION_NAMES:
        org_id = conn.execute(
            sa.text("SELECT id FROM organizations WHERE name = :n"), {"n": org_name}
        ).scalar()
        if org_id is None:
            continue
        for code, (approved, actual, forecast) in PROJECT_FINANCIALS.items():
            conn.execute(
                sa.text(
                    "UPDATE projects SET approved_budget = :approved, actual_cost = :actual, "
                    "forecast_cost = :forecast WHERE organization_id = :o AND code = :c"
                ),
                {"approved": approved, "actual": actual, "forecast": forecast, "o": org_id, "c": code},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for org_name in SEED_ORGANIZATION_NAMES:
        org_id = conn.execute(
            sa.text("SELECT id FROM organizations WHERE name = :n"), {"n": org_name}
        ).scalar()
        if org_id is None:
            continue
        for code in PROJECT_FINANCIALS:
            conn.execute(
                sa.text(
                    "UPDATE projects SET approved_budget = NULL, actual_cost = NULL, "
                    "forecast_cost = NULL WHERE organization_id = :o AND code = :c"
                ),
                {"o": org_id, "c": code},
            )

    op.drop_column("projects", "forecast_cost")
    op.drop_column("projects", "actual_cost")
    op.drop_column("projects", "approved_budget")
