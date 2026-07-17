"""FastAPI dependency that resolves a RequestContext from the Institutional
Headers (TDS Epic 2, Section 15.6). No V1 or Epic 1 route depends on this
yet -- it is infrastructure for Epics 3-5, exercised directly by its own
tests in this epic.

`request_id` is read from the existing `request_id_var` contextvar
(src/api/request_context.py's RequestIDMiddleware), not from a new header
-- that middleware already resolves/generates the correlation ID for every
request; duplicating that here would create two divergent "request id"
concepts for the same request.
"""
from fastapi import Header, HTTPException

from src.api.request_context import request_id_var
from src.services.identity.models import (
    AuthenticatedUser,
    OrganizationIdentity,
    RequestContext,
    SessionIdentity,
)


def get_request_context(
    x_stratech_user_id: str | None = Header(default=None, alias="X-Stratech-User-Id"),
    x_stratech_organization_id: str | None = Header(
        default=None, alias="X-Stratech-Organization-Id"
    ),
    x_stratech_session_id: str | None = Header(default=None, alias="X-Stratech-Session-Id"),
) -> RequestContext:
    if not x_stratech_user_id or not x_stratech_organization_id or not x_stratech_session_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "X-Stratech-User-Id, X-Stratech-Organization-Id and "
                "X-Stratech-Session-Id are all required"
            ),
        )

    try:
        user_id = int(x_stratech_user_id)
        organization_id = int(x_stratech_organization_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="X-Stratech-User-Id and X-Stratech-Organization-Id must be integers",
        ) from exc

    # Minimal identity: this dependency only trusts what the headers say.
    # Enriching it with email/display_name/organization name from the
    # database is the caller's responsibility (none does so in this epic).
    user = AuthenticatedUser(user_id=user_id, email="", display_name="")
    organization = OrganizationIdentity(organization_id=organization_id, name="", slug="")
    session = SessionIdentity(session_id=x_stratech_session_id)

    return RequestContext(
        user=user,
        organization=organization,
        session=session,
        request_id=request_id_var.get(),
    )
