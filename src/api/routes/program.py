"""Enterprise Domain API -- Program (Wave 2, Sprint 2).

Same auth stack and RBAC note as `portfolio.py`. A Program is only ever
reachable through a Portfolio that belongs to the caller's organization
(`DomainService.get_portfolio`/`list_programs` enforce this) -- a
cross-organization portfolio_id resolves to 404, identical to a
non-existent one, never a 403 that would confirm the id exists elsewhere.
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
from src.services.domain_service import DomainService
from src.services.identity.models import RequestContext

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


class ProgramResponse(BaseModel):
    id: int
    portfolio_id: int
    name: str
    code: str
    description: str | None
    sponsor: str | None
    program_manager: str | None
    status: str
    health: str
    priority: str
    objective: str | None
    start_date: date | None
    planned_end_date: date | None
    actual_end_date: date | None
    progress_percentage: int
    project_count: int
    linked_demands: int
    linked_risks: int
    linked_issues: int
    pending_decisions: int
    pending_actions: int
    pmo_owner: str | None
    last_updated: date | None
    next_review: date | None

    model_config = {"from_attributes": True}


class ProgramCreateRequest(BaseModel):
    portfolio_id: int
    name: str
    code: str
    description: str | None = None
    sponsor: str | None = None
    program_manager: str | None = None
    status: str | None = None
    health: str | None = None
    priority: str | None = None
    objective: str | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    actual_end_date: date | None = None
    pmo_owner: str | None = None
    last_updated: date | None = None
    next_review: date | None = None


@router.get("/programs", response_model=list[ProgramResponse], tags=["program"])
def list_programs(
    portfolio_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("program.read")),
):
    """Lists Programs for the caller's organization -- optionally filtered
    to a single Portfolio via `portfolio_id`."""
    programs = service.list_programs(context.organization.organization_id, portfolio_id)
    if programs is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return programs


@router.get("/programs/{program_id}", response_model=ProgramResponse, tags=["program"])
def get_program(
    program_id: int,
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("program.read")),
):
    program = service.get_program(program_id, context.organization.organization_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.post("/programs", response_model=ProgramResponse, status_code=201, tags=["program"])
def create_program(
    request: ProgramCreateRequest,
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("program.write")),
):
    fields = request.model_dump(exclude_none=True, exclude={"portfolio_id", "name", "code"})
    logger.info(
        "Creating program organization_id=%s portfolio_id=%s code=%s",
        context.organization.organization_id,
        request.portfolio_id,
        request.code,
    )
    program = service.create_program(
        context.organization.organization_id,
        request.portfolio_id,
        request.name,
        request.code,
        **fields,
    )
    if program is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return program
