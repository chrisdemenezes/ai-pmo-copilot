"""`StrategyAdvisorAgent` unit tests (Wave 5, fourth Classe B Advisor), per
`TECHNICAL-DESIGN-STRATEGY-ADVISOR.md` §10.

Covers scenarios M (two citations of the same unit with different kinds
remain distinguishable) and the JSON-formation half of R (the synthetic
`source_id` is present under `"source_id"`, distinct from the always-real
`"entity_id"` -- the exact correction demanded by the Founder Decision that
harmonized this Technical Design, §10/§10.2)."""
import json
from datetime import datetime, timezone

from src.agents.strategy_advisor.agent import StrategyAdvisorAgent
from src.agents.strategy_advisor.evidence_assembler import _synthetic_source_id
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "strategy_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nRecords: $records_json"


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider) -> StrategyAdvisorAgent:
    framework = AdvisorFramework(
        repository=None,
        prompt_registry=FakePromptRegistry(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    return StrategyAdvisorAgent(framework)


SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1")


def _declared_strategy_evidence(level: str, real_entity_id: int, entity_name: str, objective: str) -> Evidence:
    return Evidence(
        source_type="declared_strategy",
        source_id=_synthetic_source_id(level, real_entity_id),
        source_label=f"{level.capitalize()} {entity_name} -- objetivo declarado",
        content={"objective": objective},
        metadata={
            "level": level,
            "real_entity_id": real_entity_id,
            "entity_name": entity_name,
            "declared_objective": objective,
            "kind": "declared_strategy",
        },
    )


def _status_evidence(source_id: int, real_entity_id: int, entity_name: str) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (status)",
        content={"structured": True, "health_status": "green", "key_findings": [], "recommendations": []},
        metadata={
            "created_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
            "kind": "status",
            "level": "project",
            "real_entity_id": real_entity_id,
            "entity_name": entity_name,
        },
    )


def test_advise_returns_structured_answer_and_citations():
    provider = RecordingProvider(
        json.dumps({"answer": "Aurora esta alinhada.", "cited_analysis_ids": [-303, 1]})
    )
    agent = _agent(provider)
    evidence = [
        _declared_strategy_evidence("project", 30, "Aurora", "Migrar workloads"),
        _status_evidence(1, 30, "Aurora"),
    ]

    result = agent.advise(session=SESSION, question="Aurora esta alinhada?", evidence=evidence)

    assert result["structured"] is True
    assert result["cited_analysis_ids"] == [-303, 1]


def test_advise_sends_synthetic_source_id_never_the_real_entity_id_for_declared_strategy():
    # The exact correction demanded by the harmonization Founder Decision:
    # "source_id" in records_json must always equal Evidence.source_id --
    # the synthetic token for declared_strategy -- never
    # metadata["real_entity_id"] (the bug in the original Technical Design).
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    declared = _declared_strategy_evidence("portfolio", 7, "Atlas", "Expandir para APAC")
    evidence = [declared]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert len(sent_records) == 1
    record = sent_records[0]
    assert record["source_id"] == declared.source_id  # synthetic, e.g. -71
    assert record["source_id"] != declared.metadata["real_entity_id"]  # never 7
    assert record["entity_id"] == 7  # always real, for prose
    assert record["source_id"] < 0


def test_advise_sends_real_analysis_record_id_as_source_id_for_execution():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    evidence = [_status_evidence(42, 30, "Aurora")]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert sent_records[0]["source_id"] == 42
    assert sent_records[0]["entity_id"] == 30
    assert sent_records[0]["kind"] == "status"


def test_advise_serializes_content_unflattened_with_kind_distinguishing_shape():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    evidence = [
        _declared_strategy_evidence("project", 30, "Aurora", "Migrar workloads"),
        _status_evidence(1, 30, "Aurora"),
    ]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    declared_record = next(r for r in sent_records if r["kind"] == "declared_strategy")
    status_record = next(r for r in sent_records if r["kind"] == "status")
    assert declared_record["content"] == {"objective": "Migrar workloads"}
    assert "health_status" not in declared_record["content"]
    assert status_record["content"]["health_status"] == "green"


def test_advise_serializes_two_citations_of_the_same_unit_with_different_kinds_scenario_m():
    # Scenario M: declared_strategy + status of the same Project unit remain
    # distinguishable citations, same discipline already proven for the
    # Executive Advisor's multi-kind evidence.
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    declared = _declared_strategy_evidence("project", 30, "Aurora", "Migrar workloads")
    status = _status_evidence(10, 30, "Aurora")
    evidence = [declared, status]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert [r["source_id"] for r in sent_records] == [declared.source_id, 10]
    assert [r["kind"] for r in sent_records] == ["declared_strategy", "status"]
    assert len({r["source_id"] for r in sent_records}) == 2


def test_advise_never_reorders_the_evidence_it_receives():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    evidence = [
        _status_evidence(1, 30, "Aurora"),
        _declared_strategy_evidence("project", 30, "Aurora", "Migrar workloads"),
    ]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    sent_records = json.loads(provider.received_prompt.split("Records: ", 1)[1])
    assert [r["kind"] for r in sent_records] == ["status", "declared_strategy"]


def test_advise_prepends_the_shared_digital_pmo_preamble():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    agent = _agent(provider)
    evidence = [_declared_strategy_evidence("project", 30, "Aurora", "Migrar workloads")]

    agent.advise(session=SESSION, question="?", evidence=evidence)

    assert "Digital PMO Intelligence Foundation" in provider.received_prompt
    assert "never decide anything" in provider.received_prompt


def test_advise_falls_back_to_unstructured_when_model_output_is_not_json():
    provider = RecordingProvider("not json at all")
    agent = _agent(provider)
    evidence = [_declared_strategy_evidence("project", 30, "Aurora", "Migrar workloads")]

    result = agent.advise(session=SESSION, question="?", evidence=evidence)

    assert result["structured"] is False
    assert result["raw_output"] == "not json at all"
