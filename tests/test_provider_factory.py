import pytest

from src.llm.providers.base import ProviderConfigError
from src.llm.providers.factory import get_provider
from src.llm.providers.mock_provider import MockLLMProvider
from src.llm.providers.production_provider import ProductionLLMProvider


def test_get_provider_returns_mock_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    assert isinstance(get_provider(), MockLLMProvider)


def test_get_provider_returns_production_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert isinstance(get_provider(), ProductionLLMProvider)


def test_get_provider_defaults_to_anthropic_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(get_provider(), ProductionLLMProvider)


def test_get_provider_raises_on_unknown_value(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown-provider")

    with pytest.raises(ProviderConfigError):
        get_provider()
