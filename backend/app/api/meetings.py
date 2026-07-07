from fastapi import APIRouter

router = APIRouter(prefix="/api/meetings")

@router.post("/process")
def process_meeting(payload: dict):
    return {
        "summary": "Processing pending AI analysis",
        "decisions": [],
        "actions": [],
        "risks": []
    }
