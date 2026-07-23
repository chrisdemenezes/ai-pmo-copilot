"""Enterprise Administration API (Wave 2, Sprint 4 + User Management Capability).

Épico 5 Nível 1 (Usuários, Organizações, Papéis, Auditoria) + the ratified
Nível 2 subset that needed no new domain concept (`DOMAIN-BLUEPRINT-
ENTERPRISE-ADMINISTRATION.md` §2-3): "Logs" is served by the same
audit_logs table as "Auditoria" (one structured store, not two), and
"Segurança" is a minimal read-only posture endpoint (no MFA/password
policy configuration exists to expose beyond that).

User Management (`DOMAIN-BLUEPRINT-USER-MANAGEMENT.md`,
`TECHNICAL-DESIGN-USER-MANAGEMENT.md`) closes the last gap in Nível 1:
create/edit/activate-deactivate/assign-remove-role for Usuários. Initial
credential is set directly by the admin at creation (no invite/reset
flow) -- see the Technical Design §1 for why that doesn't require one.

Not included, deliberately: "Sessões" -- no server-side session store
exists (`src/services/identity/auth_service.py`'s `logout()` docstring:
"No server-side session store exists yet"), so the Blueprint's assumed
"painel é só leitura+revogação sobre o que já existe" doesn't hold; a
real session store is a bigger scope than this Sprint's ratified
extension, corrected in the Decision Log, not built as a fake list.
"Configurações" stays out per the Blueprint's own deferral (needs product
scope definition first). Invites, SSO, MFA, password reset/recovery are
explicitly out of scope for this Capability per the Founder's approval.

Same auth stack as every other Enterprise Domain router: `verify_api_key`
+ `enforce_rate_limit` + `get_request_context` + `require_permission`
(`administration.read`/`administration.write`, migration 0007).
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.authorization import require_permission
from src.api.identity_context import get_request_context
from src.api.rate_limiter import enforce_rate_limit
from src.api.routes.intelligence import build_repository
from src.api.security import verify_api_key
from src.database.enterprise_repository import (
    EmailConflictError,
    LastActiveAdminError,
    SelfDeactivationError,
)
from src.database.repository import AnalysisRepository
from src.services.administration_service import AdministrationService
from src.services.identity.models import RequestContext

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


def build_administration_service(
    repository: AnalysisRepository = Depends(build_repository),
) -> AdministrationService:
    return AdministrationService(repository=repository)


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


class OrganizationUpdateRequest(BaseModel):
    name: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    identity_type: str
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    # Initial credential, set directly by the admin (Technical Design §1 --
    # no invite/reset flow exists or is introduced by this Capability).
    password: str = Field(..., min_length=1, max_length=1024)
    role_name: str = Field(..., min_length=1)


class UserUpdateRequest(BaseModel):
    email: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)


class UserStatusUpdateRequest(BaseModel):
    is_active: bool


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class PermissionResponse(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class RoleAssignmentRequest(BaseModel):
    role_name: str


class AuditLogEntryResponse(BaseModel):
    id: int
    actor_user_id: int
    action: str
    entity_type: str
    entity_id: int | None
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SecurityPostureResponse(BaseModel):
    password_hashing_algorithm: str
    mfa_available: bool


@router.get("/admin/organization", response_model=OrganizationResponse, tags=["administration"])
def get_organization(
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.read")),
):
    organization = service.get_organization(context.organization.organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.patch(
    "/admin/organization", response_model=OrganizationResponse, tags=["administration"]
)
def update_organization(
    request: OrganizationUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.write")),
):
    organization = service.rename_organization(
        context.organization.organization_id, request.name, actor_user_id=context.user.user_id
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.get("/admin/users", response_model=list[UserResponse], tags=["administration"])
def list_users(
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.read")),
):
    return service.list_users(context.organization.organization_id)


@router.post(
    "/admin/users", response_model=UserResponse, status_code=201, tags=["administration"]
)
def create_user(
    request: UserCreateRequest,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.write")),
):
    try:
        return service.create_user(
            context.organization.organization_id,
            request.email,
            request.display_name,
            request.password,
            request.role_name,
            actor_user_id=context.user.user_id,
        )
    except EmailConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/admin/user-roles-index",
    response_model=dict[int, list[str]],
    tags=["administration"],
)
def user_roles_index(
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.read")),
):
    """Bulk role-name index for every user in the organization -- lets the
    Frontend's user list render/filter by role in one request instead of
    one per row."""
    return service.list_role_names_by_user(context.organization.organization_id)


@router.get("/admin/users/{user_id}", response_model=UserResponse, tags=["administration"])
def get_user(
    user_id: int,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.read")),
):
    user = service.get_user(user_id, context.organization.organization_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get(
    "/admin/users/{user_id}/roles",
    response_model=list[RoleResponse],
    tags=["administration"],
)
def list_user_roles(
    user_id: int,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.read")),
):
    roles = service.list_roles_for_user(user_id, context.organization.organization_id)
    if roles is None:
        raise HTTPException(status_code=404, detail="User not found")
    return roles


@router.patch("/admin/users/{user_id}", response_model=UserResponse, tags=["administration"])
def update_user(
    user_id: int,
    request: UserUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.write")),
):
    try:
        user = service.update_user(
            user_id,
            context.organization.organization_id,
            actor_user_id=context.user.user_id,
            email=request.email,
            display_name=request.display_name,
        )
    except EmailConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/admin/users/{user_id}/status", response_model=UserResponse, tags=["administration"]
)
def update_user_status(
    user_id: int,
    request: UserStatusUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.write")),
):
    try:
        user = service.set_user_active(
            user_id,
            context.organization.organization_id,
            request.is_active,
            actor_user_id=context.user.user_id,
        )
    except SelfDeactivationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LastActiveAdminError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete(
    "/admin/users/{user_id}/roles/{role_name}",
    response_model=UserResponse,
    tags=["administration"],
)
def remove_role(
    user_id: int,
    role_name: str,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.write")),
):
    try:
        user = service.remove_role(
            user_id,
            context.organization.organization_id,
            role_name,
            actor_user_id=context.user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LastActiveAdminError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/admin/roles", response_model=list[RoleResponse], tags=["administration"])
def list_roles(
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.read")),
):
    """Roles are a global catalog (Épico 1), not org-scoped -- listing them
    still requires an authenticated, permitted actor within an
    organization, same as every other route here."""
    return service.list_roles()


@router.get(
    "/admin/roles/{role_id}/permissions",
    response_model=list[PermissionResponse],
    tags=["administration"],
)
def list_role_permissions(
    role_id: int,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.read")),
):
    return service.list_permissions_for_role(role_id)


@router.post(
    "/admin/users/{user_id}/roles", response_model=UserResponse, tags=["administration"]
)
def assign_role(
    user_id: int,
    request: RoleAssignmentRequest,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.write")),
):
    try:
        user = service.assign_role(
            user_id,
            context.organization.organization_id,
            request.role_name,
            actor_user_id=context.user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get(
    "/admin/audit-log", response_model=list[AuditLogEntryResponse], tags=["administration"]
)
def list_audit_log(
    limit: int = 50,
    context: RequestContext = Depends(get_request_context),
    service: AdministrationService = Depends(build_administration_service),
    _permission: None = Depends(require_permission("administration.read")),
):
    """Also serves as the "Logs" surface (Nível 2) -- one structured
    store, not a separate logging system alongside Auditoria."""
    return service.list_audit_log(context.organization.organization_id, limit)


@router.get(
    "/admin/security", response_model=SecurityPostureResponse, tags=["administration"]
)
def get_security_posture(
    _context: RequestContext = Depends(get_request_context),
    _permission: None = Depends(require_permission("administration.read")),
):
    """Minimal, read-only (Nível 2 "Segurança" -- no password policy
    configuration or MFA exists to expose beyond this today)."""
    return SecurityPostureResponse(password_hashing_algorithm="argon2", mfa_available=False)
