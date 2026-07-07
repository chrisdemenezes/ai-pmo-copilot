from .processor import clean_transcript
from .schemas import MeetingAnalysis

class MeetingIntelligenceAgent:
    def analyze(self, transcript: str) -> MeetingAnalysis:
        content = clean_transcript(transcript)

        return MeetingAnalysis(
            summary=f"Analysis generated for transcript with {len(content)} characters.",
            decisions=[],
            actions=[],
            risks=[],
            confidence_score=0.5
        )
