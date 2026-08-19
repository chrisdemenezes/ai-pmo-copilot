"""Dual-key project resolution (TD-008 Phase 3b, Etapa 1). Covers the five
scenarios the Founder mandated: nonexistent name, duplicate name,
nonexistent id, id/name divergence, and cross-organization access."""
import pytest
from sqlalchemy.exc import IntegrityError

from src.database.enterprise_repository import (
    ProjectNotFoundError,
    ProjectReferenceMismatchError,
)
from src.database.repository import AnalysisRepository
from tests.db import temp_database_url


@pytest.fixture()
def repo():
    with temp_database_url("project_resolver") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def org_id(repo):
    return repo.enterprise.create_organization("Org A")


def _resolve(repo, organization_id, project_id=None, project_name=None):
    return repo.enterprise.resolve_project_reference(
        organization_id, project_id=project_id, project_name=project_name
    )


class TestNeitherKey:
    def test_both_none_returns_none(self, repo, org_id):
        assert _resolve(repo, org_id) is None

    def test_blank_name_returns_none(self, repo, org_id):
        assert _resolve(repo, org_id, project_name="   ") is None


class TestByName:
    def test_unique_name_resolves(self, repo, org_id):
        pid = repo.enterprise.create_project(org_id, "Aurora")
        resolved = _resolve(repo, org_id, project_name="Aurora")
        assert resolved is not None and resolved.id == pid

    def test_name_is_whitespace_normalized(self, repo, org_id):
        pid = repo.enterprise.create_project(org_id, "Aurora")
        resolved = _resolve(repo, org_id, project_name="  Aurora ")
        assert resolved.id == pid

    def test_nonexistent_name_raises_not_found(self, repo, org_id):
        with pytest.raises(ProjectNotFoundError):
            _resolve(repo, org_id, project_name="Ghost")

    def test_duplicate_project_name_is_prevented_by_the_schema(self, repo, org_id):
        # Finding (TD-008 Phase 3b, Etapa 1): a UNIQUE constraint
        # `uq_projects_org_name` on (organization_id, name) already makes two
        # Projects with the same name in one organization impossible -- so the
        # "duplicate name" ambiguity the migration guards against cannot
        # occur today. This test documents (and locks in) that invariant; the
        # resolver's AmbiguousProjectNameError branch is retained as fail-safe
        # defensive code should a future migration ever drop the constraint.
        repo.enterprise.create_project(org_id, "Multilift")
        with pytest.raises(IntegrityError):
            repo.enterprise.create_project(org_id, "Multilift")


class TestById:
    def test_existing_id_resolves(self, repo, org_id):
        pid = repo.enterprise.create_project(org_id, "Aurora")
        resolved = _resolve(repo, org_id, project_id=pid)
        assert resolved.id == pid

    def test_nonexistent_id_raises_not_found(self, repo, org_id):
        with pytest.raises(ProjectNotFoundError):
            _resolve(repo, org_id, project_id=999999)

    def test_cross_organization_id_raises_not_found(self, repo, org_id):
        other_org = repo.enterprise.create_organization("Org B")
        other_pid = repo.enterprise.create_project(other_org, "Secret")
        # Org A must never resolve (or even confirm) Org B's project.
        with pytest.raises(ProjectNotFoundError):
            _resolve(repo, org_id, project_id=other_pid)


class TestBothKeys:
    def test_matching_id_and_name_resolve(self, repo, org_id):
        pid = repo.enterprise.create_project(org_id, "Aurora")
        resolved = _resolve(repo, org_id, project_id=pid, project_name="Aurora")
        assert resolved.id == pid

    def test_divergent_id_and_name_raise_mismatch(self, repo, org_id):
        aurora = repo.enterprise.create_project(org_id, "Aurora")
        repo.enterprise.create_project(org_id, "Multilift")
        with pytest.raises(ProjectReferenceMismatchError):
            _resolve(repo, org_id, project_id=aurora, project_name="Multilift")

    def test_id_in_org_but_name_nonexistent_raises_not_found(self, repo, org_id):
        pid = repo.enterprise.create_project(org_id, "Aurora")
        # The name half doesn't resolve -> not found (before any mismatch check).
        with pytest.raises(ProjectNotFoundError):
            _resolve(repo, org_id, project_id=pid, project_name="Ghost")
