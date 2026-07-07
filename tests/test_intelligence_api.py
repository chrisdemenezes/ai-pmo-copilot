from dataclasses import dataclass
from datetime import datetime, timezone

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
    def save_analysis(self, kind, payload, project_name=None):
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


@dataclass
class FakeAnalysisRecord:
    id: int
    kind: str
    project_name: str | None
    created_at: datetime


class FakeRepositoryWithAnalyses:
    def __init__(self, records):
        self.records = records
        self.received_kwargs = None

    def list_analyses(self, project_name=None, limit=20, offset=0):
        self.received_kwargs = {"project_name": project_name, "limit": limit, "offset": offset}
        return self.records


def test_list_analyses_endpoint_returns_summaries():
    fake_repository = FakeRepositoryWithAnalyses(
        records=[
            FakeAnalysisRecord(id=2, kind="risk", project_name="Multilift", created_at=datetime.now(timezone.utc)),
            FakeAnalysisRecord(id=1, kind="meeting", project_name="Multilift", created_at=datetime.now(timezone.utc)),
        ]
    )
    app.dependency_overrides[intelligence.build_repository] = lambda: fake_repository

    client = TestClient(app)
    response = client.get("/api/analyses", params={"project_name": "Multilift"})

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [2, 1]
    assert fake_repository.received_kwargs == {"project_name": "Multilift", "limit": 20, "offset": 0}

    app.dependency_overrides.clear()


def test_list_analyses_endpoint_with_no_results_returns_empty_list():
    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepositoryWithAnalyses(records=[])

    client = TestClient(app)
    response = client.get("/api/analyses", params={"project_name": "Unknown"})

    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()


@dataclass
class FakeAnalysisRecordWithPayload:
    id: int
    kind: str
    project_name: str | None
    created_at: datetime
    payload: dict


class FakeRepositoryWithGetAnalysis:
    def __init__(self, record):
        self.record = record

    def get_analysis(self, analysis_id):
        return self.record


def test_get_analysis_endpoint_returns_full_payload():
    record = FakeAnalysisRecordWithPayload(
        id=1,
        kind="meeting",
        project_name="Multilift",
        created_at=datetime.now(timezone.utc),
        payload={"model_output": "summary generated"},
    )
    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepositoryWithGetAnalysis(record)

    client = TestClient(app)
    response = client.get("/api/analyses/1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["payload"] == {"model_output": "summary generated"}

    app.dependency_overrides.clear()


def test_get_analysis_endpoint_returns_404_when_not_found():
    app.dependency_overrides[intelligence.build_repository] = lambda: FakeRepositoryWithGetAnalysis(None)

    client = TestClient(app)
    response = client.get("/api/analyses/999")

    assert response.status_code == 404

    app.dependency_overrides.clear()
