"""`ExecutiveEvidenceAssembler` unit tests (Wave 5, third Classe B Advisor),
per `TECHNICAL-DESIGN-EXECUTIVE-ADVISOR.md` §3.

Uses fakes for `DomainService`/`AdvisorFramework` so these tests exercise
exclusively the Assembler's own composition logic -- two explicit
gather_context() calls per Project, evidence[0] selection per kind, the
seven structural coverage counts and their invariants -- never a real
database. Framework-level integration (real Postgres, real
`AIContextEngine.gather()` ordering) is covered by
`tests/test_executive_advisor.py`.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.agents.executive_advisor.evidence_assembler import ExecutiveEvidenceAssembler
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
    def __init__(self, projects_by_organization: dict[int, list] | None = None):
        self.projects_by_organization = projects_by_organization or {}
        self.list_projects_calls: list = []

    def list_projects(self, organization_id, program_id=None):
        self.list_projects_calls.append((organization_id, program_id))
        assert program_id is None, "Executive Advisor scope is organizational -- never a Program traversal"
        return self.projects_by_organization.get(organization_id, [])


class FakeFramework:
    def __init__(self, evidence_by_project_and_kind: dict[tuple[str, str], list[Evidence]]):
        self._evidence_by_project_and_kind = evidence_by_project_and_kind
        self.gather_context_calls: list[tuple] = []

    def gather_context(self, organization_id, project_name, kind):
        self.gather_context_calls.append((organization_id, project_name, kind))
        return self._evidence_by_project_and_kind.get((project_name, kind), [])


PROJECT_AURORA = SimpleNamespace(id=30, name="Aurora")
PROJECT_BOREAL = SimpleNamespace(id=31, name="Boreal")
PROJECT_CASTOR = SimpleNamespace(id=32, name="Castor")


def test_organization_without_projects_yields_zero_coverage():
    domain_service = FakeDomainService(projects_by_organization={1: []})
    framework = FakeFramework({})
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.evidence == []
    assert result.total_projects == 0
    assert result.projects_with_status == 0
    assert result.projects_without_status == 0
    assert result.projects_with_risk == 0
    assert result.projects_without_risk == 0
    assert result.projects_with_status_and_risk == 0
    assert result.projects_without_any_evidence == 0


def test_scenario_a_project_with_status_and_risk():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework(
        {
            (PROJECT_AURORA.name, "status"): [_status_evidence(1)],
            (PROJECT_AURORA.name, "risk"): [_risk_evidence(2)],
        }
    )
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.total_projects == 1
    assert result.projects_with_status == 1
    assert result.projects_with_risk == 1
    assert result.projects_with_status_and_risk == 1
    assert result.projects_without_any_evidence == 0
    assert len(result.evidence) == 2
    assert {item.source_id for item in result.evidence} == {1, 2}


def test_scenario_b_project_only_with_status():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({(PROJECT_AURORA.name, "status"): [_status_evidence(1)]})
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.projects_with_status == 1
    assert result.projects_with_risk == 0
    assert result.projects_with_status_and_risk == 0
    assert result.projects_without_any_evidence == 0
    assert len(result.evidence) == 1
    assert result.evidence[0].metadata["kind"] == "status"


def test_scenario_c_project_only_with_risk():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({(PROJECT_AURORA.name, "risk"): [_risk_evidence(1)]})
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.projects_with_status == 0
    assert result.projects_with_risk == 1
    assert result.projects_with_status_and_risk == 0
    assert result.projects_without_any_evidence == 0
    assert len(result.evidence) == 1
    assert result.evidence[0].metadata["kind"] == "risk"


def test_scenario_d_project_without_any_evidence():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({})
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.total_projects == 1
    assert result.projects_with_status == 0
    assert result.projects_with_risk == 0
    assert result.projects_with_status_and_risk == 0
    assert result.projects_without_any_evidence == 1
    assert result.evidence == []


def test_selects_only_evidence_zero_of_each_kind_never_history():
    older = _status_evidence(1, NOW - timedelta(days=10))
    newest = _status_evidence(2, NOW)
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    # AnalysisRepository.list_analyses() ordering (created_at DESC) already
    # guarantees the most recent arrives first -- the Assembler trusts it.
    framework = FakeFramework({(PROJECT_AURORA.name, "status"): [newest, older]})
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert len(result.evidence) == 1
    assert result.evidence[0].source_id == 2


def test_enriches_metadata_with_project_without_altering_evidence_contract():
    snapshot = _status_evidence(5)
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({(PROJECT_AURORA.name, "status"): [snapshot]})
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    enriched = result.evidence[0]
    assert enriched.metadata["project_id"] == PROJECT_AURORA.id
    assert enriched.metadata["project_name"] == PROJECT_AURORA.name
    # kind/created_at survive from the original Evidence.metadata, untouched
    # -- already populated by AIContextEngine.gather(), never invented here.
    assert enriched.metadata["kind"] == "status"
    assert enriched.metadata["created_at"] == snapshot.metadata["created_at"]
    assert enriched.source_id == snapshot.source_id
    assert enriched.content == snapshot.content


def test_calls_gather_context_exactly_twice_per_project_status_and_risk():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA, PROJECT_BOREAL]})
    framework = FakeFramework(
        {
            (PROJECT_AURORA.name, "status"): [_status_evidence(1)],
            (PROJECT_BOREAL.name, "risk"): [_risk_evidence(2)],
        }
    )
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    assembler.assemble(organization_id=1)

    assert len(framework.gather_context_calls) == 4
    kinds_called = {kind for _org, _name, kind in framework.gather_context_calls}
    assert kinds_called == {"status", "risk"}
    for project in (PROJECT_AURORA, PROJECT_BOREAL):
        assert (1, project.name, "status") in framework.gather_context_calls
        assert (1, project.name, "risk") in framework.gather_context_calls


def test_never_calls_list_projects_with_a_program_scope():
    domain_service = FakeDomainService(projects_by_organization={1: []})
    framework = FakeFramework({})
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    assembler.assemble(organization_id=1)

    assert domain_service.list_projects_calls == [(1, None)]


def test_coverage_invariants_hold_across_a_mixed_organization():
    domain_service = FakeDomainService(
        projects_by_organization={1: [PROJECT_AURORA, PROJECT_BOREAL, PROJECT_CASTOR]}
    )
    framework = FakeFramework(
        {
            (PROJECT_AURORA.name, "status"): [_status_evidence(1)],
            (PROJECT_AURORA.name, "risk"): [_risk_evidence(2)],
            (PROJECT_BOREAL.name, "status"): [_status_evidence(3)],
            # Boreal has no risk.
            # Castor contributes nothing.
        }
    )
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.total_projects == 3
    assert result.projects_with_status == 2
    assert result.projects_without_status == 1
    assert result.projects_with_risk == 1
    assert result.projects_without_risk == 2
    assert result.projects_with_status_and_risk == 1
    assert result.projects_without_any_evidence == 1
    # Invariants (AR-14 §4/Technical Design §6).
    assert result.projects_with_status + result.projects_without_status == result.total_projects
    assert result.projects_with_risk + result.projects_without_risk == result.total_projects
    assert result.projects_with_status_and_risk <= min(result.projects_with_status, result.projects_with_risk)
    assert result.projects_without_any_evidence == (
        result.total_projects
        - result.projects_with_status
        - result.projects_with_risk
        + result.projects_with_status_and_risk
    )
