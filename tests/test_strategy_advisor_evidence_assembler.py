"""`StrategyEvidenceAssembler` unit tests (Wave 5, fourth Classe B Advisor,
eighth and last Advisor of the Wave), per
`TECHNICAL-DESIGN-STRATEGY-ADVISOR.md` §2/§3.

Uses fakes for `DomainService`/`AdvisorFramework` so these tests exercise
exclusively the Assembler's own composition logic -- three independent
alignment units, the synthetic namespace formula, the 18 structural
coverage counts -- never a real database. Framework-level integration
(real Postgres, real `AIContextEngine.gather()`) is covered by
`tests/test_strategy_advisor.py`.

Covers scenarios A-G, J, K, L, O, S (§12/§12.1)."""
from datetime import datetime, timezone
from types import SimpleNamespace

from src.agents.strategy_advisor.evidence_assembler import (
    StrategyEvidenceAssembler,
    _decode_synthetic_source_id,
    _synthetic_source_id,
)
from src.services.ai_foundation.types import Evidence

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def _status_evidence(source_id: int, created_at: datetime = NOW) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (status)",
        content={"structured": True, "health_status": "green", "key_findings": [], "recommendations": []},
        metadata={"created_at": created_at, "kind": "status"},
    )


def _risk_evidence(source_id: int, created_at: datetime = NOW) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (risk)",
        content={"structured": True, "risks": [], "escalation_recommendation": None},
        metadata={"created_at": created_at, "kind": "risk"},
    )


class FakeDomainService:
    def __init__(
        self,
        projects_by_organization: dict[int, list] | None = None,
        portfolios_by_organization: dict[int, list] | None = None,
        programs_by_portfolio: dict[int, list] | None = None,
        projects_by_program: dict[int, list] | None = None,
    ):
        self.projects_by_organization = projects_by_organization or {}
        self.portfolios_by_organization = portfolios_by_organization or {}
        self.programs_by_portfolio = programs_by_portfolio or {}
        self.projects_by_program = projects_by_program or {}
        self.list_projects_calls: list = []

    def list_portfolios(self, organization_id):
        return self.portfolios_by_organization.get(organization_id, [])

    def list_programs(self, organization_id, portfolio_id=None):
        return self.programs_by_portfolio.get(portfolio_id, [])

    def list_projects(self, organization_id, program_id=None):
        self.list_projects_calls.append((organization_id, program_id))
        if program_id is None:
            return self.projects_by_organization.get(organization_id, [])
        return self.projects_by_program.get(program_id, [])


class FakeFramework:
    def __init__(self, evidence_by_project_and_kind: dict[tuple[str, str], list[Evidence]]):
        self._evidence_by_project_and_kind = evidence_by_project_and_kind
        self.gather_context_calls: list[tuple] = []

    def gather_context(self, organization_id, project_name, kind):
        self.gather_context_calls.append((organization_id, project_name, kind))
        return self._evidence_by_project_and_kind.get((project_name, kind), [])


PORTFOLIO_ATLAS = SimpleNamespace(id=7, name="Atlas", strategic_objective="Expandir para APAC")
PORTFOLIO_NO_OBJECTIVE = SimpleNamespace(id=8, name="Sem Objetivo", strategic_objective=None)
PROGRAM_ORION = SimpleNamespace(id=7, name="Orion", objective="Consolidar squads de dados")
PROGRAM_NO_OBJECTIVE = SimpleNamespace(id=15, name="Sem Objetivo", objective=None)
PROJECT_AURORA = SimpleNamespace(id=30, name="Aurora", objective="Migrar workloads para APAC")
PROJECT_BOREAL = SimpleNamespace(id=31, name="Boreal", objective=None)
PROJECT_CASTOR = SimpleNamespace(id=32, name="Castor", objective="Lançar squad regional")


def test_organization_without_anything_yields_zero_coverage():
    domain_service = FakeDomainService()
    framework = FakeFramework({})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.evidence == []
    assert result.portfolios_total == 0
    assert result.programs_total == 0
    assert result.projects_total == 0


def test_scenario_a_project_with_objective_and_execution_is_comparable():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework(
        {
            (PROJECT_AURORA.name, "status"): [_status_evidence(1)],
            (PROJECT_AURORA.name, "risk"): [_risk_evidence(2)],
        }
    )
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.projects_total == 1
    assert result.projects_with_declared_strategy == 1
    assert result.projects_with_execution_evidence == 1
    assert result.projects_comparable == 1
    assert result.projects_with_strategy_without_execution == 0
    declared = next(e for e in result.evidence if e.metadata["kind"] == "declared_strategy")
    assert declared.source_id == _synthetic_source_id("project", PROJECT_AURORA.id)
    assert declared.metadata["real_entity_id"] == PROJECT_AURORA.id
    assert declared.content == {"objective": PROJECT_AURORA.objective}


