"""First end-to-end PMO workflow.

**HISTORICAL SUPERSEDED ARCHITECTURE — non-production, non-reference
implementation** (Founder Decision, Wave 4 Decision Proposal, D-074).
Preserved only for historical traceability — do NOT import, extend, or
use this class or its pattern as a basis for any new code:

- The multi-agent orchestration this class anticipated
  (`architecture/05-ai-orchestration-design.md`) was superseded by the
  `AdvisorFramework` (Wave 3, `src/services/advisor_framework/`), which
  executes exactly one Advisor per call and never routes autonomously
  between agents.
- Operational orchestration (events, processes, integrations) is now
  the responsibility of the Wave 4 Workflow Runtime
  (`docs/architecture/WAVE-4-DOMAIN-BLUEPRINT.md`), never this class.
- This file mixes workflow orchestration with business logic
  (`ai.process(document)`), which the Wave 4 principle "Workflow ≠
  Business Logic" explicitly forbids in any new code.

Reservado intencionalmente para a próxima fase do projeto
(orquestração multi-agente, conforme architecture/05-ai-orchestration-design.md).

Ainda não conectado ao MVP atual (src/api/routes/intelligence.py).
Não remover nem tratar como órfão em futuras reavaliações de débito técnico.
"""

class PMOWorkflow:
    def execute(self, document, ai, repository):
        return repository.save(ai.process(document))
