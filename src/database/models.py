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
    Column,
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


class Project(Base):
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


class UserProjectMembership(Base):
    __tablename__ = "user_project_memberships"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    role_in_project = Column(String(50), nullable=False, default="member")
