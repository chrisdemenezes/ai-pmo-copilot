"""Enterprise Memory Model -- memory_records

STRATECH V2, Wave 3 (Digital PMO Intelligence), Fase 2 -- Knowledge
Services.

Purely additive: adds `memory_records`, the table backing
`EnterpriseMemoryService.classify()`/`list_by_category()`
(`src/services/knowledge_platform/enterprise_memory_service.py`). Each row
classifies an already-ingested `documents` row into one of the 5 memory
categories (documental/operacional/decisoes/aprendizados/organizacional,
`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §2) -- it never duplicates
the document's content, only references it (`document_id`) plus the
classification and when it was captured.

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017"
down_revision: Union[str, Sequence[str], None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
    )
    op.create_index(op.f("ix_memory_records_id"), "memory_records", ["id"], unique=False)
    op.create_index(
        op.f("ix_memory_records_organization_id"),
        "memory_records",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_memory_records_document_id"), "memory_records", ["document_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_memory_records_document_id"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_organization_id"), table_name="memory_records")
    op.drop_index(op.f("ix_memory_records_id"), table_name="memory_records")
    op.drop_table("memory_records")
