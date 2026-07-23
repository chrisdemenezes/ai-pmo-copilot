from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import intelligence
from src.main import app

ORG_ID = 1
HEADERS = {
    "X-Stratech-User-Id": "1",
    "X-Stratech-Organization-Id": str(ORG_ID),
    "X-Stratech-Session-Id": "session-1",
}


class AlwaysAllowChecker:
    def has_permission(self, user_id, permission):
        return True


class FakeService:
    def __init__(self, summary: dict | None = None, portfolio: list[dict] | None = None) -> None:
        self._summary = summary
        self._portfolio = portfolio
        self.received_organization_id = None
        self.received_project_name = None

    def summarize(self, organization_id: int, project_name: str) -> dict:
        self.received_organization_id = organization_id
        self.received_project_name = project_name
        return self._summary

    def summarize_portfolio(self, organization_id: int) -> list[dict]:
        self.received_organization_id = organization_id
        return self._portfolio


def _install(fake_service):
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service
    app.dependency_overrides[authorization_module.build_permission_checker] = (
        lambda: AlwaysAllowChecker()
    )


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
    _install(fake_service)

    client = TestClient(app)
    response = client.get(
        "/api/projects/summary", headers=HEADERS, params={"project_name": "Multilift"}
    )

    assert response.status_code == 200
    assert response.json() == fake_summary
    assert fake_service.received_organization_id == ORG_ID
    assert fake_service.received_project_name == "Multilift"

    app.dependency_overrides.clear()


def test_get_project_summary_for_unknown_project_returns_zeros():
    fake_service = FakeService(
        {
            "project_name": "DoesNotExist",
            "project_id": None,
            "total_analyses": 0,
            "open_risks": 0,
            "pending_action_items": 0,
            "latest_health_status": None,
        }
    )
    _install(fake_service)

    client = TestClient(app)
    response = client.get(
        "/api/projects/summary", headers=HEADERS, params={"project_name": "DoesNotExist"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["project_name"] == "DoesNotExist"
    assert body["total_analyses"] == 0
    assert body["open_risks"] == 0
    assert body["pending_action_items"] == 0
    assert body["latest_health_status"] is None

    app.dependency_overrides.clear()


def test_get_project_summary_requires_project_name():
    _install(FakeService({}))
    client = TestClient(app)

    response = client.get("/api/projects/summary", headers=HEADERS)

    assert response.status_code == 422

    app.dependency_overrides.clear()


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
            "project_id": 1,
            "total_analyses": 6,
            "open_risks": 12,
            "pending_action_items": 0,
            "latest_health_status": "red",
        }
    )
    _install(fake_service)

    client = TestClient(app)
    response = client.get(
        "/api/projects/summary",
        headers=HEADERS,
        params={"project_name": "Implantacao SAP S/4HANA"},
    )

    assert response.status_code == 200
    assert response.json()["project_name"] == "Implantacao SAP S/4HANA"
    assert fake_service.received_project_name == "Implantacao SAP S/4HANA"

    app.dependency_overrides.clear()


def test_get_project_summary_handles_a_project_name_with_spaces():
    fake_service = FakeService(
        {
            "project_name": "Migracao de Data Center",
            "project_id": 1,
            "total_analyses": 0,
            "open_risks": 0,
            "pending_action_items": 0,
            "latest_health_status": None,
        }
    )
    _install(fake_service)

    client = TestClient(app)
    response = client.get(
        "/api/projects/summary",
        headers=HEADERS,
        params={"project_name": "Migracao de Data Center"},
    )

    assert response.status_code == 200
    assert response.json()["project_name"] == "Migracao de Data Center"

    app.dependency_overrides.clear()


def test_get_project_summary_handles_a_project_name_with_accents():
    fake_service = FakeService(
        {
            "project_name": "Programa de Governança de Dados",
            "project_id": 1,
            "total_analyses": 0,
            "open_risks": 0,
            "pending_action_items": 0,
            "latest_health_status": None,
        }
    )
    _install(fake_service)

    client = TestClient(app)
    response = client.get(
        "/api/projects/summary",
        headers=HEADERS,
        params={"project_name": "Programa de Governança de Dados"},
    )

    assert response.status_code == 200
    assert response.json()["project_name"] == "Programa de Governança de Dados"

    app.dependency_overrides.clear()


def test_get_project_summary_handles_a_manually_percent_encoded_query_string():
    fake_service = FakeService(
        {
            "project_name": "Implantacao SAP S/4HANA",
            "project_id": 1,
            "total_analyses": 0,
            "open_risks": 0,
            "pending_action_items": 0,
            "latest_health_status": None,
        }
    )
    _install(fake_service)

    client = TestClient(app)

    # Built by hand (not via `params=`) to exercise the exact wire format a
    # browser's fetch(), URLSearchParams, or curl --data-urlencode produces --
    # %20 for space, %2F for slash -- rather than TestClient's own encoding.
    response = client.get(
        "/api/projects/summary?project_name=Implantacao%20SAP%20S%2F4HANA",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["project_name"] == "Implantacao SAP S/4HANA"

    app.dependency_overrides.clear()


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
    _install(fake_service)

    client = TestClient(app)
    response = client.get("/api/portfolio/summary", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == fake_portfolio
    assert fake_service.received_organization_id == ORG_ID

    app.dependency_overrides.clear()


def test_get_portfolio_summary_returns_empty_list_when_no_projects_exist():
    fake_service = FakeService(portfolio=[])
    _install(fake_service)

    client = TestClient(app)
    response = client.get("/api/portfolio/summary", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()
