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

    def test_list_permissions_for_role_matches_migration_0006_and_0010(self, migrated_repo):
        roles = {r.name: r.id for r in migrated_repo.administration.list_roles()}
        viewer_permissions = {
            p.name
            for p in migrated_repo.administration.list_permissions_for_role(roles["viewer"])
        }
        assert viewer_permissions == {
            "portfolio.read",
            "program.read",
            "project_delivery.read",
            "intelligence.read",
        }

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


class TestUserManagement:
    """User Management Capability -- create/edit/activate-deactivate/
    assign-remove role, with the governance guards the Founder mandated
    (self-deactivation, last active admin, cross-tenant, email conflict)."""

    def test_create_user_and_assigns_role_transactionally(self, migrated_repo):
        org_id = migrated_repo.enterprise.create_organization("Org A")

        user = migrated_repo.administration.create_user(
            org_id, "New@Example.com", "New User", "hashed-password", "viewer"
        )

        assert user.email == "new@example.com"  # normalized
        assert user.is_active is True
        with migrated_repo.SessionLocal() as session:
            from src.database.models import Role, UserRole

            role = session.query(Role).filter(Role.name == "viewer").one()
            assert (
                session.query(UserRole)
                .filter(UserRole.user_id == user.id, UserRole.role_id == role.id)
                .one_or_none()
                is not None
            )

    def test_create_user_with_unknown_role_leaves_no_orphan_user(self, migrated_repo):
        from src.database.models import User

        org_id = migrated_repo.enterprise.create_organization("Org A")

        with pytest.raises(ValueError):
            migrated_repo.administration.create_user(
                org_id, "orphan@example.com", "Orphan", "hash", "does_not_exist"
            )

        with migrated_repo.SessionLocal() as session:
            assert (
                session.query(User).filter(User.email == "orphan@example.com").one_or_none()
                is None
            )

    def test_create_user_rejects_case_insensitive_duplicate_email_in_same_org(self, migrated_repo):
        from src.database.enterprise_repository import EmailConflictError

        org_id = migrated_repo.enterprise.create_organization("Org A")
        migrated_repo.administration.create_user(
            org_id, "dup@example.com", "First", "hash", "viewer"
        )

        with pytest.raises(EmailConflictError):
            migrated_repo.administration.create_user(
                org_id, "DUP@Example.com", "Second", "hash", "viewer"
            )

    def test_create_user_allows_same_email_in_different_organization(self, migrated_repo):
        org_a = migrated_repo.enterprise.create_organization("Org A")
        org_b = migrated_repo.enterprise.create_organization("Org B")
        migrated_repo.administration.create_user(org_a, "shared@example.com", "A", "hash", "viewer")

        user_b = migrated_repo.administration.create_user(
            org_b, "shared@example.com", "B", "hash", "viewer"
        )

        assert user_b.organization_id == org_b

    def test_get_user_is_scoped_by_organization(self, migrated_repo):
        org_a = migrated_repo.enterprise.create_organization("Org A")
        org_b = migrated_repo.enterprise.create_organization("Org B")
        user = migrated_repo.administration.create_user(
            org_a, "user@example.com", "User", "hash", "viewer"
        )

        assert migrated_repo.administration.get_user(user.id, org_a) is not None
        assert migrated_repo.administration.get_user(user.id, org_b) is None

    def test_update_user_changes_email_and_display_name(self, migrated_repo):
        org_id = migrated_repo.enterprise.create_organization("Org A")
        user = migrated_repo.administration.create_user(
            org_id, "old@example.com", "Old Name", "hash", "viewer"
        )

        result = migrated_repo.administration.update_user(
            user.id, org_id, email="New@Example.com", display_name="New Name"
        )

        updated_user, before, after = result
        assert updated_user.email == "new@example.com"
        assert updated_user.display_name == "New Name"
        assert before == {"email": "old@example.com", "display_name": "Old Name"}
        assert after == {"email": "new@example.com", "display_name": "New Name"}

    def test_update_user_rejects_case_insensitive_duplicate_email(self, migrated_repo):
        from src.database.enterprise_repository import EmailConflictError

        org_id = migrated_repo.enterprise.create_organization("Org A")
        migrated_repo.administration.create_user(org_id, "taken@example.com", "A", "hash", "viewer")
        user_b = migrated_repo.administration.create_user(
            org_id, "b@example.com", "B", "hash", "viewer"
        )

        with pytest.raises(EmailConflictError):
            migrated_repo.administration.update_user(
                user_b.id, org_id, email="Taken@Example.com"
            )

    def test_update_unknown_user_returns_none(self, migrated_repo):
        org_id = migrated_repo.enterprise.create_organization("Org A")
        assert migrated_repo.administration.update_user(999999, org_id, display_name="X") is None

    def test_set_user_active_toggles_status(self, migrated_repo):
        org_id = migrated_repo.enterprise.create_organization("Org A")
        actor = migrated_repo.administration.create_user(
            org_id, "actor@example.com", "Actor", "hash", "organization_admin"
        )
        target = migrated_repo.administration.create_user(
            org_id, "target@example.com", "Target", "hash", "viewer"
        )

        deactivated = migrated_repo.administration.set_user_active(
            target.id, org_id, False, actor_user_id=actor.id
        )
        assert deactivated.is_active is False

        reactivated = migrated_repo.administration.set_user_active(
            target.id, org_id, True, actor_user_id=actor.id
        )
        assert reactivated.is_active is True

    def test_admin_cannot_deactivate_self(self, migrated_repo):
        from src.database.enterprise_repository import SelfDeactivationError

        org_id = migrated_repo.enterprise.create_organization("Org A")
        admin = migrated_repo.administration.create_user(
            org_id, "admin@example.com", "Admin", "hash", "organization_admin"
        )
        # A second admin so "last admin" would not also fire -- isolates
        # the self-deactivation guard specifically.
        migrated_repo.administration.create_user(
            org_id, "admin2@example.com", "Admin 2", "hash", "organization_admin"
        )

        with pytest.raises(SelfDeactivationError):
            migrated_repo.administration.set_user_active(
                admin.id, org_id, False, actor_user_id=admin.id
            )

    def test_cannot_deactivate_the_last_active_admin(self, migrated_repo):
        from src.database.enterprise_repository import LastActiveAdminError

        org_id = migrated_repo.enterprise.create_organization("Org A")
        sole_admin = migrated_repo.administration.create_user(
            org_id, "admin@example.com", "Admin", "hash", "organization_admin"
        )
        other_actor = migrated_repo.administration.create_user(
            org_id, "other@example.com", "Other", "hash", "viewer"
        )

        with pytest.raises(LastActiveAdminError):
            migrated_repo.administration.set_user_active(
                sole_admin.id, org_id, False, actor_user_id=other_actor.id
            )

    def test_deactivating_one_of_two_admins_is_allowed(self, migrated_repo):
        org_id = migrated_repo.enterprise.create_organization("Org A")
        admin_a = migrated_repo.administration.create_user(
            org_id, "admin-a@example.com", "Admin A", "hash", "organization_admin"
        )
        admin_b = migrated_repo.administration.create_user(
            org_id, "admin-b@example.com", "Admin B", "hash", "organization_admin"
        )

        result = migrated_repo.administration.set_user_active(
            admin_b.id, org_id, False, actor_user_id=admin_a.id
        )
        assert result.is_active is False

    def test_last_admin_guard_is_scoped_by_organization(self, migrated_repo):
        """The sole admin of Org A being deactivated must never be blocked
        by an admin existing in Org B -- the count is organization-scoped."""
        org_a = migrated_repo.enterprise.create_organization("Org A")
        org_b = migrated_repo.enterprise.create_organization("Org B")
        migrated_repo.administration.create_user(
            org_b, "admin-b@example.com", "Admin B", "hash", "organization_admin"
        )
        sole_admin_a = migrated_repo.administration.create_user(
            org_a, "admin-a@example.com", "Admin A", "hash", "organization_admin"
        )
        other_actor = migrated_repo.administration.create_user(
            org_a, "other@example.com", "Other", "hash", "viewer"
        )

        from src.database.enterprise_repository import LastActiveAdminError

        with pytest.raises(LastActiveAdminError):
            migrated_repo.administration.set_user_active(
                sole_admin_a.id, org_a, False, actor_user_id=other_actor.id
            )

    def test_remove_role_deletes_the_assignment(self, migrated_repo):
        from src.database.models import Role, UserRole

        org_id = migrated_repo.enterprise.create_organization("Org A")
        admin = migrated_repo.administration.create_user(
            org_id, "admin@example.com", "Admin", "hash", "organization_admin"
        )
        user = migrated_repo.administration.create_user(
            org_id, "user@example.com", "User", "hash", "viewer"
        )

        migrated_repo.administration.remove_role(user.id, org_id, "viewer", actor_user_id=admin.id)

        with migrated_repo.SessionLocal() as session:
            role = session.query(Role).filter(Role.name == "viewer").one()
            assert (
                session.query(UserRole)
                .filter(UserRole.user_id == user.id, UserRole.role_id == role.id)
                .one_or_none()
                is None
            )

    def test_cannot_remove_organization_admin_role_from_the_last_active_admin(self, migrated_repo):
        from src.database.enterprise_repository import LastActiveAdminError

        org_id = migrated_repo.enterprise.create_organization("Org A")
        sole_admin = migrated_repo.administration.create_user(
            org_id, "admin@example.com", "Admin", "hash", "organization_admin"
        )
        other_actor = migrated_repo.administration.create_user(
            org_id, "other@example.com", "Other", "hash", "viewer"
        )

        with pytest.raises(LastActiveAdminError):
            migrated_repo.administration.remove_role(
                sole_admin.id, org_id, "organization_admin", actor_user_id=other_actor.id
            )

    def test_remove_role_unknown_role_raises(self, migrated_repo):
        org_id = migrated_repo.enterprise.create_organization("Org A")
        admin = migrated_repo.administration.create_user(
            org_id, "admin@example.com", "Admin", "hash", "organization_admin"
        )
        user = migrated_repo.administration.create_user(
            org_id, "user@example.com", "User", "hash", "viewer"
        )

        with pytest.raises(ValueError):
            migrated_repo.administration.remove_role(
                user.id, org_id, "does_not_exist", actor_user_id=admin.id
            )


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


