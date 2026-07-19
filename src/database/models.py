"""Enterprise Foundation entities (STRATECH V2, Release 0.1, Épico 1).

Schema only: no authentication flow, no RBAC engine, no admin UI in this
package -- those arrive in later épicos operating on these tables. Every
tenant-scoped table carries organization_id so multi-organization isolation
is structural from day one, even though the initial operating mode is a
single main organization per installation (Founder directive, 2026-07-17).

Cross-tenant integrity that a plain FK cannot express (e.g. a membership
linking a user of org A to a project of org B) is enforced by
EnterpriseRepository -- never bypass it for writes to these tables.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from src.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    # Stable external identifier -- used by APIs, login and integrations;
    # independent of `name` after creation (0004 migration, EO-015
    # Organizational Identity Scope Correction). `name` remains purely a
    # display attribute.
    slug = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_users_org_email"),)

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)
    # "standard" | "demo" -- distinguishes the Demo Mode user from real
    # accounts without a second boolean column (Epico 2, migration 0003).
    identity_type = Column(String(20), nullable=False, default="standard")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)


class Portfolio(Base):
    """Enterprise Domain persistence (Wave 2, Domain Blueprint
    `DOMAIN-BLUEPRINT-PROJECT.md`). Root of the Portfolio -> Program ->
    Project chain -- the only table in the chain that carries
    organization_id directly; Program and Project derive their
    organization transitively (Foundation Technical Design §3/§3.10)."""

    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_portfolios_org_code"),)

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(String(1000), nullable=True)
    category = Column(String(255), nullable=True)
    executive_owner = Column(String(255), nullable=True)
    strategic_objective = Column(String(1000), nullable=True)
    status = Column(String(20), nullable=False, default="Ativo")
    health = Column(String(10), nullable=False, default="green")
    priority = Column(String(10), nullable=False, default="Média")
    start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    progress_percentage = Column(Integer, nullable=False, default=0)
    program_count = Column(Integer, nullable=False, default=0)
    project_count = Column(Integer, nullable=False, default=0)
    linked_demands = Column(Integer, nullable=False, default=0)
    linked_risks = Column(Integer, nullable=False, default=0)
    linked_issues = Column(Integer, nullable=False, default=0)
    pending_decisions = Column(Integer, nullable=False, default=0)
    sponsor = Column(String(255), nullable=True)
    pmo_owner = Column(String(255), nullable=True)
    last_updated = Column(Date, nullable=True)
    next_review = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Program(Base):
    """Belongs to exactly one Portfolio -- FK is NOT NULL by design (Domain
    Blueprint CB-002 invariant, now enforced at the schema level, not just
    by the frontend's `Program.create()`)."""

    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("portfolio_id", "code", name="uq_programs_portfolio_code"),)

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(String(1000), nullable=True)
    sponsor = Column(String(255), nullable=True)
    program_manager = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="Ativo")
    health = Column(String(10), nullable=False, default="green")
    priority = Column(String(10), nullable=False, default="Média")
    objective = Column(String(1000), nullable=True)
    start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    progress_percentage = Column(Integer, nullable=False, default=0)
    project_count = Column(Integer, nullable=False, default=0)
    linked_demands = Column(Integer, nullable=False, default=0)
    linked_risks = Column(Integer, nullable=False, default=0)
    linked_issues = Column(Integer, nullable=False, default=0)
    pending_decisions = Column(Integer, nullable=False, default=0)
    pending_actions = Column(Integer, nullable=False, default=0)
    pmo_owner = Column(String(255), nullable=True)
    last_updated = Column(Date, nullable=True)
    next_review = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Project(Base):
    """Unified per `DOMAIN-BLUEPRINT-PROJECT.md` (Opção A, Fase 1): the
    domain fields (program_id onward) extend this same Épico-1 table
    instead of a separate `projects_delivery` table, so TD-008's three
    "Project" concepts collapse toward one instead of becoming a fourth.
    Every column below is nullable -- pre-existing rows (migrated from
    legacy `project_name`, Épico 1) have none of them populated; only
    Projects created through the Enterprise Domain going forward set
    them, via `program_id`."""

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_projects_org_name"),)

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    # Exact original free-text value this Project was migrated from (0002
    # migration); NULL for the fallback project and for projects born native.
    legacy_project_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # -- Enterprise Domain fields (Wave 2) ---------------------------------
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=True, index=True)
    code = Column(String(50), nullable=True)
    description = Column(String(1000), nullable=True)
    objective = Column(String(1000), nullable=True)
    sponsor = Column(String(255), nullable=True)
    project_manager = Column(String(255), nullable=True)
    status = Column(String(20), nullable=True)
    health = Column(String(10), nullable=True)
    priority = Column(String(10), nullable=True)
    start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    progress_percentage = Column(Integer, nullable=True)
    last_updated = Column(Date, nullable=True)
    next_review = Column(Date, nullable=True)
    # Value objects not yet promoted to entities (Domain Blueprint CB-003
    # §1) -- stored as JSON, matching the frontend's Owner/Milestone[]/Team
    # shape exactly, so no data is lost by not modeling them relationally.
    owner_json = Column(JSON, nullable=True)
    milestones_json = Column(JSON, nullable=True)
    team_json = Column(JSON, nullable=True)


class UserProjectMembership(Base):
    __tablename__ = "user_project_memberships"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    role_in_project = Column(String(50), nullable=False, default="member")
