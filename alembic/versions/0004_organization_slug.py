"""organization slug -- stable external identifier, independent of name

STRATECH V2 Release 0.1, Épico 2 (Identity Foundation), EO-015
Organizational Identity Scope Correction.

Additive, backfillable column: every pre-existing organization receives a
slug derived from its current `name` (frozen copy of
src/database/project_identity.py's organization_slug(), same discipline
the 0002 migration already uses for normalize_project_name -- migrations
must keep producing the historical result even if the application-level
rule evolves later). Collisions across distinct names that would slugify
identically are disambiguated with a numeric suffix so the backfill can
never violate the new UNIQUE constraint. After this migration, `slug` and
`name` are independent: renaming an organization never touches its slug.

Reversible by dropping the column (and its unique constraint).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-17

"""
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _organization_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return slug or "organization"


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=255), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, name FROM organizations ORDER BY id")).fetchall()
    seen: set[str] = set()
    for row in rows:
        base = _organization_slug(row.name)
        candidate = base
        suffix = 2
        while candidate in seen:
            candidate = f"{base}-{suffix}"
            suffix += 1
        seen.add(candidate)
        bind.execute(
            sa.text("UPDATE organizations SET slug = :slug WHERE id = :id"),
            {"slug": candidate, "id": row.id},
        )

    with op.batch_alter_table("organizations") as batch_op:
        batch_op.alter_column("slug", existing_type=sa.String(length=255), nullable=False)
        batch_op.create_unique_constraint("uq_organizations_slug", ["slug"])


def downgrade() -> None:
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_constraint("uq_organizations_slug", type_="unique")
        batch_op.drop_column("slug")
