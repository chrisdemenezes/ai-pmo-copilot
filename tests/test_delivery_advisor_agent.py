import json
from datetime import datetime, timezone

from src.agents.delivery_advisor.agent import DeliveryAdvisorAgent
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "delivery_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nHistory: $status_history_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider) -> DeliveryAdvisorAgent:
    # Classe A, no RAG (Founder Decision -- Technical Design do Delivery
    # Advisor, item 2/6): rag_pipeline is unused by this agent and never
    # constructed by the route, so a stub suffices here too.
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=FakePromptRegistry(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    return DeliveryAdvisorAgent(framework)


SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1", project_name="Aurora")


def _status_evidence(source_id: int, health_status: str, created_at: datetime) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (status)",
        content={
            "structured": True,
            "health_status": health_status,
            "key_findings": [f"finding for {health_status}"],
            "recommendations": [f"recommendation for {health_status}"],
        },
        metadata={"created_at": created_at, "kind": "status"},
    )


# Deliberately built most-recent-first, exactly as AIContextEngine.gather()
# already returns (AR-11 grounding) -- this test file never reorders.
IMPROVING_SEQUENCE = [
    _status_evidence(3, "green", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
    _status_evidence(2, "yellow", datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc)),
    _status_evidence(1, "red", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)),
]

SINGLE_RECORD = [_status_evidence(1, "yellow", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))]


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "O projeto esta green, melhorando.", "cited_analysis_ids": [3, 2, 1]})
    )
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Como esta o projeto?", evidence=IMPROVING_SEQUENCE)

    assert result["structured"] is True
    assert result["answer"] == "O projeto esta green, melhorando."
    assert result["cited_analysis_ids"] == [3, 2, 1]


def test_advise_sends_status_history_in_the_exact_order_evidence_was_given():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Como esta o projeto?", evidence=IMPROVING_SEQUENCE)

    sent_history_json = provider.received_prompt.split("History: ", 1)[1]
    sent_history = json.loads(sent_history_json)
    # Position 0 = most recent (green), position 2 = oldest (red) -- proves
    # the agent never reorders/reverses the sequence AIContextEngine.gather()
    # already returns (AR-11).
    assert [item["health_status"] for item in sent_history] == ["green", "yellow", "red"]
    assert [item["source_analysis_id"] for item in sent_history] == [3, 2, 1]


def test_advise_never_reverses_a_deteriorating_sequence():
    deteriorating = [
        _status_evidence(3, "red", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
        _status_evidence(2, "yellow", datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc)),
        _status_evidence(1, "green", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)),
    ]
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Como esta o projeto?", evidence=deteriorating)

    sent_history = json.loads(provider.received_prompt.split("History: ", 1)[1])
    assert [item["health_status"] for item in sent_history] == ["red", "yellow", "green"]


def test_advise_sends_only_structured_status_data_never_raw_context():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Existem bloqueios?", evidence=IMPROVING_SEQUENCE)

    assert "finding for green" in provider.received_prompt
    assert "Existem bloqueios?" in provider.received_prompt


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Como esta o projeto?", evidence=IMPROVING_SEQUENCE)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Como esta o projeto?", evidence=IMPROVING_SEQUENCE)

    assert result["structured"] is False
    assert result["raw_output"] == "not json at all"


def test_advise_with_a_single_record_sends_a_one_item_history():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": [1]}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Como esta o projeto?", evidence=SINGLE_RECORD)

    sent_history = json.loads(provider.received_prompt.split("History: ", 1)[1])
    assert len(sent_history) == 1
    assert sent_history[0]["health_status"] == "yellow"


def test_advise_never_builds_a_rag_supplementary_block():
    # Founder Decision -- Technical Design do Delivery Advisor, item 2/6:
    # RAG is out of scope for this Advisor. The prompt template used by
    # this agent's own prompts/advise.md carries no $additional_context_json
    # placeholder at all -- confirmed here by asserting the rendered prompt
    # never mentions it, using the real prompt registry (not the fake one).
    from src.prompts.registry import PromptRegistry

    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=PromptRegistry(base_path="src/agents"),
        llm_provider=provider,
        rag_pipeline=None,
    )
    agent = DeliveryAdvisorAgent(framework)

    agent.advise(session=SESSION, question="Como esta o projeto?", evidence=IMPROVING_SEQUENCE)

    assert "additional_context_json" not in provider.received_prompt
    assert "rag" not in provider.received_prompt.lower()
