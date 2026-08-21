from datetime import datetime, timezone

import pytest

from src.database.repository import AnalysisRepository
from src.services.ai_foundation.context_engine import AIContextEngine
from src.services.knowledge_platform.rag_pipeline import RagContext
from src.services.knowledge_platform.types import ScoredChunk
from tests.db import temp_database_url


@pytest.fixture()
def repository():
    with temp_database_url("ai_context_engine") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


def test_gather_returns_evidence_from_structured_analyses(repository, org_id):
    repository.save_analysis(
        kind="risk",
        payload={
            "model_output": {
                "structured": True,
                "risks": [{"description": "Atraso", "probability": "high", "impact": "high", "mitigation": "x"}],
                "escalation_recommendation": None,
            }
        },
        organization_id=org_id,
        project_name="Aurora",
    )

    engine = AIContextEngine(repository)
    evidence = engine.gather(org_id, "Aurora", kind="risk")

    assert len(evidence) == 1
    assert evidence[0].metadata["kind"] == "risk"
    assert evidence[0].content["risks"][0]["description"] == "Atraso"


def test_gather_skips_unstructured_analyses(repository, org_id):
    repository.save_analysis(
        kind="risk",
        payload={"model_output": {"structured": False, "raw_output": "not json"}},
        organization_id=org_id,
        project_name="Aurora",
    )

    engine = AIContextEngine(repository)
    evidence = engine.gather(org_id, "Aurora", kind="risk")

    assert evidence == []


def test_gather_only_returns_the_requested_kind(repository, org_id):
    repository.save_analysis(
        kind="meeting",
        payload={"model_output": {"structured": True, "summary": "x", "decisions": [], "action_items": [], "issues": [], "dependencies": []}},
        organization_id=org_id,
        project_name="Aurora",
    )

    engine = AIContextEngine(repository)
    evidence = engine.gather(org_id, "Aurora", kind="risk")

    assert evidence == []


def test_gather_never_returns_evidence_from_another_organization(repository, org_id):
    other_org = repository.enterprise.create_organization("Org B")
    repository.save_analysis(
        kind="risk",
        payload={
            "model_output": {
                "structured": True,
                "risks": [{"description": "Risco de outra org", "probability": "low", "impact": "low", "mitigation": "y"}],
                "escalation_recommendation": None,
            }
        },
        organization_id=other_org,
        project_name="Aurora",
    )

    engine = AIContextEngine(repository)
    evidence = engine.gather(org_id, "Aurora", kind="risk")

    assert evidence == []


