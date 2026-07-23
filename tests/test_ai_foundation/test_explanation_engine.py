from datetime import datetime, timezone

from src.services.ai_foundation.explanation_engine import ExplanationEngine
from src.services.ai_foundation.types import Evidence, Recommendation


def test_explain_includes_the_evidence_count_in_the_rationale():
    evidence = [
        Evidence(source_analysis_id=1, source_created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), kind="risk", summary={}),
        Evidence(source_analysis_id=2, source_created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), kind="risk", summary={}),
    ]
    recommendation = Recommendation(answer="resposta", cited_evidence=evidence)

    explanation = ExplanationEngine.explain(recommendation)

    assert explanation.recommendation is recommendation
    assert "2 evidência" in explanation.rationale


def test_explain_never_claims_to_be_an_automatic_decision():
    recommendation = Recommendation(answer="resposta", cited_evidence=[])

    explanation = ExplanationEngine.explain(recommendation)

    assert "não é uma decisão automática" in explanation.rationale
    assert "0 evidência" in explanation.rationale
