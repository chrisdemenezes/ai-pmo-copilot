"""Executive Orchestrator -- internal contract (Wave 6, Technical Design
`TECHNICAL-DESIGN-EXECUTIVE-ORCHESTRATOR.md` §1/§4/§5). Etapa 1: structure
only -- no Selection Rule evaluation (§2, Etapa 2), no Advisor execution
(§3, Etapa 3), no Correlation (§6, Etapa 3), no Synthesis (§7, Etapa 4).

Never a new evidence source, never an `AdvisorContract` implementation,
never a domain type (Vision, "Conceito Permanente -- Executive
Intelligence Result"; D-140). `ExecutiveIntelligenceResult` and
`CompositionTrace` are the sole architectural representation of the
Executive Orchestrator's result -- no persistence, no HTTP contract is
decided here.
"""
from dataclasses import dataclass, field
from enum import Enum

from src.services.ai_foundation.types import Explanation


class Capability(str, Enum):
    """The six permanent Capabilities (AR-17 §1/§2, D-139) -- closed,
    nothing added without demonstrated real need (Camada 2, "Grounded
    before Generalized")."""

    EXECUTIVE_BRIEFING = "executive_briefing"
    EXECUTIVE_NARRATIVE = "executive_narrative"
    CROSS_ADVISOR_CORRELATION = "cross_advisor_correlation"
    CONFLICT_ANALYSIS = "conflict_analysis"
    RECOMMENDATION_PACKAGE = "recommendation_package"
    DECISION_SUPPORT = "decision_support"


class InsufficientBasisReason(Enum):
    """The two exhaustive triggers for base insuficiente (Domain Blueprint
    §4, D-138) -- never a third state."""

    SELECTION_EMPTY = "selection_empty"
    COLLECTION_EMPTY = "collection_empty"


@dataclass(frozen=True)
class AdvisorIdentity:
    """The already-public institutional identity of one of the 8 Advisors
    (Domain Blueprint §2.1, D-138) -- never a new data, only a reference to
    what each Advisor already declares about itself. `name` matches the
    same string every `AdvisorContract` implementation already exposes
    (e.g. `RiskAdvisorAgent.name == "risk_advisor"`)."""

    name: str
    description: str


@dataclass(frozen=True)
class AttributedExplanation:
    """An `Explanation` paired with the `AdvisorIdentity` that produced it
    -- proveniência preservada integralmente (Vision, Princípio 4), nunca
    achatada ou anônima."""

    advisor_name: str
    explanation: Explanation


@dataclass(frozen=True)
class CorrelationFinding:
    """Structural-only relation between two `AttributedExplanation`s
    (Technical Design §6) -- never a judgment of content. `is_structural_pair`
    comes exclusively from the static, versioned catalog of pairs
    (`correlation.STRUCTURAL_PAIRS`), never inferred from text."""

    advisor_names: tuple[str, str]
    is_structural_pair: bool
    explanations: tuple[AttributedExplanation, AttributedExplanation]


@dataclass(frozen=True)
class SelectionTraceEntry:
    """Records exactly which signals were evaluated and which Advisor
    Identities they matched (Technical Design §2.3, §5.1) -- auditability
    of the Selection Rule."""

    signals: tuple[str, ...]
    selected_advisor_names: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionTraceEntry:
    """One entry per Advisor Identity actually invoked via
    `AdvisorFramework.run()` -- `had_evidence` distinguishes a real
    contribution from the Advisor's own no-evidence outcome, never
    interpreting *what* the evidence says."""

    advisor_name: str
    had_evidence: bool


@dataclass(frozen=True)
class CorrelationTraceEntry:
    """One entry per `CorrelationFinding` produced -- mirrors the finding's
    own identity, never a copy of its content."""

    advisor_names: tuple[str, str]
    is_structural_pair: bool


@dataclass(frozen=True)
class SynthesisTraceEntry:
    """Records which Advisor Identities' Explanations fed the Synthesis --
    every synthesized claim remains traceable to at least one of them
    (Vision, Princípio 11; AR-17 §4)."""

    source_advisor_names: tuple[str, ...]


