"""Enterprise Administration repository (Wave 2, Sprint 4).

Sibling of `EnterpriseRepository`/`DomainRepository`, not a growth of
either -- same rationale as `DomainRepository`'s own docstring (TD-003:
avoid an indefinitely growing class; a new sibling per Bounded Context is
the established alternative). Covers Épico 5 Nível 1 (Organizations/Users/
Roles read, Auditoria) and the ratified Nível 2 subset that needed no new
domain concept (Logs, served by the same audit_logs table as Auditoria).

Nível 2's "Sessões" and "Segurança" are deliberately NOT here:
`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §2 described Sessões as a
"painel é só leitura+revogação sobre o que já existe" -- but no
server-side session store exists (`auth_service.py`'s `logout()`
docstring: "No server-side session store exists yet, TDS Section 15.2" --
sessions are a stateless HMAC-signed cookie). Listing/revoking sessions
the Blueprint described is not buildable without a new session-store
component, a bigger scope than "extensão de baixo risco" assumed --
correction registered in the Decision Log, not silently implemented as a
fake list. "Configurações" stays out per the Blueprint's own deferral
(needs product scope definition first).
"""
import logging

from sqlalchemy.orm import sessionmaker

from src.database.models import (
    AuditLog,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)


class AdministrationRepository:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    # -- Organization ------------------------------------------------------

    def get_organization(self, organization_id: int) -> Organization | None:
        with self._session_factory() as session:
            return session.get(Organization, organization_id)

    def update_organization_name(self, organization_id: int, name: str) -> Organization | None:
        """Renames the organization -- `slug` is never touched (EO-015:
        stable external identifier, independent of `name` once created)."""
        with self._session_factory() as session:
            org = session.get(Organization, organization_id)
            if org is None:
                return None
            org.name = name
            session.commit()
            session.refresh(org)
            logger.info("Renamed organization id=%s to name=%s", organization_id, name)
            return org

    # -- Users -------------------------------------------------------------

    def list_users_by_organization(self, organization_id: int) -> list[User]:
        with self._session_factory() as session:
            users = (
                session.query(User)
                .filter(User.organization_id == organization_id)
                .order_by(User.email)
                .all()
            )
            logger.info("Listed %d users organization_id=%s", len(users), organization_id)
            return users

    # -- Roles / Permissions (global catalog, per Épico 1) ------------------

    def list_roles(self) -> list[Role]:
        with self._session_factory() as session:
            return session.query(Role).order_by(Role.name).all()

    def list_permissions_for_role(self, role_id: int) -> list[Permission]:
        with self._session_factory() as session:
            return (
                session.query(Permission)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .filter(RolePermission.role_id == role_id)
                .order_by(Permission.name)
                .all()
            )

    def assign_role(self, user_id: int, organization_id: int, role_name: str) -> User | None:
        """Standalone (not `_in_session`) counterpart of
        `EnterpriseRepository.assign_role_in_session` -- verifies the user
        belongs to the caller's organization first (same not-found-not-yours
        discipline as `DomainService`), and is idempotent (assigning a role
        the user already has is a no-op, not a duplicate row)."""
        with self._session_factory() as session:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.organization_id == organization_id)
                .one_or_none()
            )
            if user is None:
                return None
            role = session.query(Role).filter(Role.name == role_name).one_or_none()
            if role is None:
                raise ValueError(f"Role {role_name!r} does not exist")
            already_has = (
                session.query(UserRole)
                .filter(UserRole.user_id == user_id, UserRole.role_id == role.id)
                .one_or_none()
            )
            if already_has is None:
                session.add(UserRole(user_id=user_id, role_id=role.id))
                session.commit()
                session.refresh(user)
                logger.info("Assigned role=%s to user_id=%s", role_name, user_id)
            return user

    # -- Audit Log (also serves as "Logs", Nível 2) -------------------------

    def record_audit(
        self,
        organization_id: int,
        actor_user_id: int,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        details: dict | None = None,
    ) -> int:
        with self._session_factory() as session:
            entry = AuditLog(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            logger.info(
                "Audit action=%s entity_type=%s entity_id=%s organization_id=%s actor_user_id=%s",
                action,
                entity_type,
                entity_id,
                organization_id,
                actor_user_id,
            )
            return entry.id

    def list_audit_log(self, organization_id: int, limit: int = 50) -> list[AuditLog]:
        with self._session_factory() as session:
            return (
                session.query(AuditLog)
                .filter(AuditLog.organization_id == organization_id)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
