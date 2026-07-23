from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.rate_limiter import build_rate_limiter, enforce_rate_limit
from src.api.routes import intelligence
from src.api.security import verify_api_key
from src.main import app


class FakeRepository:
    def list_analyses(self, **kwargs):
        return []


class AlwaysAllowChecker:
    def has_permission(self, user_id, permission):
        return True


INSTITUTIONAL_HEADERS = {
    "X-Stratech-User-Id": "1",
    "X-Stratech-Organization-Id": "1",
    "X-Stratech-Session-Id": "session-1",
}


def test_protected_route_returns_429_after_exceeding_limit(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    build_rate_limiter.cache_clear()

    app.dependency_overrides.pop(verify_api_key, None)
    app.dependency_overrides.pop(enforce_rate_limit, None)
    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepository()
    app.dependency_overrides[authorization_module.build_permission_checker] = (
        lambda: AlwaysAllowChecker()
    )

    client = TestClient(app)
    headers = {"X-API-Key": "secret-key", **INSTITUTIONAL_HEADERS}

    first = client.get("/api/analyses", headers=headers)
    second = client.get("/api/analyses", headers=headers)
    third = client.get("/api/analyses", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "Rate limit exceeded"

    build_rate_limiter.cache_clear()


def test_rate_limit_tracks_api_keys_independently(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    build_rate_limiter.cache_clear()

    # verify_api_key is bypassed here on purpose: this test isolates rate-limit
    # bucketing by X-API-Key value, independent of whether that value is a real key.
    app.dependency_overrides.pop(verify_api_key, None)
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides.pop(enforce_rate_limit, None)
    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepository()
    app.dependency_overrides[authorization_module.build_permission_checker] = (
        lambda: AlwaysAllowChecker()
    )

    client = TestClient(app)

    response_key_a = client.get(
        "/api/analyses", headers={"X-API-Key": "key-a", **INSTITUTIONAL_HEADERS}
    )
    response_key_a_again = client.get(
        "/api/analyses", headers={"X-API-Key": "key-a", **INSTITUTIONAL_HEADERS}
    )
    response_key_b = client.get(
        "/api/analyses", headers={"X-API-Key": "key-b", **INSTITUTIONAL_HEADERS}
    )

    assert response_key_a.status_code == 200
    assert response_key_a_again.status_code == 429
    assert response_key_b.status_code == 200

    build_rate_limiter.cache_clear()
    app.dependency_overrides.pop(verify_api_key, None)
