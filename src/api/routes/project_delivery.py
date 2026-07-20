"""Enterprise Domain API -- Project Delivery (Wave 2, Sprint 2).

Named `project_delivery`, not `project`, so this module is never
ambiguous alongside the Épico-1 `Project` model or a future backend module
for it (TD-008, `DOMAIN-BLUEPRINT-PROJECT.md`). The entity itself is the
same Épico-1 `projects` table (Opção A, Fase 1) -- only the route module's
name is kept distinct, for the same reason the frontend page is
`/project-delivery`, not `/project`.

Same auth stack and RBAC note as `portfolio.py`/`program.py`. A Project is
only reachable through a Program that belongs to the caller's
organization (transitively, via the Program's Portfolio).
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.authorization import require_permission
from src.api.identity_context import get_request_context
from src.api.rate_limiter import enforce_rate_limit
from src.api.routes.portfolio import build_domain_service
from src.api.security import verify_api_key
from src.database.models import Project
from src.services.domain_service import DomainService
from src.services.identity.models import RequestContext

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


class ProjectDeliveryResponse(BaseModel):
    id: int
    organization_id: int
    program_id: int
    name: str
    code: str | None
    description: str | None
    objective: str | None
    sponsor: str | None
    project_manager: str | None
    status: str | None
    health: str | None
    priority: str | None
    start_date: date | None
    planned_end_date: date | None
    actual_end_date: date | None
    progress_percentage: int | None
    last_updated: date | None
    next_review: date | None
    # Value objects not yet promoted to entities (Domain Blueprint CB-003
    # §1) -- passed through as-is from the JSON columns.
    owner: dict | None
    milestones: list[dict] | None
    team: dict | None


class ProjectDeliveryCreateRequest(BaseModel):
    program_id: int
    name: str
    code: str | None = None
    description: str | None = None
    objective: str | None = None
    sponsor: str | None = None
    project_manager: str | None = None
    status: str | None = None
    health: str | None = None
    priority: str | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    actual_end_date: date | None = None
    last_updated: date | None = None
    next_review: date | None = None
    owner: dict | None = None
    milestones: list[dict] | None = None
    team: dict | None = None


def _to_response(project: Project) -> ProjectDeliveryResponse:
    """Explicit mapping (not `from_attributes`) because the ORM's
    `owner_json`/`milestones_json`/`team_json` columns are exposed without
    the `_json` suffix -- storage detail, not API shape."""
    return ProjectDeliveryResponse(
        id=project.id,
        organization_id=project.organization_id,
        program_id=project.program_id,
        name=project.name,
        code=project.code,
        description=project.description,
        objective=project.objective,
        sponsor=project.sponsor,
        project_manager=project.project_manager,
        status=project.status,
        health=project.health,
        priority=project.priority,
        start_date=project.start_date,
        planned_end_date=project.planned_end_date,
        actual_end_date=project.actual_end_date,
        progress_percentage=project.progress_percentage,
        last_updated=project.last_updated,
        next_review=project.next_review,
        owner=project.owner_json,
        milestones=project.milestones_json,
        team=project.team_json,
    )


@router.get(
    "/projects-delivery", response_model=list[ProjectDeliveryResponse], tags=["project-delivery"]
)
def list_projects_delivery(
    program_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("project_delivery.read")),
):
    """Lists domain Projects (program_id set) for the caller's organization
    -- optionally filtered to a single Program via `program_id`. A plain
    Épico-1 Project with no Program yet does not appear here (TD-008,
    Fase 2 -- it must go through `attach_project_to_program()` first)."""
    projects = service.list_projects(context.organization.organization_id, program_id)
    if projects is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return [_to_response(project) for project in projects]


@router.get(
    "/projects-delivery/{project_id}",
    response_model=ProjectDeliveryResponse,
    tags=["project-delivery"],
)
def get_project_delivery(
    project_id: int,
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("project_delivery.read")),
):
    project = service.get_project(project_id, context.organization.organization_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_response(project)


@router.post(
    "/projects-delivery",
    response_model=ProjectDeliveryResponse,
    status_code=201,
    tags=["project-delivery"],
)
def create_project_delivery(
    request: ProjectDeliveryCreateRequest,
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("project_delivery.write")),
):
    fields = request.model_dump(exclude_none=True, exclude={"program_id", "name"})
    if "owner" in fields:
        fields["owner_json"] = fields.pop("owner")
    if "milestones" in fields:
        fields["milestones_json"] = fields.pop("milestones")
    if "team" in fields:
        fields["team_json"] = fields.pop("team")
    logger.info(
        "Creating project-delivery organization_id=%s program_id=%s",
        context.organization.organization_id,
        request.program_id,
    )
    project = service.create_project(
        context.organization.organization_id,
        request.program_id,
        request.name,
        actor_user_id=context.user.user_id,
        **fields,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return _to_response(project)
