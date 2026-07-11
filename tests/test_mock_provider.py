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


def test_mock_provider_reads_response_file_when_configured(tmp_path):
    response_file = tmp_path / "response.json"
    response_file.write_text('{"health_status": "red"}', encoding="utf-8")

    provider = MockLLMProvider(response_file=str(response_file))

    assert provider.generate("any prompt") == '{"health_status": "red"}'


def test_mock_provider_response_file_is_read_fresh_per_call(tmp_path):
    response_file = tmp_path / "response.json"
    response_file.write_text('{"health_status": "green"}', encoding="utf-8")
    provider = MockLLMProvider(response_file=str(response_file))

    first = provider.generate("any prompt")
    response_file.write_text('{"health_status": "red"}', encoding="utf-8")
    second = provider.generate("any prompt")

    assert first == '{"health_status": "green"}'
    assert second == '{"health_status": "red"}'


def test_mock_provider_ignores_response_file_when_unset():
    provider = MockLLMProvider()
    assert provider.generate("any prompt") == "mock analysis output"
