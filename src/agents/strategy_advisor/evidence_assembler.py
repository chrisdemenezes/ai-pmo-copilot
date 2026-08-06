"""Strategy Advisor evidence composition (Wave 5, fourth Classe B Advisor,
eighth and last Advisor of the Wave), per
`TECHNICAL-DESIGN-STRATEGY-ADVISOR.md`.

Three independent, parallel alignment units -- Portfolio, Program, Project
(Domain Blueprint §2) -- each compared exclusively against its own declared
objective field (`Portfolio.strategic_objective`/`Program.objective`/
`Project.objective`), never inherited between levels. Execution evidence
(`kind="status"`/`kind="risk"`) exists structurally only at Project level;
Program/Portfolio "execution" is always an aggregation of the same
`execution_by_project` results, never a second `gather_context()` call for
the same Project (Domain Blueprint §5.2/§6, Technical Design §2.4).

Project-level composition resolves via `DomainService.list_projects(
organization_id)` -- the same organization-wide call already used by the
Executive/PMO Advisor -- rather than exclusively via Program traversal, so
that orphan Projects (`program_id IS NULL`) participate normally in the
Project unit (Domain Blueprint §2.3), while remaining structurally
unreachable from any Program/Portfolio aggregation (they are never returned
by `list_projects(organization_id, program_id)` for any real Program).

First-ever use of a synthetic, disjoint `Evidence.source_id`
(`_synthetic_source_id`/`_decode_synthetic_source_id`) to let evidence of a
non-`AnalysisRecord` source type (`declared_strategy`) coexist, in the same
`RecommendationEngine.build()` call, with `AnalysisRecord`-sourced evidence
without ever colliding (AR-15 §6.1, Technical Design §3)."""
from dataclasses import dataclass

from src.database.models import Program, Project
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence
from src.services.domain_service import DomainService

_LEVEL_CODE: dict[str, int] = {"portfolio": 1, "program": 2, "project": 3}
_LEVEL_BY_CODE: dict[int, str] = {code: level for level, code in _LEVEL_CODE.items()}


def _synthetic_source_id(level: str, real_entity_id: int) -> int:
    return -(real_entity_id * 10 + _LEVEL_CODE[level])


def _decode_synthetic_source_id(synthetic_id: int) -> tuple[str, int]:
    encoded = -synthetic_id
    level_code = encoded % 10
    real_entity_id = encoded // 10
    return _LEVEL_BY_CODE[level_code], real_entity_id


@dataclass(frozen=True)
class StrategyAssemblyResult:
    evidence: list[Evidence]
    portfolios_total: int
    portfolios_with_declared_strategy: int
    portfolios_without_declared_strategy: int
    portfolios_with_execution_evidence: int
    portfolios_comparable: int
    portfolios_with_strategy_without_execution: int
    programs_total: int
    programs_with_declared_strategy: int
    programs_without_declared_strategy: int
    programs_with_execution_evidence: int
    programs_comparable: int
    programs_with_strategy_without_execution: int
    projects_total: int
    projects_with_declared_strategy: int
    projects_without_declared_strategy: int
    projects_with_execution_evidence: int
    projects_comparable: int
    projects_with_strategy_without_execution: int


class StrategyEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        self._domain_service = domain_service
        self._framework = framework

    def assemble(self, organization_id: int) -> StrategyAssemblyResult:
        evidence: list[Evidence] = []

        # Step 1 -- resolve execution for every Project in the organization
        # exactly once (one gather_context() call per kind), including
        # orphan Projects (program_id IS NULL) -- Domain Blueprint §2.3.
        all_projects: list[Project] = self._domain_service.list_projects(organization_id) or []
        execution_by_project: dict[int, dict[str, Evidence | None]] = {}
        for project in all_projects:
            status_evidence = self._framework.gather_context(
                organization_id, project.name, kind="status"
            )
            risk_evidence = self._framework.gather_context(
                organization_id, project.name, kind="risk"
            )
            execution_by_project[project.id] = {
                "status": self._enrich_execution(status_evidence[0], project)
                if status_evidence
                else None,
                "risk": self._enrich_execution(risk_evidence[0], project) if risk_evidence else None,
            }

        portfolios_total = 0
        portfolios_with_declared_strategy = 0
        portfolios_with_execution_evidence = 0
        portfolios_comparable = 0
        portfolios_with_strategy_without_execution = 0
        programs_total = 0
        programs_with_declared_strategy = 0
        programs_with_execution_evidence = 0
        programs_comparable = 0
        programs_with_strategy_without_execution = 0
        projects_total = 0
        projects_with_declared_strategy = 0
        projects_with_execution_evidence = 0
        projects_comparable = 0
        projects_with_strategy_without_execution = 0

        # Step 2 -- Project unit: own objective vs. own execution.
        for project in all_projects:
            projects_total += 1
            exec_items = [e for e in execution_by_project[project.id].values() if e is not None]
            has_strategy = bool(project.objective)
            has_execution = bool(exec_items)
            if has_strategy:
                projects_with_declared_strategy += 1
                evidence.append(
                    self._declared_strategy_evidence(
                        "project", project.id, project.name, project.objective
                    )
                )
            if has_execution:
                projects_with_execution_evidence += 1
                evidence.extend(exec_items)
            if has_strategy and has_execution:
                projects_comparable += 1
            elif has_strategy and not has_execution:
                projects_with_strategy_without_execution += 1

        portfolios = self._domain_service.list_portfolios(organization_id) or []

        # Step 3 -- Program unit: own objective vs. execution aggregated
        # from its own Projects, reusing execution_by_project -- never a
        # new gather_context() call.
        all_programs: list[Program] = []
        for portfolio in portfolios:
            for program in self._domain_service.list_programs(organization_id, portfolio.id) or []:
                all_programs.append(program)
                programs_total += 1
                program_projects = (
                    self._domain_service.list_projects(organization_id, program.id) or []
                )
                exec_items = [
                    e
                    for p in program_projects
                    for e in execution_by_project[p.id].values()
                    if e is not None
                ]
                has_strategy = bool(program.objective)
                has_execution = bool(exec_items)
                if has_strategy:
                    programs_with_declared_strategy += 1
                    evidence.append(
                        self._declared_strategy_evidence(
                            "program", program.id, program.name, program.objective
                        )
                    )
                if has_execution:
                    programs_with_execution_evidence += 1
                    # exec_items already present in `evidence` via Step 2 --
                    # never duplicated here.
                if has_strategy and has_execution:
                    programs_comparable += 1
                elif has_strategy and not has_execution:
                    programs_with_strategy_without_execution += 1

        # Step 4 -- Portfolio unit: own objective vs. execution aggregated
        # from every Project under every one of its Programs, same reuse.
        for portfolio in portfolios:
            portfolios_total += 1
            portfolio_projects = [
                p
                for program in (self._domain_service.list_programs(organization_id, portfolio.id) or [])
                for p in (self._domain_service.list_projects(organization_id, program.id) or [])
            ]
            exec_items = [
                e
                for p in portfolio_projects
                for e in execution_by_project[p.id].values()
                if e is not None
            ]
            has_strategy = bool(portfolio.strategic_objective)
            has_execution = bool(exec_items)
            if has_strategy:
                portfolios_with_declared_strategy += 1
                evidence.append(
                    self._declared_strategy_evidence(
                        "portfolio", portfolio.id, portfolio.name, portfolio.strategic_objective
                    )
                )
            if has_execution:
                portfolios_with_execution_evidence += 1
            if has_strategy and has_execution:
                portfolios_comparable += 1
            elif has_strategy and not has_execution:
                portfolios_with_strategy_without_execution += 1

        return StrategyAssemblyResult(
            evidence=evidence,
            portfolios_total=portfolios_total,
            portfolios_with_declared_strategy=portfolios_with_declared_strategy,
            portfolios_without_declared_strategy=portfolios_total - portfolios_with_declared_strategy,
            portfolios_with_execution_evidence=portfolios_with_execution_evidence,
            portfolios_comparable=portfolios_comparable,
            portfolios_with_strategy_without_execution=portfolios_with_strategy_without_execution,
            programs_total=programs_total,
            programs_with_declared_strategy=programs_with_declared_strategy,
            programs_without_declared_strategy=programs_total - programs_with_declared_strategy,
            programs_with_execution_evidence=programs_with_execution_evidence,
            programs_comparable=programs_comparable,
            programs_with_strategy_without_execution=programs_with_strategy_without_execution,
            projects_total=projects_total,
            projects_with_declared_strategy=projects_with_declared_strategy,
            projects_without_declared_strategy=projects_total - projects_with_declared_strategy,
            projects_with_execution_evidence=projects_with_execution_evidence,
            projects_comparable=projects_comparable,
            projects_with_strategy_without_execution=projects_with_strategy_without_execution,
        )

    @staticmethod
    def _declared_strategy_evidence(
        level: str, real_entity_id: int, entity_name: str, objective: str
    ) -> Evidence:
        return Evidence(
            source_type="declared_strategy",
            source_id=_synthetic_source_id(level, real_entity_id),
            source_label=f"{level.capitalize()} {entity_name} -- objetivo declarado",
            content={"objective": objective},
            metadata={
                "level": level,
                "real_entity_id": real_entity_id,
                "entity_name": entity_name,
                "declared_objective": objective,
                "kind": "declared_strategy",
            },
        )

    @staticmethod
    def _enrich_execution(item: Evidence, project: Project) -> Evidence:
        return Evidence(
            source_type=item.source_type,
            source_id=item.source_id,
            source_label=item.source_label,
            content=item.content,
            metadata={
                **item.metadata,
                "level": "project",
                "real_entity_id": project.id,
                "entity_name": project.name,
            },
        )
