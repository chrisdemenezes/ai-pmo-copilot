from datetime import datetime, timezone

from src.services.ai_foundation.recommendation_engine import RecommendationEngine
from src.services.ai_foundation.types import Evidence

EVIDENCE = [
    Evidence(source_analysis_id=1, source_created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), kind="risk", summary={}),
    Evidence(source_analysis_id=2, source_created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), kind="risk", summary={}),
]


def test_no_evidence_returns_the_generic_canned_answer_by_default():
    recommendation = RecommendationEngine.no_evidence()

    assert recommendation.answer == RecommendationEngine.NO_EVIDENCE_ANSWER
    assert recommendation.cited_evidence == []


def test_no_evidence_accepts_a_domain_specific_answer():
    recommendation = RecommendationEngine.no_evidence("Nenhum risco identificado ainda para este projeto.")

    assert recommendation.answer == "Nenhum risco identificado ainda para este projeto."


def test_build_keeps_only_citations_that_match_real_evidence():
    recommendation = RecommendationEngine.build("resposta", [1, 2], EVIDENCE)

    assert recommendation.answer == "resposta"
    assert [e.source_analysis_id for e in recommendation.cited_evidence] == [1, 2]


def test_build_discards_a_citation_the_model_invented():
    # id 999 was never in the evidence handed to the model -- must never be
    # trusted, no matter what the model claims it cited.
    recommendation = RecommendationEngine.build("resposta", [1, 999], EVIDENCE)

    assert [e.source_analysis_id for e in recommendation.cited_evidence] == [1]


def test_build_with_no_cited_ids_returns_no_evidence():
    recommendation = RecommendationEngine.build("resposta", [], EVIDENCE)

    assert recommendation.cited_evidence == []
