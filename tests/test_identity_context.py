from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.identity_context import get_request_context
from src.services.identity.models import RequestContext

# This epic wires get_request_context as reusable infrastructure without
# attaching it to any V1 or Epic 1 route (TDS Section 15.6/22) -- it is
# exercised here through a throwaway test-only route, not a production one.
_test_app = FastAPI()


@_test_app.get("/whoami")
def whoami(context: RequestContext = Depends(get_request_context)):
    return {
        "user_id": context.user.user_id,
        "organization_id": context.organization.organization_id,
        "session_id": context.session.session_id,
        "request_id": context.request_id,
    }


client = TestClient(_test_app)


def test_populates_context_from_institutional_headers():
    response = client.get(
        "/whoami",
        headers={
            "X-Stratech-User-Id": "42",
            "X-Stratech-Organization-Id": "7",
            "X-Stratech-Session-Id": "session-abc",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 42
    assert body["organization_id"] == 7
    assert body["session_id"] == "session-abc"
    assert body["request_id"]  # populated from the existing request-id middleware


def test_missing_user_header_returns_400():
    response = client.get(
        "/whoami",
        headers={
            "X-Stratech-Organization-Id": "7",
            "X-Stratech-Session-Id": "session-abc",
        },
    )
    assert response.status_code == 400


def test_missing_organization_header_returns_400():
    response = client.get(
        "/whoami",
        headers={"X-Stratech-User-Id": "42", "X-Stratech-Session-Id": "session-abc"},
    )
    assert response.status_code == 400


def test_missing_session_header_returns_400():
    response = client.get(
        "/whoami",
        headers={"X-Stratech-User-Id": "42", "X-Stratech-Organization-Id": "7"},
    )
    assert response.status_code == 400


def test_non_integer_ids_return_400():
    response = client.get(
        "/whoami",
        headers={
            "X-Stratech-User-Id": "not-a-number",
            "X-Stratech-Organization-Id": "7",
            "X-Stratech-Session-Id": "session-abc",
        },
    )
    assert response.status_code == 400
