"""Production Embedding Provider: vector(16) -> vector(1024) + provenance

STRATECH V2, Wave 7 (Enterprise Readiness), W7-1 -- Production Embedding
Provider Approval (Founder Decision, D-177): Voyage AI (`voyage-4`,
dimension 1024) replaces the `MockEmbeddingProvider` dimension-16
placeholder that has been in place since migration 0016. Per the
Technical Design (`TECHNICAL-DESIGN-PRODUCTION-EMBEDDING-CONTRACT-VECTOR-MIGRATION.md`
S6) and this Founder Decision itself: existing `chunks.embedding` rows
carry only Mock vectors with zero semantic value (no real production RAG
has ever been validated against them) -- deleted here rather than
migrated/preserved, since a 16-dimension vector cannot be reinterpreted
as a 1024-dimension vector by any lossless transformation. Any document
already ingested keeps its `document_versions.content` intact (never
touched by this migration) and can be reindexed against the new provider
once one is configured.

Also adds minimal proveniencia (Founder Decision D-175/D-177):
`embedding_provider`/`embedding_model`, nullable string columns -- no
versioning table, no multi-model coexistence mechanism (rejected in the
Technical Design as unneeded abstraction).

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0021"
down_revision: Union[str, Sequence[str], None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_EMBEDDING_DIM = 16
NEW_EMBEDDING_DIM = 1024


def upgrade() -> None:
    # Existing chunks (if any) carry only Mock vectors with zero semantic
    # value -- deleted rather than migrated, since no lossless conversion
    # from 16 to 1024 dimensions exists. document_versions.content (the
    # source text) is never touched, so any document can be reindexed.
    op.execute("DELETE FROM chunks")
    op.drop_column("chunks", "embedding")
    op.add_column("chunks", sa.Column("embedding", Vector(NEW_EMBEDDING_DIM), nullable=False))
    op.add_column("chunks", sa.Column("embedding_provider", sa.String(length=64), nullable=True))
    op.add_column("chunks", sa.Column("embedding_model", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "embedding_model")
    op.drop_column("chunks", "embedding_provider")
    op.execute("DELETE FROM chunks")
    op.drop_column("chunks", "embedding")
    op.add_column("chunks", sa.Column("embedding", Vector(OLD_EMBEDDING_DIM), nullable=False))
