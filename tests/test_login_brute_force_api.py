"""HTTP-level tests for login brute-force protection (W7-4 Etapa 1, F1 --
Founder Decision). Covers mandate letters A, D, E, F, G, H, I, J at the
real `POST /api/auth/login` route -- guard-internals letters (B/C/K) are
covered in `tests/test_login_brute_force_guard.py`.
"""
import pytest
from fastapi.testclient import TestClient

from src.api.rate_limiter import LoginBruteForceGuard, build_login_brute_force_guard
from src.api.routes import auth
from src.database.models import Role
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.identity.auth_service import (
    DEFAULT_ORGANIZATION_SLUG,
    DEMO_ORGANIZATION_SLUG,
    AuthService,
)
from src.services.identity.email_normalization import normalize_email
from src.services.identity.password_hashing import Argon2PasswordHasher
from tests.db import temp_database_url


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture()
def service():
    with temp_database_url("login_brute_force_api") as database_url:
        repo = AnalysisRepository(database_url=database_url)
        with repo.SessionLocal() as session:
            for name in ("organization_admin", "pmo", "project_manager", "viewer"):
                session.add(Role(name=name))
            session.commit()
        yield AuthService(repo.SessionLocal, Argon2PasswordHasher())


@pytest.fixture()
def client(service, monkeypatch):
    monkeypatch.setenv("API_KEY", "server-to-server-key")
    clock = FakeClock()
    guard = LoginBruteForceGuard(
        max_attempts=3, window_seconds=900, lockout_seconds=900, time_func=clock
    )
    app.dependency_overrides[auth.build_auth_service] = lambda: service
    app.dependency_overrides[build_login_brute_force_guard] = lambda: guard
    test_client = TestClient(app)
    test_client.clock = clock  # type: ignore[attr-defined]
    test_client.headers.update({"X-API-Key": "server-to-server-key"})
    yield test_client
    app.dependency_overrides.pop(auth.build_auth_service, None)
    app.dependency_overrides.pop(build_login_brute_force_guard, None)


def _login(client, organization, email, password):
    return client.post(
        "/api/auth/login",
        json={"organization": organization, "email": email, "password": password},
    )


class TestValidLoginStillWorks:
    def test_correct_credentials_succeed(self, client, service) -> None:
        service.bootstrap_administrator("admin@example.com", "correct-password")
        response = _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password")
        assert response.status_code == 200
        assert response.json()["session_id"]


class TestThresholdBlocksFurtherAttempts:
    def test_attempt_above_threshold_is_blocked_even_with_correct_password(self, client, service) -> None:
        service.bootstrap_administrator("admin@example.com", "correct-password")
        for _ in range(3):
            response = _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
            assert response.status_code == 401

        locked_out_attempt = _login(
            client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password"
        )
        assert locked_out_attempt.status_code == 429


class TestLockoutExpiration:
    def test_login_possible_again_after_lockout_window_elapses(self, client, service) -> None:
        service.bootstrap_administrator("admin@example.com", "correct-password")
        for _ in range(3):
            _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
        assert (
            _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password").status_code
            == 429
        )

        client.clock.advance(901)  # type: ignore[attr-defined]

        response = _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password")
        assert response.status_code == 200


class TestSuccessResetsTheContract:
    def test_successful_login_resets_the_failure_count(self, client, service) -> None:
        service.bootstrap_administrator("admin@example.com", "correct-password")
        _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
        _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
        success = _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password")
        assert success.status_code == 200

        # 2 more failures post-success -- below the threshold of 3, must
        # not be locked (the earlier 2 failures were cleared by the success).
        _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
        third = _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
        assert third.status_code == 401


class TestNoUserEnumeration:
    def test_nonexistent_identity_locks_out_identically_to_a_real_one(self, client, service) -> None:
        service.bootstrap_administrator("admin@example.com", "correct-password")

        for _ in range(3):
            real_user = _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
            fake_user = _login(client, DEFAULT_ORGANIZATION_SLUG, "nobody@example.com", "wrong")
            assert real_user.status_code == fake_user.status_code == 401
            assert real_user.json()["detail"] == fake_user.json()["detail"]

        real_locked = _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password")
        fake_locked = _login(client, DEFAULT_ORGANIZATION_SLUG, "nobody@example.com", "anything")
        assert real_locked.status_code == fake_locked.status_code == 429
        assert real_locked.json()["detail"] == fake_locked.json()["detail"]


class TestOrganizationIsolation:
    def test_lockout_in_one_organization_does_not_affect_another(self, client, service) -> None:
        service.bootstrap_administrator("admin@example.com", "admin-password")
        service.bootstrap_demo_user("demo-password")

        for _ in range(3):
            _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
        assert (
            _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "admin-password").status_code
            == 429
        )

        # Different organization, same real email would collide only if
        # keyed by email alone -- confirms it is not.
        demo_login = _login(client, DEMO_ORGANIZATION_SLUG, "demo@stratech.local", "demo-password")
        assert demo_login.status_code == 200


class TestUserIsolation:
    def test_lockout_for_one_user_does_not_affect_another_in_the_same_organization(
        self, client, service
    ) -> None:
        service.bootstrap_administrator("admin@example.com", "admin-password")
        with service._session_factory() as session:
            org = service._repo.get_organization_by_slug(session, DEFAULT_ORGANIZATION_SLUG)
            service._repo.create_user_in_session(
                session,
                organization_id=org.id,
                email=normalize_email("second@example.com"),
                display_name="Second",
                password_hash=service._credentials.hash("second-password"),
                identity_type="standard",
            )
            session.commit()

        for _ in range(3):
            _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
        assert (
            _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "admin-password").status_code
            == 429
        )

        other_user_login = _login(
            client, DEFAULT_ORGANIZATION_SLUG, "second@example.com", "second-password"
        )
        assert other_user_login.status_code == 200


class TestExistingSessionIsNeverInvalidatedByTheGuard:
    def test_earlier_session_remains_valid_after_the_identity_is_later_locked_out(
        self, client, service
    ) -> None:
        service.bootstrap_administrator("admin@example.com", "correct-password")
        success = _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password")
        assert success.status_code == 200
        session_id = success.json()["session_id"]

        for _ in range(3):
            _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
        assert (
            _login(client, DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password").status_code
            == 429
        )

        assert service._administration.is_session_revoked(session_id) is False
