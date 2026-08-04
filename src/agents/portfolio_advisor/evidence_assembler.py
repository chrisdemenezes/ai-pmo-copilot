"""`PortfolioEvidenceAssembler` -- Portfolio Advisor's exclusive composition
component (Wave 5, Classe B, D-109/AR-12/D-111).

Resolves a Portfolio's evidence by making N calls to
`AdvisorFramework.gather_context(kind="status")`, one per Project under the
Portfolio's Programs -- never a new `AdvisorFramework`/`AIContextEngine`
method. Lives exclusively inside this package (never `src/services/`), per
the Founder's explicit instruction that this composition responsibility
must not be transferred to the shared Framework, and must not become a
generic abstraction at this stage.

Per Founder Decision ("Technical Design do Portfolio Advisor", items 3/4):
each Project contributes exactly one `Evidence` -- its most recent status
`AnalysisRecord`, selected mechanically as `evidence[0]` (already guaranteed
by `AnalysisRepository.list_analyses()`'s `created_at DESC` ordering). This
class never reads `content`, never compares `health_status`, never computes
a trend, never assigns a weight, and never applies any selection rule beyond
"first item of an already-ordered list".
"""
from dataclasses import dataclass

from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence
from src.services.domain_service import DomainService


@dataclass(frozen=True)
class PortfolioAssemblyResult:
    evidence: list[Evidence]
    total_projects: int
    projects_with_evidence: int


class PortfolioEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        self._domain_service = domain_service
        self._framework = framework

    def assemble(self, organization_id: int, portfolio_id: int) -> PortfolioAssemblyResult | None:
        portfolio = self._domain_service.get_portfolio(portfolio_id, organization_id)
        if portfolio is None:
            return None

        programs = self._domain_service.list_programs(organization_id, portfolio_id) or []

        evidence: list[Evidence] = []
        total_projects = 0
        projects_with_evidence = 0

        for program in programs:
            projects = self._domain_service.list_projects(organization_id, program.id) or []
            for project in projects:
                total_projects += 1
                project_evidence = self._framework.gather_context(
                    organization_id, project.name, kind="status"
                )
                if not project_evidence:
                    continue

                most_recent = project_evidence[0]
                evidence.append(
                    Evidence(
                        source_type=most_recent.source_type,
                        source_id=most_recent.source_id,
                        source_label=most_recent.source_label,
                        content=most_recent.content,
                        metadata={
                            **most_recent.metadata,
                            "portfolio_id": portfolio.id,
                            "program_id": program.id,
                            "project_id": project.id,
                            "project_name": project.name,
                        },
                    )
                )
                projects_with_evidence += 1

        return PortfolioAssemblyResult(
            evidence=evidence,
            total_projects=total_projects,
            projects_with_evidence=projects_with_evidence,
        )
