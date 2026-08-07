"""The Selection Rule (Domain Blueprint §2.2, D-138; Technical Design §2) --
a deterministic, explicit, reproducible, auditable correspondence between
structured signals and `AdvisorIdentity`s. Never the LLM's responsibility
(Vision, Princípio 12/D-137): this module never imports an `LLMProvider`,
never calls one.

Pure function of its inputs: the same `SelectionSignals`, against the same
`ADVISOR_IDENTITY_CATALOG`/`VOCABULARY`, always produces the same
`SelectionOutcome` -- no randomness, no external state, no evidence already
collected (Domain Blueprint §3.2: evaluating against evidence would be
circular).
"""
from dataclasses import dataclass, field

from src.services.executive_orchestrator.catalog import (
    ADVISOR_ELIGIBLE_SCOPES,
    ADVISOR_IDENTITY_CATALOG,
    ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID,
    VOCABULARY,
)
from src.services.executive_orchestrator.types import AdvisorIdentity, SelectionTraceEntry


@dataclass(frozen=True)
class OrchestrationScope:
    """The union of scope parameters the 8 Advisors' own existing evidence
    provisioning already requires (Technical Design §1.1) -- nothing
    invented, `project_name` and `portfolio_id` are exactly the two scope
    fields already present across the 8 real `*AdvisorRequest` models."""

    project_name: str | None = None
    portfolio_id: int | None = None


@dataclass(frozen=True)
class SelectionSignals:
    """Structured signals a Selection Rule evaluation consumes (Technical
    Design §2.1) -- `explicit` always takes precedence over lexical
    matching against `question` when non-empty (deterministic precedence,
    §2.1: "ordem de precedência determinística")."""

    explicit: frozenset[str] = field(default_factory=frozenset)
    question: str = ""
    scope: OrchestrationScope = field(default_factory=OrchestrationScope)


@dataclass(frozen=True)
class SelectionOutcome:
    selected: tuple[AdvisorIdentity, ...]
    trace_entry: SelectionTraceEntry


def _matches_vocabulary(advisor_name: str, explicit: frozenset[str]) -> bool:
    terms = VOCABULARY[advisor_name]
    return bool(explicit & terms) or advisor_name in explicit


def _matches_question_text(advisor_name: str, question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in VOCABULARY[advisor_name])


def _scope_type(scope: OrchestrationScope) -> str:
    """Infers which of the three Explicit Scope types (Founder Decision --
    Eliminação do Risco de Escopo Implícito; Vision, Princípio 13) `scope`
    represents. Safe by construction: `OrchestrationScope` is only ever
    built by a validated caller boundary (Technical Design §5) where
    `project_name`/`portfolio_id` being simultaneously `None` always means
    `organization` was explicitly declared, never that scope was omitted."""
    if scope.project_name is not None:
        return "project"
    if scope.portfolio_id is not None:
        return "portfolio"
    return "organization"


def _meets_structural_precondition(advisor_name: str, scope: OrchestrationScope) -> bool:
    if advisor_name in ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID:
        if scope.portfolio_id is None:
            return False
    return _scope_type(scope) in ADVISOR_ELIGIBLE_SCOPES[advisor_name]


def evaluate_selection_rule(
    signals: SelectionSignals,
    catalog: tuple[AdvisorIdentity, ...] = ADVISOR_IDENTITY_CATALOG,
) -> SelectionOutcome:
    """Deterministic: same `signals` (and same `catalog`, which is static)
    always produces the same `SelectionOutcome`. Explicit signals, when
    present, are the exclusive basis for matching -- lexical matching
    against `signals.question` is only consulted when `signals.explicit`
    is empty."""
    use_explicit = bool(signals.explicit)
    selected = tuple(
        identity
        for identity in catalog
        if (
            _matches_vocabulary(identity.name, signals.explicit)
            if use_explicit
            else _matches_question_text(identity.name, signals.question)
        )
        and _meets_structural_precondition(identity.name, signals.scope)
    )
    trace_entry = SelectionTraceEntry(
        signals=tuple(sorted(signals.explicit)) if use_explicit else (signals.question,),
        selected_advisor_names=tuple(identity.name for identity in selected),
    )
    return SelectionOutcome(selected=selected, trace_entry=trace_entry)
