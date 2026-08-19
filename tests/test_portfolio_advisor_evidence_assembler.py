"""`PortfolioEvidenceAssembler` unit tests (Wave 5, Classe B), per
`TECHNICAL-DESIGN-PORTFOLIO-ADVISOR.md` §2/§12.

Uses fakes for `DomainService`/`AdvisorFramework` so these tests exercise
exclusively the Assembler's own composition logic -- mechanical selection
of `evidence[0]`, metadata enrichment, coverage counting -- never a real
database. Framework-level integration (real Postgres, real
`AIContextEngine.gather()` ordering) is covered by
`tests/test_portfolio_advisor.py`.
"""
from datetime import datetime, timezone
from types import SimpleNamespace

from src.agents.portfolio_advisor.evidence_assembler import PortfolioEvidenceAssembler
from src.services.ai_foundation.types import Evidence


def _status_evidence(source_id: int, health_status: str, created_at: datetime) -> Evidence:
    return Evidence(
        source_type="analysis_record",
        source_id=source_id,
        source_label=f"AnalysisRecord#{source_id} (status)",
        content={"structured": True, "health_status": health_status, "key_findings": [], "recommendations": []},
        metadata={"created_at": created_at, "kind": "status"},
    )


class FakeDomainService:
    def __init__(self, portfolio=None, programs_by_portfolio=None, projects_by_program=None):
        self.portfolio = portfolio
        self.programs_by_portfolio = programs_by_portfolio or {}
        self.projects_by_program = projects_by_program or {}
        self.get_portfolio_calls = []
        self.list_programs_calls = []
        self.list_projects_calls = []

    def get_portfolio(self, portfolio_id, organization_id):
        self.get_portfolio_calls.append((portfolio_id, organization_id))
        return self.portfolio

    def list_programs(self, organization_id, portfolio_id):
        self.list_programs_calls.append((organization_id, portfolio_id))
        return self.programs_by_portfolio.get(portfolio_id, [])

    def list_projects(self, organization_id, program_id):
        self.list_projects_calls.append((organization_id, program_id))
        return self.projects_by_program.get(program_id, [])


class FakeFramework:
    def __init__(self, evidence_by_project_name: dict[str, list[Evidence]]):
        self._evidence_by_project_name = evidence_by_project_name
        self.gather_context_calls: list[tuple] = []

    def gather_context(self, organization_id, project_name, kind):
        self.gather_context_calls.append((organization_id, project_name, kind))
        return self._evidence_by_project_name.get(project_name, [])


PORTFOLIO = SimpleNamespace(id=10, name="Cloud Modernization")
PROGRAM_A = SimpleNamespace(id=20, name="Infra", code="INFRA")
PROGRAM_B = SimpleNamespace(id=21, name="Data", code="DATA")
PROJECT_AURORA = SimpleNamespace(id=30, name="Aurora")
PROJECT_BOREAL = SimpleNamespace(id=31, name="Boreal")
PROJECT_CASTOR = SimpleNamespace(id=32, name="Castor")


def test_returns_none_when_portfolio_is_not_found():
    domain_service = FakeDomainService(portfolio=None)
    framework = FakeFramework(evidence_by_project_name={})
    assembler = PortfolioEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1, portfolio_id=999)

    assert result is None
    assert domain_service.get_portfolio_calls == [(999, 1)]


def test_selects_evidence_zero_mechanically_per_project():
    old = _status_evidence(1, "red", datetime(2026, 7, 1, tzinfo=timezone.utc))
    recent = _status_evidence(2, "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
    domain_service = FakeDomainService(
        portfolio=PORTFOLIO,
        programs_by_portfolio={PORTFOLIO.id: [PROGRAM_A]},
        projects_by_program={PROGRAM_A.id: [PROJECT_AURORA]},
    )
    # Framework already returns most-recent-first, exactly as
    # AIContextEngine.gather() guarantees in production (AR-11/AR-12).
    framework = FakeFramework({PROJECT_AURORA.name: [recent, old]})
    assembler = PortfolioEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1, portfolio_id=PORTFOLIO.id)

    assert len(result.evidence) == 1
    assert result.evidence[0].source_id == 2  # the recent one, never the old one
    assert result.total_projects == 1
    assert result.projects_with_evidence == 1


