from fastapi.testclient import TestClient

from src.main import app
from src.api.routes import intelligence
from src.llm.providers.base import ProviderConfigError, ProviderUnavailableError


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        if agent_name == "meeting_intelligence":
            return "Project: $project_name\nInput: $transcript"
        if agent_name == "risk_review":
            return "Project: $project_name\nInput: $project_context"
        raise AssertionError(f"Unexpected agent: {agent_name}")


class FakeProvider:
    def generate(self, prompt):
        return "api analysis generated"


class FakeRepository:
    def save_analysis(self, kind, payload):
        assert kind in {"meeting", "risk"}
        assert payload["model_output"] == "api analysis generated"
        return 1


def test_meeting_and_risk_endpoints_with_dependency_overrides():
    app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
    app.dependency_overrides[intelligence.build_provider] = lambda: FakeProvider()
    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepository()

    client = TestClient(app)

    meeting_response = client.post(
        "/api/meetings/analyze",
        json={"project_name": "Multilift", "transcript": "Client approved the handover plan."},
    )
    assert meeting_response.status_code == 200
    assert meeting_response.json()["agent"] == "meeting_intelligence"

    risk_response = client.post(
        "/api/risks/analyze",
        json={"project_name": "Medlog", "project_context": "Timeline has relevant constraints."},
    )
    assert risk_response.status_code == 200
    assert risk_response.json()["agent"] == "risk_review"

    app.dependency_overrides.clear()


class RaisingProvider:
    def __init__(self, exc):
        self.exc = exc

    def generate(self, prompt):
        raise self.exc


def test_meeting_endpoint_returns_503_on_provider_config_error():
    app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
    app.dependency_overrides[intelligence.build_provider] = lambda: RaisingProvider(
        ProviderConfigError("ANTHROPIC_API_KEY is required")
    )
    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepository()

    client = TestClient(app)
    response = client.post(
        "/api/meetings/analyze",
        json={"project_name": "Multilift", "transcript": "Client approved the handover plan."},
    )

    assert response.status_code == 503
    assert response.json()["error"] == "provider_config_error"

    app.dependency_overrides.clear()


def test_risk_endpoint_returns_502_on_provider_unavailable_error():
    app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
    app.dependency_overrides[intelligence.build_provider] = lambda: RaisingProvider(
        ProviderUnavailableError("Anthropic API call failed")
    )
    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepository()

    client = TestClient(app)
    response = client.post(
        "/api/risks/analyze",
        json={"project_name": "Medlog", "project_context": "Timeline has relevant constraints."},
    )

    assert response.status_code == 502
    assert response.json()["error"] == "provider_unavailable"

    app.dependency_overrides.clear()
