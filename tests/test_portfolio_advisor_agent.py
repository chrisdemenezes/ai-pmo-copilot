import json
from datetime import datetime, timezone

from src.agents.portfolio_advisor.agent import PortfolioAdvisorAgent
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "portfolio_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nProjects: $projects_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider) -> PortfolioAdvisorAgent:
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=FakePromptRegistry(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    return PortfolioAdvisorAgent(framework)


SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1")


def _project_evidence(source_id: int, project_id: int, project_name: str, health_status: str) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (status)",
        content={"structured": True, "health_status": health_status, "key_findings": [], "recommendations": []},
        metadata={
            "created_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
            "kind": "status",
            "portfolio_id": 10,
            "program_id": 20,
            "project_id": project_id,
            "project_name": project_name,
        },
    )


PORTFOLIO_EVIDENCE = [
    _project_evidence(1, 30, "Aurora", "green"),
    _project_evidence(2, 31, "Boreal", "red"),
]


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "Aurora esta green, Boreal esta red.", "cited_analysis_ids": [1, 2]})
    )
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Como esta o portfolio?", evidence=PORTFOLIO_EVIDENCE)

    assert result["structured"] is True
    assert result["cited_analysis_ids"] == [1, 2]


def test_advise_serializes_project_id_and_name_for_each_project():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Quais projetos precisam de atencao?", evidence=PORTFOLIO_EVIDENCE)

    sent_projects = json.loads(provider.received_prompt.split("Projects: ", 1)[1])
    assert [p["project_name"] for p in sent_projects] == ["Aurora", "Boreal"]
    assert [p["project_id"] for p in sent_projects] == [30, 31]
    assert [p["health_status"] for p in sent_projects] == ["green", "red"]


def test_advise_never_reorders_the_evidence_it_receives():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    reversed_evidence = list(reversed(PORTFOLIO_EVIDENCE))

    agent.advise(session=SESSION, question="Como esta o portfolio?", evidence=reversed_evidence)

    sent_projects = json.loads(provider.received_prompt.split("Projects: ", 1)[1])
    # Whatever order the Assembler handed to the agent is preserved exactly
    # -- the agent itself never reorders/sorts/weighs.
    assert [p["project_name"] for p in sent_projects] == ["Boreal", "Aurora"]


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Como esta o portfolio?", evidence=PORTFOLIO_EVIDENCE)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Como esta o portfolio?", evidence=PORTFOLIO_EVIDENCE)

    assert result["structured"] is False
    assert result["raw_output"] == "not json at all"
