"""Tests for Release Identity on GET /health (W7-5 Etapa 3)."""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestReleaseIdentity:
    def test_defaults_to_unknown_when_release_sha_is_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("RELEASE_SHA", raising=False)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["release"] == "unknown"

    def test_reports_the_configured_release_sha(self, monkeypatch) -> None:
        monkeypatch.setenv("RELEASE_SHA", "abc1234")
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["release"] == "abc1234"
