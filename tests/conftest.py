import pytest

from src.api.rate_limiter import enforce_rate_limit
from src.api.security import verify_api_key
from src.main import app


@pytest.fixture(autouse=True)
def _bypass_security_dependencies_by_default():
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[enforce_rate_limit] = lambda: None
    yield
    app.dependency_overrides.pop(verify_api_key, None)
    app.dependency_overrides.pop(enforce_rate_limit, None)
