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
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.authorization import require_permission
from src.api.dependencies import build_event_publisher, build_repository
from src.api.identity_context import get_request_context
from src.api.rate_limiter import enforce_rate_limit
from src.api.routes.portfolio import build_domain_service
from src.api.security import verify_api_key
from src.database.models import Project
from src.database.repository import AnalysisRepository
from src.services.domain_service import DomainService
from src.services.events.interfaces import EventPublisher
from src.services.executive_analytics.metrics_engine import (
    EvmSummary,
    HistoryPoint,
    MetricValue,
)
from src.services.executive_analytics.performance_service import (
    ProjectPerformanceService,
)
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
    # V1 Product & Capability Completion, Package K: raw financial fields
    # only -- variance/variance_percentage are always computed at the point
    # of read (frontend), never stored or returned pre-computed here.
    approved_budget: float | None
    actual_cost: float | None
    forecast_cost: float | None


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
    approved_budget: float | None = None
    actual_cost: float | None = None
    forecast_cost: float | None = None


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
        approved_budget=float(project.approved_budget) if project.approved_budget is not None else None,
        actual_cost=float(project.actual_cost) if project.actual_cost is not None else None,
        forecast_cost=float(project.forecast_cost) if project.forecast_cost is not None else None,
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
        correlation_id=context.request_id,
        **fields,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return _to_response(project)


# -- Wave 8 (Executive Analytics): EVM Temporal Baseline ---------------------
# Founder Decision, `docs/architecture/TECHNICAL-DESIGN-WAVE-8-EXECUTIVE-ANALYTICS.md`.


def build_performance_service(
    repository: AnalysisRepository = Depends(build_repository),
    publisher: EventPublisher = Depends(build_event_publisher),
) -> ProjectPerformanceService:
    return ProjectPerformanceService(repository=repository, publisher=publisher)


# Fixed, single-source-of-truth disclosure -- Earned Value here is derived
# from `progress_percentage`, a manually-reported field with no formal
# WBS/earned-value discipline behind it (Technical Design Section 2.D).
# Every surface that renders `ev` must carry this label, never present it
# as a certified EV.
EV_ESTIMATE_LABEL = (
    "Valor Agregado (estimado a partir do progresso reportado -- não é um EV certificado)"
)


class PerformanceBaselinePointRequest(BaseModel):
    period_date: date
    planned_progress_percentage: Decimal


class CreatePerformanceBaselineRequest(BaseModel):
    bac_reference: Decimal
    points: list[PerformanceBaselinePointRequest]


class PerformanceBaselineResponse(BaseModel):
    baseline_version: int


class CaptureSnapshotRequest(BaseModel):
    snapshot_date: date | None = None


class PerformanceSnapshotResponse(BaseModel):
    id: int
    project_id: int
    snapshot_date: date
    actual_cost: float
    progress_percentage: int


class MetricValueResponse(BaseModel):
    value: float | None
    reason: str | None


def _to_metric_response(metric: MetricValue) -> MetricValueResponse:
    return MetricValueResponse(
        value=float(metric.value) if metric.value is not None else None, reason=metric.reason
    )


class EvmSummaryResponse(BaseModel):
    as_of: date
    ev_label: str
    bac: MetricValueResponse
    pv: MetricValueResponse
    ev: MetricValueResponse
    ac: MetricValueResponse
    cpi: MetricValueResponse
    spi: MetricValueResponse
    cv: MetricValueResponse
    sv: MetricValueResponse
    eac: MetricValueResponse
    etc_: MetricValueResponse
    vac: MetricValueResponse


def _to_evm_response(summary: EvmSummary, as_of: date) -> EvmSummaryResponse:
    return EvmSummaryResponse(
        as_of=as_of,
        ev_label=EV_ESTIMATE_LABEL,
        bac=_to_metric_response(summary.bac),
        pv=_to_metric_response(summary.pv),
        ev=_to_metric_response(summary.ev),
        ac=_to_metric_response(summary.ac),
        cpi=_to_metric_response(summary.cpi),
        spi=_to_metric_response(summary.spi),
        cv=_to_metric_response(summary.cv),
        sv=_to_metric_response(summary.sv),
        eac=_to_metric_response(summary.eac),
        etc_=_to_metric_response(summary.etc),
        vac=_to_metric_response(summary.vac),
    )


