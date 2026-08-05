"""PMO Advisor evidence composition (Wave 5, second Classe B Advisor --
AR-8 SS4.2/D-104), per `TECHNICAL-DESIGN-PMO-ADVISOR.md`.

Organizational scope, resolved directly via `DomainService.list_projects()`
(no Portfolio/Program traversal -- D-114). For each Project, up to the five
most recent `AnalysisRecord`/kind="status" become independent `Evidence`
items (never one aggregate per Project, unlike `PortfolioEvidenceAssembler`
-- AR-13 SS2/SS3). Staleness is computed once per Project, from the single
most recent record, and replicated identically across every `Evidence` item
that Project contributes -- the LLM never calculates it.

Deliberately NOT generalized with `PortfolioEvidenceAssembler` (D-114/AR-13
SS5): the two Assemblers' evidence-selection logic (evidence[0] mechanic vs.
capped history) and scope-resolution logic (Portfolio-rooted traversal vs.
direct organization-wide listing) diverge structurally, not just in form."""
from dataclasses import dataclass
from datetime import datetime, timezone

from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence
from src.services.domain_service import DomainService

PMO_STALENESS_THRESHOLD_DAYS = 14
PMO_MAX_RECORDS_PER_PROJECT = 5


@dataclass(frozen=True)
class PMOAssemblyResult:
    evidence: list[Evidence]
    total_projects: int
    projects_with_status: int
    projects_without_status: int
    projects_stale: int
    projects_current: int


class PMOEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        self._domain_service = domain_service
        self._framework = framework

    def assemble(self, organization_id: int) -> PMOAssemblyResult:
        projects = self._domain_service.list_projects(organization_id) or []
        # Captured once per call (AR-13 SS4.3) -- every Project's
        # staleness_days in this response is measured against the same
        # instant, never a different one per iteration.
        reference_time = datetime.now(timezone.utc)

        evidence: list[Evidence] = []
        total_projects = 0
        projects_with_status = 0
        projects_stale = 0
        projects_current = 0

        for project in projects:
            total_projects += 1
            project_evidence = self._framework.gather_context(
                organization_id, project.name, kind="status"
            )
            if not project_evidence:
                continue

            projects_with_status += 1
            most_recent = project_evidence[0]
            staleness_days = (reference_time - most_recent.metadata["created_at"]).days
            is_stale = staleness_days >= PMO_STALENESS_THRESHOLD_DAYS
            if is_stale:
                projects_stale += 1
            else:
                projects_current += 1

            for item in project_evidence[:PMO_MAX_RECORDS_PER_PROJECT]:
                evidence.append(
                    Evidence(
                        source_type=item.source_type,
                        source_id=item.source_id,
                        source_label=item.source_label,
                        content=item.content,
                        metadata={
                            **item.metadata,
                            "project_id": project.id,
                            "project_name": project.name,
                            "staleness_days": staleness_days,
                            "is_stale": is_stale,
                        },
                    )
                )

        return PMOAssemblyResult(
            evidence=evidence,
            total_projects=total_projects,
            projects_with_status=projects_with_status,
            projects_without_status=total_projects - projects_with_status,
            projects_stale=projects_stale,
            projects_current=projects_current,
        )
