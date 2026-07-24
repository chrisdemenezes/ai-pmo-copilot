"""Application layer for the Enterprise Administration API (Wave 2, Sprint 4).

Same split as `DomainService`: routes stay thin adapters, mutations
record an audit entry here (not in the route, not in the repository) so
every write path goes through exactly one place that remembers to audit.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from src.database.models import (
    ApiKey,
    AuditLog,
    Invitation,
    Organization,
    Permission,
    Role,
    User,
    UserSession,
)
from src.database.repository import AnalysisRepository
from src.services.identity.password_hashing import Argon2PasswordHasher
from src.services.notifications.interfaces import NotificationProvider
from src.services.notifications.noop_provider import NoOpNotificationProvider

logger = logging.getLogger(__name__)

API_KEY_PREFIX = "sk_live_"
# Displayed forever in the list view so an admin can tell keys apart
# without the full secret ever being shown again after creation.
API_KEY_DISPLAY_PREFIX_LENGTH = len(API_KEY_PREFIX) + 8

# Invitations (item 6, Convites -- D-054).
INVITATION_TOKEN_PREFIX = "inv_"
INVITATION_DISPLAY_PREFIX_LENGTH = len(INVITATION_TOKEN_PREFIX) + 8
# Implementation default, not a documented product behavior: the "Expirado"
# state named by the Founder's decision requires that a validity exist; the
# concrete duration is a sensible default (same nature as a Session's 12h
# TTL), documented in TECHNICAL-DESIGN-INVITATIONS.md §1.
INVITATION_TTL = timedelta(days=7)


class AdministrationService:
    def __init__(
        self,
        repository: AnalysisRepository,
        password_hasher: Argon2PasswordHasher | None = None,
        notification_provider: NotificationProvider | None = None,
    ) -> None:
        self._repository = repository
        # Only User Management's create_user needs this -- the plaintext
        # password lives only as a local variable inside that one method,
        # never reaching the repository, the audit log, or a log line.
        self._password_hasher = password_hasher or Argon2PasswordHasher()
        # Delivery seam for Convites (D-054). NoOp by default -- no concrete
        # provider is chosen; the invitation token is returned once at
        # creation for manual delivery. A real provider implements the same
        # Protocol without this class changing.
        self._notifications = notification_provider or NoOpNotificationProvider()

    # -- Organization ------------------------------------------------------

    def get_organization(self, organization_id: int) -> Organization | None:
        return self._repository.administration.get_organization(organization_id)

    def rename_organization(
        self, organization_id: int, name: str, actor_user_id: int
    ) -> Organization | None:
        organization = self._repository.administration.update_organization_name(
            organization_id, name
        )
        if organization is None:
            return None
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "organization.renamed",
            "organization",
            organization_id,
            {"name": name},
        )
        return organization

    # -- Users ---------------------------------------------------------

    def list_users(self, organization_id: int) -> list[User]:
        return self._repository.administration.list_users_by_organization(organization_id)

    def get_user(self, user_id: int, organization_id: int) -> User | None:
        return self._repository.administration.get_user(user_id, organization_id)

    def create_user(
        self,
        organization_id: int,
        email: str,
        display_name: str,
        password: str,
        role_name: str,
        actor_user_id: int,
    ) -> User:
        """`password` is the initial credential the admin sets directly
        (Technical Design §1 -- no invite/reset flow). Hashed here, in this
        one place, before it ever reaches the repository or the audit log."""
        password_hash = self._password_hasher.hash(password)
        user = self._repository.administration.create_user(
            organization_id, email, display_name, password_hash, role_name
        )
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "user.created",
            "user",
            user.id,
            {"email": user.email, "display_name": user.display_name},
        )
        return user

    def update_user(
        self,
        user_id: int,
        organization_id: int,
        actor_user_id: int,
        email: str | None = None,
        display_name: str | None = None,
    ) -> User | None:
        result = self._repository.administration.update_user(
            user_id, organization_id, email=email, display_name=display_name
        )
        if result is None:
            return None
        user, before, after = result
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "user.updated",
            "user",
            user_id,
            {"before": before, "after": after},
        )
        return user

    def set_user_active(
        self, user_id: int, organization_id: int, is_active: bool, actor_user_id: int
    ) -> User | None:
        before_user = self._repository.administration.get_user(user_id, organization_id)
        before_active = before_user.is_active if before_user else None
        user = self._repository.administration.set_user_active(
            user_id, organization_id, is_active, actor_user_id
        )
        if user is None:
            return None
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "user.activated" if is_active else "user.deactivated",
            "user",
            user_id,
            {"before": {"is_active": before_active}, "after": {"is_active": is_active}},
        )
        return user

    # -- Roles / Permissions -----------------------------------------------

    def list_roles(self) -> list[Role]:
        return self._repository.administration.list_roles()

    def list_permissions_for_role(self, role_id: int) -> list[Permission]:
        return self._repository.administration.list_permissions_for_role(role_id)

    def list_roles_for_user(self, user_id: int, organization_id: int) -> list[Role] | None:
        return self._repository.administration.list_roles_for_user(user_id, organization_id)

    def list_role_names_by_user(self, organization_id: int) -> dict[int, list[str]]:
        return self._repository.administration.list_role_names_by_user(organization_id)

    def assign_role(
        self, user_id: int, organization_id: int, role_name: str, actor_user_id: int
    ) -> User | None:
        user = self._repository.administration.assign_role(user_id, organization_id, role_name)
        if user is None:
            return None
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "role.assigned",
            "user",
            user_id,
            {"role_name": role_name},
        )
        return user

    def remove_role(
        self, user_id: int, organization_id: int, role_name: str, actor_user_id: int
    ) -> User | None:
        user = self._repository.administration.remove_role(
            user_id, organization_id, role_name, actor_user_id
        )
        if user is None:
            return None
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "role.removed",
            "user",
            user_id,
            {"role_name": role_name},
        )
        return user

    # -- Audit Log (also serves as "Logs") ----------------------------------

    def list_audit_log(self, organization_id: int, limit: int = 50) -> list[AuditLog]:
        return self._repository.administration.list_audit_log(organization_id, limit)

    # -- API Keys (D-051) ----------------------------------------------
    #
    # A foundational Enterprise Administration credential, not an
    # Integration Hub artifact (see DOMAIN-BLUEPRINT-API-KEYS.md). An API
    # Key authenticates as the user who created it -- `authenticate_api_key`
    # below is consumed by `get_request_context`'s second auth path, and
    # every permission check downstream is the exact same RBAC check a
    # session-authenticated request for that user would get.

    def create_api_key(self, organization_id: int, name: str, actor_user_id: int) -> tuple[ApiKey, str]:
        """Returns (ApiKey, plaintext_key). The plaintext is never stored --
        this is the only place in the system it exists outside the caller's
        response, and the caller must display it to the admin exactly once."""
        plaintext_key = API_KEY_PREFIX + secrets.token_urlsafe(32)
        hashed_secret = self._password_hasher.hash(plaintext_key)
        api_key = self._repository.administration.create_api_key(
            organization_id,
            actor_user_id,
            name,
            plaintext_key[:API_KEY_DISPLAY_PREFIX_LENGTH],
            hashed_secret,
        )
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "api_key.created",
            "api_key",
            api_key.id,
            {"name": name, "key_prefix": api_key.key_prefix},
        )
        return api_key, plaintext_key

    def list_api_keys(self, organization_id: int) -> list[ApiKey]:
        return self._repository.administration.list_api_keys(organization_id)

    def revoke_api_key(
        self, api_key_id: int, organization_id: int, actor_user_id: int
    ) -> ApiKey | None:
        api_key = self._repository.administration.revoke_api_key(api_key_id, organization_id)
        if api_key is None:
            return None
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "api_key.revoked",
            "api_key",
            api_key_id,
            {"name": api_key.name},
        )
        return api_key

    def authenticate_api_key(self, plaintext_key: str) -> ApiKey | None:
        """Never logs or raises on the plaintext -- an unrecognized or
        revoked key is indistinguishable from a wrong one, same discipline
        `AuthService` already applies to passwords."""
        if not plaintext_key.startswith(API_KEY_PREFIX):
            return None
        prefix = plaintext_key[:API_KEY_DISPLAY_PREFIX_LENGTH]
        candidates = self._repository.administration.list_active_api_keys_by_prefix(prefix)
        for candidate in candidates:
            if self._password_hasher.verify(plaintext_key, candidate.hashed_secret):
                self._repository.administration.touch_api_key_last_used(candidate.id)
                return candidate
        return None

    # -- Sessions (item 5, resolves TD-010) -----------------------------

    def list_active_sessions(self, organization_id: int) -> list[UserSession]:
        return self._repository.administration.list_active_sessions(organization_id)

    def revoke_session(
        self, session_id: str, organization_id: int, actor_user_id: int
    ) -> UserSession | None:
        """Tenant isolation is enforced here, not in the repository: a
        session_id belonging to another organization (or one that doesn't
        exist / is already revoked) returns None, mapped to 404 by the
        route -- an admin can never revoke a session outside their own org
        even though `session_id` is globally unique."""
        existing = self._repository.administration.get_session(session_id)
        if existing is None or existing.organization_id != organization_id:
            return None
        user_session = self._repository.administration.revoke_session(session_id)
        if user_session is None:
            return None
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "session.revoked",
            "session",
            None,
            {"session_id": session_id, "user_id": user_session.user_id},
        )
        return user_session

    # -- Invitations (item 6, Convites -- D-054) ------------------------

    def create_invitation(
        self, organization_id: int, email: str, role_name: str, actor_user_id: int
    ) -> tuple[Invitation, str]:
        """Returns (Invitation, plaintext_token). The plaintext token is
        never stored -- this is the only place it exists outside the
        caller's response, delivered to the admin exactly once for manual
        (or, later, provider-automated) delivery. The NotificationProvider
        is invoked here; today it is a NoOp, so nothing is sent -- the
        returned token is the delivery path."""
        plaintext_token = INVITATION_TOKEN_PREFIX + secrets.token_urlsafe(32)
        hashed_token = self._password_hasher.hash(plaintext_token)
        expires_at = datetime.now(timezone.utc) + INVITATION_TTL
        invitation = self._repository.administration.create_invitation(
            organization_id=organization_id,
            email=email,
            role_name=role_name,
            invited_by_user_id=actor_user_id,
            token_prefix=plaintext_token[:INVITATION_DISPLAY_PREFIX_LENGTH],
            hashed_token=hashed_token,
            expires_at=expires_at,
        )
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "invitation.created",
            "invitation",
            invitation.id,
            {"email": invitation.email, "role_name": role_name},
        )
        self._notifications.notify_invitation_created(invitation, plaintext_token)
        return invitation, plaintext_token

    def list_invitations(self, organization_id: int) -> list[Invitation]:
        return self._repository.administration.list_invitations(organization_id)

    def cancel_invitation(
        self, invitation_id: int, organization_id: int, actor_user_id: int
    ) -> Invitation | None:
        invitation = self._repository.administration.cancel_invitation(
            invitation_id, organization_id
        )
        if invitation is None:
            return None
        self._repository.administration.record_audit(
            organization_id,
            actor_user_id,
            "invitation.cancelled",
            "invitation",
            invitation_id,
            {"email": invitation.email},
        )
        return invitation

    def preview_invitation(self, plaintext_token: str) -> Invitation | None:
        """Resolves a token to its invitation for the public acceptance page
        (shows org/role/status before accepting). No session required -- the
        token is the authorization. Returns the invitation even when
        expired, so the page can say Expirado rather than 'not found'."""
        invitation = self._resolve_invitation_token(plaintext_token)
        return invitation

    def accept_invitation(
        self, plaintext_token: str, display_name: str, password: str
    ) -> User | None:
        """Verifies the token, confirms the invitation is still Pendente,
        then atomically creates the account + role and marks it Aceito.
        Returns None for an invalid token or an invitation in any
        non-pending state -- the route maps that to 404."""
        invitation = self._resolve_invitation_token(plaintext_token)
        if invitation is None:
            return None
        if invitation.status(datetime.now(timezone.utc)) != "pending":
            return None
        password_hash = self._password_hasher.hash(password)
        user = self._repository.administration.accept_invitation(
            invitation.id, display_name, password_hash
        )
        if user is None:
            return None
        self._repository.administration.record_audit(
            invitation.organization_id,
            user.id,
            "invitation.accepted",
            "invitation",
            invitation.id,
            {"email": invitation.email, "role_name": invitation.role_name},
        )
        return user

    def _resolve_invitation_token(self, plaintext_token: str) -> Invitation | None:
        """Narrow by non-secret prefix, then Argon2-verify -- same discipline
        as `authenticate_api_key`. Never logs or raises on the token."""
        if not plaintext_token.startswith(INVITATION_TOKEN_PREFIX):
            return None
        prefix = plaintext_token[:INVITATION_DISPLAY_PREFIX_LENGTH]
        candidates = self._repository.administration.list_pending_invitations_by_prefix(
            prefix
        )
        for candidate in candidates:
            if self._password_hasher.verify(plaintext_token, candidate.hashed_token):
                return candidate
        return None
