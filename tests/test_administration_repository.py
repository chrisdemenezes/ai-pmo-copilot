"""AdministrationRepository (Wave 2, Sprint 4) -- Organization/Users/Roles
reads, role assignment, and the audit log that doubles as "Logs"."""
import os
import subprocess
import sys

import pytest

from src.database.repository import AnalysisRepository
from tests.db import temp_database_url


@pytest.fixture()
def repo():
    with temp_database_url("administration_repo") as database_url:
        yield AnalysisRepository(database_url=database_url)


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result


@pytest.fixture()
def migrated_repo():
    """Roles/permissions/role_permissions only exist with real data after
    `alembic upgrade head` -- `AnalysisRepository`'s own `create_all()` only
    provisions empty tables (same reason `test_domain_repository.py`'s
    plain `repo` fixture can't be used for RBAC-dependent assertions)."""
    with temp_database_url("administration_migrated") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")
        yield AnalysisRepository(database_url=database_url)


class TestOrganization:
    def test_get_organization(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        org = repo.administration.get_organization(org_id)
        assert org.name == "Org A"

    def test_get_unknown_organization_returns_none(self, repo):
        assert repo.administration.get_organization(999999) is None

    def test_update_organization_name_keeps_slug_stable(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        original_slug = repo.administration.get_organization(org_id).slug

        updated = repo.administration.update_organization_name(org_id, "Org A Renamed")

        assert updated.name == "Org A Renamed"
        assert updated.slug == original_slug  # EO-015: slug never changes after creation

    def test_update_unknown_organization_returns_none(self, repo):
        assert repo.administration.update_organization_name(999999, "X") is None


class TestUsers:
    def test_list_users_is_scoped_by_organization(self, repo):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        repo.enterprise.create_user(org_a, "a@example.com", "User A")
        repo.enterprise.create_user(org_b, "b@example.com", "User B")

        users_a = repo.administration.list_users_by_organization(org_a)
        assert [u.email for u in users_a] == ["a@example.com"]


class TestRoles:
    def test_list_roles_returns_the_epico_1_seed(self, migrated_repo):
        roles = {r.name for r in migrated_repo.administration.list_roles()}
        assert roles == {"organization_admin", "pmo", "project_manager", "viewer"}

    def test_list_permissions_for_role_matches_migration_0006(self, migrated_repo):
        roles = {r.name: r.id for r in migrated_repo.administration.list_roles()}
        viewer_permissions = {
            p.name
            for p in migrated_repo.administration.list_permissions_for_role(roles["viewer"])
        }
        assert viewer_permissions == {"portfolio.read", "program.read", "project_delivery.read"}

    def test_assign_role_is_idempotent(self, migrated_repo):
        org_id = migrated_repo.enterprise.create_organization("Org A")
        user_id = migrated_repo.enterprise.create_user(org_id, "user@example.com", "User")

        migrated_repo.administration.assign_role(user_id, org_id, "viewer")
        migrated_repo.administration.assign_role(user_id, org_id, "viewer")  # no-op

        with migrated_repo.SessionLocal() as session:
            from src.database.models import UserRole

            count = session.query(UserRole).filter(UserRole.user_id == user_id).count()
        assert count == 1

    def test_assign_role_refuses_cross_tenant_user(self, migrated_repo):
        org_a = migrated_repo.enterprise.create_organization("Org A")
        org_b = migrated_repo.enterprise.create_organization("Org B")
        user_b = migrated_repo.enterprise.create_user(org_b, "b@example.com", "User B")

        result = migrated_repo.administration.assign_role(user_b, org_a, "viewer")

        assert result is None

    def test_assign_unknown_role_raises(self, migrated_repo):
        org_id = migrated_repo.enterprise.create_organization("Org A")
        user_id = migrated_repo.enterprise.create_user(org_id, "user@example.com", "User")

        with pytest.raises(ValueError):
            migrated_repo.administration.assign_role(user_id, org_id, "does_not_exist")


class TestAuditLog:
    def test_record_and_list_audit_log(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "user@example.com", "User")

        repo.administration.record_audit(
            org_id, user_id, "portfolio.created", "portfolio", 1, {"code": "PF-001"}
        )

        entries = repo.administration.list_audit_log(org_id)
        assert len(entries) == 1
        assert entries[0].action == "portfolio.created"
        assert entries[0].entity_type == "portfolio"
        assert entries[0].entity_id == 1
        assert entries[0].details == {"code": "PF-001"}

    def test_audit_log_is_scoped_by_organization(self, repo):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = repo.enterprise.create_user(org_a, "a@example.com", "A")
        user_b = repo.enterprise.create_user(org_b, "b@example.com", "B")

        repo.administration.record_audit(org_a, user_a, "portfolio.created", "portfolio", 1)
        repo.administration.record_audit(org_b, user_b, "portfolio.created", "portfolio", 2)

        entries_a = repo.administration.list_audit_log(org_a)
        assert len(entries_a) == 1
        assert entries_a[0].organization_id == org_a

    def test_audit_log_orders_newest_first(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "user@example.com", "User")

        first_id = repo.administration.record_audit(org_id, user_id, "portfolio.created", "portfolio", 1)
        second_id = repo.administration.record_audit(org_id, user_id, "program.created", "program", 2)

        entries = repo.administration.list_audit_log(org_id)
        assert [e.id for e in entries] == [second_id, first_id]
