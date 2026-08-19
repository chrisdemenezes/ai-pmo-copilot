"""Tests for GET /ready (W7-5 Etapa 2), distinct from GET /health.

/health stays pure liveness (unchanged). /ready additionally checks
critical configuration (reusing the Configuration Contract) and real
database connectivity, and must report -- never crash -- on a broken
dependency.
"""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.api.dependencies import build_repository
from src.main import app

client = TestClient(app)


class TestHealthUnchanged:
    def test_health_is_still_liveness_only(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        # Field-based, not exact-dict-equality: /health additively gains a
        # "release" field once W7-5 Etapa 3 (Release Identity) lands, and
        # this test's job is liveness semantics, not the full response shape.
        body = response.json()
        assert body["status"] == "healthy"
        assert body["service"] == "AI PMO Copilot"


class TestReadyHappyPath:
    def test_returns_200_ready_with_real_database(self) -> None:
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}


class TestReadyReportsMissingConfig:
    def test_returns_503_when_staging_config_is_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.delenv("API_KEY", raising=False)
        response = client.get("/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert any("API_KEY" in problem for problem in body["problems"])


class TestReadyReportsUnreachableDatabase:
    def test_returns_503_with_a_specific_problem(self) -> None:
        broken_repository = MagicMock()
        broken_repository.engine.connect.side_effect = RuntimeError("connection refused")

        # `Depends(build_repository)` captures the callable itself at route
        # registration time -- patching the module attribute afterward
        # would not reach it. FastAPI's own override mechanism is the
        # correct seam for this.
        app.dependency_overrides[build_repository] = lambda: broken_repository
        try:
            response = client.get("/ready")
        finally:
            app.dependency_overrides.pop(build_repository, None)

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert any("database unreachable" in problem for problem in body["problems"])
