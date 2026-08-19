"""Citation consolidation at the Executive Intelligence composition layer
(Founder Decision -- Wave 6 Final Consolidation Actions, D-165).

`_consolidate_citations()` (src/api/routes/intelligence.py) is the single
place either response builder (`_decision_support_response()`/
`_executive_narrative_response()`) turns `AttributedExplanation`s into the
`citations` list. Tested here in isolation -- no HTTP, no LLM, no database
-- against the exact scenarios A-G mandated by the Founder. Never runs
inside an Advisor, the RAG Pipeline, or the Executive Orchestrator (all
untouched); see `tests/test_executive_narrative_api.py::TestCitation
Consolidation` for the same guarantee proven end to end through a real
multi-Advisor RAG scenario.
"""
from src.api.routes.intelligence import _consolidate_citations
from src.services.ai_foundation.types import Evidence, Explanation, Recommendation
from src.services.executive_orchestrator.types import AttributedExplanation


def _explanation(advisor_name: str, *evidence: Evidence) -> AttributedExplanation:
    recommendation = Recommendation(answer="Resposta fundamentada.", cited_evidence=list(evidence))
    return AttributedExplanation(
        advisor_name=advisor_name, explanation=Explanation(recommendation=recommendation, rationale="")
    )


def _chunk(source_id: int, label: str = "Document 1 / Chunk") -> Evidence:
    return Evidence(
        source_type="document_chunk", source_id=source_id, source_label=f"{label} {source_id}", content={}
    )


def _analysis(source_id: int, kind: str = "risk") -> Evidence:
    return Evidence(
        source_type="analysis_record", source_id=source_id, source_label=f"AnalysisRecord#{source_id} ({kind})", content={}
    )


class TestScenarioA_SameChunkTwoAdvisors:
    def test_two_advisors_citing_the_same_chunk_consolidate_into_one_source(self):
        chunk = _chunk(1)
        result = _consolidate_citations(
            [_explanation("document_advisor", chunk), _explanation("governance_advisor", chunk)]
        )

        assert len(result) == 1
        assert result[0].source_type == "document_chunk"
        assert result[0].source_id == 1
        assert result[0].advisor_names == ["document_advisor", "governance_advisor"]


class TestScenarioB_DistinctChunksTwoAdvisors:
    def test_two_advisors_citing_different_chunks_produce_two_distinct_sources(self):
        result = _consolidate_citations(
            [_explanation("document_advisor", _chunk(1)), _explanation("governance_advisor", _chunk(2))]
        )

        assert len(result) == 2
        assert {c.source_id for c in result} == {1, 2}
        assert {c.advisor_names[0] for c in result} == {"document_advisor", "governance_advisor"}


class TestScenarioC_OneAdvisorMultipleSources:
    def test_one_advisor_citing_multiple_sources_loses_nothing(self):
        result = _consolidate_citations([_explanation("risk_advisor", _analysis(1), _analysis(2), _analysis(3))])

        assert len(result) == 3
        assert {c.source_id for c in result} == {1, 2, 3}
        assert all(c.advisor_names == ["risk_advisor"] for c in result)


class TestScenarioD_StructurallyDifferentTypesSameNumericId:
    def test_same_numeric_id_but_different_source_type_never_dedupes_accidentally(self):
        # A document_chunk id=1 and an analysis_record id=1 are unrelated
        # facts that merely share a numeric primary key in two different
        # tables -- consolidation keys on (source_type, source_id), never
        # on source_id alone.
        result = _consolidate_citations(
            [_explanation("document_advisor", _chunk(1)), _explanation("risk_advisor", _analysis(1))]
        )

        assert len(result) == 2
        types_by_advisor = {c.advisor_names[0]: c.source_type for c in result}
        assert types_by_advisor == {"document_advisor": "document_chunk", "risk_advisor": "analysis_record"}


class TestScenarioF_NoEvidenceDisappears:
    def test_every_distinct_real_source_survives_consolidation(self):
        result = _consolidate_citations(
            [
                _explanation("risk_advisor", _analysis(1), _analysis(2)),
                _explanation("delivery_advisor", _analysis(2)),
                _explanation("document_advisor", _chunk(9)),
            ]
        )

        by_key = {(c.source_type, c.source_id): c for c in result}
        assert set(by_key) == {("analysis_record", 1), ("analysis_record", 2), ("document_chunk", 9)}
        assert by_key[("analysis_record", 1)].advisor_names == ["risk_advisor"]
        assert by_key[("analysis_record", 2)].advisor_names == ["risk_advisor", "delivery_advisor"]
        assert by_key[("document_chunk", 9)].advisor_names == ["document_advisor"]


class TestScenarioG_NoEvidenceInvented:
    def test_consolidated_citation_fields_always_come_from_real_input_evidence(self):
        chunk = _chunk(5, label="Document 3 / Chunk")
        result = _consolidate_citations(
            [_explanation("document_advisor", chunk), _explanation("governance_advisor", chunk)]
        )

        assert len(result) == 1
        assert result[0].source_label == chunk.source_label
        assert result[0].source_id == chunk.source_id
        assert result[0].source_type == chunk.source_type

    def test_no_evidence_and_no_explanations_produce_no_citations(self):
        assert _consolidate_citations([]) == []
        assert _consolidate_citations([_explanation("risk_advisor")]) == []


class TestOrderingIsDeterministic:
    def test_citations_are_ordered_by_first_appearance_across_explanations(self):
        result = _consolidate_citations(
            [
                _explanation("risk_advisor", _analysis(2)),
                _explanation("delivery_advisor", _analysis(1)),
            ]
        )

        assert [c.source_id for c in result] == [2, 1]
