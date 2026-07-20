"""SQL-backed `PermissionChecker` (Wave 2, Sprint 3).

Resolves a user's permissions through the schema that has existed,
unused, since Épico 1: `user_roles` -> `role_permissions` -> `permissions`.
No `organization_id` on `user_roles` is needed -- `users.organization_id`
is a single NOT NULL FK (Épico 1), so a user never has roles in more than
one organization today; `DOMAIN-BLUEPRINT-RBAC.md` §1's suggestion to add
one was based on a multi-org-membership scenario that this schema does
not actually support, corrected here rather than carried into a migration
nobody needs yet.
"""
import logging

from sqlalchemy.orm import sessionmaker

from src.database.models import Permission, RolePermission, UserRole

logger = logging.getLogger(__name__)


class SqlPermissionChecker:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def has_permission(self, user_id: int, permission: str) -> bool:
        with self._session_factory() as session:
            match = (
                session.query(Permission)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(UserRole, UserRole.role_id == RolePermission.role_id)
                .filter(UserRole.user_id == user_id, Permission.name == permission)
                .first()
            )
            granted = match is not None
            logger.info(
                "Permission check user_id=%s permission=%s granted=%s",
                user_id,
                permission,
                granted,
            )
            return granted
