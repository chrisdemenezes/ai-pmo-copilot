import logging
from datetime import datetime
from functools import lru_cache

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from src.agents.meeting_intelligence.agent import MeetingIntelligenceAgent
from src.agents.risk_review.agent import RiskReviewAgent
from src.llm.providers.base import LLMProvider
from src.llm.providers.factory import get_provider
from src.prompts.registry import PromptRegistry
from src.database.repository import AnalysisRepository

logger = logging.getLogger(__name__)

router = APIRouter()


class MeetingAnalysisRequest(BaseModel):
    transcript: str = Field(..., min_length=10)
    project_name: str | None = None


class RiskAnalysisRequest(BaseModel):
    project_context: str = Field(..., min_length=10)
    project_name: str | None = None


class AnalysisSummary(BaseModel):
    id: int
    kind: str
    project_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisDetail(AnalysisSummary):
    payload: dict


def build_prompt_registry() -> PromptRegistry:
    return PromptRegistry(base_path="src/agents")


def build_provider() -> LLMProvider:
    return get_provider()


@lru_cache
def build_repository() -> AnalysisRepository:
    return AnalysisRepository()


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
