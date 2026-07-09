from dataclasses import dataclass

from src.llm.providers.base import ProviderUnavailableError


@dataclass
class MockLLMProvider:
    """Deterministic local provider used for development and testing without API costs.

    ``fail_mode`` lets tests exercise the same ProviderUnavailableError path a real
    provider outage would trigger, without depending on the Anthropic SDK's exception
    hierarchy.
    """

    response: str = "mock analysis output"
    fail_mode: bool = False

    def generate(self, prompt: str) -> str:
        if self.fail_mode:
            raise ProviderUnavailableError("Mock provider configured to simulate an outage.")
        return self.response
