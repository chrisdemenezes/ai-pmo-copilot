from src.agents.risk_review.agent import RiskReviewAgent


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "risk_review"
        assert prompt_name == "analysis"
        return "Project: {project_name}\nContext: {project_context}"


class FakeModelClient:
    def generate(self, prompt):
        assert "Project: Medlog" in prompt
        assert "Context:" in prompt
        return "analysis generated"


def test_agent_uses_prompt_and_model_client():
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
    assert result["model_output"] == "analysis generated"
