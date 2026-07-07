from functools import lru_cache

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from src.agents.meeting_intelligence.agent import MeetingIntelligenceAgent
from src.agents.risk_review.agent import RiskReviewAgent
from src.llm.providers.base import LLMProvider
from src.llm.providers.factory import get_provider
from src.prompts.registry import PromptRegistry
from src.database.repository import AnalysisRepository

router = APIRouter()


class MeetingAnalysisRequest(BaseModel):
    transcript: str = Field(..., min_length=10)
    project_name: str | None = None


class RiskAnalysisRequest(BaseModel):
    project_context: str = Field(..., min_length=10)
    project_name: str | None = None


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
    agent = MeetingIntelligenceAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(transcript=request.transcript, project_name=request.project_name)
    repository.save_analysis(kind="meeting", payload=result)
    return result


@router.post("/risks/analyze")
def analyze_risk(
    request: RiskAnalysisRequest,
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
):
    agent = RiskReviewAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(project_context=request.project_context, project_name=request.project_name)
    repository.save_analysis(kind="risk", payload=result)
    return result
