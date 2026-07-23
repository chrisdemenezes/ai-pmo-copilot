"""RBAC enforcement dependency (Wave 2, Sprint 3; `DOMAIN-BLUEPRINT-RBAC.md`).

`require_permission(permission)` is meant to be the one additional
`Depends(...)` every Enterprise Domain route gains this Sprint, inserted
immediately after `get_request_context` -- exactly the seam
`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4.5 described, added without
changing any route's signature otherwise.
"""
import logging

from fastapi import Depends, HTTPException

from src.api.dependencies import build_repository
from src.api.identity_context import get_request_context
from src.database.repository import AnalysisRepository
from src.services.authorization.checker import SqlPermissionChecker
from src.services.authorization.interfaces import PermissionChecker
from src.services.identity.models import RequestContext

logger = logging.getLogger(__name__)


def build_permission_checker(
    repository: AnalysisRepository = Depends(build_repository),
) -> PermissionChecker:
    return SqlPermissionChecker(repository.SessionLocal)


def require_permission(permission: str):
    def _check(
        context: RequestContext = Depends(get_request_context),
        checker: PermissionChecker = Depends(build_permission_checker),
    ) -> None:
        if not checker.has_permission(context.user.user_id, permission):
            logger.warning(
                "Permission denied user_id=%s permission=%s", context.user.user_id, permission
            )
            raise HTTPException(status_code=403, detail=f"missing permission: {permission}")

    return _check
