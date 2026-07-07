class AIService:
    """Central service for AI provider integrations."""

    def analyze_meeting(self, transcript: str):
        from agents.meeting_intelligence.agent import MeetingIntelligenceAgent

        agent = MeetingIntelligenceAgent()
        return agent.analyze(transcript)
