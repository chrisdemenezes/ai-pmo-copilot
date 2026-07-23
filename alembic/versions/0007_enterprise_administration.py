"""Enterprise Administration -- audit_logs table + administration permissions

STRATECH V2 Wave 2, Sprint 4 (Épico 5, Nível 1 + Nível 2 per
`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`, ratified by the Founder).
`audit_logs` covers both "Auditoria" (Nível 1) and "Logs" (Nível 2) with
one structured store, not two.

New permissions: `administration.read` (organization_admin, pmo) and
`administration.write` (organization_admin only) -- matches the existing
role descriptions from migration 0002 (organization_admin: "Administra a
organização"; pmo: "Visão e governança").

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("administration.read", "Ler dados administrativos (usuários, papéis, auditoria/logs)"),
    ("administration.write", "Administrar organização, usuários e papéis"),
]

ROLE_PERMISSIONS = {
    "organization_admin": ["administration.read", "administration.write"],
    "pmo": ["administration.read"],
}


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False
    )

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

    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_organization_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
