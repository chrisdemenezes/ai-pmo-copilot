"""Security Hardening Gate -- RBAC on Intelligence + tenant isolation on
analysis_records.

Repository Audit Wave 3 (`docs/product/governance/REPOSITORY-AUDIT-WAVE-3.md`)
found 2 Critical, pre-existing (V1-era) security gaps, resolved together
here because they share the same route surface (`src/api/routes/intelligence.py`):

1. **C-1 -- RBAC**: none of intelligence.py's 8 routes carried a
   `require_permission` dependency, unlike every other Enterprise Domain
   route module. Adds `intelligence.read`/`intelligence.write` to the
   permission catalog, same vocabulary and seeding pattern as migration
   0006 -- `intelligence.read` for all 4 seed roles (every authenticated
   user browsing Workspace/Dashboard needs it), `intelligence.write` for
   the same 3 roles that already hold `project_delivery.write`
   (organization_admin, pmo, project_manager); viewer stays read-only.

2. **C-2 -- Tenant isolation**: `analysis_records` had no `organization_id`,
   so a query without an explicit project_name filter returned rows across
   every organization in the database -- a real, live cross-tenant leak
   now that more than one organization exists. Backfilled via the existing
   `project_id` link (populated for every row since Épico 1, itself always
   pointing at a Project whose `organization_id` is NOT NULL since Wave 1)
   -- a pure metadata join, never a read/exposure of historical row
   content. Column becomes NOT NULL after backfill; the migration fails
   loudly, not silently, if any row is left unbackfilled.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("intelligence.read", "Ler análises de IA (meetings/risks/status) da organização"),
    ("intelligence.write", "Executar novas análises de IA (meetings/risks/status) da organização"),
]

ROLE_PERMISSIONS = {
    "organization_admin": ["intelligence.read", "intelligence.write"],
    "pmo": ["intelligence.read", "intelligence.write"],
    "project_manager": ["intelligence.read", "intelligence.write"],
    "viewer": ["intelligence.read"],
}


def upgrade() -> None:
    conn = op.get_bind()

    # -- C-1: permission catalog (same pattern as migration 0006) ---------
    permission_ids: dict[str, int] = {}
    for name, description in PERMISSIONS:
        existing = conn.execute(
            sa.text("SELECT id FROM permissions WHERE name = :n"), {"n": name}
        ).scalar()
        if existing is None:
            conn.execute(
                sa.text("INSERT INTO permissions (name, description) VALUES (:n, :d)"),
                {"n": name, "d": description},
            )
            existing = conn.execute(
                sa.text("SELECT id FROM permissions WHERE name = :n"), {"n": name}
            ).scalar()
        permission_ids[name] = existing

    for role_name, permission_names in ROLE_PERMISSIONS.items():
        role_id = conn.execute(
            sa.text("SELECT id FROM roles WHERE name = :n"), {"n": role_name}
        ).scalar()
        if role_id is None:
            continue
        for permission_name in permission_names:
            permission_id = permission_ids[permission_name]
            exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"
                ),
                {"r": role_id, "p": permission_id},
            ).scalar()
            if exists is None:
                conn.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"
                    ),
                    {"r": role_id, "p": permission_id},
                )

    # -- C-2: organization_id on analysis_records --------------------------
    op.add_column("analysis_records", sa.Column("organization_id", sa.Integer(), nullable=True))

    conn.execute(
        sa.text(
            "UPDATE analysis_records SET organization_id = "
            "(SELECT organization_id FROM projects WHERE projects.id = analysis_records.project_id) "
            "WHERE project_id IS NOT NULL"
        )
    )

    unbackfilled = conn.execute(
        sa.text("SELECT COUNT(*) FROM analysis_records WHERE organization_id IS NULL")
    ).scalar()
    if unbackfilled:
        raise RuntimeError(
            f"{unbackfilled} analysis_records row(s) could not be backfilled with an "
            "organization_id (project_id NULL or dangling) -- resolve before this "
            "migration can proceed; refusing to silently leave tenant-unscoped rows."
        )

    op.alter_column("analysis_records", "organization_id", nullable=False)
    op.create_foreign_key(
        "fk_analysis_records_organization_id",
        "analysis_records",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_index(
        "ix_analysis_records_organization_id", "analysis_records", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_records_organization_id", table_name="analysis_records")
    op.drop_constraint(
        "fk_analysis_records_organization_id", "analysis_records", type_="foreignkey"
    )
    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.drop_column("organization_id")

    conn = op.get_bind()
    for name, _description in PERMISSIONS:
        permission_id = conn.execute(
            sa.text("SELECT id FROM permissions WHERE name = :n"), {"n": name}
        ).scalar()
        if permission_id is not None:
            conn.execute(
                sa.text("DELETE FROM role_permissions WHERE permission_id = :p"),
                {"p": permission_id},
            )
            conn.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": permission_id})
