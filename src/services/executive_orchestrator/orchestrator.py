"""`ExecutiveOrchestrator` (Technical Design, full document) -- Etapa 3:
Selection -> Execution -> Correlation -> Composition Trace -> Executive
Intelligence Result. Still without Synthesis (Etapa 4).

Never implements `AdvisorContract` (Vision, Princípio 8: never a 9th
Advisor). Never calls `AIContextEngine`/`DomainService`/any repository
except through the exact same `AdvisorFramework.gather_context()`/
`gather_rag_context()`/`EvidenceAssembler` calls each Advisor's own route
already performs (`provisioning.py`) -- reused verbatim, never a new or
different evidence-access path. `AdvisorFramework.run()` is called exactly
once per selected Advisor Identity, unmodified, same signature already in
production (Vision, Princípio 2).

Request-scoped by construction: holds no state beyond its two injected,
already-shared dependencies (`AdvisorFramework`, `DomainService`) -- never
mutated after `__init__`, never written to during `run()`.
"""
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import SessionContext
from src.services.domain_service import DomainService
from src.services.executive_orchestrator.correlation import correlate
from src.services.executive_orchestrator.provisioning import provision
from src.services.executive_orchestrator.selection_rule import SelectionSignals, evaluate_selection_rule
from src.services.executive_orchestrator.types import (
    AttributedExplanation,
    Capability,
    CompositionTrace,
    CorrelationTraceEntry,
    ExecutionTraceEntry,
    ExecutiveIntelligenceResult,
    InsufficientBasisReason,
)


class ExecutiveOrchestrator:
    def __init__(self, framework: AdvisorFramework, domain_service: DomainService):
        self._framework = framework
        self._domain_service = domain_service

    def run(
        self,
        capability: Capability,
        session: SessionContext,
        question: str,
        signals: SelectionSignals,
    ) -> ExecutiveIntelligenceResult:
        outcome = evaluate_selection_rule(signals)
        trace = CompositionTrace().with_selection(outcome.trace_entry)

        if not outcome.selected:
            return ExecutiveIntelligenceResult.insufficient_basis(
                capability, trace, InsufficientBasisReason.SELECTION_EMPTY
            )

        explanations: list[AttributedExplanation] = []
        any_had_evidence = False
        for identity in outcome.selected:
            provisioned = provision(
                identity.name, self._framework, self._domain_service, session, question, signals.scope
            )
            # "Had evidence" reflects the Domain Blueprint §4 definition of
            # Collection Empty verbatim -- whether the Advisor's own
            # `no_evidence()` gate (AdvisorFramework.run(): `if not
            # evidence`) was triggered, i.e. whether evidence was gathered
            # at all -- never whether the LLM chose to cite it afterward
            # (a separate concern the LLM alone controls).
            had_evidence = bool(provisioned.evidence)
            any_had_evidence = any_had_evidence or had_evidence
            explanation = self._framework.run(
                provisioned.agent,
                session,
                question,
                provisioned.evidence,
                rag_context=provisioned.rag_context,
                no_evidence_answer=provisioned.no_evidence_answer,
            )
            trace = trace.with_execution(
                ExecutionTraceEntry(advisor_name=identity.name, had_evidence=had_evidence)
            )
            explanations.append(AttributedExplanation(advisor_name=identity.name, explanation=explanation))

        if not any_had_evidence:
            return ExecutiveIntelligenceResult.insufficient_basis(
                capability,
                trace,
                InsufficientBasisReason.COLLECTION_EMPTY,
                advisor_identities=outcome.selected,
                explanations=tuple(explanations),
            )

        correlation = correlate(tuple(explanations))
        if capability == Capability.CONFLICT_ANALYSIS:
            correlation = tuple(finding for finding in correlation if finding.is_structural_pair)
        trace = trace.with_correlations(
            tuple(
                CorrelationTraceEntry(
                    advisor_names=finding.advisor_names, is_structural_pair=finding.is_structural_pair
                )
                for finding in correlation
            )
        )

        return ExecutiveIntelligenceResult.complete(
            capability,
            trace,
            advisor_identities=outcome.selected,
            explanations=tuple(explanations),
            correlation=correlation,
        )
