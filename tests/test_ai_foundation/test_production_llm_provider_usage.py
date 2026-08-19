from unittest.mock import MagicMock, patch

from src.llm.providers.production_provider import ProductionLLMProvider


def test_generate_populates_last_usage_from_the_anthropic_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    provider = ProductionLLMProvider()

    assert provider.last_usage is None

    fake_message = MagicMock()
    fake_message.content = [MagicMock(type="text", text="resposta")]
    fake_message.usage = MagicMock(input_tokens=200, output_tokens=50)

    with patch("anthropic.Anthropic") as anthropic_client_cls:
        anthropic_client_cls.return_value.messages.create.return_value = fake_message
        result = provider.generate("prompt")

    assert result == "resposta"
    assert provider.last_usage is not None
    assert provider.last_usage.input_tokens == 200
    assert provider.last_usage.output_tokens == 50


def test_mock_provider_has_no_last_usage_attribute():
    from src.llm.providers.mock_provider import MockLLMProvider

    provider = MockLLMProvider()

    assert not hasattr(provider, "last_usage")
