from pydantic import BaseModel
from typing import List

class MeetingRequest(BaseModel):
    transcript: str
    project_context: str | None = None
    participants: List[str] = []

class MeetingAnalysis(BaseModel):
    summary: str
    decisions: List[str]
    actions: List[str]
    risks: List[str]
    confidence_score: float = 0.0
