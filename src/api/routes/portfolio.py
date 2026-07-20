"""Enterprise Domain API -- Portfolio (Wave 2, Sprint 2).

Auth stack matches `intelligence.py`'s router-level dependencies exactly
(`verify_api_key`, `enforce_rate_limit`), plus `get_request_context` --
the first real route consumer of that dependency since it was built in
Épico 2 "for Epics 3-5" and left unused. Every read/write below is scoped
by `context.organization.organization_id`, never by a client-supplied
organization id, so one organization can never address another's rows by
guessing an id.

RBAC (Wave 2, Sprint 3; `DOMAIN-BLUEPRINT-RBAC.md`): every route below now
carries `Depends(require_permission("portfolio.read"|"portfolio.write"))`,
inserted after `get_request_context`, exactly the seam
`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4.5 described -- no route
signature or response shape changed to add it.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import date

from src.api.authorization import require_permission
from src.api.identity_context import get_request_context
from src.api.rate_limiter import enforce_rate_limit
from src.api.security import verify_api_key
from src.database.repository import AnalysisRepository
from src.services.domain_service import DomainService
from src.services.identity.models import RequestContext
from src.api.routes.intelligence import build_repository

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


def build_domain_service(
    repository: AnalysisRepository = Depends(build_repository),
) -> DomainService:
    return DomainService(repository=repository)


class PortfolioResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    code: str
    description: str | None
    category: str | None
    executive_owner: str | None
    strategic_objective: str | None
    status: str
    health: str
    priority: str
    start_date: date | None
    planned_end_date: date | None
    actual_end_date: date | None
    progress_percentage: int
    program_count: int
    project_count: int
    linked_demands: int
    linked_risks: int
    linked_issues: int
    pending_decisions: int
    sponsor: str | None
    pmo_owner: str | None
    last_updated: date | None
    next_review: date | None

    model_config = {"from_attributes": True}


class PortfolioCreateRequest(BaseModel):
    name: str
    code: str
    description: str | None = None
    category: str | None = None
    executive_owner: str | None = None
    strategic_objective: str | None = None
    status: str | None = None
    health: str | None = None
    priority: str | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    actual_end_date: date | None = None
    sponsor: str | None = None
    pmo_owner: str | None = None
    last_updated: date | None = None
    next_review: date | None = None


@router.get("/portfolios", response_model=list[PortfolioResponse], tags=["portfolio"])
def list_portfolios(
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("portfolio.read")),
):
    """Lists every Portfolio belonging to the caller's organization."""
    logger.info("Listing portfolios organization_id=%s", context.organization.organization_id)
    return service.list_portfolios(context.organization.organization_id)


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse, tags=["portfolio"])
def get_portfolio(
    portfolio_id: int,
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("portfolio.read")),
):
    portfolio = service.get_portfolio(portfolio_id, context.organization.organization_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.post(
    "/portfolios",
    response_model=PortfolioResponse,
    status_code=201,
    tags=["portfolio"],
)
def create_portfolio(
    request: PortfolioCreateRequest,
    context: RequestContext = Depends(get_request_context),
    service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("portfolio.write")),
):
    # exclude_none: leaving a field out of the request lets the model's own
    # column default (e.g. status="Ativo") apply -- passing None explicitly
    # would try to insert NULL into a NOT NULL column instead.
    fields = request.model_dump(exclude_none=True, exclude={"name", "code"})
    logger.info(
        "Creating portfolio organization_id=%s code=%s",
        context.organization.organization_id,
        request.code,
    )
    return service.create_portfolio(
        context.organization.organization_id,
        request.name,
        request.code,
        actor_user_id=context.user.user_id,
        **fields,
    )
