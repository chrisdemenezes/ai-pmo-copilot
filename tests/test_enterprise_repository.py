"""Cross-tenant segregation and deterministic project resolution (Épico 1).

Founder-mandated scenario: Organização A/B, Usuário A/B, Projeto A/B -- the
schema and repositories must refuse invalid cross-organization links even
before the RBAC engine exists (Release 0.1 opening directive, Seção 6).
"""
import pytest

from src.database.enterprise_repository import CrossTenantViolationError
from src.database.models import Project, UserProjectMembership
from src.database.project_identity import FALLBACK_PROJECT_NAME
from src.database.repository import AnalysisRecord, AnalysisRepository
from tests.db import temp_database_url


@pytest.fixture()
def repo():
    with temp_database_url("enterprise_repo") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def two_orgs(repo):
    org_a = repo.enterprise.create_organization("Organização A")
    org_b = repo.enterprise.create_organization("Organização B")
    user_a = repo.enterprise.create_user(org_a, "a@example.com", "Usuário A")
    user_b = repo.enterprise.create_user(org_b, "b@example.com", "Usuário B")
    project_a = repo.enterprise.create_project(org_a, "Projeto A")
    project_b = repo.enterprise.create_project(org_b, "Projeto B")
    return {
        "org_a": org_a,
        "org_b": org_b,
        "user_a": user_a,
        "user_b": user_b,
        "project_a": project_a,
        "project_b": project_b,
    }


class TestCrossTenantSegregation:
    def test_same_org_membership_is_allowed(self, repo, two_orgs):
        repo.enterprise.add_project_member(two_orgs["user_a"], two_orgs["project_a"])
        with repo.SessionLocal() as session:
            membership = session.get(
                UserProjectMembership, (two_orgs["user_a"], two_orgs["project_a"])
            )
            assert membership is not None
            assert membership.role_in_project == "member"

    def test_cross_org_membership_is_refused(self, repo, two_orgs):
        with pytest.raises(CrossTenantViolationError):
            repo.enterprise.add_project_member(two_orgs["user_a"], two_orgs["project_b"])
        with pytest.raises(CrossTenantViolationError):
            repo.enterprise.add_project_member(two_orgs["user_b"], two_orgs["project_a"])
        with repo.SessionLocal() as session:
            assert session.query(UserProjectMembership).count() == 0

    def test_project_listing_is_scoped_by_organization(self, repo, two_orgs):
        names_a = {p.name for p in repo.enterprise.list_projects(two_orgs["org_a"])}
        names_b = {p.name for p in repo.enterprise.list_projects(two_orgs["org_b"])}
        assert names_a == {"Projeto A"}
        assert names_b == {"Projeto B"}

    def test_membership_requires_existing_entities(self, repo, two_orgs):
        with pytest.raises(ValueError):
            repo.enterprise.add_project_member(999999, two_orgs["project_a"])
        with pytest.raises(ValueError):
            repo.enterprise.add_project_member(two_orgs["user_a"], 999999)

    def test_user_and_project_require_existing_organization(self, repo):
        with pytest.raises(ValueError):
            repo.enterprise.create_user(999999, "x@example.com", "X")
        with pytest.raises(ValueError):
            repo.enterprise.create_project(999999, "X")


class TestDeterministicProjectResolution:
    @pytest.fixture()
    def org(self, repo):
        return repo.enterprise.create_organization("Organização Única")

    def test_save_analysis_links_a_real_project(self, repo, org):
        record_id = repo.save_analysis("project_status", {}, org, "Projeto Novo")
        with repo.SessionLocal() as session:
            record = session.get(AnalysisRecord, record_id)
            assert record.project_id is not None
            assert record.organization_id == org
            project = session.get(Project, record.project_id)
            assert project.name == "Projeto Novo"
            assert project.legacy_project_name == "Projeto Novo"

    def test_whitespace_variants_share_one_project(self, repo, org):
        id1 = repo.save_analysis("project_status", {}, org, "Projeto Alfa")
        id2 = repo.save_analysis("risk_review", {}, org, "  Projeto Alfa  ")
        with repo.SessionLocal() as session:
            r1 = session.get(AnalysisRecord, id1)
            r2 = session.get(AnalysisRecord, id2)
            assert r1.project_id == r2.project_id
            # Original free text preserved untouched per record.
            assert r2.project_name == "  Projeto Alfa  "

    def test_capitalization_variants_stay_distinct(self, repo, org):
        id1 = repo.save_analysis("project_status", {}, org, "Projeto Alfa")
        id2 = repo.save_analysis("project_status", {}, org, "projeto alfa")
        with repo.SessionLocal() as session:
            r1 = session.get(AnalysisRecord, id1)
            r2 = session.get(AnalysisRecord, id2)
            assert r1.project_id != r2.project_id

    def test_null_and_empty_use_the_fallback_project(self, repo, org):
        id1 = repo.save_analysis("meeting_intelligence", {}, org, None)
        id2 = repo.save_analysis("meeting_intelligence", {}, org, "")
        id3 = repo.save_analysis("meeting_intelligence", {}, org, "   ")
        with repo.SessionLocal() as session:
            pids = {session.get(AnalysisRecord, i).project_id for i in (id1, id2, id3)}
            assert len(pids) == 1
            project = session.get(Project, pids.pop())
            assert project.name == FALLBACK_PROJECT_NAME
            assert project.legacy_project_name is None

    def test_projects_created_at_save_belong_to_the_given_organization(self, repo, org):
        repo.save_analysis("project_status", {}, org, "Projeto Alfa")
        with repo.SessionLocal() as session:
            project = session.query(Project).filter(Project.name == "Projeto Alfa").one()
            assert project.organization_id == org

    def test_two_organizations_with_the_same_project_name_get_distinct_projects(self, repo):
        # Security Hardening Gate (C-2): get_or_create_project_for_name used
        # to always resolve to one hardcoded "default organization"
        # regardless of who called it -- confirms that regression can't
        # come back: each organization gets its own Project namespace.
        org_a = repo.enterprise.create_organization("Organização A")
        org_b = repo.enterprise.create_organization("Organização B")
        id_a = repo.save_analysis("project_status", {}, org_a, "Projeto Alfa")
        id_b = repo.save_analysis("project_status", {}, org_b, "Projeto Alfa")
        with repo.SessionLocal() as session:
            record_a = session.get(AnalysisRecord, id_a)
            record_b = session.get(AnalysisRecord, id_b)
            assert record_a.project_id != record_b.project_id
            assert record_a.organization_id == org_a
            assert record_b.organization_id == org_b
            project_a = session.get(Project, record_a.project_id)
            project_b = session.get(Project, record_b.project_id)
            assert project_a.organization_id == org_a
            assert project_b.organization_id == org_b
