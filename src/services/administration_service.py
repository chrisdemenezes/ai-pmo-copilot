"""Application layer for the Enterprise Administration API (Wave 2, Sprint 4).

Same split as `DomainService`: routes stay thin adapters, mutations
record an audit entry here (not in the route, not in the repository) so
every write path goes through exactly one place that remembers to audit.
"""
import logging

from src.database.models import AuditLog, Organization, Permission, Role, User
from src.database.repository import AnalysisRepository
from src.services.identity.password_hashing import Argon2PasswordHasher

logger = logging.getLogger(__name__)


class AdministrationService:
    def __init__(
        self,
        repository: AnalysisRepository,
        password_hasher: Argon2PasswordHasher | None = None,
    ) -> None:
        self._repository = repository
        # Only User Management's create_user needs this -- the plaintext
        # password lives only as a local variable inside that one method,
        # never reaching the repository, the audit log, or a log line.
        self._password_hasher = password_hasher or Argon2PasswordHasher()

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
