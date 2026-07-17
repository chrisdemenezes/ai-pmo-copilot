from fastapi.testclient import TestClient

from src.api.routes import intelligence
from src.api.security import verify_api_key
from src.main import app


class FakeService:
    def __init__(self, items: list[dict]) -> None:
        self._items = items
        self.received_project_name = "sentinel-not-called"

    def list_action_items(self, project_name: str | None = None) -> list[dict]:
        self.received_project_name = project_name
        return self._items


SAMPLE_ITEMS = [
    {
        "project_name": "Multilift",
        "description": "Atualizar cronograma",
        "owner": "Ana",
        "due_date": "2026-07-20",
        "source_analysis_id": 7,
        "source_created_at": "2026-07-10T14:00:00Z",
    },
    {
        "project_name": "Medlog",
        "description": "Cobrar fornecedor",
        "owner": None,
        "due_date": None,
        "source_analysis_id": 9,
        "source_created_at": "2026-07-09T10:00:00Z",
    },
]


def test_list_action_items_without_filter_returns_the_portfolio_view():
    fake_service = FakeService(SAMPLE_ITEMS)
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/action-items")

    assert response.status_code == 200
    body = response.json()
    assert [item["description"] for item in body] == ["Atualizar cronograma", "Cobrar fornecedor"]
    assert body[0]["source_analysis_id"] == 7
    assert fake_service.received_project_name is None

    app.dependency_overrides.clear()


def test_list_action_items_passes_project_name_through_to_the_service():
    fake_service = FakeService([SAMPLE_ITEMS[0]])
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/action-items", params={"project_name": "Multilift"})

    assert response.status_code == 200
    assert fake_service.received_project_name == "Multilift"

    app.dependency_overrides.clear()


def test_list_action_items_handles_a_project_name_containing_a_slash():
    fake_service = FakeService([])
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    # Built by hand to exercise the exact wire format a browser produces --
    # %20 for space, %2F for slash -- same hazard already covered for
    # GET /api/projects/summary.
    response = client.get("/api/action-items?project_name=Implantacao%20SAP%20S%2F4HANA")

    assert response.status_code == 200
    assert fake_service.received_project_name == "Implantacao SAP S/4HANA"

    app.dependency_overrides.clear()


def test_list_action_items_returns_empty_list_when_there_are_no_items():
    fake_service = FakeService([])
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/action-items")

    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()


def test_list_action_items_requires_api_key(monkeypatch):
    # Same auth contract as every other route on this router -- the shared
    # verify_api_key dependency, no bespoke middleware.
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)
    client = TestClient(app)

    response = client.get("/api/action-items")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
