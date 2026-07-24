"""Intelligence API -- meeting/risk/status analysis + read endpoints.

RBAC + organization scope (Security Hardening Gate, C-1/C-2; Repository
Audit Wave 3): every route below carries `Depends(require_permission(
"intelligence.read"|"intelligence.write"))`, inserted after
`get_request_context`, the same seam every other Enterprise Domain route
module uses (`portfolio.py`, `program.py`, `project_delivery.py`,
`administration.py`). Every read/write is scoped by
`context.organization.organization_id`, never a client-supplied value.
"""
import logging
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException

from src.agents.meeting_intelligence.agent import MeetingIntelligenceAgent
from src.agents.project_status.agent import ProjectStatusAgent
from src.agents.risk_advisor.agent import RiskAdvisorAgent
from src.agents.risk_review.agent import RiskReviewAgent
from src.api.authorization import require_permission
from src.api.dependencies import build_repository
from src.api.identity_context import get_request_context
from src.api.rate_limiter import enforce_rate_limit
from src.api.security import verify_api_key
from src.database.enterprise_repository import (
    AmbiguousProjectNameError,
    ProjectNotFoundError,
    ProjectReferenceMismatchError,
)
from src.llm.providers.base import LLMProvider
from src.llm.providers.factory import get_provider
from src.prompts.registry import PromptRegistry
from src.database.repository import AnalysisRepository
from src.services.ai_foundation.audit_integration import AIFoundationAudit
from src.services.ai_foundation.context_engine import AIContextEngine
from src.services.ai_foundation.explanation_engine import ExplanationEngine
from src.services.ai_foundation.recommendation_engine import RecommendationEngine
from src.services.ai_foundation.types import SessionContext
from src.services.identity.models import RequestContext
from src.services.project_summary_service import ProjectSummaryService

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


def _ensure_has_content(value: str) -> str:
    if not value.strip():
        raise ValueError("must contain non-whitespace content")
    return value


class MeetingAnalysisRequest(BaseModel):
    transcript: str = Field(..., min_length=10, max_length=20000)
    project_name: str | None = None

    _validate_transcript = field_validator("transcript")(_ensure_has_content)


class RiskAnalysisRequest(BaseModel):
    project_context: str = Field(..., min_length=10, max_length=20000)
    project_name: str | None = None

    _validate_project_context = field_validator("project_context")(_ensure_has_content)


class ProjectStatusRequest(BaseModel):
    project_context: str = Field(..., min_length=10, max_length=20000)
    project_name: str | None = None

    _validate_project_context = field_validator("project_context")(_ensure_has_content)


class AnalysisSummary(BaseModel):
    id: int
    kind: str
    project_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisDetail(AnalysisSummary):
    payload: dict


class ProjectSummaryResponse(BaseModel):
    project_name: str
    project_id: int | None = None
    total_analyses: int
    open_risks: int
    pending_action_items: int
    latest_health_status: str | None


class ActionItemResponse(BaseModel):
    project_name: str | None
    description: str
    # due_date stays a plain string, never parsed to a date here -- it's
    # free text extracted by the AI (FS-007 §11); the frontend treats an
    # unparseable value as "sem prazo" instead of the API rejecting it.
    owner: str | None
    due_date: str | None
    source_analysis_id: int
    source_created_at: datetime


class LatestRiskItemResponse(BaseModel):
    project_name: str | None
    description: str
    probability: str | None
    impact: str | None
    mitigation: str | None
    escalation_recommendation: str | None
    source_analysis_id: int
    source_created_at: datetime


class RiskAdvisorRequest(BaseModel):
    project_name: str
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class CitedAnalysis(BaseModel):
    source_analysis_id: int
    source_created_at: datetime


class RiskAdvisorResponse(BaseModel):
    answer: str
    cited_analyses: list[CitedAnalysis]


def build_prompt_registry() -> PromptRegistry:
    return PromptRegistry(base_path="src/agents")


def build_provider() -> LLMProvider:
    return get_provider()


def build_project_summary_service(
    repository: AnalysisRepository = Depends(build_repository),
) -> ProjectSummaryService:
    return ProjectSummaryService(repository=repository)


