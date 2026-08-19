"""FastAPI dependency that resolves a RequestContext from the Institutional
Headers (TDS Epic 2, Section 15.6). No V1 or Epic 1 route depends on this
yet -- it is infrastructure for Epics 3-5, exercised directly by its own
tests in this epic.

`request_id` is read from the existing `request_id_var` contextvar
(src/api/request_context.py's RequestIDMiddleware), not from a new header
-- that middleware already resolves/generates the correlation ID for every
request; duplicating that here would create two divergent "request id"
concepts for the same request.

D-051 (API Keys, Enterprise Administration): a second, alternative auth
path via a single `X-Stratech-Api-Key` header, additive to the 3-header
session path above -- neither replaces the other, and every existing
route gains API Key authentication for free with zero changes to its own
`Depends(...)` wiring. A key authenticates AS the user who created it, so
every RBAC/audit check downstream is identical to what that user's normal
session would get -- no new permission model, no Integration Hub
involved (DOMAIN-BLUEPRINT-API-KEYS.md).

`build_repository` is called directly here (a plain function call, not a
declared `Depends(...)` parameter) so it only ever runs on the rare
request that actually presents `X-Stratech-Api-Key`. Declaring it as a
`Depends(...)` parameter instead would make FastAPI resolve it -- and
construct a real `AnalysisRepository()` -- on *every* call to
`get_request_context`, i.e. every authenticated request in the whole
application, including the dozen existing test modules that never send
this header and have no reason to know it exists.
"""
from fastapi import Header, HTTPException

from src.api.dependencies import build_repository
from src.api.request_context import request_id_var
from src.services.administration_service import AdministrationService
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
    x_stratech_api_key: str | None = Header(default=None, alias="X-Stratech-Api-Key"),
) -> RequestContext:
    if x_stratech_api_key:
        administration_service = AdministrationService(repository=build_repository())
        api_key = administration_service.authenticate_api_key(x_stratech_api_key)
        if api_key is None:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")

        user = AuthenticatedUser(user_id=api_key.created_by_user_id, email="", display_name="")
        organization = OrganizationIdentity(
            organization_id=api_key.organization_id, name="", slug=""
        )
        # Not a real browser session -- deliberately not a UUID/HMAC token,
        # so it can never be confused for one further down the stack.
        session = SessionIdentity(session_id=f"api-key:{api_key.id}")

        return RequestContext(
            user=user,
            organization=organization,
            session=session,
            request_id=request_id_var.get(),
        )

    if not x_stratech_user_id or not x_stratech_organization_id or not x_stratech_session_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "X-Stratech-User-Id, X-Stratech-Organization-Id and "
                "X-Stratech-Session-Id are all required (or X-Stratech-Api-Key)"
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
