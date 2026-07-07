from fastapi import APIRouter

from agents.meeting_intelligence.schemas import MeetingRequest
from backend.app.services.ai_service import AIService

router = APIRouter(prefix="/api/meetings")
ai_service = AIService()

@router.post("/process")
def process_meeting(payload: MeetingRequest):
    result = ai_service.analyze_meeting(payload.transcript)
    return result
