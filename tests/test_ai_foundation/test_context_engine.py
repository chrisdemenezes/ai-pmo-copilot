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
