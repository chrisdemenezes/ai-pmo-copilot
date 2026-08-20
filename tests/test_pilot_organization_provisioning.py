"""Local V1 Pilot Findings Review (D-217, Finding 04b) -- Controlled Pilot
organization pre-provisioning. This is both a regression test AND the
"Ensaio de Provisionamento" the mandate requires: it exercises the real API
(TestClient, real Postgres via temp_database_url, real alembic migration),
never a mock, proving the 7 Runbook criteria mechanically end to end. See
docs/operations/LOCAL-V1-PILOT-ORGANIZATION-PROVISIONING-RUNBOOK.md.
"""
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import administration as administration_routes
from src.api.routes import auth as auth_routes
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.administration_service import AdministrationService
from src.services.authorization.checker import SqlPermissionChecker
from src.services.identity.auth_service import AuthService
from src.services.identity.password_hashing import Argon2PasswordHasher
from tests.db import temp_database_url


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result


def _headers(organization_id: int, user_id: int, session_id: str = "session-1") -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": session_id,
    }


@pytest.fixture()
def provisioned():
    """A real, alembic-migrated Postgres database with the default
    organization ("Organizacao Principal") already seeded by migration
    0008, plus a freshly pre-provisioned pilot organization -- the exact
    scenario the Runbook describes: an existing installation onboarding one
    new Controlled Pilot tenant."""
    with temp_database_url("pilot_provisioning") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

        repo = AnalysisRepository(database_url=database_url)
        auth_service = AuthService(repo.SessionLocal, Argon2PasswordHasher())

        # Etapa 1+2 of the Runbook: create/provision the pilot organization
        # and its organization_admin, via the same code path a real boot
        # with PILOT_ORGANIZATION_NAME/PILOT_ORGANIZATION_ADMIN_EMAIL/
        # PILOT_ORGANIZATION_ADMIN_PASSWORD set would run.
        pilot_org_id = auth_service.bootstrap_organization(
            "Piloto Externo A", "admin@piloto-a.example", "pilot-admin-password"
        )

        app.dependency_overrides[auth_routes.build_auth_service] = lambda: auth_service
        app.dependency_overrides[administration_routes.build_administration_service] = (
            lambda: AdministrationService(repo)
        )
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo, pilot_org_id
        app.dependency_overrides.pop(auth_routes.build_auth_service, None)
        app.dependency_overrides.pop(administration_routes.build_administration_service, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


class TestPilotOrganizationProvisioningRehearsal:
    def test_admin_can_log_in(self, provisioned):
        """Runbook item 6 (validar login)."""
        client, _repo, _pilot_org_id = provisioned

        response = client.post(
            "/api/auth/login",
            json={
                "organization": "piloto-externo-a",
                "email": "admin@piloto-a.example",
                "password": "pilot-admin-password",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["organization_id"] and body["user_id"] and body["session_id"]

    def test_admin_role_is_confirmed_via_the_real_roles_endpoint(self, provisioned):
        """Runbook item 3 (confirmar roles/permissions)."""
        client, repo, pilot_org_id = provisioned
        with repo.SessionLocal() as session:
            admin_id = repo.enterprise.get_user_by_email(
                session, pilot_org_id, "admin@piloto-a.example"
            ).id

        response = client.get(
            f"/api/admin/users/{admin_id}/roles",
            headers=_headers(pilot_org_id, admin_id),
        )

        assert response.status_code == 200
        role_names = {role["name"] for role in response.json()}
        assert role_names == {"organization_admin"}

    def test_admin_can_create_a_pilot_user(self, provisioned):
        """Runbook item 4 (criar/convidar usuários do piloto) -- via the
        direct-create path (POST /admin/users), the real mechanism
        administration.py already exposes for an org_admin setting an
        initial password directly, no invite flow required."""
        client, repo, pilot_org_id = provisioned
        with repo.SessionLocal() as session:
            admin = repo.enterprise.get_user_by_email(
                session, pilot_org_id, "admin@piloto-a.example"
            )
            admin_id = admin.id

        response = client.post(
            "/api/admin/users",
            json={
                "email": "user@piloto-a.example",
                "display_name": "Usuário do Piloto",
                "password": "pilot-user-password",
                "role_name": "project_manager",
            },
            headers=_headers(pilot_org_id, admin_id),
        )

        assert response.status_code == 201
        created = response.json()
        assert created["email"] == "user@piloto-a.example"

        login = client.post(
            "/api/auth/login",
            json={
                "organization": "piloto-externo-a",
                "email": "user@piloto-a.example",
                "password": "pilot-user-password",
            },
        )
        assert login.status_code == 200

    def test_tenant_isolation_holds_between_pilot_and_default_organization(self, provisioned):
        """Runbook item 5 (validar tenant isolation) -- the pilot admin must
        never reach a resource that belongs to the pre-existing default
        organization, and vice versa. Same uniform-404 convention as
        tests/test_administration_api.py::test_get_user_scoped_to_organization."""
        client, repo, pilot_org_id = provisioned
        default_org_id = repo.enterprise.create_organization("Outra Organização")
        other_user_id = repo.enterprise.create_user(
            default_org_id, "someone@outra.example", "Someone"
        )
        with repo.SessionLocal() as session:
            pilot_admin = repo.enterprise.get_user_by_email(
                session, pilot_org_id, "admin@piloto-a.example"
            )
            pilot_admin_id = pilot_admin.id

        cross_tenant = client.get(
            f"/api/admin/users/{other_user_id}",
            headers=_headers(pilot_org_id, pilot_admin_id),
        )

        assert cross_tenant.status_code == 404

    def test_admin_has_expected_access_to_own_organization(self, provisioned):
        """Runbook item 7 (validar acesso esperado às Capabilities) -- the
        pilot admin reads their own organization record without error."""
        client, repo, pilot_org_id = provisioned
        with repo.SessionLocal() as session:
            admin = repo.enterprise.get_user_by_email(
                session, pilot_org_id, "admin@piloto-a.example"
            )
            admin_id = admin.id

        response = client.get(
            "/api/admin/organization",
            headers=_headers(pilot_org_id, admin_id),
        )

        assert response.status_code == 200
        assert response.json()["id"] == pilot_org_id
