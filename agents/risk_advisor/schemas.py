from pydantic import BaseModel
from typing import List

class RiskAnalysisRequest(BaseModel):
    project_name: str
    risks: List[str] = []
    issues: List[str] = []

class RiskAnalysisResponse(BaseModel):
    risk_level: str
    identified_risks: List[str]
    mitigation_actions: List[str]
    confidence_score: float = 0.0