def resolve_project_scope(
    repository: AnalysisRepository,
    organization_id: int,
    project_id: int | None,
    project_name: str | None,
) -> tuple[int | None, str | None]:
    """Dual-key boundary check (TD-008 Phase 3b, Etapa 1). Returns the
    `(project_id, project_name)` pair the caller should filter by -- at most
    one is non-None. Maps the resolver's domain errors to HTTP:
    - not found by id / cross-organization -> 404 (never confirm a foreign id);
    - ambiguous name                       -> 409 (never silently pick one);
    - id/name divergence                   -> 409.

    Additive-by-design rules that keep this a zero-regression change:
    - neither given -> (None, None): portfolio scope, unchanged.
    - id given (with or without name) -> full validation, filter by the
      resolved id (exact -- the migration's whole point).
    - name only:
        * resolves uniquely -> filter by its id (identical results to the
          legacy name filter for a unique name, but now exact);
        * ambiguous (>1 match) -> 409 (the one behavior we tighten, per the
          Founder's 'não permitir resolução ambígua por nome');
        * no Project row at all (never analyzed) -> preserve the legacy
          empty-list behavior by filtering on the raw name (a genuinely
          nonexistent project simply has no analyses).
    """
    has_name = project_name is not None and project_name.strip() != ""
    if project_id is None and not has_name:
        return (None, None)

    try:
        project = repository.enterprise.resolve_project_reference(
            organization_id, project_id=project_id, project_name=project_name
        )
        return (project.id, None) if project is not None else (None, None)
    except ProjectNotFoundError as exc:
        # An id that doesn't resolve is always a hard 404 (incl. cross-org).
        # A NAME that doesn't resolve, with no id supplied, is the legacy
        # "never-analyzed project" case -> keep filtering by the raw name
        # (empty result), never a 404, to stay additive.
        if project_id is None:
            return (None, project_name)
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except AmbiguousProjectNameError as exc:
        raise HTTPException(
            status_code=409, detail="Project name is ambiguous; use project_id"
        ) from exc
    except ProjectReferenceMismatchError as exc:
        raise HTTPException(
            status_code=409,
            detail="project_id and project_name refer to different projects",
        ) from exc


@router.post("/meetings/analyze")
def analyze_meeting(
    request: MeetingAnalysisRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.write")),
):
    organization_id = context.organization.organization_id
    logger.info(
        "Analyzing meeting organization_id=%s project_name=%s", organization_id, request.project_name
    )
    agent = MeetingIntelligenceAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(transcript=request.transcript, project_name=request.project_name)
    analysis_id = repository.save_analysis(
        kind="meeting",
        payload=result,
        organization_id=organization_id,
        project_name=request.project_name,
    )
    repository.administration.record_audit(
        organization_id,
        context.user.user_id,
        "analysis.meeting_created",
        "analysis",
        analysis_id,
        {"project_name": request.project_name},
    )
    return result


@router.post("/risks/analyze")
def analyze_risk(
    request: RiskAnalysisRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.write")),
):
    organization_id = context.organization.organization_id
    logger.info(
        "Analyzing risk organization_id=%s project_name=%s", organization_id, request.project_name
    )
    agent = RiskReviewAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(project_context=request.project_context, project_name=request.project_name)
    analysis_id = repository.save_analysis(
        kind="risk",
        payload=result,
        organization_id=organization_id,
        project_name=request.project_name,
    )
    repository.administration.record_audit(
        organization_id,
        context.user.user_id,
        "analysis.risk_created",
        "analysis",
        analysis_id,
        {"project_name": request.project_name},
    )
    return result


