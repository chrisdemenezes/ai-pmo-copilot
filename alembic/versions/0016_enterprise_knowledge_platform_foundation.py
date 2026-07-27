"""Enterprise Knowledge Platform Fase 1 -- documents, document_versions, chunks

STRATECH V2, Wave 3 (Digital PMO Intelligence), Fase 1 -- Foundation.

Purely additive: no existing table or column is touched. Adds the 3 tables
that back `KnowledgeRepository` (`src/services/knowledge_platform/`):
`documents`, `document_versions` (one row per re-ingestion, never
overwritten) and `chunks` (the retrievable unit, carrying its embedding
vector). `chunks.organization_id` is denormalized from the owning document
so tenant-scoped similarity search never needs a join, the same technique
already used by `analysis_records.organization_id`.

Enables the `vector` (pgvector) Postgres extension -- the Vector Store
technology approved by the Founder for the Enterprise Knowledge Platform,
always behind the `KnowledgeRepository`/`VectorRepository` abstraction,
never referenced directly by domain code. `CREATE EXTENSION IF NOT EXISTS`
is idempotent: local/CI provisioning (`scripts/rc2-db.sh`, the
`pgvector/pgvector:pg16` images) already installs it ahead of time where
the connecting role isn't a superuser, so this statement is a no-op there
and a real bootstrap anywhere the extension isn't pre-installed but the
migration runs as a superuser (e.g. a managed Postgres granting one).

Downgrade drops the 3 tables but deliberately does NOT drop the `vector`
extension -- it is a shared, cheap-to-keep database-level resource, and
dropping it could break any other object created against it in the
meantime; the same "never remove more than you added" discipline already
applied by every migration since RC-2.

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 16


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)
    op.create_index(
        op.f("ix_documents_organization_id"), "documents", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_documents_project_id"), "documents", ["project_id"], unique=False)

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
    )
    op.create_index(
        op.f("ix_document_versions_id"), "document_versions", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_document_versions_document_id"),
        "document_versions",
        ["document_id"],
        unique=False,
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_version_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )
    op.create_index(op.f("ix_chunks_id"), "chunks", ["id"], unique=False)
    op.create_index(
        op.f("ix_chunks_document_version_id"), "chunks", ["document_version_id"], unique=False
    )
    op.create_index(
        op.f("ix_chunks_organization_id"), "chunks", ["organization_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_chunks_organization_id"), table_name="chunks")
    op.drop_index(op.f("ix_chunks_document_version_id"), table_name="chunks")
    op.drop_index(op.f("ix_chunks_id"), table_name="chunks")
    op.drop_table("chunks")

    op.drop_index(op.f("ix_document_versions_document_id"), table_name="document_versions")
    op.drop_index(op.f("ix_document_versions_id"), table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index(op.f("ix_documents_project_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_organization_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_id"), table_name="documents")
    op.drop_table("documents")