def test_scenario_b_project_with_objective_but_no_execution():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.projects_with_declared_strategy == 1
    assert result.projects_with_execution_evidence == 0
    assert result.projects_comparable == 0
    assert result.projects_with_strategy_without_execution == 1


def test_scenario_c_project_without_objective_but_with_execution():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_BOREAL]})
    framework = FakeFramework({(PROJECT_BOREAL.name, "status"): [_status_evidence(1)]})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.projects_with_declared_strategy == 0
    assert result.projects_with_execution_evidence == 1
    assert result.projects_comparable == 0
    assert result.projects_with_strategy_without_execution == 0


def test_scenario_d_project_without_objective_and_without_execution():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_BOREAL]})
    framework = FakeFramework({})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.projects_with_declared_strategy == 0
    assert result.projects_with_execution_evidence == 0
    assert result.projects_comparable == 0
    assert result.projects_with_strategy_without_execution == 0


def test_scenario_e_program_comparable_via_aggregation_of_its_projects():
    domain_service = FakeDomainService(
        projects_by_organization={1: [PROJECT_AURORA]},
        portfolios_by_organization={1: [PORTFOLIO_NO_OBJECTIVE]},
        programs_by_portfolio={PORTFOLIO_NO_OBJECTIVE.id: [PROGRAM_ORION]},
        projects_by_program={PROGRAM_ORION.id: [PROJECT_AURORA]},
    )
    framework = FakeFramework({(PROJECT_AURORA.name, "status"): [_status_evidence(1)]})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.programs_total == 1
    assert result.programs_with_declared_strategy == 1
    assert result.programs_with_execution_evidence == 1
    assert result.programs_comparable == 1
    # gather_context() called exactly once per kind per Project -- never
    # repeated for the Program aggregation.
    assert len(framework.gather_context_calls) == 2


def test_scenario_f_portfolio_comparable_via_multi_level_aggregation_no_duplicate_calls():
    domain_service = FakeDomainService(
        projects_by_organization={1: [PROJECT_AURORA, PROJECT_CASTOR]},
        portfolios_by_organization={1: [PORTFOLIO_ATLAS]},
        programs_by_portfolio={PORTFOLIO_ATLAS.id: [PROGRAM_ORION, PROGRAM_NO_OBJECTIVE]},
        projects_by_program={
            PROGRAM_ORION.id: [PROJECT_AURORA],
            PROGRAM_NO_OBJECTIVE.id: [PROJECT_CASTOR],
        },
    )
    framework = FakeFramework(
        {
            (PROJECT_AURORA.name, "status"): [_status_evidence(1)],
            (PROJECT_CASTOR.name, "risk"): [_risk_evidence(2)],
        }
    )
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.portfolios_total == 1
    assert result.portfolios_with_declared_strategy == 1
    assert result.portfolios_with_execution_evidence == 1
    assert result.portfolios_comparable == 1
    # 2 Projects x 2 kinds = 4 calls, never duplicated for Program/Portfolio.
    assert len(framework.gather_context_calls) == 4


def test_scenario_g_absence_at_intermediate_level_never_propagates():
    domain_service = FakeDomainService(
        projects_by_organization={1: [PROJECT_AURORA]},
        portfolios_by_organization={1: [PORTFOLIO_ATLAS]},
        programs_by_portfolio={PORTFOLIO_ATLAS.id: [PROGRAM_NO_OBJECTIVE]},
        projects_by_program={PROGRAM_NO_OBJECTIVE.id: [PROJECT_AURORA]},
    )
    framework = FakeFramework({(PROJECT_AURORA.name, "status"): [_status_evidence(1)]})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    # Program has no objective of its own -- never comparable, but this
    # never affects the neighboring Project (comparable) or Portfolio
    # (comparable via its own strategic_objective + aggregated execution).
    assert result.programs_with_declared_strategy == 0
    assert result.programs_comparable == 0
    assert result.projects_comparable == 1
    assert result.portfolios_comparable == 1


def test_scenario_j_synthetic_source_id_never_collides_with_analysis_record_id():
    # Portfolio.id numerically equal to an AnalysisRecord.id present in the
    # same response -- synthetic_source_id is always negative by
    # construction, AnalysisRecord.id is always positive. PROJECT_BOREAL has
    # no objective of its own, so evidence contains exactly the execution
    # record plus Atlas' declared_strategy record -- nothing else.
    domain_service = FakeDomainService(
        projects_by_organization={1: [PROJECT_BOREAL]},
        portfolios_by_organization={1: [PORTFOLIO_ATLAS]},
        programs_by_portfolio={PORTFOLIO_ATLAS.id: []},
    )
    analysis_record_id = 71  # numerically equal to Atlas' encoded portfolio value
    framework = FakeFramework({(PROJECT_BOREAL.name, "status"): [_status_evidence(analysis_record_id)]})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    source_ids = {item.source_id for item in result.evidence}
    assert analysis_record_id in source_ids
    assert -analysis_record_id in source_ids  # Portfolio Atlas' synthetic id
    assert len(source_ids) == 2  # never collide -- both present distinctly


