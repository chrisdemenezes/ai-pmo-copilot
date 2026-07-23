import logging

from src.llm.providers.base import TokenUsage
from src.services.ai_foundation.observability import ObservabilityRecorder
from src.services.ai_foundation.types import SessionContext

SESSION = SessionContext(organization_id=1, user_id=1, session_id="session-1", project_name="Aurora")


class ProviderWithUsage:
    def __init__(self):
        self.last_usage = None

    def generate(self, prompt):
        self.last_usage = TokenUsage(input_tokens=120, output_tokens=45)
        return "resposta"


class ProviderWithoutUsage:
    def generate(self, prompt):
        return "resposta"


def test_record_call_returns_the_providers_result_unchanged():
    result = ObservabilityRecorder.record_call("risk_advisor", SESSION, ProviderWithUsage(), "prompt")

    assert result == "resposta"


def test_record_call_logs_latency_and_token_usage_when_available(caplog):
    with caplog.at_level(logging.INFO, logger="src.services.ai_foundation.observability"):
        ObservabilityRecorder.record_call("risk_advisor", SESSION, ProviderWithUsage(), "prompt")

    message = caplog.records[-1].getMessage()
    assert "analyst=risk_advisor" in message
    assert "organization_id=1" in message
    assert "input_tokens=120" in message
    assert "output_tokens=45" in message


def test_record_call_treats_missing_usage_as_no_cost_data_not_an_error(caplog):
    with caplog.at_level(logging.INFO, logger="src.services.ai_foundation.observability"):
        result = ObservabilityRecorder.record_call(
            "risk_advisor", SESSION, ProviderWithoutUsage(), "prompt"
        )

    assert result == "resposta"
    message = caplog.records[-1].getMessage()
    assert "input_tokens=None" in message
    assert "output_tokens=None" in message
