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
from src.llm.providers.base import LLMProvider
from src.llm.providers.factory import get_provider
from src.prompts.registry import PromptRegistry
from src.database.repository import AnalysisRepository
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
    logger.info(
        "Listing analyses organization_id=%s project_name=%s kind=%s created_from=%s created_to=%s limit=%d offset=%d",
        organization_id,
        project_name,
        kind,
        created_from,
        created_to,
        limit,
        offset,
    )
    return repository.list_analyses(
        organization_id=organization_id,
        project_name=project_name,
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
    context: RequestContext = Depends(get_request_context),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # project_name is optional: present = Workspace view, absent = portfolio
    # view (FS-007 §2.2) -- same query-parameter design as GET /analyses.
    logger.info("Listing action items project_name=%s", project_name)
    return service.list_action_items(
        organization_id=context.organization.organization_id, project_name=project_name
    )


@router.get("/risks/latest", response_model=list[LatestRiskItemResponse])
def list_latest_risks(
    project_name: str | None = None,
    context: RequestContext = Depends(get_request_context),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Same query-parameter design as GET /action-items: project_name
    # present = Workspace scope, absent = portfolio scope. Decision
    # Center's single new backend investment (FS-008 §3.1) -- reused by
    # any future Capability needing the latest risk analysis per project.
    logger.info("Listing latest risks project_name=%s", project_name)
    return service.list_latest_risks(
        organization_id=context.organization.organization_id, project_name=project_name
    )


@router.get("/projects/summary", response_model=ProjectSummaryResponse)
def get_project_summary(
    project_name: str,
    context: RequestContext = Depends(get_request_context),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # project_name is a query parameter, not a path segment -- Starlette's
    # default path converter cannot capture a literal "/" in a {name}
    # segment (the ASGI server decodes %2F before route matching, so no
    # client-side encoding can work around it). Query parameters don't have
    # this restriction, matching the already-working GET /analyses design.
    logger.info("Summarizing project_name=%s", project_name)
    return service.summarize(
        organization_id=context.organization.organization_id, project_name=project_name
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
    service: ProjectSummaryService = Depends(build_project_summary_service),
    # Read-only: reuses the same permission protecting GET /risks/latest,
    # its own data source (Technical Design §2 -- no dedicated permission,
    # this agent never creates/edits/triggers an analysis).
    _permission: None = Depends(require_permission("intelligence.read")),
):
    organization_id = context.organization.organization_id
    logger.info(
        "Risk Advisor question organization_id=%s project_name=%s",
        organization_id,
        request.project_name,
    )
    risks = service.list_latest_risks(
        organization_id=organization_id, project_name=request.project_name
    )

    # Every question is audited, regardless of outcome -- never the model's
    # answer itself (Domain Blueprint §12).
    repository.administration.record_audit(
        organization_id,
        context.user.user_id,
        "risk_advisor.question_asked",
        "project",
        None,
        {"project_name": request.project_name, "question": request.question},
    )

    if not risks:
        # No LLM call for a project with nothing to synthesize -- avoids
        # cost and a hallucinated answer over non-existent data.
        return RiskAdvisorResponse(
            answer="Nenhum risco identificado ainda para este projeto.",
            cited_analyses=[],
        )

    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=prompts)
    result = agent.advise(question=request.question, risks=risks)
    model_output = result["model_output"]

    if not model_output.get("structured") or not isinstance(model_output.get("answer"), str):
        raise HTTPException(status_code=502, detail="Risk Advisor returned an invalid response")

    risks_by_id = {risk["source_analysis_id"]: risk for risk in risks}
    cited_analyses = [
        CitedAnalysis(
            source_analysis_id=risk_id,
            source_created_at=risks_by_id[risk_id]["source_created_at"],
        )
        for risk_id in model_output.get("cited_analysis_ids") or []
        if risk_id in risks_by_id
    ]

    return RiskAdvisorResponse(answer=model_output["answer"], cited_analyses=cited_analyses)
