import json
from datetime import datetime, timezone

from src.agents.risk_advisor.agent import RiskAdvisorAgent
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "risk_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nRisks: $risks_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1", project_name="Aurora")

SAMPLE_EVIDENCE = [
    Evidence(
        source_analysis_id=7,
        source_created_at=datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc),
        kind="risk",
        summary={
            "structured": True,
            "risks": [
                {
                    "description": "Atraso no fornecedor de middleware",
                    "probability": "high",
                    "impact": "high",
                    "mitigation": "Escalar ao patrocinador",
                }
            ],
            "escalation_recommendation": "Escalar ao comitê executivo",
        },
    )
]


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "O risco mais crítico é o atraso no fornecedor.", "cited_analysis_ids": [7]})
    )
    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=FakePromptRegistry())

    result = agent.advise(session=SESSION, question="Qual o risco mais crítico?", evidence=SAMPLE_EVIDENCE)

    assert result["agent"] == "risk_advisor"
    assert result["model_output"]["structured"] is True
    assert result["model_output"]["answer"] == "O risco mais crítico é o atraso no fornecedor."
    assert result["model_output"]["cited_analysis_ids"] == [7]


def test_advise_sends_only_structured_risk_data_never_raw_context():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=FakePromptRegistry())

    agent.advise(session=SESSION, question="Algum risco recorrente?", evidence=SAMPLE_EVIDENCE)

    assert "Atraso no fornecedor de middleware" in provider.received_prompt
    assert "Algum risco recorrente?" in provider.received_prompt


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=FakePromptRegistry())

    agent.advise(session=SESSION, question="Algum risco recorrente?", evidence=SAMPLE_EVIDENCE)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=FakePromptRegistry())

    result = agent.advise(session=SESSION, question="Qual o risco mais crítico?", evidence=SAMPLE_EVIDENCE)

    assert result["model_output"]["structured"] is False
    assert result["model_output"]["raw_output"] == "not json at all"
