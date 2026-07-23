"""RBAC permission catalog -- seeds permissions and role_permissions for
the Enterprise Domain API (Wave 2, Sprint 3).

`permissions` and `role_permissions` have existed as empty tables since
Épico 1 (migration 0002) -- RBAC was storage without behavior until this
migration + `src/services/authorization/`. Vocabulary is `resource.action`
(`DOMAIN-BLUEPRINT-RBAC.md` §2, Foundation Technical Design §4.9):
portfolio/program/project_delivery x read/write.

Role -> permission assignments follow the 4 seed roles' own descriptions
from migration 0002 (organization_admin: full access; pmo: full
visibility+governance; project_manager: operational read/write on
program+project_delivery, read-only on portfolio; viewer: read-only on
everything).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("portfolio.read", "Ler Portfolios da organização"),
    ("portfolio.write", "Criar/editar Portfolios da organização"),
    ("program.read", "Ler Programs da organização"),
    ("program.write", "Criar/editar Programs da organização"),
    ("project_delivery.read", "Ler Projects (Project Delivery) da organização"),
    ("project_delivery.write", "Criar/editar Projects (Project Delivery) da organização"),
]

ROLE_PERMISSIONS = {
    "organization_admin": [
        "portfolio.read",
        "portfolio.write",
        "program.read",
        "program.write",
        "project_delivery.read",
        "project_delivery.write",
    ],
    "pmo": [
        "portfolio.read",
        "portfolio.write",
        "program.read",
        "program.write",
        "project_delivery.read",
        "project_delivery.write",
    ],
    "project_manager": [
        "portfolio.read",
        "program.read",
        "program.write",
        "project_delivery.read",
        "project_delivery.write",
    ],
    "viewer": ["portfolio.read", "program.read", "project_delivery.read"],
}


def upgrade() -> None:
    conn = op.get_bind()

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
            # Same defensive stance as EnterpriseRepository.assign_role_in_session:
            # an install that skipped migration 0002 seeding shouldn't crash here.
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


def downgrade() -> None:
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
