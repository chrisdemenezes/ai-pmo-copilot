from src.agents.project_status.agent import ProjectStatusAgent


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "project_status"
        assert prompt_name == "analysis"
        return "Project: $project_name\nContext: $project_context"


class FakeModelClient:
    def generate(self, prompt):
        assert "Project: Medlog" in prompt
        assert "Context:" in prompt
        return "status generated"


def test_agent_falls_back_to_raw_output_when_not_json():
    agent = ProjectStatusAgent(
        model_client=FakeModelClient(),
        prompt_registry=FakePromptRegistry(),
    )

    result = agent.analyze(
        project_name="Medlog",
        project_context="Schedule slipping two weeks, budget on track.",
    )

    assert result["agent"] == "project_status"
    assert result["project_name"] == "Medlog"
    assert result["model_output"] == {"structured": False, "raw_output": "status generated"}


class FakeModelClientReturningJson:
    def generate(self, prompt):
        return (
            '{"health_status": "yellow", "key_findings": ["Schedule slipping two weeks"], '
            '"recommendations": ["Re-baseline the plan"]}'
        )


def test_agent_parses_structured_json_output():
    agent = ProjectStatusAgent(
        model_client=FakeModelClientReturningJson(),
        prompt_registry=FakePromptRegistry(),
    )

    result = agent.analyze(project_name="Medlog", project_context="Schedule slipping two weeks.")

    assert result["model_output"]["structured"] is True
    assert result["model_output"]["health_status"] == "yellow"
    assert result["model_output"]["key_findings"] == ["Schedule slipping two weeks"]
    assert result["model_output"]["recommendations"] == ["Re-baseline the plan"]
