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
        "project_id": 7,
        "total_analyses": 3,
        "open_risks": 2,
        "pending_action_items": 1,
        "latest_health_status": "yellow",
    }
    fake_service = FakeService(fake_summary)
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get("/api/projects/summary", params={"project_name": "Multilift"})

    assert response.status_code == 200
    assert response.json() == fake_summary
    assert fake_service.received_project_name == "Multilift"

    app.dependency_overrides.clear()


def test_get_project_summary_for_unknown_project_returns_zeros():
    client = TestClient(app)

    response = client.get("/api/projects/summary", params={"project_name": "DoesNotExist"})

    assert response.status_code == 200
    body = response.json()
    assert body["project_name"] == "DoesNotExist"
    assert body["total_analyses"] == 0
    assert body["open_risks"] == 0
    assert body["pending_action_items"] == 0
    assert body["latest_health_status"] is None


def test_get_project_summary_requires_project_name():
    client = TestClient(app)

    response = client.get("/api/projects/summary")

    assert response.status_code == 422


# Real hazard this endpoint was migrated to fix (TIP-004 follow-up): a
# project_name containing "/" 404'd unconditionally as a path segment, no
# matter how the client encoded it, because Starlette's default path
# converter cannot capture a literal slash. Query parameters don't have
# this restriction. Each case below is a real character class already
# present in this product's own data (the "Implantacao SAP S/4HANA" demo
# project) or realistically expected (accented Portuguese project names).
def test_get_project_summary_handles_a_project_name_containing_a_slash():
    fake_service = FakeService(
        {
            "project_name": "Implantacao SAP S/4HANA",
            "total_analyses": 6,
            "open_risks": 12,
            "pending_action_items": 0,
            "latest_health_status": "red",
        }
    )
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service

    client = TestClient(app)
    response = client.get(
        "/api/projects/summary", params={"project_name": "Implantacao SAP S/4HANA"}
    )

    assert response.status_code == 200
    assert response.json()["project_name"] == "Implantacao SAP S/4HANA"
    assert fake_service.received_project_name == "Implantacao SAP S/4HANA"

    app.dependency_overrides.clear()


def test_get_project_summary_handles_a_project_name_with_spaces():
    client = TestClient(app)

    response = client.get(
        "/api/projects/summary", params={"project_name": "Migracao de Data Center"}
    )

    assert response.status_code == 200
    assert response.json()["project_name"] == "Migracao de Data Center"


def test_get_project_summary_handles_a_project_name_with_accents():
    client = TestClient(app)

    response = client.get(
        "/api/projects/summary", params={"project_name": "Programa de Governança de Dados"}
    )

    assert response.status_code == 200
    assert response.json()["project_name"] == "Programa de Governança de Dados"


def test_get_project_summary_handles_a_manually_percent_encoded_query_string():
    client = TestClient(app)

    # Built by hand (not via `params=`) to exercise the exact wire format a
    # browser's fetch(), URLSearchParams, or curl --data-urlencode produces --
    # %20 for space, %2F for slash -- rather than TestClient's own encoding.
    response = client.get(
        "/api/projects/summary?project_name=Implantacao%20SAP%20S%2F4HANA"
    )

    assert response.status_code == 200
    assert response.json()["project_name"] == "Implantacao SAP S/4HANA"


def test_get_portfolio_summary_returns_service_result():
    fake_portfolio = [
        {
            "project_name": "Medlog",
            "project_id": 3,
            "total_analyses": 1,
            "open_risks": 0,
            "pending_action_items": 2,
            "latest_health_status": None,
        },
        {
            "project_name": "Multilift",
            "project_id": 7,
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
