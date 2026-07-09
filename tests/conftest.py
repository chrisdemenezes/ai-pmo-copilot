import pytest

from src.api.security import verify_api_key
from src.main import app


@pytest.fixture(autouse=True)
def _bypass_api_key_by_default():
    app.dependency_overrides[verify_api_key] = lambda: None
    yield
    app.dependency_overrides.pop(verify_api_key, None)