@router.post(
    "/projects-delivery/{project_id}/performance-baselines",
    response_model=PerformanceBaselineResponse,
    status_code=201,
    tags=["project-delivery"],
)
def create_performance_baseline(
    project_id: int,
    request: CreatePerformanceBaselineRequest,
    context: RequestContext = Depends(get_request_context),
    service: ProjectPerformanceService = Depends(build_performance_service),
    _permission: None = Depends(require_permission("project_delivery.write")),
):
    """Authors a new planned-value baseline version -- points are always
    human-provided, never inferred or linearized by the system (Technical
    Design Section 2.A). Creating a baseline for a project that already has
    one is a rebaseline: it never touches the prior version's rows."""
    if not request.points:
        raise HTTPException(status_code=422, detail="At least one baseline point is required")
    points = [(point.period_date, point.planned_progress_percentage) for point in request.points]
    baseline_version = service.create_baseline(
        context.organization.organization_id,
        project_id,
        context.user.user_id,
        context.request_id,
        request.bac_reference,
        points,
    )
    if baseline_version is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return PerformanceBaselineResponse(baseline_version=baseline_version)


@router.post(
    "/projects-delivery/{project_id}/performance-snapshots",
    response_model=PerformanceSnapshotResponse,
    status_code=201,
    tags=["project-delivery"],
)
def capture_performance_snapshot(
    project_id: int,
    request: CaptureSnapshotRequest = CaptureSnapshotRequest(),
    context: RequestContext = Depends(get_request_context),
    service: ProjectPerformanceService = Depends(build_performance_service),
    _permission: None = Depends(require_permission("project_delivery.write")),
):
    """Copies the Project's current `actual_cost`/`progress_percentage`
    into a new append-only snapshot row -- idempotent per day (Technical
    Design Section 2.B). Never accepts a cost/progress value from the
    caller; there is nothing to capture when either field is still null."""
    try:
        snapshot = service.capture_snapshot(
            context.organization.organization_id,
            project_id,
            context.user.user_id,
            context.request_id,
            snapshot_date=request.snapshot_date,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return PerformanceSnapshotResponse(
        id=snapshot.id,
        project_id=snapshot.project_id,
        snapshot_date=snapshot.snapshot_date,
        actual_cost=float(snapshot.actual_cost),
        progress_percentage=snapshot.progress_percentage,
    )


@router.get(
    "/projects-delivery/{project_id}/performance-summary",
    response_model=EvmSummaryResponse,
    tags=["project-delivery"],
)
def get_performance_summary(
    project_id: int,
    as_of: date | None = None,
    context: RequestContext = Depends(get_request_context),
    service: ProjectPerformanceService = Depends(build_performance_service),
    _permission: None = Depends(require_permission("project_delivery.read")),
):
    """Deterministic EVM summary -- every metric is either a real value or
    an explicit N/A carrying a machine-readable `reason`, never fabricated
    or zero-filled (Technical Design Section 2.H)."""
    resolved_as_of = as_of or datetime.now(tz=timezone.utc).date()
    summary = service.get_evm_summary(
        project_id, context.organization.organization_id, resolved_as_of
    )
    if summary is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_evm_response(summary, resolved_as_of)


class HistoryPointResponse(BaseModel):
    as_of: date
    pv: MetricValueResponse
    ev: MetricValueResponse
    ac: MetricValueResponse


def _to_history_point_response(point: HistoryPoint) -> HistoryPointResponse:
    return HistoryPointResponse(
        as_of=point.as_of,
        pv=_to_metric_response(point.pv),
        ev=_to_metric_response(point.ev),
        ac=_to_metric_response(point.ac),
    )


@router.get(
    "/projects-delivery/{project_id}/performance-history",
    response_model=list[HistoryPointResponse],
    tags=["project-delivery"],
)
def get_performance_history(
    project_id: int,
    context: RequestContext = Depends(get_request_context),
    service: ProjectPerformanceService = Depends(build_performance_service),
    _permission: None = Depends(require_permission("project_delivery.read")),
):
    """S-Curve data -- one point per real captured snapshot, empty when
    none exist yet (never a fabricated/interpolated series, Technical
    Design Section 2.H)."""
    history = service.get_performance_history(project_id, context.organization.organization_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return [_to_history_point_response(point) for point in history]
