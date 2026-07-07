import pytest

from src.llm.providers.base import ProviderUnavailableError
from src.llm.providers.mock_provider import MockLLMProvider


def test_mock_provider_returns_configured_response():
    provider = MockLLMProvider(response="fixed output")
    assert provider.generate("any prompt") == "fixed output"


def test_mock_provider_simulates_outage_when_fail_mode_enabled():
    provider = MockLLMProvider(fail_mode=True)

    with pytest.raises(ProviderUnavailableError):
        provider.generate("any prompt")