@router.post("/projects/analyze")
def analyze_project_status(
    request: ProjectStatusRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.write")),
):
    organization_id = context.organization.organization_id
    logger.info(
        "Analyzing project status organization_id=%s project_name=%s",
        organization_id,
        request.project_name,
    )
    agent = ProjectStatusAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(project_context=request.project_context, project_name=request.project_name)
    analysis_id = repository.save_analysis(
        kind="status",
        payload=result,
        organization_id=organization_id,
        project_name=request.project_name,
    )
    repository.administration.record_audit(
        organization_id,
        context.user.user_id,
        "analysis.status_created",
        "analysis",
        analysis_id,
        {"project_name": request.project_name},
    )
    return result


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(
    project_name: str | None = None,
    project_id: int | None = None,
    kind: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    organization_id = context.organization.organization_id
    scope_id, scope_name = resolve_project_scope(
        repository, organization_id, project_id, project_name
    )
    logger.info(
        "Listing analyses organization_id=%s project_id=%s project_name=%s kind=%s created_from=%s created_to=%s limit=%d offset=%d",
        organization_id,
        scope_id,
        scope_name,
        kind,
        created_from,
        created_to,
        limit,
        offset,
    )
    return repository.list_analyses(
        organization_id=organization_id,
        project_name=scope_name,
        project_id=scope_id,
        kind=kind,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(
    analysis_id: int,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    logger.info("Fetching analysis id=%s", analysis_id)
    record = repository.get_analysis(analysis_id, context.organization.organization_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record


@router.get("/action-items", response_model=list[ActionItemResponse])
def list_action_items(
    project_name: str | None = None,
    project_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # project_name/project_id are optional: present = Workspace view, absent
    # = portfolio view (FS-007 §2.2) -- same query-parameter design as
    # GET /analyses. project_id takes precedence (TD-008 Phase 3b, Etapa 1).
    organization_id = context.organization.organization_id
    scope_id, scope_name = resolve_project_scope(
        repository, organization_id, project_id, project_name
    )
    logger.info("Listing action items project_id=%s project_name=%s", scope_id, scope_name)
    return service.list_action_items(
        organization_id=organization_id, project_name=scope_name, project_id=scope_id
    )


@router.get("/risks/latest", response_model=list[LatestRiskItemResponse])
def list_latest_risks(
    project_name: str | None = None,
    project_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Same query-parameter design as GET /action-items: project_name/id
    # present = Workspace scope, absent = portfolio scope. Decision
    # Center's single new backend investment (FS-008 §3.1) -- reused by
    # any future Capability needing the latest risk analysis per project.
    organization_id = context.organization.organization_id
    scope_id, scope_name = resolve_project_scope(
        repository, organization_id, project_id, project_name
    )
    logger.info("Listing latest risks project_id=%s project_name=%s", scope_id, scope_name)
    return service.list_latest_risks(
        organization_id=organization_id, project_name=scope_name, project_id=scope_id
    )


@router.get("/projects/summary", response_model=ProjectSummaryResponse)
def get_project_summary(
    project_name: str | None = None,
    project_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # project_name is a query parameter, not a path segment -- Starlette's
    # default path converter cannot capture a literal "/" in a {name}
    # segment (the ASGI server decodes %2F before route matching, so no
    # client-side encoding can work around it). Query parameters don't have
    # this restriction, matching the already-working GET /analyses design.
    # project_id takes precedence when supplied (TD-008 Phase 3b, Etapa 1).
    organization_id = context.organization.organization_id
    if project_id is None and (project_name is None or project_name.strip() == ""):
        raise HTTPException(
            status_code=422, detail="project_name or project_id is required"
        )
    scope_id, scope_name = resolve_project_scope(
        repository, organization_id, project_id, project_name
    )
    logger.info("Summarizing project_id=%s project_name=%s", scope_id, scope_name)
    return service.summarize(
        organization_id=organization_id, project_name=scope_name, project_id=scope_id
    )


@router.get("/portfolio/summary", response_model=list[ProjectSummaryResponse])
def get_portfolio_summary(
    context: RequestContext = Depends(get_request_context),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    logger.info("Summarizing portfolio")
    return service.summarize_portfolio(organization_id=context.organization.organization_id)


@router.post("/risk-advisor/ask", response_model=RiskAdvisorResponse)
def ask_risk_advisor(
    request: RiskAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    # Read-only: reuses the same permission protecting GET /risks/latest,
    # its own data source (Technical Design §2 -- no dedicated permission,
    # this agent never creates/edits/triggers an analysis).
    _permission: None = Depends(require_permission("intelligence.read")),
):
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
        project_name=request.project_name,
    )
    logger.info(
        "Risk Advisor question organization_id=%s project_name=%s",
        session.organization_id,
        session.project_name,
    )

    context_engine = AIContextEngine(repository)
    evidence = context_engine.gather(session.organization_id, session.project_name, kind="risk")

    # Every question is audited, regardless of outcome -- never the model's
    # answer itself (Domain Blueprint §12).
    AIFoundationAudit.record_question(repository, session, "risk_advisor", request.question)

    if not evidence:
        # No LLM call for a project with nothing to synthesize -- avoids
        # cost and a hallucinated answer over non-existent data.
        recommendation = RecommendationEngine.no_evidence(
            "Nenhum risco identificado ainda para este projeto."
        )
        explanation = ExplanationEngine.explain(recommendation)
        return _risk_advisor_response(explanation)

    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=prompts)
    result = agent.advise(session=session, question=request.question, evidence=evidence)
    model_output = result["model_output"]

    if not model_output.get("structured") or not isinstance(model_output.get("answer"), str):
        raise HTTPException(status_code=502, detail="Risk Advisor returned an invalid response")

    recommendation = RecommendationEngine.build(
        model_output["answer"], model_output.get("cited_analysis_ids") or [], evidence
    )
    explanation = ExplanationEngine.explain(recommendation)
    return _risk_advisor_response(explanation)


def _risk_advisor_response(explanation) -> RiskAdvisorResponse:
    return RiskAdvisorResponse(
        answer=explanation.recommendation.answer,
        cited_analyses=[
            CitedAnalysis(
                source_analysis_id=item.source_analysis_id,
                source_created_at=item.source_created_at,
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )
