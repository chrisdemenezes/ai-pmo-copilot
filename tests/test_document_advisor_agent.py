import json

from src.agents.document_advisor.agent import DocumentAdvisorAgent
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "document_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nChunks: $chunks_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider) -> DocumentAdvisorAgent:
    # rag_pipeline is unused by these tests -- they exercise advise()
    # directly, never framework.gather_rag_context(), so a stub suffices
    # (same pattern as test_risk_advisor_agent.py).
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=FakePromptRegistry(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    return DocumentAdvisorAgent(framework)


SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1")

SAMPLE_EVIDENCE = [
    Evidence(
        source_type="document_chunk",
        source_id=42,
        source_label="Document 7 / Chunk 42",
        content={"text": "the middleware vendor has a history of delayed delivery"},
        metadata={"document_id": 7, "score": 0.9, "created_at": None},
    )
]


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "O documento indica atraso recorrente.", "cited_analysis_ids": [42]})
    )
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="O que o documento diz sobre atrasos?", evidence=SAMPLE_EVIDENCE)

    assert result["structured"] is True
    assert result["answer"] == "O documento indica atraso recorrente."
    assert result["cited_analysis_ids"] == [42]


def test_advise_sends_only_chunk_data_never_raw_document_text_outside_evidence():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Algum atraso relatado?", evidence=SAMPLE_EVIDENCE)

    assert "delayed delivery" in provider.received_prompt
    assert "Algum atraso relatado?" in provider.received_prompt
    assert '"chunk_id": 42' in provider.received_prompt
    assert '"document_id": 7' in provider.received_prompt


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Algum atraso relatado?", evidence=SAMPLE_EVIDENCE)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="O que o documento diz?", evidence=SAMPLE_EVIDENCE)

    assert result["structured"] is False
    assert result["raw_output"] == "not json at all"


def test_advise_with_no_evidence_sends_an_empty_chunk_array():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Algo?", evidence=[])

    assert "Chunks: []" in provider.received_prompt
