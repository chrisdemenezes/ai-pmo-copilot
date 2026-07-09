import httpx
import pytest

from src.llm.providers.base import ProviderConfigError, ProviderUnavailableError
from src.llm.providers.production_provider import ProductionLLMProvider


def test_generate_raises_provider_config_error_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = ProductionLLMProvider()

    with pytest.raises(ProviderConfigError):
        provider.generate("Analyze this project.")


def test_generate_raises_provider_unavailable_on_anthropic_api_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    import anthropic

    class FailingMessages:
        def create(self, **kwargs):
            raise anthropic.APIConnectionError(
                message="connection failed",
                request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
            )

    class FailingClient:
        def __init__(self, api_key):
            self.messages = FailingMessages()

    monkeypatch.setattr(anthropic, "Anthropic", FailingClient)

    provider = ProductionLLMProvider()

    with pytest.raises(ProviderUnavailableError):
        provider.generate("Analyze this project.")
