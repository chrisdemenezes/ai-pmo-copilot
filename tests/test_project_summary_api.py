from fastapi.testclient import TestClient

from src.api.routes import intelligence
from src.main import app


class FakeService:
    def __init__(self, summary: dict) -> None:
        self._summary = summary
        self.received_project_name = None

    def summarize(self, project_name: str) -> dict:
        self.received_project_name = project_name
        return self._summary


def test_get_project_summary_returns_service_result():
    fake_summary = {
        "project_name": "Multilift",
        "total_analyses": 3,
        "open_risks": 2,
        "pending_action_items": 1,
        "latest_health_status": "yellow",
    }
    fake_service = FakeService(fake_summary)
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/projects/Multilift/summary")

    assert response.status_code == 200
    assert response.json() == fake_summary
    assert fake_service.received_project_name == "Multilift"

    app.dependency_overrides.clear()


def test_get_project_summary_for_unknown_project_returns_zeros():
    client = TestClient(app)

    response = client.get("/api/projects/DoesNotExist/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["project_name"] == "DoesNotExist"
    assert body["total_analyses"] == 0
    assert body["open_risks"] == 0
    assert body["pending_action_items"] == 0
    assert body["latest_health_status"] is None
