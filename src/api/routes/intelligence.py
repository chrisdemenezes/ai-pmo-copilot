import logging
from datetime import datetime
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException

from src.agents.meeting_intelligence.agent import MeetingIntelligenceAgent
from src.agents.project_status.agent import ProjectStatusAgent
from src.agents.risk_review.agent import RiskReviewAgent
from src.api.rate_limiter import enforce_rate_limit
from src.api.security import verify_api_key
from src.llm.providers.base import LLMProvider
from src.llm.providers.factory import get_provider
from src.prompts.registry import PromptRegistry
from src.database.repository import AnalysisRepository
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


def build_prompt_registry() -> PromptRegistry:
    return PromptRegistry(base_path="src/agents")


def build_provider() -> LLMProvider:
    return get_provider()


@lru_cache
def build_repository() -> AnalysisRepository:
    return AnalysisRepository()


def build_project_summary_service(
    repository: AnalysisRepository = Depends(build_repository),
) -> ProjectSummaryService:
    return ProjectSummaryService(repository=repository)


@router.post("/meetings/analyze")
def analyze_meeting(
    request: MeetingAnalysisRequest,
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
):
    logger.info("Analyzing meeting for project_name=%s", request.project_name)
    agent = MeetingIntelligenceAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(transcript=request.transcript, project_name=request.project_name)
    repository.save_analysis(kind="meeting", payload=result, project_name=request.project_name)
    return result


@router.post("/risks/analyze")
def analyze_risk(
    request: RiskAnalysisRequest,
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
):
    logger.info("Analyzing risk for project_name=%s", request.project_name)
    agent = RiskReviewAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(project_context=request.project_context, project_name=request.project_name)
    repository.save_analysis(kind="risk", payload=result, project_name=request.project_name)
    return result


@router.post("/projects/analyze")
def analyze_project_status(
    request: ProjectStatusRequest,
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
):
    logger.info("Analyzing project status for project_name=%s", request.project_name)
    agent = ProjectStatusAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(project_context=request.project_context, project_name=request.project_name)
    repository.save_analysis(kind="status", payload=result, project_name=request.project_name)
    return result


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(
    project_name: str | None = None,
    kind: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
    repository: AnalysisRepository = Depends(build_repository),
):
    logger.info(
        "Listing analyses project_name=%s kind=%s created_from=%s created_to=%s limit=%d offset=%d",
        project_name,
        kind,
        created_from,
        created_to,
        limit,
        offset,
    )
    return repository.list_analyses(
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
    repository: AnalysisRepository = Depends(build_repository),
):
    logger.info("Fetching analysis id=%s", analysis_id)
    record = repository.get_analysis(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record


@router.get("/action-items", response_model=list[ActionItemResponse])
def list_action_items(
    project_name: str | None = None,
    service: ProjectSummaryService = Depends(build_project_summary_service),
):
    # project_name is optional: present = Workspace view, absent = portfolio
    # view (FS-007 §2.2) -- same query-parameter design as GET /analyses.
    logger.info("Listing action items project_name=%s", project_name)
    return service.list_action_items(project_name=project_name)


@router.get("/risks/latest", response_model=list[LatestRiskItemResponse])
def list_latest_risks(
    project_name: str | None = None,
    service: ProjectSummaryService = Depends(build_project_summary_service),
):
    # Same query-parameter design as GET /action-items: project_name
    # present = Workspace scope, absent = portfolio scope. Decision
    # Center's single new backend investment (FS-008 §3.1) -- reused by
    # any future Capability needing the latest risk analysis per project.
    logger.info("Listing latest risks project_name=%s", project_name)
    return service.list_latest_risks(project_name=project_name)


@router.get("/projects/summary", response_model=ProjectSummaryResponse)
def get_project_summary(
    project_name: str,
    service: ProjectSummaryService = Depends(build_project_summary_service),
):
    # project_name is a query parameter, not a path segment -- Starlette's
    # default path converter cannot capture a literal "/" in a {name}
    # segment (the ASGI server decodes %2F before route matching, so no
    # client-side encoding can work around it). Query parameters don't have
    # this restriction, matching the already-working GET /analyses design.
    logger.info("Summarizing project_name=%s", project_name)
    return service.summarize(project_name=project_name)


@router.get("/portfolio/summary", response_model=list[ProjectSummaryResponse])
def get_portfolio_summary(
    service: ProjectSummaryService = Depends(build_project_summary_service),
):
    logger.info("Summarizing portfolio")
    return service.summarize_portfolio()
