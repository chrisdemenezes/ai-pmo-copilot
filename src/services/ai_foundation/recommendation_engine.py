from src.services.ai_foundation.types import Evidence, Recommendation


class RecommendationEngine:
    """Normalizes an Analyst's raw model output into the one Recommendation
    shape every Analyst returns (Domain Blueprint §4.3)."""

    NO_EVIDENCE_ANSWER = "Nenhuma evidência identificada ainda para este projeto."

    @staticmethod
    def no_evidence(answer: str | None = None) -> Recommendation:
        # Domain-specific wording ("Nenhum risco...") stays with the Analyst
        # that knows its own domain -- the Foundation's default is generic,
        # never assumed correct for every future Analyst's vocabulary.
        return Recommendation(answer=answer or RecommendationEngine.NO_EVIDENCE_ANSWER, cited_evidence=[])

    @staticmethod
    def build(answer: str, cited_ids: list[int], evidence: list[Evidence]) -> Recommendation:
        # Never trusts a citation the model invented -- only ids present in
        # the evidence actually handed to it survive.
        by_id = {item.source_analysis_id: item for item in evidence}
        cited = [by_id[cited_id] for cited_id in cited_ids if cited_id in by_id]
        return Recommendation(answer=answer, cited_evidence=cited)
