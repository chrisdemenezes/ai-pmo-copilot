"""Enterprise Administration repository (Wave 2, Sprint 4).

Sibling of `EnterpriseRepository`/`DomainRepository`, not a growth of
either -- same rationale as `DomainRepository`'s own docstring (TD-003:
avoid an indefinitely growing class; a new sibling per Bounded Context is
the established alternative). Covers Épico 5 Nível 1 (Organizations/Users/
Roles read, Auditoria) and the ratified Nível 2 subset that needed no new
domain concept (Logs, served by the same audit_logs table as Auditoria).

"Sessões" (item 5 of the Wave Completion Review retrospective, resolving
TD-010) is implemented below alongside API Keys -- the session store this
docstring used to say didn't exist. "Configurações" stays out per the
Blueprint's own deferral (D-052: no functional scope defined anywhere in
the repository, not an architectural or business-model block)."""
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.database.enterprise_repository import (
    EmailConflictError,
    EnterpriseRepository,
    LastActiveAdminError,
    SelfDeactivationError,
)
from src.database.models import (
    ApiKey,
    AuditLog,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserSession,
)
from src.services.identity.email_normalization import normalize_email

logger = logging.getLogger(__name__)

ADMIN_ROLE_NAME = "organization_admin"


class AdministrationRepository:
    def __init__(self, session_factory: sessionmaker, enterprise: EnterpriseRepository):
        self._session_factory = session_factory
        self._enterprise = enterprise

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

    def get_user(self, user_id: int, organization_id: int) -> User | None:
        with self._session_factory() as session:
            return (
                session.query(User)
                .filter(User.id == user_id, User.organization_id == organization_id)
                .one_or_none()
            )

    def create_user(
        self,
        organization_id: int,
        email: str,
        display_name: str,
        password_hash: str,
        role_name: str,
    ) -> User:
        """Creates the user and assigns the initial role in one
        transaction (Technical Design §3) -- if the role does not exist,
        neither the user nor the role assignment is persisted (same
        all-or-nothing guarantee `AuthService.bootstrap_administrator`
        already relies on for `create_user_in_session` +
        `assign_role_in_session`, reused here rather than duplicated).

        Unlike `assign_role_in_session`'s bootstrap-only fallback (which
        creates an unknown role on demand for cold-start installs), an
        admin-supplied role name here must already exist in the catalog --
        checked explicitly so a typo creates a 400, never a new role."""
        normalized_email = normalize_email(email)
        with self._session_factory() as session:
            if session.query(Role).filter(Role.name == role_name).one_or_none() is None:
                raise ValueError(f"Role {role_name!r} does not exist")
            try:
                user = self._enterprise.create_user_in_session(
                    session,
                    organization_id=organization_id,
                    email=normalized_email,
                    display_name=display_name,
                    password_hash=password_hash,
                )
                self._enterprise.assign_role_in_session(session, user.id, role_name)
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise EmailConflictError(
                    f"Email {email!r} already exists in this organization"
                ) from exc
            session.refresh(user)
            logger.info(
                "Created user id=%s organization_id=%s role=%s",
                user.id,
                organization_id,
                role_name,
            )
            return user

    def update_user(
        self,
        user_id: int,
        organization_id: int,
        email: str | None = None,
        display_name: str | None = None,
    ) -> tuple[User, dict, dict] | None:
        """Returns (user, before, after) so the caller can audit the exact
        state transition. Only email/display_name are accepted -- there is
        no password parameter here at all, so a plaintext credential can
        never reach this method, let alone the audit log it feeds."""
        with self._session_factory() as session:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.organization_id == organization_id)
                .one_or_none()
            )
            if user is None:
                return None
            before = {"email": user.email, "display_name": user.display_name}
            if email is not None:
                user.email = normalize_email(email)
            if display_name is not None:
                user.display_name = display_name
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise EmailConflictError(
                    f"Email {email!r} already exists in this organization"
                ) from exc
            session.refresh(user)
            after = {"email": user.email, "display_name": user.display_name}
            logger.info("Updated user id=%s organization_id=%s", user_id, organization_id)
            return user, before, after

    def _lock_active_admin_user_ids(self, session, organization_id: int) -> list[int]:
        """Row-locks (`SELECT ... FOR UPDATE`) every active
        `organization_admin` user in the organization, closing the race
        between two concurrent requests that could otherwise both pass a
        naive pre-check and leave the organization with zero admins."""
        rows = (
            session.query(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .filter(
                User.organization_id == organization_id,
                User.is_active.is_(True),
                Role.name == ADMIN_ROLE_NAME,
            )
            .with_for_update(of=User)
            .all()
        )
        return [row[0] for row in rows]

    def set_user_active(
        self,
        user_id: int,
        organization_id: int,
        is_active: bool,
        actor_user_id: int,
    ) -> User | None:
        if not is_active and user_id == actor_user_id:
            raise SelfDeactivationError("An administrator cannot deactivate their own account")
        with self._session_factory() as session:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.organization_id == organization_id)
                .one_or_none()
            )
            if user is None:
                return None
            before_active = user.is_active
            if not is_active and before_active:
                has_admin_role = (
                    session.query(UserRole)
                    .join(Role, Role.id == UserRole.role_id)
                    .filter(UserRole.user_id == user_id, Role.name == ADMIN_ROLE_NAME)
                    .first()
                    is not None
                )
                if has_admin_role:
                    locked_ids = self._lock_active_admin_user_ids(session, organization_id)
                    if len(locked_ids) <= 1:
                        raise LastActiveAdminError(
                            "Cannot deactivate the last active administrator of this organization"
                        )
            user.is_active = is_active
            session.commit()
            session.refresh(user)
            logger.info(
                "Set is_active=%s for user_id=%s organization_id=%s",
                is_active,
                user_id,
                organization_id,
            )
            return user

    def remove_role(
        self, user_id: int, organization_id: int, role_name: str, actor_user_id: int
    ) -> User | None:
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
            if role_name == ADMIN_ROLE_NAME and user.is_active:
                locked_ids = self._lock_active_admin_user_ids(session, organization_id)
                if len(locked_ids) <= 1 and user_id in locked_ids:
                    raise LastActiveAdminError(
                        "Cannot remove the last active administrator's role"
                    )
            user_role = (
                session.query(UserRole)
                .filter(UserRole.user_id == user_id, UserRole.role_id == role.id)
                .one_or_none()
            )
            if user_role is not None:
                session.delete(user_role)
                session.commit()
                session.refresh(user)
                logger.info(
                    "Removed role=%s from user_id=%s organization_id=%s",
                    role_name,
                    user_id,
                    organization_id,
                )
            return user

    # -- Roles / Permissions (global catalog, per Épico 1) ------------------

    def list_roles(self) -> list[Role]:
        with self._session_factory() as session:
            return session.query(Role).order_by(Role.name).all()

    def list_role_names_by_user(self, organization_id: int) -> dict[int, list[str]]:
        """Bulk (whole org, one query) role-name index -- lets the
        Frontend's user list render/filter by role without an N+1 request
        per row, and without changing `UserResponse`'s shape."""
        with self._session_factory() as session:
            rows = (
                session.query(User.id, Role.name)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .filter(User.organization_id == organization_id)
                .order_by(User.id, Role.name)
                .all()
            )
            result: dict[int, list[str]] = {}
            for user_id, role_name in rows:
                result.setdefault(user_id, []).append(role_name)
            return result

    def list_roles_for_user(self, user_id: int, organization_id: int) -> list[Role] | None:
        """Org-scoped (same not-found-not-yours discipline as every other
        per-user lookup here) -- the Frontend needs this to render which
        roles a user already has, so it can offer "assign" vs. "remove"."""
        with self._session_factory() as session:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.organization_id == organization_id)
                .one_or_none()
            )
            if user is None:
                return None
            return (
                session.query(Role)
                .join(UserRole, UserRole.role_id == Role.id)
                .filter(UserRole.user_id == user_id)
                .order_by(Role.name)
                .all()
            )

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

    # -- API Keys (D-051) ----------------------------------------------

    def create_api_key(
        self,
        organization_id: int,
        created_by_user_id: int,
        name: str,
        key_prefix: str,
        hashed_secret: str,
    ) -> ApiKey:
        with self._session_factory() as session:
            api_key = ApiKey(
                organization_id=organization_id,
                created_by_user_id=created_by_user_id,
                name=name,
                key_prefix=key_prefix,
                hashed_secret=hashed_secret,
            )
            session.add(api_key)
            session.commit()
            session.refresh(api_key)
            logger.info(
                "Created api_key id=%s organization_id=%s created_by_user_id=%s",
                api_key.id,
                organization_id,
                created_by_user_id,
            )
            return api_key

    def list_api_keys(self, organization_id: int) -> list[ApiKey]:
        with self._session_factory() as session:
            return (
                session.query(ApiKey)
                .filter(ApiKey.organization_id == organization_id)
                .order_by(ApiKey.created_at.desc())
                .all()
            )

    def get_api_key(self, api_key_id: int, organization_id: int) -> ApiKey | None:
        with self._session_factory() as session:
            return (
                session.query(ApiKey)
                .filter(ApiKey.id == api_key_id, ApiKey.organization_id == organization_id)
                .one_or_none()
            )

    def revoke_api_key(self, api_key_id: int, organization_id: int) -> ApiKey | None:
        with self._session_factory() as session:
            api_key = (
                session.query(ApiKey)
                .filter(ApiKey.id == api_key_id, ApiKey.organization_id == organization_id)
                .one_or_none()
            )
            if api_key is None or api_key.revoked_at is not None:
                return None
            api_key.revoked_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(api_key)
            logger.info("Revoked api_key id=%s organization_id=%s", api_key_id, organization_id)
            return api_key

    def list_active_api_keys_by_prefix(self, key_prefix: str) -> list[ApiKey]:
        """Candidates for `AuthService`-style credential verification: never
        looked up by id (the caller doesn't have one, only the raw key), and
        `hashed_secret` can't be queried by equality -- narrowing by the
        cheap, non-secret `key_prefix` keeps this to a handful of rows for
        `Argon2PasswordHasher.verify` to check, exactly like email lookup
        narrows password verification instead of scanning every user."""
        with self._session_factory() as session:
            return (
                session.query(ApiKey)
                .filter(ApiKey.key_prefix == key_prefix, ApiKey.revoked_at.is_(None))
                .all()
            )

    def touch_api_key_last_used(self, api_key_id: int) -> None:
        with self._session_factory() as session:
            api_key = session.get(ApiKey, api_key_id)
            if api_key is None:
                return
            api_key.last_used_at = datetime.now(timezone.utc)
            session.commit()

    # -- Sessions (item 5, resolves TD-010) -----------------------------

    def create_session(
        self, session_id: str, user_id: int, organization_id: int
    ) -> UserSession:
        with self._session_factory() as db_session:
            user_session = UserSession(
                id=session_id, user_id=user_id, organization_id=organization_id
            )
            db_session.add(user_session)
            db_session.commit()
            db_session.refresh(user_session)
            logger.info(
                "Created session id=%s user_id=%s organization_id=%s",
                session_id,
                user_id,
                organization_id,
            )
            return user_session

    def list_active_sessions(self, organization_id: int) -> list[UserSession]:
        with self._session_factory() as db_session:
            return (
                db_session.query(UserSession)
                .filter(
                    UserSession.organization_id == organization_id,
                    UserSession.revoked_at.is_(None),
                )
                .order_by(UserSession.created_at.desc())
                .all()
            )

    def get_session(self, session_id: str) -> UserSession | None:
        with self._session_factory() as db_session:
            return db_session.get(UserSession, session_id)

    def revoke_session(self, session_id: str) -> UserSession | None:
        """Returns None for both "not found" and "already revoked" -- same
        idempotency guard as `revoke_api_key`. Not organization-scoped at
        this layer -- `session_id` is a globally unique, unguessable UUID
        (unlike `ApiKey.id`, a small sequential integer that needs a
        compound scope); tenant-isolation for the admin-facing revoke route
        is enforced one level up, in `AdministrationService`, by checking
        `get_session(...).organization_id` before calling this."""
        with self._session_factory() as db_session:
            user_session = db_session.get(UserSession, session_id)
            if user_session is None or user_session.revoked_at is not None:
                return None
            user_session.revoked_at = datetime.now(timezone.utc)
            db_session.commit()
            db_session.refresh(user_session)
            logger.info("Revoked session id=%s", session_id)
            return user_session

    def is_session_revoked(self, session_id: str) -> bool:
        """True only when a row exists AND has been explicitly revoked --
        an unknown session_id (e.g. one that predates this table, or a
        fabricated id such as a test fixture) is treated as still active,
        never as revoked. This is what lets revocation enforcement be added
        to `require_permission` without retroactively breaking any session
        that isn't tracked by this store."""
        with self._session_factory() as db_session:
            user_session = db_session.get(UserSession, session_id)
            return user_session is not None and user_session.revoked_at is not None

    def touch_session_last_seen(self, session_id: str) -> None:
        with self._session_factory() as db_session:
            user_session = db_session.get(UserSession, session_id)
            if user_session is None:
                return
            user_session.last_seen_at = datetime.now(timezone.utc)
            db_session.commit()
