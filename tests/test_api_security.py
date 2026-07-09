from fastapi.testclient import TestClient

from src.api.security import verify_api_key
from src.main import app


def test_health_endpoint_does_not_require_api_key():
    app.dependency_overrides.pop(verify_api_key, None)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200


def test_protected_route_returns_503_when_api_key_not_configured(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    app.dependency_overrides.pop(verify_api_key, None)
    client = TestClient(app)

    response = client.get("/api/analyses")

    assert response.status_code == 503
    assert response.json()["detail"] == "API_KEY is not configured on the server"


def test_protected_route_returns_401_when_api_key_header_missing(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)
    client = TestClient(app)

    response = client.get("/api/analyses")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_protected_route_returns_401_when_api_key_header_is_wrong(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)
    client = TestClient(app)

    response = client.get("/api/analyses", headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401


def test_protected_route_returns_200_when_api_key_header_is_correct(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)

    class FakeRepository:
        def list_analyses(self, **kwargs):
            return []

    from src.api.routes import intelligence

    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepository()
    client = TestClient(app)

    response = client.get("/api/analyses", headers={"X-API-Key": "secret-key"})

    assert response.status_code == 200
    assert response.json() == []
