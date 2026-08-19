"""API Keys -- organization-scoped credential for programmatic API access

STRATECH V2 Wave 2, Enterprise Administration (D-051, Superseding Decision).

The original `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` deferred API
Keys as depending on a future Integration Hub (Wave 4) decision -- an
architecturally backwards dependency (a foundational credential primitive
made to wait on a future consumer). `DOMAIN-BLUEPRINT-API-KEYS.md`
corrects this: Enterprise Administration owns API Keys outright; any
future Integration Hub consumes them, never the reverse.

`api_keys` stores only a hash of the secret (`hashed_secret`, Argon2 via
the same `Argon2PasswordHasher` already used for user passwords -- no new
hashing infrastructure) plus a short `key_prefix` for display. The
plaintext key is shown to the admin exactly once, at creation.

New permission `api_keys.manage` (organization_admin only -- issuing a
credential that authenticates as its creator is at least as sensitive as
`administration.write`).

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("api_keys.manage", "Criar, listar e revogar API Keys da organização"),
]

ROLE_PERMISSIONS = {
    "organization_admin": ["api_keys.manage"],
}


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=20), nullable=False),
        sa.Column("hashed_secret", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_api_keys_id"), "api_keys", ["id"], unique=False)
    op.create_index(
        op.f("ix_api_keys_organization_id"), "api_keys", ["organization_id"], unique=False
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

    op.drop_index(op.f("ix_api_keys_organization_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_id"), table_name="api_keys")
    op.drop_table("api_keys")
