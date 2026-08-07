"""Correlação (AR-17 §2/§6; Technical Design §6) -- strictly structural.
Operates on exactly two signals, never on the content of any
`AttributedExplanation`: shared organizational-unit scope (already known
before any evidence is interpreted -- every selected Advisor in one
orchestration run is invoked with the same `OrchestrationScope`) and a
static, versioned pairing of `AdvisorIdentity` names (`STRUCTURAL_PAIRS`).
Never judges whether two Explanations actually diverge in content -- that
judgment remains exclusively human (Vision, Princípio 5).
"""
from itertools import combinations

from src.services.executive_orchestrator.types import AttributedExplanation, CorrelationFinding

# Static, versioned pairs of Advisor Identities whose own declared
# institutional identities represent structurally distinct perspectives on
# the same organizational unit (AR-17 §3, "participação tipicamente
# esperada" generalized into a fixed table) -- never inferred from text,
# never altered without a governance event (Decision Log).
STRUCTURAL_PAIRS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"delivery_advisor", "risk_advisor"}),
        frozenset({"strategy_advisor", "risk_advisor"}),
        frozenset({"strategy_advisor", "executive_advisor"}),
        frozenset({"governance_advisor", "delivery_advisor"}),
    }
)


def _has_real_evidence(item: AttributedExplanation) -> bool:
    return bool(item.explanation.recommendation.cited_evidence)


def correlate(explanations: tuple[AttributedExplanation, ...]) -> tuple[CorrelationFinding, ...]:
    """Every pair of Explanations that both carry real evidence is a
    finding -- every selected Advisor shares the same call-level scope in
    this first implementation (Technical Design §6.1.1), so scope overlap
    is structural, not computed per pair. `is_structural_pair` comes
    exclusively from `STRUCTURAL_PAIRS`, never from reading either
    Explanation's `answer`."""
    grounded = tuple(item for item in explanations if _has_real_evidence(item))
    findings = []
    for first, second in combinations(grounded, 2):
        names = tuple(sorted((first.advisor_name, second.advisor_name)))
        findings.append(
            CorrelationFinding(
                advisor_names=names,
                is_structural_pair=frozenset(names) in STRUCTURAL_PAIRS,
                explanations=(first, second),
            )
        )
    return tuple(findings)
