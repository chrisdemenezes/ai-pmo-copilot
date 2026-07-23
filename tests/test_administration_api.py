"""Enterprise Administration API (Wave 2, Sprint 4)."""
import os
import subprocess
import sys

import pytest

from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import administration as administration_routes
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.administration_service import AdministrationService
from src.services.authorization.checker import SqlPermissionChecker

from tests.db import temp_database_url


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


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


@pytest.fixture()
def client():
    with temp_database_url("administration_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

        repo = AnalysisRepository(database_url=database_url)
        app.dependency_overrides[administration_routes.build_administration_service] = (
            lambda: AdministrationService(repo)
        )
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo
        app.dependency_overrides.pop(administration_routes.build_administration_service, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


class TestOrganization:
    def test_get_organization(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.get("/api/admin/organization", headers=_headers(org_id, admin_id))

        assert response.status_code == 200
        assert response.json()["name"] == "Org A"

    def test_pmo_can_read_but_not_write_organization(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        pmo_id = _actor(repo, org_id, "pmo")

        read_response = test_client.get(
            "/api/admin/organization", headers=_headers(org_id, pmo_id)
        )
        assert read_response.status_code == 200

        write_response = test_client.patch(
            "/api/admin/organization", headers=_headers(org_id, pmo_id), json={"name": "X"}
        )
        assert write_response.status_code == 403
        assert write_response.json()["detail"] == "missing permission: administration.write"

    def test_viewer_cannot_read_organization(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.get("/api/admin/organization", headers=_headers(org_id, viewer_id))

        assert response.status_code == 403

    def test_get_organization_not_found_returns_404(self, client):
        """context.organization.organization_id comes from a trusted header
        -- exercised here via an id that was never created, same defensive
        branch every other entity's GET-by-id route has. Permissions are a
        global catalog (not org-scoped), so the admin's grant still applies
        even though the header names a nonexistent organization."""
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.get(
            "/api/admin/organization", headers=_headers(999999, admin_id)
        )
        assert response.status_code == 404

    def test_organization_admin_can_rename_and_slug_stays_stable(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        original_slug = repo.administration.get_organization(org_id).slug

        response = test_client.patch(
            "/api/admin/organization",
            headers=_headers(org_id, admin_id),
            json={"name": "Org A Renamed"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Org A Renamed"
        assert response.json()["slug"] == original_slug

    def test_rename_unknown_organization_returns_404(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.patch(
            "/api/admin/organization", headers=_headers(999999, admin_id), json={"name": "X"}
        )
        assert response.status_code == 404


class TestUsers:
    def test_list_users_is_scoped_by_organization(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        admin_a = _actor(repo, org_a)
        repo.enterprise.create_user(org_b, "other@example.com", "Other")

        response = test_client.get("/api/admin/users", headers=_headers(org_a, admin_a))

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()}
        assert "other@example.com" not in emails
        assert "organization_admin@example.com" in emails


class TestRoles:
    def test_list_roles(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.get("/api/admin/roles", headers=_headers(org_id, admin_id))

        assert response.status_code == 200
        assert {r["name"] for r in response.json()} == {
            "organization_admin",
            "pmo",
            "project_manager",
            "viewer",
        }

    def test_list_role_permissions(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        roles = {r.name: r.id for r in repo.administration.list_roles()}

        response = test_client.get(
            f"/api/admin/roles/{roles['viewer']}/permissions", headers=_headers(org_id, admin_id)
        )

        assert response.status_code == 200
        assert {p["name"] for p in response.json()} == {
            "portfolio.read",
            "program.read",
            "project_delivery.read",
        }

    def test_assign_role(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        target_user_id = repo.enterprise.create_user(org_id, "newuser@example.com", "New User")

        response = test_client.post(
            f"/api/admin/users/{target_user_id}/roles",
            headers=_headers(org_id, admin_id),
            json={"role_name": "viewer"},
        )

        assert response.status_code == 200

        audit = repo.administration.list_audit_log(org_id)
        assert any(entry.action == "role.assigned" for entry in audit)

    def test_assign_role_to_user_from_another_org_returns_404(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        admin_a = _actor(repo, org_a)
        user_b = repo.enterprise.create_user(org_b, "b@example.com", "User B")

        response = test_client.post(
            f"/api/admin/users/{user_b}/roles",
            headers=_headers(org_a, admin_a),
            json={"role_name": "viewer"},
        )

        assert response.status_code == 404

    def test_assign_unknown_role_returns_400(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        target_user_id = repo.enterprise.create_user(org_id, "newuser@example.com", "New User")

        response = test_client.post(
            f"/api/admin/users/{target_user_id}/roles",
            headers=_headers(org_id, admin_id),
            json={"role_name": "does_not_exist"},
        )

        assert response.status_code == 400

    def test_viewer_cannot_assign_roles(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")
        target_user_id = repo.enterprise.create_user(org_id, "newuser@example.com", "New User")

        response = test_client.post(
            f"/api/admin/users/{target_user_id}/roles",
            headers=_headers(org_id, viewer_id),
            json={"role_name": "viewer"},
        )

        assert response.status_code == 403


class TestUserManagementAPI:
    """User Management Capability -- create/get/edit/activate-deactivate/
    remove role, exercised end to end through the real API + RBAC +
    audit log, against the real migration 0006/0009 schema."""

    def test_organization_admin_creates_a_user(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.post(
            "/api/admin/users",
            headers=_headers(org_id, admin_id),
            json={
                "email": "New@Example.com",
                "display_name": "New User",
                "password": "a-strong-password",
                "role_name": "viewer",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "new@example.com"
        assert body["is_active"] is True
        assert "password" not in body

        audit = repo.administration.list_audit_log(org_id)
        created_entries = [e for e in audit if e.action == "user.created"]
        assert len(created_entries) == 1
        assert "password" not in str(created_entries[0].details).lower().replace(
            "passwordless", ""
        )

    def test_create_user_rejects_duplicate_email_case_insensitively(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        repo.enterprise.create_user(org_id, "dup@example.com", "Existing")

        response = test_client.post(
            "/api/admin/users",
            headers=_headers(org_id, admin_id),
            json={
                "email": "DUP@Example.com",
                "display_name": "Duplicate",
                "password": "a-strong-password",
                "role_name": "viewer",
            },
        )

        assert response.status_code == 409

    def test_viewer_cannot_create_users(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.post(
            "/api/admin/users",
            headers=_headers(org_id, viewer_id),
            json={
                "email": "new@example.com",
                "display_name": "New",
                "password": "a-strong-password",
                "role_name": "viewer",
            },
        )

        assert response.status_code == 403

    def test_get_user_scoped_to_organization(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        admin_a = _actor(repo, org_a)
        user_b = repo.enterprise.create_user(org_b, "b@example.com", "User B")

        own_org_response = test_client.get(
            "/api/admin/users/" + str(admin_a), headers=_headers(org_a, admin_a)
        )
        assert own_org_response.status_code == 200

        cross_tenant_response = test_client.get(
            f"/api/admin/users/{user_b}", headers=_headers(org_a, admin_a)
        )
        assert cross_tenant_response.status_code == 404

    def test_update_user_display_name_and_email(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        target = repo.enterprise.create_user(org_id, "old@example.com", "Old Name")

        response = test_client.patch(
            f"/api/admin/users/{target}",
            headers=_headers(org_id, admin_id),
            json={"email": "New@Example.com", "display_name": "New Name"},
        )

        assert response.status_code == 200
        assert response.json()["email"] == "new@example.com"
        assert response.json()["display_name"] == "New Name"

        audit = repo.administration.list_audit_log(org_id)
        updated = [e for e in audit if e.action == "user.updated"]
        assert len(updated) == 1
        assert updated[0].details["before"]["email"] == "old@example.com"
        assert updated[0].details["after"]["email"] == "new@example.com"

    def test_update_user_email_conflict_returns_409(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        repo.enterprise.create_user(org_id, "taken@example.com", "Taken")
        target = repo.enterprise.create_user(org_id, "target@example.com", "Target")

        response = test_client.patch(
            f"/api/admin/users/{target}",
            headers=_headers(org_id, admin_id),
            json={"email": "Taken@Example.com"},
        )

        assert response.status_code == 409

    def test_update_unknown_user_returns_404(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.patch(
            "/api/admin/users/999999",
            headers=_headers(org_id, admin_id),
            json={"display_name": "X"},
        )

        assert response.status_code == 404

    def test_deactivate_and_reactivate_a_user(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        target = repo.enterprise.create_user(org_id, "target@example.com", "Target")

        deactivate_response = test_client.patch(
            f"/api/admin/users/{target}/status",
            headers=_headers(org_id, admin_id),
            json={"is_active": False},
        )
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["is_active"] is False

        reactivate_response = test_client.patch(
            f"/api/admin/users/{target}/status",
            headers=_headers(org_id, admin_id),
            json={"is_active": True},
        )
        assert reactivate_response.status_code == 200
        assert reactivate_response.json()["is_active"] is True

        audit = repo.administration.list_audit_log(org_id)
        actions = [e.action for e in audit]
        assert "user.deactivated" in actions
        assert "user.activated" in actions

    def test_admin_cannot_deactivate_self_via_api(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        _actor(repo, org_id, "pmo")  # irrelevant second user, not another admin

        response = test_client.patch(
            f"/api/admin/users/{admin_id}/status",
            headers=_headers(org_id, admin_id),
            json={"is_active": False},
        )

        assert response.status_code == 400

    def test_two_admins_one_can_deactivate_the_other(self, client):
        """Only `organization_admin` holds `administration.write` (migration
        0007), so any actor able to reach this route is themselves an
        active admin -- the last-admin guard can only ever be tripped by a
        sole admin acting on their own account, never by a distinct actor
        deactivating someone else (that always leaves >= 1 admin: the
        actor). Covered here for deactivation; role removal's equivalent
        self-service case is covered below since it has no separate
        self-protection rule to short-circuit it first."""
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_a = _actor(repo, org_id, "organization_admin")
        with repo.SessionLocal() as session:
            other_admin = repo.enterprise.create_user_in_session(
                session,
                organization_id=org_id,
                email="admin-b@example.com",
                display_name="Admin B",
                password_hash="hash",
            )
            repo.enterprise.assign_role_in_session(session, other_admin.id, "organization_admin")
            session.commit()
            admin_b_id = other_admin.id

        response = test_client.patch(
            f"/api/admin/users/{admin_b_id}/status",
            headers=_headers(org_id, admin_a),
            json={"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_inactive_user_is_denied_every_protected_route(self, client):
        """RBAC (Wave 2, Sprint 3) + is_active (User Management): an
        inactive user must be blocked platform-wide, not just at login."""
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        target = repo.enterprise.create_user(org_id, "target@example.com", "Target")
        with repo.SessionLocal() as session:
            repo.enterprise.assign_role_in_session(session, target, "organization_admin")
            session.commit()

        test_client.patch(
            f"/api/admin/users/{target}/status",
            headers=_headers(org_id, admin_id),
            json={"is_active": False},
        )

        response = test_client.get("/api/admin/users", headers=_headers(org_id, target))

        assert response.status_code == 403

    def test_remove_role(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        target = repo.enterprise.create_user(org_id, "target@example.com", "Target")
        with repo.SessionLocal() as session:
            repo.enterprise.assign_role_in_session(session, target, "viewer")
            session.commit()

        response = test_client.delete(
            f"/api/admin/users/{target}/roles/viewer", headers=_headers(org_id, admin_id)
        )

        assert response.status_code == 200
        audit = repo.administration.list_audit_log(org_id)
        assert any(e.action == "role.removed" for e in audit)

    def test_sole_admin_cannot_remove_their_own_admin_role(self, client):
        """Role removal has no separate self-protection rule (unlike
        deactivation) -- this is the one API-reachable path that actually
        exercises the last-active-admin guard end to end, since the sole
        admin is both the actor and the target."""
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        sole_admin = _actor(repo, org_id, "organization_admin")

        response = test_client.delete(
            f"/api/admin/users/{sole_admin}/roles/organization_admin",
            headers=_headers(org_id, sole_admin),
        )

        assert response.status_code == 409

    def test_remove_unknown_role_returns_400(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)
        target = repo.enterprise.create_user(org_id, "target@example.com", "Target")

        response = test_client.delete(
            f"/api/admin/users/{target}/roles/does_not_exist",
            headers=_headers(org_id, admin_id),
        )

        assert response.status_code == 400


class TestAuditLog:
    def test_domain_mutations_are_recorded_and_visible_via_the_api(self, client):
        """End-to-end: creating a Portfolio through the Enterprise Domain
        API (Sprint 2) shows up in the Administration audit log (Sprint 4)
        -- proves DomainService's record_audit wiring, not just a unit test
        of the repository in isolation."""
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        from src.api.routes import portfolio as portfolio_routes
        from src.services.domain_service import DomainService

        app.dependency_overrides[portfolio_routes.build_domain_service] = (
            lambda: DomainService(repo)
        )
        try:
            create_response = test_client.post(
                "/api/portfolios",
                headers=_headers(org_id, admin_id),
                json={"name": "Portfólio A", "code": "PF-A"},
            )
            assert create_response.status_code == 201
        finally:
            app.dependency_overrides.pop(portfolio_routes.build_domain_service, None)

        audit_response = test_client.get(
            "/api/admin/audit-log", headers=_headers(org_id, admin_id)
        )
        assert audit_response.status_code == 200
        actions = [entry["action"] for entry in audit_response.json()]
        assert "portfolio.created" in actions

    def test_audit_log_is_scoped_by_organization(self, client):
        test_client, repo = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        admin_a = _actor(repo, org_a)
        admin_b = _actor(repo, org_b)
        repo.administration.record_audit(org_b, admin_b, "organization.renamed", "organization", org_b)

        response = test_client.get("/api/admin/audit-log", headers=_headers(org_a, admin_a))

        assert response.status_code == 200
        assert response.json() == []


class TestSecurity:
    def test_get_security_posture(self, client):
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        admin_id = _actor(repo, org_id)

        response = test_client.get("/api/admin/security", headers=_headers(org_id, admin_id))

        assert response.status_code == 200
        assert response.json() == {"password_hashing_algorithm": "argon2", "mfa_available": False}

    def test_viewer_cannot_see_security_posture(self, client):
        """administration.read is organization_admin/pmo only (migration
        0007) -- viewer has no Administration surface at all."""
        test_client, repo = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.get("/api/admin/security", headers=_headers(org_id, viewer_id))

        assert response.status_code == 403
