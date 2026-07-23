import pytest

from src.database.repository import AnalysisRepository
from src.services.ai_foundation.context_engine import AIContextEngine
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
    assert evidence[0].kind == "risk"
    assert evidence[0].summary["risks"][0]["description"] == "Atraso"


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
