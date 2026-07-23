import json

from src.agents.risk_advisor.agent import RiskAdvisorAgent


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


SAMPLE_RISKS = [
    {
        "description": "Atraso no fornecedor de middleware",
        "probability": "high",
        "impact": "high",
        "mitigation": "Escalar ao patrocinador",
        "escalation_recommendation": "Escalar ao comitê executivo",
        "source_analysis_id": 7,
        "source_created_at": "2026-07-10T14:00:00",
    }
]


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "O risco mais crítico é o atraso no fornecedor.", "cited_analysis_ids": [7]})
    )
    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=FakePromptRegistry())

    result = agent.advise(question="Qual o risco mais crítico?", risks=SAMPLE_RISKS)

    assert result["agent"] == "risk_advisor"
    assert result["model_output"]["structured"] is True
    assert result["model_output"]["answer"] == "O risco mais crítico é o atraso no fornecedor."
    assert result["model_output"]["cited_analysis_ids"] == [7]


def test_advise_sends_only_structured_risk_data_never_raw_context():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=FakePromptRegistry())

    agent.advise(question="Algum risco recorrente?", risks=SAMPLE_RISKS)

    assert "Atraso no fornecedor de middleware" in provider.received_prompt
    assert "Algum risco recorrente?" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=FakePromptRegistry())

    result = agent.advise(question="Qual o risco mais crítico?", risks=SAMPLE_RISKS)

    assert result["model_output"]["structured"] is False
    assert result["model_output"]["raw_output"] == "not json at all"
