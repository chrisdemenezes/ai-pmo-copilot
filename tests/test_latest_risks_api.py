from fastapi.testclient import TestClient

from src.api.routes import intelligence
from src.api.security import verify_api_key
from src.main import app


class FakeService:
    def __init__(self, items: list[dict]) -> None:
        self._items = items
        self.received_project_name = "sentinel-not-called"

    def list_latest_risks(self, project_name: str | None = None) -> list[dict]:
        self.received_project_name = project_name
        return self._items


SAMPLE_ITEMS = [
    {
        "project_name": "Multilift",
        "description": "Atraso no fornecedor de middleware",
        "probability": "high",
        "impact": "high",
        "mitigation": "Escalar ao patrocinador",
        "escalation_recommendation": "Escalar ao comitê executivo",
        "source_analysis_id": 7,
        "source_created_at": "2026-07-10T14:00:00Z",
    },
    {
        "project_name": "Medlog",
        "description": "Pequeno atraso na documentação",
        "probability": "low",
        "impact": "low",
        "mitigation": "Monitorar",
        "escalation_recommendation": None,
        "source_analysis_id": 9,
        "source_created_at": "2026-07-09T10:00:00Z",
    },
]


def test_list_latest_risks_without_filter_returns_the_portfolio_view():
    fake_service = FakeService(SAMPLE_ITEMS)
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/risks/latest")

    assert response.status_code == 200
    body = response.json()
    assert [item["description"] for item in body] == [
        "Atraso no fornecedor de middleware",
        "Pequeno atraso na documentação",
    ]
    assert body[0]["escalation_recommendation"] == "Escalar ao comitê executivo"
    assert fake_service.received_project_name is None

    app.dependency_overrides.clear()


def test_list_latest_risks_passes_project_name_through_to_the_service():
    fake_service = FakeService([SAMPLE_ITEMS[0]])
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/risks/latest", params={"project_name": "Multilift"})

    assert response.status_code == 200
    assert fake_service.received_project_name == "Multilift"

    app.dependency_overrides.clear()


def test_list_latest_risks_handles_a_project_name_containing_a_slash():
    fake_service = FakeService([])
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/risks/latest?project_name=Implantacao%20SAP%20S%2F4HANA")

    assert response.status_code == 200
    assert fake_service.received_project_name == "Implantacao SAP S/4HANA"

    app.dependency_overrides.clear()


def test_list_latest_risks_returns_empty_list_when_there_are_no_risks():
    fake_service = FakeService([])
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/risks/latest")

    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()


def test_list_latest_risks_requires_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)
    client = TestClient(app)

    response = client.get("/api/risks/latest")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
