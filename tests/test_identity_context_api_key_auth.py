"""D-051 -- proves the API Key auth path is a real, working alternative to
the 3 session headers on an existing, unmodified route (`GET
/admin/organization`), not a provisional/speculative capability.

`get_request_context`'s API Key branch calls `build_repository()` directly
rather than through a declared `Depends(...)` (see `identity_context.py`'s
own docstring for why: declaring it there would force every existing test
in the suite to override it). That means this is the one test that
legitimately needs to repoint the process-wide `@lru_cache`'d singleton at
a real temp database instead of using `app.dependency_overrides` -- and to
clear it again afterward so nothing leaks into any other test.
"""
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from src.api import dependencies as dependencies_module
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.administration_service import AdministrationService

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


@pytest.fixture()
def repo_pointed_at_temp_db(monkeypatch):
    with temp_database_url("identity_context_api_key_auth") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

        monkeypatch.setenv("DATABASE_URL", database_url)
        dependencies_module.build_repository.cache_clear()
        try:
            yield AnalysisRepository(database_url=database_url)
        finally:
            dependencies_module.build_repository.cache_clear()


def test_existing_route_authenticates_via_x_stratech_api_key_header(repo_pointed_at_temp_db):
    repo = repo_pointed_at_temp_db
    service = AdministrationService(repository=repo)

    org_id = repo.enterprise.create_organization("Org A")
    admin_id = repo.enterprise.create_user(org_id, "admin@example.com", "Admin")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, admin_id, "organization_admin")
        session.commit()

    _, plaintext_key = service.create_api_key(org_id, "CI pipeline", admin_id)

    client = TestClient(app)
    response = client.get(
        "/api/admin/organization", headers={"X-Stratech-Api-Key": plaintext_key}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Org A"


def test_a_revoked_api_key_is_rejected_with_401(repo_pointed_at_temp_db):
    repo = repo_pointed_at_temp_db
    service = AdministrationService(repository=repo)

    org_id = repo.enterprise.create_organization("Org A")
    admin_id = repo.enterprise.create_user(org_id, "admin@example.com", "Admin")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, admin_id, "organization_admin")
        session.commit()

    api_key, plaintext_key = service.create_api_key(org_id, "CI pipeline", admin_id)
    service.revoke_api_key(api_key.id, org_id, admin_id)

    client = TestClient(app)
    response = client.get(
        "/api/admin/organization", headers={"X-Stratech-Api-Key": plaintext_key}
    )

    assert response.status_code == 401


def test_an_unknown_api_key_is_rejected_with_401(repo_pointed_at_temp_db):
    client = TestClient(app)
    response = client.get(
        "/api/admin/organization", headers={"X-Stratech-Api-Key": "sk_live_not-a-real-key"}
    )

    assert response.status_code == 401


def test_a_viewer_scoped_api_key_still_gets_403_on_administration_write(repo_pointed_at_temp_db):
    """The API Key path reuses RBAC in full -- it is not a bypass. The key
    authenticates as its creator, so a viewer's key is still just a
    viewer."""
    repo = repo_pointed_at_temp_db
    service = AdministrationService(repository=repo)

    org_id = repo.enterprise.create_organization("Org A")
    viewer_id = repo.enterprise.create_user(org_id, "viewer@example.com", "Viewer")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, viewer_id, "viewer")
        session.commit()

    _, plaintext_key = service.create_api_key(org_id, "Viewer's key", viewer_id)

    client = TestClient(app)
    response = client.patch(
        "/api/admin/organization",
        headers={"X-Stratech-Api-Key": plaintext_key},
        json={"name": "New Name"},
    )

    assert response.status_code == 403
