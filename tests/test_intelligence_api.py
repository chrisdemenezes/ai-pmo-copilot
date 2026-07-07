from fastapi.testclient import TestClient

from src.main import app
from src.api.routes import intelligence


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        return "Project: {project_name}\nInput: {transcript}{project_context}"


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