def test_scenario_k_decode_is_the_exact_inverse_of_encode_for_a_wide_sample():
    for level in ("portfolio", "program", "project"):
        for real_id in (1, 2, 7, 42, 999, 1_000_000):
            synthetic = _synthetic_source_id(level, real_id)
            assert _decode_synthetic_source_id(synthetic) == (level, real_id)


def test_scenario_l_synthetic_source_id_distinguishable_from_real_entity_id_in_metadata():
    domain_service = FakeDomainService(portfolios_by_organization={1: [PORTFOLIO_ATLAS]}, programs_by_portfolio={PORTFOLIO_ATLAS.id: []})
    framework = FakeFramework({})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    declared = result.evidence[0]
    assert declared.source_id != declared.metadata["real_entity_id"]
    assert declared.metadata["real_entity_id"] == PORTFOLIO_ATLAS.id
    assert declared.source_id < 0


def test_scenario_o_created_at_absent_from_declared_strategy_metadata_present_for_execution():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({(PROJECT_AURORA.name, "status"): [_status_evidence(1, NOW)]})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    declared = next(e for e in result.evidence if e.metadata["kind"] == "declared_strategy")
    status = next(e for e in result.evidence if e.metadata["kind"] == "status")
    assert "created_at" not in declared.metadata
    assert status.metadata["created_at"] == NOW


def test_scenario_s_same_real_id_across_levels_generates_distinct_tokens():
    portfolio_id_7 = _synthetic_source_id("portfolio", 7)
    program_id_7 = _synthetic_source_id("program", 7)
    project_id_7 = _synthetic_source_id("project", 7)

    assert portfolio_id_7 == -71
    assert program_id_7 == -72
    assert project_id_7 == -73
    assert len({portfolio_id_7, program_id_7, project_id_7}) == 3


def test_orphan_project_participates_in_project_unit_never_in_program_aggregation():
    # Project.program_id IS NULL (Domain Blueprint §2.3) -- resolved via the
    # organization-wide list_projects(organization_id), never reachable via
    # any Program's list_projects(organization_id, program_id).
    orphan = SimpleNamespace(id=99, name="Orphan", objective="Objetivo orfao")
    domain_service = FakeDomainService(
        projects_by_organization={1: [orphan]},
        portfolios_by_organization={1: [PORTFOLIO_NO_OBJECTIVE]},
        programs_by_portfolio={PORTFOLIO_NO_OBJECTIVE.id: []},
    )
    framework = FakeFramework({})
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.projects_total == 1
    assert result.projects_with_declared_strategy == 1
    # No Program/Portfolio ever aggregates the orphan's execution/strategy.
    assert result.programs_total == 0
    assert result.portfolios_with_execution_evidence == 0


def test_coverage_invariants_hold_across_a_mixed_organization():
    domain_service = FakeDomainService(
        projects_by_organization={1: [PROJECT_AURORA, PROJECT_BOREAL, PROJECT_CASTOR]},
        portfolios_by_organization={1: [PORTFOLIO_ATLAS]},
        programs_by_portfolio={PORTFOLIO_ATLAS.id: [PROGRAM_ORION]},
        projects_by_program={PROGRAM_ORION.id: [PROJECT_AURORA, PROJECT_BOREAL, PROJECT_CASTOR]},
    )
    framework = FakeFramework(
        {
            (PROJECT_AURORA.name, "status"): [_status_evidence(1)],
            (PROJECT_CASTOR.name, "risk"): [_risk_evidence(2)],
            # Boreal contributes nothing.
        }
    )
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    for prefix in ("portfolios", "programs", "projects"):
        total = getattr(result, f"{prefix}_total")
        with_ds = getattr(result, f"{prefix}_with_declared_strategy")
        without_ds = getattr(result, f"{prefix}_without_declared_strategy")
        comparable = getattr(result, f"{prefix}_comparable")
        with_exec = getattr(result, f"{prefix}_with_execution_evidence")
        with_ds_without_exec = getattr(result, f"{prefix}_with_strategy_without_execution")
        assert with_ds + without_ds == total
        assert comparable + with_ds_without_exec == with_ds
        assert comparable <= min(with_ds, with_exec)
