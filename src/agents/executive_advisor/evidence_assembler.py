"""Executive Advisor evidence composition (Wave 5, third Classe B Advisor --
AR-8 §4.2/D-104), per `TECHNICAL-DESIGN-EXECUTIVE-ADVISOR.md`.

Organizational scope, resolved directly via `DomainService.list_projects()`
(same mechanism already used by `PMOEvidenceAssembler` -- D-120, no
Portfolio/Program traversal, no 404 case). For each Project, two explicit
`gather_context()` calls -- `kind="status"` and `kind="risk"` -- each
contributing at most its most recent record (`evidence[0]`), never
history (D-120/AR-14 §5). `gather_context_many()` was evaluated and
rejected for this Epic (D-120 §8): two explicit calls fully resolve the
composition without any Framework extension.

Deliberately NOT generalized with `PortfolioEvidenceAssembler`/
`PMOEvidenceAssembler` (D-118/D-120): this Assembler's two-`kind`,
evidence[0]-per-kind composition is structurally distinct from both --
neither capped history (PMO) nor single-`kind` evidence[0] (Portfolio).
The seven structural coverage counts are produced in the same pass as
composition, never a second iteration, and their invariants (AR-14 §4,
Technical Design §6) are a direct consequence of the loop's arithmetic,
never separately recomputed."""
from dataclasses import dataclass

from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence
from src.services.domain_service import DomainService


@dataclass(frozen=True)
class ExecutiveAssemblyResult:
    evidence: list[Evidence]
    total_projects: int
    projects_with_status: int
    projects_without_status: int
    projects_with_risk: int
    projects_without_risk: int
    projects_with_status_and_risk: int
    projects_without_any_evidence: int


class ExecutiveEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        self._domain_service = domain_service
        self._framework = framework

    def assemble(self, organization_id: int) -> ExecutiveAssemblyResult:
        projects = self._domain_service.list_projects(organization_id) or []

        evidence: list[Evidence] = []
        total_projects = 0
        projects_with_status = 0
        projects_with_risk = 0
        projects_with_status_and_risk = 0
        projects_without_any_evidence = 0

        for project in projects:
            total_projects += 1
            status_evidence = self._framework.gather_context(
                organization_id, project.name, kind="status"
            )
            risk_evidence = self._framework.gather_context(
                organization_id, project.name, kind="risk"
            )

            has_status = bool(status_evidence)
            has_risk = bool(risk_evidence)

            if has_status:
                projects_with_status += 1
                evidence.append(self._enrich(status_evidence[0], project))
            if has_risk:
                projects_with_risk += 1
                evidence.append(self._enrich(risk_evidence[0], project))
            if has_status and has_risk:
                projects_with_status_and_risk += 1
            if not has_status and not has_risk:
                projects_without_any_evidence += 1

        return ExecutiveAssemblyResult(
            evidence=evidence,
            total_projects=total_projects,
            projects_with_status=projects_with_status,
            projects_without_status=total_projects - projects_with_status,
            projects_with_risk=projects_with_risk,
            projects_without_risk=total_projects - projects_with_risk,
            projects_with_status_and_risk=projects_with_status_and_risk,
            projects_without_any_evidence=projects_without_any_evidence,
        )

    @staticmethod
    def _enrich(item: Evidence, project) -> Evidence:
        return Evidence(
            source_type=item.source_type,
            source_id=item.source_id,
            source_label=item.source_label,
            content=item.content,
            metadata={**item.metadata, "project_id": project.id, "project_name": project.name},
        )
