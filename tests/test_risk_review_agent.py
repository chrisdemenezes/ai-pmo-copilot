from src.agents.risk_review.agent import RiskReviewAgent


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "risk_review"
        assert prompt_name == "analysis"
        return "Project: $project_name\nContext: $project_context"


class FakeModelClient:
    def generate(self, prompt):
        assert "Project: Medlog" in prompt
        assert "Context:" in prompt
        return "analysis generated"


def test_agent_falls_back_to_raw_output_when_not_json():
    agent = RiskReviewAgent(
        model_client=FakeModelClient(),
        prompt_registry=FakePromptRegistry(),
    )

    result = agent.analyze(
        project_name="Medlog",
        project_context="Timeline and resource constraints require mitigation actions.",
    )

    assert result["agent"] == "risk_review"
    assert result["project_name"] == "Medlog"
    assert result["model_output"] == {"structured": False, "raw_output": "analysis generated"}


class FakeModelClientReturningJson:
    def generate(self, prompt):
        return (
            '{"risks": [{"description": "Schedule slip", "probability": "medium", '
            '"impact": "high", "mitigation": "Add buffer"}], '
            '"escalation_recommendation": "Notify sponsor"}'
        )


def test_agent_parses_structured_json_output():
    agent = RiskReviewAgent(
        model_client=FakeModelClientReturningJson(),
        prompt_registry=FakePromptRegistry(),
    )

    result = agent.analyze(project_name="Medlog", project_context="Timeline constraints.")

    assert result["model_output"]["structured"] is True
    assert result["model_output"]["risks"][0]["description"] == "Schedule slip"
    assert result["model_output"]["risks"][0]["probability"] == "medium"
    assert result["model_output"]["escalation_recommendation"] == "Notify sponsor"
