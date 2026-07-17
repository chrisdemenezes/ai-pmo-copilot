"""enterprise foundation - organizations, users, roles, projects; link analyses

STRATECH V2 Release 0.1, Épico 1 (Blueprint v2.0, ADR-V2-002/003).

Data migration rule (frozen copy of src/database/project_identity.py -- kept
inline on purpose so this migration keeps producing the historical result
even if the application rule evolves later):

1. One Project per distinct legacy analysis_records.project_name, where the
   grouping key is the name with leading/trailing whitespace stripped.
2. No case folding, no similarity merging: "Projeto ALFA" and "projeto alfa"
   become two Projects (ADR-V2-003 -- reconciliation is a future explicit
   admin action, never an automatic guess).
3. NULL, empty, or whitespace-only names map to one fallback Project named
   "(sem projeto)" with legacy_project_name NULL.
4. Project.name = the stripped key; Project.legacy_project_name = the
   stripped key; each record's original text stays untouched in
   analysis_records.project_name.
5. Every Project belongs to the default organization
   "Organização Principal" (created here, idempotently).
6. Invariants verified by tests: row count of analysis_records is identical
   before/after, and no record is left with project_id NULL.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ORGANIZATION_NAME = "Organização Principal"
FALLBACK_PROJECT_NAME = "(sem projeto)"
SEED_ROLES = [
    ("organization_admin", "Administra a organização: usuários, papéis, projetos"),
    ("pmo", "Visão e governança de todos os projetos da organização"),
    ("project_manager", "Gerencia os projetos aos quais está vinculado"),
    ("viewer", "Acesso somente leitura ao escopo autorizado"),
]


def upgrade() -> None:
    # -- 1. Structural tables ---------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_organizations_id"), "organizations", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_permissions_id"), "permissions", ["id"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legacy_project_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("organization_id", "name", name="uq_projects_org_name"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(
        op.f("ix_projects_organization_id"), "projects", ["organization_id"], unique=False
    )

    op.create_table(
        "user_project_memberships",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("role_in_project", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "project_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )

    # -- 2. analysis_records.project_id (batch mode: SQLite-safe) ---------
    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            op.f("ix_analysis_records_project_id"), ["project_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_analysis_records_project_id", "projects", ["project_id"], ["id"]
        )

    # -- 3. Seeds (idempotent) --------------------------------------------
    conn = op.get_bind()

    org_id = conn.execute(
        sa.text("SELECT id FROM organizations WHERE name = :n"),
        {"n": DEFAULT_ORGANIZATION_NAME},
    ).scalar()
    if org_id is None:
        conn.execute(
            sa.text(
                "INSERT INTO organizations (name, created_at) "
                "VALUES (:n, CURRENT_TIMESTAMP)"
            ),
            {"n": DEFAULT_ORGANIZATION_NAME},
        )
        org_id = conn.execute(
            sa.text("SELECT id FROM organizations WHERE name = :n"),
            {"n": DEFAULT_ORGANIZATION_NAME},
        ).scalar()

    for role_name, description in SEED_ROLES:
        exists = conn.execute(
            sa.text("SELECT id FROM roles WHERE name = :n"), {"n": role_name}
        ).scalar()
        if exists is None:
            conn.execute(
                sa.text("INSERT INTO roles (name, description) VALUES (:n, :d)"),
                {"n": role_name, "d": description},
            )

    # -- 4. Data migration: one Project per distinct legacy name ----------
    rows = conn.execute(
        sa.text("SELECT DISTINCT project_name FROM analysis_records")
    ).fetchall()

    def _key(raw):
        if raw is None:
            return None
        stripped = raw.strip()
        return stripped if stripped else None

    # Grouping computed in Python so the whitespace rule is identical across
    # SQLite and Postgres (SQL TRIM semantics differ between backends).
    distinct_keys: dict[str | None, list] = {}
    for (raw_name,) in rows:
        distinct_keys.setdefault(_key(raw_name), []).append(raw_name)

    for key, originals in distinct_keys.items():
        name = key if key is not None else FALLBACK_PROJECT_NAME
        project_id = conn.execute(
            sa.text(
                "SELECT id FROM projects WHERE organization_id = :o AND name = :n"
            ),
            {"o": org_id, "n": name},
        ).scalar()
        if project_id is None:
            conn.execute(
                sa.text(
                    "INSERT INTO projects "
                    "(organization_id, name, legacy_project_name, created_at) "
                    "VALUES (:o, :n, :l, CURRENT_TIMESTAMP)"
                ),
                {"o": org_id, "n": name, "l": key},
            )
            project_id = conn.execute(
                sa.text(
                    "SELECT id FROM projects WHERE organization_id = :o AND name = :n"
                ),
                {"o": org_id, "n": name},
            ).scalar()
        for original in originals:
            if original is None:
                conn.execute(
                    sa.text(
                        "UPDATE analysis_records SET project_id = :p "
                        "WHERE project_name IS NULL"
                    ),
                    {"p": project_id},
                )
            else:
                conn.execute(
                    sa.text(
                        "UPDATE analysis_records SET project_id = :p "
                        "WHERE project_name = :orig"
                    ),
                    {"p": project_id, "orig": original},
                )


def downgrade() -> None:
    """Reverses everything 0002 added. Lossless for V1: each record's
    original project_name column was never modified, so dropping project_id
    restores the exact pre-0002 behavior."""
    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.drop_constraint("fk_analysis_records_project_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_analysis_records_project_id"))
        batch_op.drop_column("project_id")

    op.drop_table("user_project_memberships")
    op.drop_index(op.f("ix_projects_organization_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_permissions_id"), table_name="permissions")
    op.drop_table("permissions")
    op.drop_index(op.f("ix_roles_id"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_organizations_id"), table_name="organizations")
    op.drop_table("organizations")
