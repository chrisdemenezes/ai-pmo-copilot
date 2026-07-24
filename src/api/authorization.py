"""RBAC enforcement dependency (Wave 2, Sprint 3; `DOMAIN-BLUEPRINT-RBAC.md`).

`require_permission(permission)` is meant to be the one additional
`Depends(...)` every Enterprise Domain route gains this Sprint, inserted
immediately after `get_request_context` -- exactly the seam
`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4.5 described, added without
changing any route's signature otherwise.
"""
import logging
from typing import Callable

from fastapi import Depends, HTTPException

from src.api.dependencies import build_repository
from src.api.identity_context import get_request_context
from src.database.repository import AnalysisRepository
from src.services.authorization.checker import SqlPermissionChecker
from src.services.authorization.interfaces import PermissionChecker
from src.services.identity.models import RequestContext

logger = logging.getLogger(__name__)

# `api-key:` sessions (get_request_context's API Key path) are already
# gated by the key's own revocation check -- they never correspond to a
# browser-session row, so the session-store lookup is skipped for them.
API_KEY_SESSION_PREFIX = "api-key:"

# A callable `session_id -> is_revoked`. Its own dependency, separate from
# build_permission_checker, so it can be defaulted to "never revoked" by
# conftest's autouse fixture for the whole existing suite (exactly as
# verify_api_key/enforce_rate_limit already are) -- the ~12 API test
# modules use fabricated session ids that were never in any session store,
# so this default keeps them untouched while production (never overridden)
# runs the real DB-backed check.
SessionRevocationChecker = Callable[[str], bool]


def build_permission_checker(
    repository: AnalysisRepository = Depends(build_repository),
) -> PermissionChecker:
    return SqlPermissionChecker(repository.SessionLocal)


def build_session_revocation_checker(
    repository: AnalysisRepository = Depends(build_repository),
) -> SessionRevocationChecker:
    return repository.administration.is_session_revoked


def require_permission(permission: str):
    def _check(
        context: RequestContext = Depends(get_request_context),
        checker: PermissionChecker = Depends(build_permission_checker),
        is_session_revoked: SessionRevocationChecker = Depends(build_session_revocation_checker),
    ) -> None:
        session_id = context.session.session_id
        # Revocation enforcement (item 5, resolves TD-010): a session
        # revoked by an admin loses access on its next request, not in up
        # to 12h. The check only rejects an id with an explicit revoked_at
        # row -- an unknown id (predating the store, or a fabricated test
        # fixture id) is treated as active, so no existing caller is
        # retroactively broken.
        if not session_id.startswith(API_KEY_SESSION_PREFIX) and is_session_revoked(session_id):
            logger.warning(
                "Access denied: revoked session_id=%s user_id=%s",
                session_id,
                context.user.user_id,
            )
            raise HTTPException(status_code=401, detail="Session has been revoked")

        if not checker.has_permission(context.user.user_id, permission):
            logger.warning(
                "Permission denied user_id=%s permission=%s", context.user.user_id, permission
            )
            raise HTTPException(status_code=403, detail=f"missing permission: {permission}")

    return _check
