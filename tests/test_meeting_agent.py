from agents.meeting_intelligence.agent import MeetingIntelligenceAgent


def test_meeting_agent_returns_analysis():
    agent = MeetingIntelligenceAgent()
    result = agent.analyze("The deployment will happen on Friday.")

    assert result.summary is not None
    assert result.confidence_score >= 0