class TestGatherOrganizationalLearnings:
    """Package M (V1 Product & Capability Completion): the 6 mandated
    negative/positive tests. Same deterministic rule as
    `web/lib/organizational-intelligence/organizational-learnings.ts`
    (>=3 distinct projects, exact textual match)."""

    def _save_risk(self, repository, org_id, project_name, description):
        repository.save_analysis(
            kind="risk",
            payload={
                "model_output": {
                    "structured": True,
                    "risks": [{"description": description, "probability": "high", "impact": "high", "mitigation": "x"}],
                    "escalation_recommendation": None,
                }
            },
            organization_id=org_id,
            project_name=project_name,
        )

    def _save_action(self, repository, org_id, project_name, description):
        repository.save_analysis(
            kind="meeting",
            payload={
                "model_output": {
                    "structured": True,
                    "summary": "x",
                    "decisions": [],
                    "action_items": [{"description": description}],
                    "issues": [],
                    "dependencies": [],
                }
            },
            organization_id=org_id,
            project_name=project_name,
        )

    def test_a_recurring_risk_across_3_projects_is_included(self, repository, org_id):
        for project in ["Aurora", "Boreal", "Cedro"]:
            self._save_risk(repository, org_id, project, "Atraso do mesmo fornecedor critico")

        engine = AIContextEngine(repository)
        evidence = engine.gather_organizational_learnings(org_id)

        assert len(evidence) == 1
        assert evidence[0].source_type == "organizational_learning"
        assert evidence[0].content["description"] == "Atraso do mesmo fornecedor critico"
        assert evidence[0].content["occurrences"] == 3
        assert evidence[0].content["project_names"] == ["Aurora", "Boreal", "Cedro"]

    def test_a_risk_seen_in_only_2_projects_is_excluded(self, repository, org_id):
        for project in ["Aurora", "Boreal"]:
            self._save_risk(repository, org_id, project, "Risco isolado, nao recorrente")

        engine = AIContextEngine(repository)
        evidence = engine.gather_organizational_learnings(org_id)

        assert evidence == []

    def test_learnings_are_scoped_by_organization_cross_tenant_impossible(self, repository, org_id):
        other_org = repository.enterprise.create_organization("Org B")
        for project in ["Aurora", "Boreal", "Cedro"]:
            self._save_risk(repository, other_org, project, "Risco exclusivo da Org B")

        engine = AIContextEngine(repository)
        evidence = engine.gather_organizational_learnings(org_id)

        assert evidence == []

    def test_organization_with_no_data_at_all_returns_no_learnings(self, repository, org_id):
        engine = AIContextEngine(repository)
        evidence = engine.gather_organizational_learnings(org_id)

        assert evidence == []

    def test_caps_at_5_learnings_in_fixed_category_order_risks_before_actions(self, repository, org_id):
        # list_latest_risks() keeps only the most recent risk analysis PER
        # PROJECT (its own "current state" semantics) -- each of the 6
        # recurring risk descriptions here needs its own 3 distinct
        # projects, never reusing a project across descriptions, or a
        # later description would silently displace an earlier one for
        # the same project.
        for description_index in range(6):
            for project_suffix in ["A", "B", "C"]:
                self._save_risk(
                    repository,
                    org_id,
                    f"Projeto{description_index}{project_suffix}",
                    f"Risco recorrente {description_index}",
                )
        for project in ["Aurora", "Boreal", "Cedro"]:
            self._save_action(repository, org_id, project, "Acao recorrente unica")

        engine = AIContextEngine(repository)
        evidence = engine.gather_organizational_learnings(org_id)

        assert len(evidence) == 5
        assert all(item.content["category"] == "risco" for item in evidence)

    def test_source_ids_are_negative_and_never_collide_with_a_real_analysis_record_id(
        self, repository, org_id
    ):
        real_record_id = repository.save_analysis(
            kind="risk",
            payload={
                "model_output": {
                    "structured": True,
                    "risks": [{"description": "x", "probability": "low", "impact": "low", "mitigation": "y"}],
                    "escalation_recommendation": None,
                }
            },
            organization_id=org_id,
            project_name="Aurora",
        )
        for project in ["Aurora", "Boreal", "Cedro"]:
            self._save_risk(repository, org_id, project, "Padrao recorrente")

        engine = AIContextEngine(repository)
        evidence = engine.gather_organizational_learnings(org_id)

        assert evidence[0].source_id < 0
        assert evidence[0].source_id != real_record_id


class TestNormalizeRagEvidence:
    """D-086/AR-9 §3: `normalize_rag_evidence()` is purely mechanical -- one
    `Evidence` per `ScoredChunk`, in the same order, never interpreting
    `chunk.text` nor deciding relevance (already `RagPipeline`'s job)."""

    def test_wraps_each_scored_chunk_into_a_document_chunk_evidence(self, repository):
        created_at = datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc)
        rag_context = RagContext(
            query="middleware delay",
            organization_id=1,
            chunks=[
                ScoredChunk(
                    chunk_id=42,
                    document_id=7,
                    text="the middleware vendor has a history of delayed delivery",
                    score=0.87,
                    document_version_created_at=created_at,
                ),
            ],
        )

        engine = AIContextEngine(repository)
        evidence = engine.normalize_rag_evidence(rag_context)

        assert len(evidence) == 1
        item = evidence[0]
        assert item.source_type == "document_chunk"
        assert item.source_id == 42
        assert item.source_label == "Document 7 / Chunk 42"
        assert item.content == {"text": "the middleware vendor has a history of delayed delivery"}
        assert item.metadata == {"document_id": 7, "score": 0.87, "created_at": created_at}

    def test_preserves_the_order_and_count_of_ranked_chunks(self, repository):
        rag_context = RagContext(
            query="q",
            organization_id=1,
            chunks=[
                ScoredChunk(
                    chunk_id=chunk_id,
                    document_id=1,
                    text=f"chunk {chunk_id}",
                    score=1.0 - (chunk_id * 0.1),
                    document_version_created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                )
                for chunk_id in (1, 2, 3)
            ],
        )

        engine = AIContextEngine(repository)
        evidence = engine.normalize_rag_evidence(rag_context)

        assert [item.source_id for item in evidence] == [1, 2, 3]

    def test_empty_rag_context_yields_no_evidence(self, repository):
        rag_context = RagContext(query="q", organization_id=1, chunks=[])

        engine = AIContextEngine(repository)
        evidence = engine.normalize_rag_evidence(rag_context)

        assert evidence == []