@dataclass(frozen=True)
class CompositionTrace:
    """Auditable record of the full orchestration (AR-17 §4/Camada 3;
    Technical Design §5) -- built incrementally, one immutable snapshot per
    step. Each `with_*` method returns a *new* `CompositionTrace`; nothing
    here is ever mutated after being produced (Founder Decision --
    Implementação, Garantia 12: "nunca altera Composition Trace após
    produzido")."""

    selection: SelectionTraceEntry | None = None
    executions: tuple[ExecutionTraceEntry, ...] = ()
    correlations: tuple[CorrelationTraceEntry, ...] = ()
    synthesis: SynthesisTraceEntry | None = None

    def with_selection(self, entry: SelectionTraceEntry) -> "CompositionTrace":
        return CompositionTrace(
            selection=entry,
            executions=self.executions,
            correlations=self.correlations,
            synthesis=self.synthesis,
        )

    def with_execution(self, entry: ExecutionTraceEntry) -> "CompositionTrace":
        return CompositionTrace(
            selection=self.selection,
            executions=(*self.executions, entry),
            correlations=self.correlations,
            synthesis=self.synthesis,
        )

    def with_correlations(self, entries: tuple[CorrelationTraceEntry, ...]) -> "CompositionTrace":
        return CompositionTrace(
            selection=self.selection,
            executions=self.executions,
            correlations=(*self.correlations, *entries),
            synthesis=self.synthesis,
        )

    def with_synthesis(self, entry: SynthesisTraceEntry) -> "CompositionTrace":
        return CompositionTrace(
            selection=self.selection,
            executions=self.executions,
            correlations=self.correlations,
            synthesis=entry,
        )


@dataclass(frozen=True)
class ExecutiveIntelligenceResult:
    """The logical product of one orchestration (Vision, "Conceito
    Permanente"; AR-17 Camada 4; D-140) -- always exactly one of two
    exhaustive states, enforced by `__post_init__`, never constructed
    directly: use `.complete(...)` or `.insufficient_basis(...)`."""

    capability: Capability
    composition_trace: CompositionTrace
    advisor_identities: tuple[AdvisorIdentity, ...] = field(default_factory=tuple)
    explanations: tuple[AttributedExplanation, ...] = field(default_factory=tuple)
    correlation: tuple[CorrelationFinding, ...] = field(default_factory=tuple)
    synthesis: str | None = None
    insufficient_basis_reason: InsufficientBasisReason | None = None

    def __post_init__(self) -> None:
        if self.insufficient_basis_reason is not None:
            if self.synthesis is not None:
                raise ValueError("base insuficiente nunca produz síntese (Princípio 11)")
            if self.correlation:
                raise ValueError("base insuficiente nunca produz correlação")

    @property
    def is_insufficient_basis(self) -> bool:
        return self.insufficient_basis_reason is not None

    @classmethod
    def insufficient_basis(
        cls,
        capability: Capability,
        composition_trace: CompositionTrace,
        reason: InsufficientBasisReason,
        advisor_identities: tuple[AdvisorIdentity, ...] = (),
        explanations: tuple[AttributedExplanation, ...] = (),
    ) -> "ExecutiveIntelligenceResult":
        return cls(
            capability=capability,
            composition_trace=composition_trace,
            advisor_identities=advisor_identities,
            explanations=explanations,
            insufficient_basis_reason=reason,
        )

    @classmethod
    def complete(
        cls,
        capability: Capability,
        composition_trace: CompositionTrace,
        advisor_identities: tuple[AdvisorIdentity, ...],
        explanations: tuple[AttributedExplanation, ...],
        correlation: tuple[CorrelationFinding, ...] = (),
        synthesis: str | None = None,
    ) -> "ExecutiveIntelligenceResult":
        return cls(
            capability=capability,
            composition_trace=composition_trace,
            advisor_identities=advisor_identities,
            explanations=explanations,
            correlation=correlation,
            synthesis=synthesis,
        )
