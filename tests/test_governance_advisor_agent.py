import json

from src.agents.governance_advisor.agent import GovernanceAdvisorAgent
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "governance_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nChunks: $chunks_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider) -> GovernanceAdvisorAgent:
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=FakePromptRegistry(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    return GovernanceAdvisorAgent(framework)


SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1")

SAMPLE_EVIDENCE = [
    Evidence(
        source_type="document_chunk",
        source_id=7,
        source_label="Document 3 / Chunk 7",
        content={"text": "D-090: Knowledge Version Resolution registrada, nao resolvida"},
        metadata={"document_id": 3, "score": 0.9, "created_at": None},
    )
]


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "[CONFORME]\nA politica esta documentada.", "cited_analysis_ids": [7]})
    )
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="A politica esta documentada?", evidence=SAMPLE_EVIDENCE)

    assert result["structured"] is True
    assert result["answer"] == "[CONFORME]\nA politica esta documentada."
    assert result["cited_analysis_ids"] == [7]


def test_advise_sends_chunk_data_including_source_label():
    provider = RecordingProvider(json.dumps({"answer": "[CONFORME]\nok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Alguma referencia?", evidence=SAMPLE_EVIDENCE)

    assert "Knowledge Version Resolution" in provider.received_prompt
    assert '"chunk_id": 7' in provider.received_prompt
    assert '"document_id": 3' in provider.received_prompt
    assert '"source_label": "Document 3 / Chunk 7"' in provider.received_prompt


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "[CONFORME]\nok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Alguma referencia?", evidence=SAMPLE_EVIDENCE)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Alguma referencia?", evidence=SAMPLE_EVIDENCE)

    assert result["structured"] is False
    assert result["raw_output"] == "not json at all"


def test_advise_with_no_evidence_sends_an_empty_chunk_array():
    provider = RecordingProvider(json.dumps({"answer": "[SEM EVIDÊNCIA]\nok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Algo?", evidence=[])

    assert "Chunks: []" in provider.received_prompt
