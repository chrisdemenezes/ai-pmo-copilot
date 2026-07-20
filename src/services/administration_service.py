"""Application layer for the Enterprise Administration API (Wave 2, Sprint 4).

Same split as `DomainService`: routes stay thin adapters, mutations
record an audit entry here (not in the route, not in the repository) so
every write path goes through exactly one place that remembers to audit.
"""
import logging

from src.database.models import AuditLog, Organization, Permission, Role, User
from src.database.repository import AnalysisRepository

logger = logging.getLogger(__name__)


class AdministrationService:
    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

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

    # -- Roles / Permissions -----------------------------------------------

    def list_roles(self) -> list[Role]:
        return self._repository.administration.list_roles()

    def list_permissions_for_role(self, role_id: int) -> list[Permission]:
        return self._repository.administration.list_permissions_for_role(role_id)

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

    # -- Audit Log (also serves as "Logs") ----------------------------------

    def list_audit_log(self, organization_id: int, limit: int = 50) -> list[AuditLog]:
        return self._repository.administration.list_audit_log(organization_id, limit)
