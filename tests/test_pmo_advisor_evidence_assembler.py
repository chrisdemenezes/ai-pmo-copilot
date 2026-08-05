"""`PMOEvidenceAssembler` unit tests (Wave 5, second Classe B Advisor), per
`TECHNICAL-DESIGN-PMO-ADVISOR.md` §3.

Uses fakes for `DomainService`/`AdvisorFramework` so these tests exercise
exclusively the Assembler's own composition logic -- staleness computation,
volume cap, coverage counting -- never a real database. Framework-level
integration (real Postgres, real `AIContextEngine.gather()` ordering) is
covered by `tests/test_pmo_advisor.py`.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.agents.pmo_advisor.evidence_assembler import (
    PMO_MAX_RECORDS_PER_PROJECT,
    PMO_STALENESS_THRESHOLD_DAYS,
    PMOEvidenceAssembler,
)
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
    def __init__(self, projects_by_organization: dict[int, list] | None = None):
        self.projects_by_organization = projects_by_organization or {}
        self.list_projects_calls: list = []

    def list_projects(self, organization_id, program_id=None):
        self.list_projects_calls.append((organization_id, program_id))
        assert program_id is None, "PMO Advisor scope is organizational -- never a Program traversal"
        return self.projects_by_organization.get(organization_id, [])


class FakeFramework:
    def __init__(self, evidence_by_project_name: dict[str, list[Evidence]]):
        self._evidence_by_project_name = evidence_by_project_name
        self.gather_context_calls: list[tuple] = []

    def gather_context(self, organization_id, project_name, kind):
        self.gather_context_calls.append((organization_id, project_name, kind))
        return self._evidence_by_project_name.get(project_name, [])


PROJECT_AURORA = SimpleNamespace(id=30, name="Aurora")
PROJECT_BOREAL = SimpleNamespace(id=31, name="Boreal")
PROJECT_CASTOR = SimpleNamespace(id=32, name="Castor")

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _frozen_reference_time():
    # Every test in this file builds evidence timestamps relative to NOW --
    # freeze the Assembler's own reference_time to the same instant so
    # staleness_days comes out exactly as each test expects, regardless of
    # the real wall-clock date the suite happens to run on.
    with patch("src.agents.pmo_advisor.evidence_assembler.datetime") as mock_dt:
        mock_dt.now.return_value = NOW
        yield


def test_organization_without_projects_yields_zero_coverage():
    domain_service = FakeDomainService(projects_by_organization={1: []})
    framework = FakeFramework({})
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.evidence == []
    assert result.total_projects == 0
    assert result.projects_with_status == 0
    assert result.projects_without_status == 0
    assert result.projects_stale == 0
    assert result.projects_current == 0


def test_project_without_status_contributes_no_evidence_and_is_not_stale():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({})  # Aurora has no entry -> gather_context returns [].
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.total_projects == 1
    assert result.projects_with_status == 0
    assert result.projects_without_status == 1
    assert result.projects_stale == 0
    assert result.projects_current == 0
    assert result.evidence == []


def test_caps_evidence_at_five_most_recent_records_per_project():
    records = [
        _status_evidence(i, "green", NOW - timedelta(days=i)) for i in range(1, 8)  # 7 records
    ]
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({PROJECT_AURORA.name: records})
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert len(result.evidence) == PMO_MAX_RECORDS_PER_PROJECT == 5
    assert [item.source_id for item in result.evidence] == [1, 2, 3, 4, 5]


def test_fewer_than_five_records_applies_no_cut():
    records = [_status_evidence(1, "green", NOW), _status_evidence(2, "yellow", NOW - timedelta(days=1))]
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({PROJECT_AURORA.name: records})
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert len(result.evidence) == 2


def test_staleness_is_computed_once_per_project_and_replicated_across_its_evidence_items():
    records = [
        _status_evidence(1, "green", NOW - timedelta(days=20)),
        _status_evidence(2, "yellow", NOW - timedelta(days=25)),
    ]
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({PROJECT_AURORA.name: records})
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    # Both items belong to the same Project -- same staleness_days/is_stale,
    # computed once from the MOST RECENT record (20 days), never per-item.
    assert {item.metadata["staleness_days"] for item in result.evidence} == {20}
    assert {item.metadata["is_stale"] for item in result.evidence} == {True}
    assert result.projects_stale == 1
    assert result.projects_current == 0


def test_a_project_without_status_never_counts_as_stale():
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA, PROJECT_BOREAL]})
    framework = FakeFramework(
        {PROJECT_AURORA.name: [_status_evidence(1, "green", NOW - timedelta(days=30))]}
        # Boreal contributes nothing.
    )
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.projects_with_status == 1
    assert result.projects_without_status == 1
    assert result.projects_stale == 1  # Aurora only
    assert result.projects_current == 0
    # Coverage invariants hold.
    assert result.projects_with_status + result.projects_without_status == result.total_projects
    assert result.projects_stale + result.projects_current == result.projects_with_status


def test_enriches_metadata_with_project_and_staleness_without_altering_evidence_contract():
    snapshot = _status_evidence(5, "green", NOW - timedelta(days=1))
    domain_service = FakeDomainService(projects_by_organization={1: [PROJECT_AURORA]})
    framework = FakeFramework({PROJECT_AURORA.name: [snapshot]})
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    enriched = result.evidence[0]
    assert enriched.metadata["project_id"] == PROJECT_AURORA.id
    assert enriched.metadata["project_name"] == PROJECT_AURORA.name
    assert enriched.metadata["staleness_days"] == 1
    assert enriched.metadata["is_stale"] is False
    # created_at survives from the original Evidence.metadata, untouched.
    assert enriched.metadata["created_at"] == snapshot.metadata["created_at"]
    # source_id/source_type/source_label/content are the contract's own
    # top-level fields, preserved -- no new fields invented on Evidence.
    assert enriched.source_id == snapshot.source_id
    assert enriched.content == snapshot.content


def test_calls_gather_context_exactly_once_per_project_with_kind_status():
    domain_service = FakeDomainService(
        projects_by_organization={1: [PROJECT_AURORA, PROJECT_BOREAL, PROJECT_CASTOR]}
    )
    framework = FakeFramework(
        {
            PROJECT_AURORA.name: [_status_evidence(1, "green", NOW)],
            PROJECT_BOREAL.name: [_status_evidence(2, "yellow", NOW)],
            PROJECT_CASTOR.name: [_status_evidence(3, "red", NOW)],
        }
    )
    assembler = PMOEvidenceAssembler(domain_service, framework)

    assembler.assemble(organization_id=1)

    assert len(framework.gather_context_calls) == 3
    assert all(kind == "status" for _org, _name, kind in framework.gather_context_calls)
    called_names = {name for _org, name, _kind in framework.gather_context_calls}
    assert called_names == {PROJECT_AURORA.name, PROJECT_BOREAL.name, PROJECT_CASTOR.name}


def test_never_calls_list_projects_with_a_program_scope():
    domain_service = FakeDomainService(projects_by_organization={1: []})
    framework = FakeFramework({})
    assembler = PMOEvidenceAssembler(domain_service, framework)

    assembler.assemble(organization_id=1)

    assert domain_service.list_projects_calls == [(1, None)]


def test_coverage_invariants_hold_across_a_mixed_organization():
    aurora = PROJECT_AURORA  # current
    boreal = PROJECT_BOREAL  # stale
    castor = PROJECT_CASTOR  # no status
    domain_service = FakeDomainService(projects_by_organization={1: [aurora, boreal, castor]})
    framework = FakeFramework(
        {
            aurora.name: [_status_evidence(1, "green", NOW - timedelta(days=13))],
            boreal.name: [_status_evidence(2, "red", NOW - timedelta(days=15))],
        }
    )
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(organization_id=1)

    assert result.total_projects == 3
    assert result.projects_with_status == 2
    assert result.projects_without_status == 1
    assert result.projects_stale == 1
    assert result.projects_current == 1
    assert result.projects_with_status + result.projects_without_status == result.total_projects
    assert result.projects_stale + result.projects_current == result.projects_with_status


def test_staleness_threshold_constant_is_fourteen_days():
    assert PMO_STALENESS_THRESHOLD_DAYS == 14