class TestApiKeys:
    """D-051 -- a foundational Enterprise Administration credential, not an
    Integration Hub artifact (DOMAIN-BLUEPRINT-API-KEYS.md)."""

    def test_create_and_get_api_key(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "admin@example.com", "Admin")

        api_key = repo.administration.create_api_key(
            org_id, user_id, "CI pipeline", "sk_live_AbCdEfGh", "hashed-value"
        )

        fetched = repo.administration.get_api_key(api_key.id, org_id)
        assert fetched.name == "CI pipeline"
        assert fetched.key_prefix == "sk_live_AbCdEfGh"
        assert fetched.hashed_secret == "hashed-value"
        assert fetched.revoked_at is None
        assert fetched.last_used_at is None

    def test_get_api_key_from_another_organization_returns_none(self, repo):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = repo.enterprise.create_user(org_a, "a@example.com", "A")

        api_key = repo.administration.create_api_key(
            org_a, user_a, "Key A", "sk_live_AAAAAAAA", "hash-a"
        )

        assert repo.administration.get_api_key(api_key.id, org_b) is None

    def test_list_api_keys_scoped_by_organization_newest_first(self, repo):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = repo.enterprise.create_user(org_a, "a@example.com", "A")
        user_b = repo.enterprise.create_user(org_b, "b@example.com", "B")

        first = repo.administration.create_api_key(org_a, user_a, "First", "sk_live_111", "h1")
        second = repo.administration.create_api_key(org_a, user_a, "Second", "sk_live_222", "h2")
        repo.administration.create_api_key(org_b, user_b, "Other org", "sk_live_333", "h3")

        keys = repo.administration.list_api_keys(org_a)
        assert [k.id for k in keys] == [second.id, first.id]

    def test_revoke_api_key_sets_revoked_at_and_is_idempotent(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "admin@example.com", "Admin")
        api_key = repo.administration.create_api_key(
            org_id, user_id, "Key", "sk_live_AAAAAAAA", "hash"
        )

        revoked = repo.administration.revoke_api_key(api_key.id, org_id)
        assert revoked.revoked_at is not None

        # Revoking an already-revoked key returns None, never a second event.
        assert repo.administration.revoke_api_key(api_key.id, org_id) is None

    def test_revoke_api_key_from_another_organization_returns_none(self, repo):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = repo.enterprise.create_user(org_a, "a@example.com", "A")
        api_key = repo.administration.create_api_key(
            org_a, user_a, "Key A", "sk_live_AAAAAAAA", "hash-a"
        )

        assert repo.administration.revoke_api_key(api_key.id, org_b) is None
        assert repo.administration.get_api_key(api_key.id, org_a).revoked_at is None

    def test_list_active_api_keys_by_prefix_excludes_revoked_and_other_prefixes(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "admin@example.com", "Admin")
        active = repo.administration.create_api_key(
            org_id, user_id, "Active", "sk_live_AAAAAAAA", "hash-active"
        )
        revoked = repo.administration.create_api_key(
            org_id, user_id, "Revoked", "sk_live_AAAAAAAA", "hash-revoked"
        )
        repo.administration.revoke_api_key(revoked.id, org_id)
        repo.administration.create_api_key(org_id, user_id, "Other", "sk_live_BBBBBBBB", "hash-b")

        candidates = repo.administration.list_active_api_keys_by_prefix("sk_live_AAAAAAAA")

        assert [c.id for c in candidates] == [active.id]

    def test_touch_api_key_last_used_sets_timestamp(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "admin@example.com", "Admin")
        api_key = repo.administration.create_api_key(
            org_id, user_id, "Key", "sk_live_AAAAAAAA", "hash"
        )
        assert repo.administration.get_api_key(api_key.id, org_id).last_used_at is None

        repo.administration.touch_api_key_last_used(api_key.id)

        assert repo.administration.get_api_key(api_key.id, org_id).last_used_at is not None
