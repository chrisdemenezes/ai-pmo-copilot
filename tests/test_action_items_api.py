from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api.routes import intelligence
from src.api.security import verify_api_key
from src.database.enterprise_repository import ProjectNotFoundError
from src.main import app


class _UnseededEnterprise:
    """Resolver stub: no Project rows exist, so a name never resolves and the
    additive contract flows it through to the service unchanged (TD-008 Phase
    3b, Etapa 1)."""

    def resolve_project_reference(self, organization_id, project_id=None, project_name=None):
        if project_id is None and (project_name is None or project_name.strip() == ""):
            return None
        raise ProjectNotFoundError("no Project rows in this stub")


class _FakeRepository:
    enterprise = _UnseededEnterprise()

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
    def __init__(self, items: list[dict]) -> None:
        self._items = items
        self.received_organization_id = "sentinel-not-called"
        self.received_project_name = "sentinel-not-called"
        self.received_project_id = "sentinel-not-called"

    def list_action_items(
        self,
        organization_id: int,
        project_name: str | None = None,
        project_id: int | None = None,
    ) -> list[dict]:
        self.received_organization_id = organization_id
        self.received_project_name = project_name
        self.received_project_id = project_id
        return self._items


def _install(fake_service):
    app.dependency_overrides[intelligence.build_project_summary_service] = lambda: fake_service
    app.dependency_overrides[intelligence.build_repository] = lambda: _FakeRepository()
    app.dependency_overrides[authorization_module.build_permission_checker] = (
        lambda: AlwaysAllowChecker()
    )


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
    _install(fake_service)

    client = TestClient(app)
    response = client.get("/api/action-items", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert [item["description"] for item in body] == ["Atualizar cronograma", "Cobrar fornecedor"]
    assert body[0]["source_analysis_id"] == 7
    assert fake_service.received_organization_id == ORG_ID
    assert fake_service.received_project_name is None

    app.dependency_overrides.clear()


def test_list_action_items_passes_project_name_through_to_the_service():
    fake_service = FakeService([SAMPLE_ITEMS[0]])
    _install(fake_service)

    client = TestClient(app)
    response = client.get(
        "/api/action-items", headers=HEADERS, params={"project_name": "Multilift"}
    )

    assert response.status_code == 200
    assert fake_service.received_project_name == "Multilift"

    app.dependency_overrides.clear()


def test_list_action_items_handles_a_project_name_containing_a_slash():
    fake_service = FakeService([])
    _install(fake_service)

    client = TestClient(app)
    # Built by hand to exercise the exact wire format a browser produces --
    # %20 for space, %2F for slash -- same hazard already covered for
    # GET /api/projects/summary.
    response = client.get(
        "/api/action-items?project_name=Implantacao%20SAP%20S%2F4HANA", headers=HEADERS
    )

    assert response.status_code == 200
    assert fake_service.received_project_name == "Implantacao SAP S/4HANA"

    app.dependency_overrides.clear()


def test_list_action_items_returns_empty_list_when_there_are_no_items():
    fake_service = FakeService([])
    _install(fake_service)

    client = TestClient(app)
    response = client.get("/api/action-items", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()


def test_list_action_items_requires_api_key(monkeypatch):
    # Same auth contract as every other route on this router -- the shared
    # verify_api_key dependency, no bespoke middleware.
    monkeypatch.setenv("API_KEY", "secret-key")
    app.dependency_overrides.pop(verify_api_key, None)
    client = TestClient(app)

    response = client.get("/api/action-items", headers=HEADERS)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
