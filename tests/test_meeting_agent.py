from src.agents.meeting_intelligence.agent import MeetingIntelligenceAgent


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "meeting_intelligence"
        assert prompt_name == "analysis"
        return "Project: {project_name}\nTranscript: {transcript}"


class FakeModelClient:
    def generate(self, prompt):
        assert "Project: Multilift" in prompt
        assert "Transcript:" in prompt
        return "summary generated"


def test_meeting_agent_uses_prompt_and_model_client():
    agent = MeetingIntelligenceAgent(
        model_client=FakeModelClient(),
        prompt_registry=FakePromptRegistry(),
    )

    result = agent.analyze(
        project_name="Multilift",
        transcript="Client approved the handover and requested action tracking.",
    )

    assert result["agent"] == "meeting_intelligence"
    assert result["project_name"] == "Multilift"
    assert result["model_output"] == "summary generated"
