import json
from datetime import datetime, timezone

from src.agents.pmo_advisor.agent import PMOAdvisorAgent
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "pmo_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nRecords: $records_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider) -> PMOAdvisorAgent:
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=FakePromptRegistry(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    return PMOAdvisorAgent(framework)


SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1")


def _record_evidence(
    source_id: int, project_id: int, project_name: str, health_status: str, staleness_days: int, is_stale: bool
) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (status)",
        content={"structured": True, "health_status": health_status, "key_findings": [], "recommendations": []},
        metadata={
            "created_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
            "kind": "status",
            "project_id": project_id,
            "project_name": project_name,
            "staleness_days": staleness_days,
            "is_stale": is_stale,
        },
    )


ORG_EVIDENCE = [
    _record_evidence(1, 30, "Aurora", "green", staleness_days=1, is_stale=False),
    _record_evidence(2, 31, "Boreal", "red", staleness_days=20, is_stale=True),
]


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "Aurora esta green, Boreal esta stale.", "cited_analysis_ids": [1, 2]})
    )
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Algum padrao de atraso?", evidence=ORG_EVIDENCE)

    assert result["structured"] is True
    assert result["cited_analysis_ids"] == [1, 2]


def test_advise_serializes_staleness_fields_already_computed():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Quais projetos estao desatualizados?", evidence=ORG_EVIDENCE)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert [r["project_name"] for r in sent_records] == ["Aurora", "Boreal"]
    assert [r["staleness_days"] for r in sent_records] == [1, 20]
    assert [r["is_stale"] for r in sent_records] == [False, True]


def test_advise_never_reorders_the_evidence_it_receives():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    reversed_evidence = list(reversed(ORG_EVIDENCE))

    agent.advise(session=SESSION, question="Algum padrao?", evidence=reversed_evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert [r["project_name"] for r in sent_records] == ["Boreal", "Aurora"]


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Algum padrao?", evidence=ORG_EVIDENCE)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = _agent(provider)

    result = agent.advise(session=SESSION, question="Algum padrao?", evidence=ORG_EVIDENCE)

    assert result["structured"] is False
    assert result["raw_output"] == "not json at all"


def test_advise_serializes_multiple_records_of_the_same_project_distinctly():
    same_project = [
        _record_evidence(10, 30, "Aurora", "green", staleness_days=1, is_stale=False),
        _record_evidence(11, 30, "Aurora", "yellow", staleness_days=8, is_stale=False),
    ]
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": [10, 11]}))
    agent = _agent(provider)

    agent.advise(session=SESSION, question="Historico de Aurora?", evidence=same_project)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert [r["source_analysis_id"] for r in sent_records] == [10, 11]
    assert [r["project_id"] for r in sent_records] == [30, 30]
