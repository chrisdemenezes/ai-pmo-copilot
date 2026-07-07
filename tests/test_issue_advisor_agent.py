from src.agents.issue_advisor.agent import IssueAdvisorAgent


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "issue_advisor"
        assert prompt_name == "analysis"
        return "Project: {project_name}\nContext: {project_context}"


class FakeModelClient:
    def generate(self, prompt):
        assert "Project: Medlog" in prompt
        assert "Context:" in prompt
        return "issue analysis generated"


def test_issue_advisor_agent_uses_prompt_and_model_client():
    agent = IssueAdvisorAgent(
        model_client=FakeModelClient(),
        prompt_registry=FakePromptRegistry(),
    )

    result = agent.analyze(
        project_name="Medlog",
        project_context="Project has open issues requiring decision and escalation.",
    )

    assert result["agent"] == "issue_advisor"
    assert result["project_name"] == "Medlog"
    assert result["model_output"] == "issue analysis generated"
