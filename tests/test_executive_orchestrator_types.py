"""Executive Orchestrator, Etapa 1 -- estrutura interna (Founder Decision
"Implementação do Executive Orchestrator"). Proves the internal contract in
isolation: no Selection Rule, no Advisor execution, no Correlation, no
Synthesis -- those are Etapas 2-4."""
import dataclasses

import pytest

from src.services.ai_foundation.types import Evidence, Explanation, Recommendation
from src.services.executive_orchestrator.types import (
    AdvisorIdentity,
    AttributedExplanation,
    Capability,
    CompositionTrace,
    CorrelationFinding,
    CorrelationTraceEntry,
    ExecutionTraceEntry,
    ExecutiveIntelligenceResult,
    InsufficientBasisReason,
    SelectionTraceEntry,
    SynthesisTraceEntry,
)


def _explanation(answer: str = "synthesized", cited: list[Evidence] | None = None) -> Explanation:
    return Explanation(
        recommendation=Recommendation(answer=answer, cited_evidence=cited or []),
        rationale="Síntese informativa baseada em 0 evidência(s) já registrada(s).",
    )


class TestCapability:
    def test_exactly_six_permanent_members(self):
        assert len(Capability) == 6
        assert {member.value for member in Capability} == {
            "executive_briefing",
            "executive_narrative",
            "cross_advisor_correlation",
            "conflict_analysis",
            "recommendation_package",
            "decision_support",
        }


class TestCompositionTraceImmutability:
    def test_with_selection_returns_a_new_instance_and_leaves_the_original_untouched(self):
        trace = CompositionTrace()
        entry = SelectionTraceEntry(signals=("risco",), selected_advisor_names=("risk_advisor",))

        updated = trace.with_selection(entry)

        assert trace.selection is None
        assert updated.selection == entry
        assert updated is not trace

    def test_with_execution_appends_without_mutating_previous_snapshot(self):
        trace = CompositionTrace().with_selection(
            SelectionTraceEntry(signals=(), selected_advisor_names=("risk_advisor", "delivery_advisor"))
        )
        first = trace.with_execution(ExecutionTraceEntry(advisor_name="risk_advisor", had_evidence=True))
        second = first.with_execution(ExecutionTraceEntry(advisor_name="delivery_advisor", had_evidence=False))

        assert first.executions == (ExecutionTraceEntry(advisor_name="risk_advisor", had_evidence=True),)
        assert second.executions == (
            ExecutionTraceEntry(advisor_name="risk_advisor", had_evidence=True),
            ExecutionTraceEntry(advisor_name="delivery_advisor", had_evidence=False),
        )

    def test_with_correlations_and_with_synthesis_are_also_immutable(self):
        trace = CompositionTrace()
        correlated = trace.with_correlations(
            (CorrelationTraceEntry(advisor_names=("risk_advisor", "delivery_advisor"), is_structural_pair=True),)
        )
        synthesized = correlated.with_synthesis(
            SynthesisTraceEntry(source_advisor_names=("risk_advisor", "delivery_advisor"))
        )

        assert trace.correlations == ()
        assert trace.synthesis is None
        assert correlated.synthesis is None
        assert synthesized.correlations == correlated.correlations
        assert synthesized.synthesis == SynthesisTraceEntry(
            source_advisor_names=("risk_advisor", "delivery_advisor")
        )

    def test_composition_trace_is_frozen(self):
        trace = CompositionTrace()
        with pytest.raises(dataclasses.FrozenInstanceError):
            trace.selection = SelectionTraceEntry(signals=(), selected_advisor_names=())  # type: ignore[misc]


