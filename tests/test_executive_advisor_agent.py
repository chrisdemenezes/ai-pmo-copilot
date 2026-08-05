import json
from datetime import datetime, timezone

from src.agents.executive_advisor.agent import ExecutiveAdvisorAgent
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "executive_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nRecords: $records_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider) -> ExecutiveAdvisorAgent:
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=FakePromptRegistry(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    return ExecutiveAdvisorAgent(framework)


SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1")


def _status_evidence(source_id: int, project_id: int, project_name: str) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (status)",
        content={"structured": True, "health_status": "green", "key_findings": [], "recommendations": []},
        metadata={
            "created_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
            "kind": "status",
            "project_id": project_id,
            "project_name": project_name,
        },
    )


def _risk_evidence(source_id: int, project_id: int, project_name: str) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (risk)",
        content={
            "structured": True,
            "risks": [{"description": "atraso de fornecedor", "probability": "medium", "impact": "high", "mitigation": "buffer"}],
            "escalation_recommendation": None,
        },
        metadata={
            "created_at": datetime(2026, 8, 2, tzinfo=timezone.utc),
            "kind": "risk",
            "project_id": project_id,
            "project_name": project_name,
        },
    )


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "Aurora esta green mas com risco de fornecedor.", "cited_analysis_ids": [1, 2]})
    )
    agent = _agent(provider)
    evidence = [_status_evidence(1, 30, "Aurora"), _risk_evidence(2, 30, "Aurora")]

    result = agent.advise(session=SESSION, question="O que exige atencao agora?", evidence=evidence)

    assert result["structured"] is True
    assert result["cited_analysis_ids"] == [1, 2]


def test_advise_serializes_content_unflattened_with_kind_distinguishing_shape():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    evidence = [_status_evidence(1, 30, "Aurora"), _risk_evidence(2, 30, "Aurora")]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    status_record = next(r for r in sent_records if r["kind"] == "status")
    risk_record = next(r for r in sent_records if r["kind"] == "risk")
    # content is never flattened -- each kind keeps its own real shape.
    assert status_record["content"] == {
        "structured": True,
        "health_status": "green",
        "key_findings": [],
        "recommendations": [],
    }
    assert risk_record["content"]["risks"][0]["description"] == "atraso de fornecedor"
    assert "health_status" not in risk_record["content"]


def test_advise_serializes_two_citations_of_the_same_project_with_different_kinds():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": [10, 11]}))
    agent = _agent(provider)
    evidence = [_status_evidence(10, 30, "Aurora"), _risk_evidence(11, 30, "Aurora")]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert [r["source_analysis_id"] for r in sent_records] == [10, 11]
    assert [r["project_id"] for r in sent_records] == [30, 30]
    assert [r["kind"] for r in sent_records] == ["status", "risk"]


def test_advise_never_reorders_the_evidence_it_receives():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    evidence = [_risk_evidence(2, 30, "Aurora"), _status_evidence(1, 30, "Aurora")]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert [r["kind"] for r in sent_records] == ["risk", "status"]


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    evidence = [_status_evidence(1, 30, "Aurora")]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = _agent(provider)
    evidence = [_status_evidence(1, 30, "Aurora")]

    result = agent.advise(session=SESSION, question="?", evidence=evidence)

    assert result["structured"] is False
    assert result["raw_output"] == "not json at all"
