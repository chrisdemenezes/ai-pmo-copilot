from fastapi.testclient import TestClient

from src.api.routes import intelligence
from src.main import app


class FakeService:
    def __init__(self, summary: dict | None = None, portfolio: list[dict] | None = None) -> None:
        self._summary = summary
        self._portfolio = portfolio
        self.received_project_name = None

    def summarize(self, project_name: str) -> dict:
        self.received_project_name = project_name
        return self._summary

    def summarize_portfolio(self) -> list[dict]:
        return self._portfolio


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


def test_get_portfolio_summary_returns_service_result():
    fake_portfolio = [
        {
            "project_name": "Medlog",
            "total_analyses": 1,
            "open_risks": 0,
            "pending_action_items": 2,
            "latest_health_status": None,
        },
        {
            "project_name": "Multilift",
            "total_analyses": 2,
            "open_risks": 1,
            "pending_action_items": 0,
            "latest_health_status": "green",
        },
    ]
    fake_service = FakeService(portfolio=fake_portfolio)
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/portfolio/summary")

    assert response.status_code == 200
    assert response.json() == fake_portfolio

    app.dependency_overrides.clear()


def test_get_portfolio_summary_returns_empty_list_when_no_projects_exist():
    fake_service = FakeService(portfolio=[])
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/portfolio/summary")

    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()
