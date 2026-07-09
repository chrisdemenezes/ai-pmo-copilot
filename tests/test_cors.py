import importlib

from fastapi.testclient import TestClient

import src.main as main_module


def test_cors_defaults_to_no_allowed_origins(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.get("/health", headers={"Origin": "https://example.com"})

    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_configured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com")
    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.get("/health", headers={"Origin": "https://example.com"})

    assert response.headers.get("access-control-allow-origin") == "https://example.com"


def test_cors_rejects_unconfigured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com")
    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.get("/health", headers={"Origin": "https://evil.com"})

    assert "access-control-allow-origin" not in response.headers
