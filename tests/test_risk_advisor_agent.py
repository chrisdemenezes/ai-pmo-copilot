import json
from datetime import datetime, timezone

from src.agents.risk_advisor.agent import RiskAdvisorAgent
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "risk_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nRisks: $risks_json\nExtra: $additional_context_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider) -> RiskAdvisorAgent:
    # Wave 3 Fase 4: the Agent is constructed from an AdvisorFramework, not
    # a raw model_client/prompt_registry pair -- rag_pipeline is unused by
    # these tests (they exercise `advise()` directly, never
    # `framework.gather_rag_context()`), so a stub suffices.
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=FakePromptRegistry(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    return RiskAdvisorAgent(framework)


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
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Qual o risco mais crítico?", evidence=SAMPLE_EVIDENCE)

    assert result["structured"] is True
    assert result["answer"] == "O risco mais crítico é o atraso no fornecedor."
    assert result["cited_analysis_ids"] == [7]


def test_advise_sends_only_structured_risk_data_never_raw_context():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Algum risco recorrente?", evidence=SAMPLE_EVIDENCE)

    assert "Atraso no fornecedor de middleware" in provider.received_prompt
    assert "Algum risco recorrente?" in provider.received_prompt


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Algum risco recorrente?", evidence=SAMPLE_EVIDENCE)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Qual o risco mais crítico?", evidence=SAMPLE_EVIDENCE)

    assert result["structured"] is False
    assert result["raw_output"] == "not json at all"


def test_advise_includes_supplementary_rag_context_when_supplied():
    from src.services.knowledge_platform.rag_pipeline import RagContext
    from src.services.knowledge_platform.types import ScoredChunk

    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    rag_context = RagContext(
        query="middleware delay",
        organization_id=1,
        chunks=[
            ScoredChunk(
                chunk_id=1,
                document_id=1,
                text="the middleware vendor has a history of delayed delivery",
                score=0.9,
                document_version_created_at=datetime.now(timezone.utc),
            )
        ],
    )

    agent.advise(session=SESSION, question="Algum risco recorrente?", evidence=SAMPLE_EVIDENCE, rag_context=rag_context)

    assert "delayed delivery" in provider.received_prompt


def test_advise_supplementary_context_is_empty_without_rag_context():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Algum risco recorrente?", evidence=SAMPLE_EVIDENCE)

    assert "Extra: []" in provider.received_prompt
