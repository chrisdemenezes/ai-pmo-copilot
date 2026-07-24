"""Convites (Invitations) API -- item 6 of the Wave Completion Review
retrospective (D-054); Release 0.2 "Convites e Stakeholders".

An invitation is a foundational Enterprise Administration credential, not
an email artifact (`DOMAIN-BLUEPRINT-INVITATIONS.md`). Admin management
(create/list/cancel) requires `invitations.manage`; the public
preview/accept flow is authenticated by the token itself, not a session --
the invitee has no account yet, exactly like `auth.py`'s login is
session-less. Delivery is abstracted behind `NotificationProvider` (NoOp
today, D-054); the plaintext token is returned once at creation for manual
delivery, so the capability is fully functional without any email provider.

Same auth stack as every other router: `verify_api_key` +
`enforce_rate_limit` at router level. Admin routes add
`require_permission`; public routes deliberately do not.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.api.authorization import require_permission
from src.api.dependencies import build_notification_provider, build_repository
from src.api.identity_context import get_request_context
from src.api.rate_limiter import enforce_rate_limit
from src.api.security import verify_api_key
from src.database.enterprise_repository import EmailConflictError
from src.database.repository import AnalysisRepository
from src.services.administration_service import AdministrationService
from src.services.identity.models import RequestContext
from src.services.notifications.interfaces import NotificationProvider

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


def build_invitation_service(
    repository: AnalysisRepository = Depends(build_repository),
    notification_provider: NotificationProvider = Depends(build_notification_provider),
) -> AdministrationService:
    return AdministrationService(
        repository=repository, notification_provider=notification_provider
    )


class InvitationResponse(BaseModel):
    id: int
    email: str
    role_name: str
    status: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    cancelled_at: datetime | None


class InvitationCreateRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    role_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def _email_shape(cls, value: str) -> str:
        # Minimal structural check -- no email-validator dependency is
        # available and none is added just for this (the address is the
        # future account's identifier, validated the same way the rest of
        # the app treats emails: normalized, uniqueness enforced at the DB).
        stripped = value.strip()
        if "@" not in stripped or stripped.startswith("@") or stripped.endswith("@"):
            raise ValueError("email must contain a local part and a domain")
        return stripped


class InvitationCreatedResponse(InvitationResponse):
    # The only time the raw token is ever returned -- the caller must show
    # it (as the invite link) to the admin exactly once for delivery.
    plaintext_token: str


class InvitationPreviewResponse(BaseModel):
    """What the public acceptance page shows before the invitee accepts --
    deliberately minimal: organization name, granted role, current state,
    and the email the account will be created under."""

    organization_name: str
    role_name: str
    status: str
    email: str


class InvitationAcceptRequest(BaseModel):
    token: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=1024)


class InvitationAcceptResponse(BaseModel):
    user_id: int
    organization_id: int


def _to_response(invitation, now: datetime) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role_name=invitation.role_name,
        status=invitation.status(now),
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        cancelled_at=invitation.cancelled_at,
    )


# -- Admin management (require invitations.manage) ---------------------


@router.get(
    "/admin/invitations", response_model=list[InvitationResponse], tags=["administration"]
)
def list_invitations(
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_invitation_service),
    _permission: None = Depends(require_permission("invitations.manage")),
):
    now = datetime.now(timezone.utc)
    return [
        _to_response(invitation, now)
        for invitation in service.list_invitations(context.organization.organization_id)
    ]


@router.post(
    "/admin/invitations",
    response_model=InvitationCreatedResponse,
    status_code=201,
    tags=["administration"],
)
def create_invitation(
    request: InvitationCreateRequest,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_invitation_service),
    _permission: None = Depends(require_permission("invitations.manage")),
):
    """The response's `plaintext_token` is the only time the raw token is
    returned -- the caller builds the invite link from it and delivers it
    (manually today; via a NotificationProvider once one exists)."""
    try:
        invitation, plaintext_token = service.create_invitation(
            context.organization.organization_id,
            request.email,
            request.role_name,
            actor_user_id=context.user.user_id,
        )
    except ValueError as exc:
        # Unknown role_name -- a typo must 400, never create a role.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    now = datetime.now(timezone.utc)
    base = _to_response(invitation, now)
    return InvitationCreatedResponse(**base.model_dump(), plaintext_token=plaintext_token)


@router.delete(
    "/admin/invitations/{invitation_id}",
    response_model=InvitationResponse,
    tags=["administration"],
)
def cancel_invitation(
    invitation_id: int,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_invitation_service),
    _permission: None = Depends(require_permission("invitations.manage")),
):
    """Returns the cancelled invitation (200), not a bare 204 -- same
    convention as API Keys / Sessions (`forwardDomainRequest` always parses
    a JSON body)."""
    invitation = service.cancel_invitation(
        invitation_id,
        context.organization.organization_id,
        actor_user_id=context.user.user_id,
    )
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found or not pending")
    now = datetime.now(timezone.utc)
    return _to_response(invitation, now)


# -- Public flow (authenticated by the token, no session) --------------


@router.get(
    "/invitations/{token}", response_model=InvitationPreviewResponse, tags=["administration"]
)
def preview_invitation(
    token: str,
    service: AdministrationService = Depends(build_invitation_service),
):
    """Public: the acceptance page shows who invited whom before the invitee
    commits. No session -- the token is the authorization."""
    invitation = service.preview_invitation(token)
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invalid invitation")
    organization = service.get_organization(invitation.organization_id)
    now = datetime.now(timezone.utc)
    return InvitationPreviewResponse(
        organization_name=organization.name if organization else "",
        role_name=invitation.role_name,
        status=invitation.status(now),
        email=invitation.email,
    )


@router.post(
    "/invitations/accept", response_model=InvitationAcceptResponse, tags=["administration"]
)
def accept_invitation(
    request: InvitationAcceptRequest,
    service: AdministrationService = Depends(build_invitation_service),
):
    """Public: creates the account from a pending invitation. The invitee
    supplies only display_name + password; email, organization and role
    come from the invitation, never from the request -- so accepting can
    never change which org/role/email the account gets."""
    try:
        user = service.accept_invitation(
            request.token, request.display_name, request.password
        )
    except EmailConflictError as exc:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from exc
    if user is None:
        raise HTTPException(
            status_code=404, detail="Invalid, expired, or already-used invitation"
        )
    return InvitationAcceptResponse(
        user_id=user.id, organization_id=user.organization_id
    )