def test_a_project_with_many_records_never_outweighs_a_project_with_one():
    many_records_project_evidence = [
        _status_evidence(3, "green", datetime(2026, 8, 1, tzinfo=timezone.utc)),
        _status_evidence(2, "yellow", datetime(2026, 7, 20, tzinfo=timezone.utc)),
        _status_evidence(1, "red", datetime(2026, 7, 1, tzinfo=timezone.utc)),
    ]
    single_record_project_evidence = [_status_evidence(4, "yellow", datetime(2026, 8, 1, tzinfo=timezone.utc))]
    domain_service = FakeDomainService(
        portfolio=PORTFOLIO,
        programs_by_portfolio={PORTFOLIO.id: [PROGRAM_A]},
        projects_by_program={PROGRAM_A.id: [PROJECT_AURORA, PROJECT_BOREAL]},
    )
    framework = FakeFramework(
        {
            PROJECT_AURORA.name: many_records_project_evidence,
            PROJECT_BOREAL.name: single_record_project_evidence,
        }
    )
    assembler = PortfolioEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1, portfolio_id=PORTFOLIO.id)

    # Exactly one Evidence per project, regardless of how much history exists.
    assert len(result.evidence) == 2
    assert {item.metadata["project_id"] for item in result.evidence} == {PROJECT_AURORA.id, PROJECT_BOREAL.id}
    assert result.total_projects == 2
    assert result.projects_with_evidence == 2


def test_enriches_metadata_with_portfolio_program_project_without_altering_evidence_contract():
    snapshot = _status_evidence(5, "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
    domain_service = FakeDomainService(
        portfolio=PORTFOLIO,
        programs_by_portfolio={PORTFOLIO.id: [PROGRAM_A]},
        projects_by_program={PROGRAM_A.id: [PROJECT_AURORA]},
    )
    framework = FakeFramework({PROJECT_AURORA.name: [snapshot]})
    assembler = PortfolioEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1, portfolio_id=PORTFOLIO.id)

    enriched = result.evidence[0]
    assert enriched.metadata["portfolio_id"] == PORTFOLIO.id
    assert enriched.metadata["program_id"] == PROGRAM_A.id
    assert enriched.metadata["project_id"] == PROJECT_AURORA.id
    assert enriched.metadata["project_name"] == PROJECT_AURORA.name
    # created_at survives from the original Evidence.metadata, untouched.
    assert enriched.metadata["created_at"] == snapshot.metadata["created_at"]
    # source_id/source_type/source_label/content are the contract's own
    # top-level fields, preserved -- no new fields invented on Evidence.
    assert enriched.source_id == snapshot.source_id
    assert enriched.content == snapshot.content


def test_project_without_status_analysis_contributes_no_evidence():
    domain_service = FakeDomainService(
        portfolio=PORTFOLIO,
        programs_by_portfolio={PORTFOLIO.id: [PROGRAM_A]},
        projects_by_program={PROGRAM_A.id: [PROJECT_AURORA, PROJECT_BOREAL]},
    )
    framework = FakeFramework({PROJECT_AURORA.name: [_status_evidence(1, "green", datetime.now(timezone.utc))]})
    # PROJECT_BOREAL has no entry in evidence_by_project_name -> gather_context returns [].
    assembler = PortfolioEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1, portfolio_id=PORTFOLIO.id)

    assert result.total_projects == 2
    assert result.projects_with_evidence == 1
    assert len(result.evidence) == 1


def test_portfolio_without_programs_yields_zero_coverage():
    domain_service = FakeDomainService(portfolio=PORTFOLIO, programs_by_portfolio={PORTFOLIO.id: []})
    framework = FakeFramework({})
    assembler = PortfolioEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1, portfolio_id=PORTFOLIO.id)

    assert result.evidence == []
    assert result.total_projects == 0
    assert result.projects_with_evidence == 0


def test_calls_gather_context_exactly_once_per_project_with_kind_status():
    domain_service = FakeDomainService(
        portfolio=PORTFOLIO,
        programs_by_portfolio={PORTFOLIO.id: [PROGRAM_A, PROGRAM_B]},
        projects_by_program={
            PROGRAM_A.id: [PROJECT_AURORA],
            PROGRAM_B.id: [PROJECT_BOREAL, PROJECT_CASTOR],
        },
    )
    framework = FakeFramework(
        {
            PROJECT_AURORA.name: [_status_evidence(1, "green", datetime.now(timezone.utc))],
            PROJECT_BOREAL.name: [_status_evidence(2, "yellow", datetime.now(timezone.utc))],
            PROJECT_CASTOR.name: [_status_evidence(3, "red", datetime.now(timezone.utc))],
        }
    )
    assembler = PortfolioEvidenceAssembler(domain_service, framework)

    assembler.assemble(organization_id=1, portfolio_id=PORTFOLIO.id)

    assert len(framework.gather_context_calls) == 3
    assert all(kind == "status" for _org, _name, kind in framework.gather_context_calls)
    called_names = {name for _org, name, _kind in framework.gather_context_calls}
    assert called_names == {PROJECT_AURORA.name, PROJECT_BOREAL.name, PROJECT_CASTOR.name}
