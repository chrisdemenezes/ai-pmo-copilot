from src.agents.meeting_intelligence.agent import MeetingIntelligenceAgent


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "meeting_intelligence"
        assert prompt_name == "analysis"
        return "Project: $project_name\nTranscript: $transcript"


class FakeModelClient:
    def generate(self, prompt):
        assert "Project: Multilift" in prompt
        assert "Transcript:" in prompt
        return "summary generated"


def test_meeting_agent_falls_back_to_raw_output_when_not_json():
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
    assert result["model_output"] == {"structured": False, "raw_output": "summary generated"}


class FakeModelClientReturningJson:
    def generate(self, prompt):
        return (
            '{"summary": "Handover approved", "decisions": ["Approve handover"], '
            '"action_items": [{"description": "Track actions", "owner": "PM", "due_date": null}], '
            '"issues": [], "dependencies": []}'
        )


def test_meeting_agent_parses_structured_json_output():
    agent = MeetingIntelligenceAgent(
        model_client=FakeModelClientReturningJson(),
        prompt_registry=FakePromptRegistry(),
    )

    result = agent.analyze(project_name="Multilift", transcript="Client approved the handover.")

    assert result["model_output"]["structured"] is True
    assert result["model_output"]["summary"] == "Handover approved"
    assert result["model_output"]["decisions"] == ["Approve handover"]
    assert result["model_output"]["action_items"][0]["owner"] == "PM"


class FakePromptRegistryWithJsonBraces:
    def get(self, agent_name, prompt_name):
        return 'Return JSON like {"decisions": [...]}. Project: $project_name\nTranscript: $transcript'


class FakeModelClientCapturingPrompt:
    def __init__(self):
        self.received_prompt = None

    def generate(self, prompt):
        self.received_prompt = prompt
        return "summary generated"


def test_meeting_agent_tolerates_literal_braces_in_prompt_template():
    model_client = FakeModelClientCapturingPrompt()
    agent = MeetingIntelligenceAgent(
        model_client=model_client,
        prompt_registry=FakePromptRegistryWithJsonBraces(),
    )

    agent.analyze(project_name="Multilift", transcript="Client approved the handover.")

    assert '{"decisions": [...]}' in model_client.received_prompt
    assert "Project: Multilift" in model_client.received_prompt
