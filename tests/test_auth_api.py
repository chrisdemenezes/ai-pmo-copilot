import pytest
from fastapi.testclient import TestClient

from src.api.routes import auth
from src.api.security import verify_api_key
from src.database.models import Role
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.identity.auth_service import (
    DEFAULT_ORGANIZATION_SLUG,
    DEMO_ORGANIZATION_SLUG,
    AuthService,
)
from src.services.identity.password_hashing import Argon2PasswordHasher
from tests.db import temp_database_url


@pytest.fixture()
def service():
    with temp_database_url("auth_api") as database_url:
        repo = AnalysisRepository(database_url=database_url)
        with repo.SessionLocal() as session:
            for name in ("organization_admin", "pmo", "project_manager", "viewer"):
                session.add(Role(name=name))
            session.commit()
        yield AuthService(repo.SessionLocal, Argon2PasswordHasher())


def test_login_succeeds_with_correct_credentials(service, monkeypatch):
    monkeypatch.setenv("API_KEY", "server-to-server-key")
    service.bootstrap_administrator("admin@example.com", "correct-password")
    app.dependency_overrides[auth.build_auth_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={
            "organization": DEFAULT_ORGANIZATION_SLUG,
            "email": "admin@example.com",
            "password": "correct-password",
        },
        headers={"X-API-Key": "server-to-server-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 1
    assert "organization_id" in body
    # Item 5 (TD-010): login now mints a server-side session id the BFF
    # signs into its cookie, so the session becomes revocable.
    assert body["session_id"]
    assert service._administration.is_session_revoked(body["session_id"]) is False
    app.dependency_overrides.pop(auth.build_auth_service, None)


def test_login_returns_401_for_wrong_password(service, monkeypatch):
    monkeypatch.setenv("API_KEY", "server-to-server-key")
    service.bootstrap_administrator("admin@example.com", "correct-password")
    app.dependency_overrides[auth.build_auth_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={
            "organization": DEFAULT_ORGANIZATION_SLUG,
            "email": "admin@example.com",
            "password": "wrong",
        },
        headers={"X-API-Key": "server-to-server-key"},
    )

    assert response.status_code == 401
    app.dependency_overrides.pop(auth.build_auth_service, None)


def test_login_returns_401_for_unknown_email_with_same_message(service, monkeypatch):
    monkeypatch.setenv("API_KEY", "server-to-server-key")
    service.bootstrap_administrator("admin@example.com", "correct-password")
    app.dependency_overrides[auth.build_auth_service] = lambda: service
    client = TestClient(app)

    wrong_password = client.post(
        "/api/auth/login",
        json={
            "organization": DEFAULT_ORGANIZATION_SLUG,
            "email": "admin@example.com",
            "password": "wrong",
        },
        headers={"X-API-Key": "server-to-server-key"},
    )
    unknown_email = client.post(
        "/api/auth/login",
        json={
            "organization": DEFAULT_ORGANIZATION_SLUG,
            "email": "nobody@example.com",
            "password": "wrong",
        },
        headers={"X-API-Key": "server-to-server-key"},
    )
    unknown_organization = client.post(
        "/api/auth/login",
        json={
            "organization": "no-such-organization",
            "email": "admin@example.com",
            "password": "wrong",
        },
        headers={"X-API-Key": "server-to-server-key"},
    )

    assert (
        wrong_password.status_code
        == unknown_email.status_code
        == unknown_organization.status_code
        == 401
    )
    assert (
        wrong_password.json()["detail"]
        == unknown_email.json()["detail"]
        == unknown_organization.json()["detail"]
    )
    app.dependency_overrides.pop(auth.build_auth_service, None)


def test_login_requires_the_server_to_server_api_key(service, monkeypatch):
    # conftest.py bypasses verify_api_key by default for every other test in
    # this file (server-to-server auth isn't what's under test there); this
    # one specifically proves the real dependency is still enforced.
    monkeypatch.setenv("API_KEY", "server-to-server-key")
    app.dependency_overrides.pop(verify_api_key, None)
    service.bootstrap_administrator("admin@example.com", "correct-password")
    app.dependency_overrides[auth.build_auth_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={
            "organization": DEFAULT_ORGANIZATION_SLUG,
            "email": "admin@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 401
    app.dependency_overrides.pop(auth.build_auth_service, None)


def test_logout_acknowledges(service, monkeypatch):
    monkeypatch.setenv("API_KEY", "server-to-server-key")
    app.dependency_overrides[auth.build_auth_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/api/auth/logout",
        json={"session_id": "session-abc", "user_id": 1},
        headers={"X-API-Key": "server-to-server-key"},
    )

    assert response.status_code == 200
    assert response.json() == {"acknowledged": True}
    app.dependency_overrides.pop(auth.build_auth_service, None)


def test_two_distinct_users_authenticate_independently_via_api(service, monkeypatch):
    monkeypatch.setenv("API_KEY", "server-to-server-key")
    service.bootstrap_administrator("admin@example.com", "admin-password")
    service.bootstrap_demo_user("demo-password")
    app.dependency_overrides[auth.build_auth_service] = lambda: service
    client = TestClient(app)
    headers = {"X-API-Key": "server-to-server-key"}

    admin_response = client.post(
        "/api/auth/login",
        json={
            "organization": DEFAULT_ORGANIZATION_SLUG,
            "email": "admin@example.com",
            "password": "admin-password",
        },
        headers=headers,
    )
    demo_response = client.post(
        "/api/auth/login",
        json={
            "organization": DEMO_ORGANIZATION_SLUG,
            "email": "demo@stratech.local",
            "password": "demo-password",
        },
        headers=headers,
    )

    assert admin_response.status_code == demo_response.status_code == 200
    assert admin_response.json()["user_id"] != demo_response.json()["user_id"]
    assert (
        admin_response.json()["organization_id"] != demo_response.json()["organization_id"]
    )
    app.dependency_overrides.pop(auth.build_auth_service, None)


def test_login_scoped_to_wrong_organization_fails_even_with_correct_credentials(
    service, monkeypatch
):
    """EO-015 requirement 2+3 at the API boundary: the Demo user's real
    credentials must never authenticate against the default organization's
    slug, and vice-versa."""
    monkeypatch.setenv("API_KEY", "server-to-server-key")
    service.bootstrap_administrator("admin@example.com", "admin-password")
    service.bootstrap_demo_user("demo-password")
    app.dependency_overrides[auth.build_auth_service] = lambda: service
    client = TestClient(app)
    headers = {"X-API-Key": "server-to-server-key"}

    cross_scoped = client.post(
        "/api/auth/login",
        json={
            "organization": DEFAULT_ORGANIZATION_SLUG,
            "email": "demo@stratech.local",
            "password": "demo-password",
        },
        headers=headers,
    )

    assert cross_scoped.status_code == 401
    app.dependency_overrides.pop(auth.build_auth_service, None)
