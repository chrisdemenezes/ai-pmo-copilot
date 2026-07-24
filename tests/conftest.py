import pytest

from src.api.authorization import build_session_revocation_checker
from src.api.rate_limiter import enforce_rate_limit
from src.api.security import verify_api_key
from src.main import app


@pytest.fixture(autouse=True)
def _bypass_security_dependencies_by_default():
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[enforce_rate_limit] = lambda: None
    # Session-revocation enforcement (item 5, TD-010) defaults to "never
    # revoked" for the whole suite: the ~12 API test modules use fabricated
    # session ids that were never in any session store, so the real
    # DB-backed check would just do a wasted lookup that always returns
    # False. Tests that specifically exercise revocation override this with
    # the real checker bound to their own temp database.
    app.dependency_overrides[build_session_revocation_checker] = lambda: (lambda _session_id: False)
    yield
    app.dependency_overrides.pop(verify_api_key, None)
    app.dependency_overrides.pop(enforce_rate_limit, None)
    app.dependency_overrides.pop(build_session_revocation_checker, None)