class TestExecutiveIntelligenceResultComplete:
    def test_complete_builds_a_valid_result_with_defaults(self):
        identity = AdvisorIdentity(name="risk_advisor", description="Riscos já identificados.")
        attributed = AttributedExplanation(advisor_name="risk_advisor", explanation=_explanation())
        trace = CompositionTrace().with_selection(
            SelectionTraceEntry(signals=("risco",), selected_advisor_names=("risk_advisor",))
        )

        result = ExecutiveIntelligenceResult.complete(
            capability=Capability.EXECUTIVE_NARRATIVE,
            composition_trace=trace,
            advisor_identities=(identity,),
            explanations=(attributed,),
        )

        assert result.is_insufficient_basis is False
        assert result.insufficient_basis_reason is None
        assert result.advisor_identities == (identity,)
        assert result.explanations == (attributed,)
        assert result.correlation == ()
        assert result.synthesis is None

    def test_complete_may_carry_correlation_and_synthesis(self):
        identity_a = AdvisorIdentity(name="risk_advisor", description="...")
        identity_b = AdvisorIdentity(name="delivery_advisor", description="...")
        attributed_a = AttributedExplanation(advisor_name="risk_advisor", explanation=_explanation())
        attributed_b = AttributedExplanation(advisor_name="delivery_advisor", explanation=_explanation())
        finding = CorrelationFinding(
            advisor_names=("risk_advisor", "delivery_advisor"),
            is_structural_pair=True,
            explanations=(attributed_a, attributed_b),
        )
        trace = CompositionTrace()

        result = ExecutiveIntelligenceResult.complete(
            capability=Capability.DECISION_SUPPORT,
            composition_trace=trace,
            advisor_identities=(identity_a, identity_b),
            explanations=(attributed_a, attributed_b),
            correlation=(finding,),
            synthesis="Ambos os Advisors reportam evidência para o mesmo projeto.",
        )

        assert result.correlation == (finding,)
        assert result.synthesis == "Ambos os Advisors reportam evidência para o mesmo projeto."


class TestExecutiveIntelligenceResultInsufficientBasis:
    def test_selection_empty_carries_no_advisors_and_no_explanations(self):
        trace = CompositionTrace().with_selection(
            SelectionTraceEntry(signals=("irrelevante",), selected_advisor_names=())
        )

        result = ExecutiveIntelligenceResult.insufficient_basis(
            capability=Capability.EXECUTIVE_BRIEFING,
            composition_trace=trace,
            reason=InsufficientBasisReason.SELECTION_EMPTY,
        )

        assert result.is_insufficient_basis is True
        assert result.insufficient_basis_reason == InsufficientBasisReason.SELECTION_EMPTY
        assert result.advisor_identities == ()
        assert result.explanations == ()
        assert result.synthesis is None
        assert result.correlation == ()

    def test_collection_empty_may_still_carry_the_selected_advisors_and_their_empty_explanations(self):
        identity = AdvisorIdentity(name="risk_advisor", description="...")
        attributed = AttributedExplanation(advisor_name="risk_advisor", explanation=_explanation())
        trace = CompositionTrace().with_execution(
            ExecutionTraceEntry(advisor_name="risk_advisor", had_evidence=False)
        )

        result = ExecutiveIntelligenceResult.insufficient_basis(
            capability=Capability.CONFLICT_ANALYSIS,
            composition_trace=trace,
            reason=InsufficientBasisReason.COLLECTION_EMPTY,
            advisor_identities=(identity,),
            explanations=(attributed,),
        )

        assert result.insufficient_basis_reason == InsufficientBasisReason.COLLECTION_EMPTY
        assert result.advisor_identities == (identity,)
        assert result.explanations == (attributed,)

    def test_never_a_third_state_synthesis_forbidden_when_insufficient(self):
        with pytest.raises(ValueError):
            ExecutiveIntelligenceResult(
                capability=Capability.EXECUTIVE_BRIEFING,
                composition_trace=CompositionTrace(),
                insufficient_basis_reason=InsufficientBasisReason.SELECTION_EMPTY,
                synthesis="uma síntese inventada",
            )

    def test_never_a_third_state_correlation_forbidden_when_insufficient(self):
        attributed_a = AttributedExplanation(advisor_name="risk_advisor", explanation=_explanation())
        attributed_b = AttributedExplanation(advisor_name="delivery_advisor", explanation=_explanation())
        finding = CorrelationFinding(
            advisor_names=("risk_advisor", "delivery_advisor"),
            is_structural_pair=True,
            explanations=(attributed_a, attributed_b),
        )
        with pytest.raises(ValueError):
            ExecutiveIntelligenceResult(
                capability=Capability.CROSS_ADVISOR_CORRELATION,
                composition_trace=CompositionTrace(),
                insufficient_basis_reason=InsufficientBasisReason.COLLECTION_EMPTY,
                correlation=(finding,),
            )
