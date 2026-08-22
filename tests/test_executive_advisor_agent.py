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


class _FakeDomainRepositoryNoProjects:
    """TD-017 (V1 Post-Completion Technical Closure): `advise()` now also
    calls `framework.gather_executive_analytics_context()`, which reads
    `repository.domain.list_projects_by_organization()`. Zero projects, i.e.
    no Executive Signals, matching every test below's original intent
    (none of them are about Executive Signals)."""

    def list_projects_by_organization(self, organization_id):
        return []


class FakeRepository:
    """Package M (V1 Product & Capability Completion): `advise()` now also
    calls `framework.gather_organizational_learnings()`, which needs a real
    repository -- `repository=None` (this file's convention before Package
    M) would crash. Defaults to zero analyses of any kind, i.e. no
    Organizational Learnings, matching every test below's original intent
    (none of them are about Learnings)."""

    domain = _FakeDomainRepositoryNoProjects()

    def resolve_scope_id(self, organization_id, project_name=None, project_id=None):
        return None, False

    def list_analyses(self, organization_id, project_id=None, kind=None, limit=None):
        return []


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


def _agent(provider, repository=None) -> ExecutiveAdvisorAgent:
    framework = AdvisorFramework(
        repository=repository if repository is not None else FakeRepository(),
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


class FakePromptRegistryWithLearnings:
    def get(self, agent_name, prompt_name):
        return "Learnings: $learnings_json"


def _fake_analysis_record(record_id, project_name, payload):
    from types import SimpleNamespace

    return SimpleNamespace(
        id=record_id,
        project_id=record_id,
        project=SimpleNamespace(name=project_name),
        payload=payload,
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


class FakeRepositoryWithRisks:
    """3+ distinct projects reporting the exact same risk description --
    a real Organizational Learning by the same rule
    `organizational-learnings.ts` uses."""

    domain = _FakeDomainRepositoryNoProjects()

    def resolve_scope_id(self, organization_id, project_name=None, project_id=None):
        return None, False

    def list_analyses(self, organization_id, project_id=None, kind=None, limit=None):
        if kind != "risk":
            return []
        return [
            _fake_analysis_record(
                index,
                project_name,
                {
                    "model_output": {
                        "structured": True,
                        "risks": [{"description": "Atraso do mesmo fornecedor critico"}],
                        "escalation_recommendation": None,
                    }
                },
            )
            for index, project_name in enumerate(["Aurora", "Boreal", "Cedro"])
        ]


def test_advise_includes_organizational_learnings_as_supporting_context():
    provider = RecordingProvider(json.dumps({"answer": "ok", "cited_analysis_ids": []}))
    framework = AdvisorFramework(
        repository=FakeRepositoryWithRisks(),
        prompt_registry=FakePromptRegistryWithLearnings(),
        llm_provider=provider,
        rag_pipeline=None,
    )
    agent = ExecutiveAdvisorAgent(framework)

    agent.advise(session=SESSION, question="Algum padrao recorrente?", evidence=[])

    sent_learnings = json.loads(provider.received_prompt.split("Learnings: ", 1)[1])
    assert len(sent_learnings) == 1
    assert sent_learnings[0]["description"] == "Atraso do mesmo fornecedor critico"
    assert sent_learnings[0]["occurrences"] == 3
    assert sent_learnings[0]["project_names"] == ["Aurora", "Boreal", "Cedro"]
