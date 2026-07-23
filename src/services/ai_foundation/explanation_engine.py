from src.services.ai_foundation.types import Explanation, Recommendation


class ExplanationEngine:
    """Wraps a Recommendation with a standard, human-readable rationale --
    no recommendation reaches an Analyst's caller without one (Domain
    Blueprint §4.4; ADR-V2-007: informational synthesis, never an automatic
    decision)."""

    RATIONALE_TEMPLATE = (
        "Síntese informativa baseada em {count} evidência(s) já registrada(s) -- "
        "não é uma decisão automática (ADR-V2-007)."
    )

    @staticmethod
    def explain(recommendation: Recommendation) -> Explanation:
        rationale = ExplanationEngine.RATIONALE_TEMPLATE.format(
            count=len(recommendation.cited_evidence)
        )
        return Explanation(recommendation=recommendation, rationale=rationale)
