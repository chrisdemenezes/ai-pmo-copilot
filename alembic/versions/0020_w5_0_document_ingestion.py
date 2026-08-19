"""Wave 5, Epic W5-0 -- Document Ingestion: knowledge.read/knowledge.write

STRATECH V2, Wave 5 (Enterprise Advisors), Epic W5-0 -- Document
Ingestion. Purely additive: no new table (Technical Design
`TECHNICAL-DESIGN-W5-0-DOCUMENT-INGESTION.md` §4 -- `documents`/
`document_versions`/`chunks` already exist since Wave 3 Fase 1, migration
0016). Adds only the two permissions the new `/documents` routes require,
same seeding pattern as migration 0010 (`intelligence.read`/
`intelligence.write`): `knowledge.read` for all 4 seed roles (browsing
ingested documents is no more sensitive than browsing analyses),
`knowledge.write` for the same 3 roles that already hold
`intelligence.write` (organization_admin, pmo, project_manager); viewer
stays read-only.

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020"
down_revision: Union[str, Sequence[str], None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("knowledge.read", "Consultar documentos e status de indexação da Knowledge Platform"),
    ("knowledge.write", "Enviar e reindexar documentos na Knowledge Platform"),
]

ROLE_PERMISSIONS = {
    "organization_admin": ["knowledge.read", "knowledge.write"],
    "pmo": ["knowledge.read", "knowledge.write"],
    "project_manager": ["knowledge.read", "knowledge.write"],
    "viewer": ["knowledge.read"],
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
