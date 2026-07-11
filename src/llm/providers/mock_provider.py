from dataclasses import dataclass
from pathlib import Path

from src.llm.providers.base import ProviderUnavailableError


@dataclass
class MockLLMProvider:
    """Deterministic local provider used for development and testing without API costs.

    ``fail_mode`` lets tests exercise the same ProviderUnavailableError path a real
    provider outage would trigger, without depending on the Anthropic SDK's exception
    hierarchy.

    ``response_file``, when set, is read fresh on every call instead of returning the
    static ``response`` default -- lets an external caller (e.g. a demo seed script)
    swap in a schema-conformant JSON body per request without touching this class.
    Unset by default, so existing callers are unaffected.
    """

    response: str = "mock analysis output"
    fail_mode: bool = False
    response_file: str | None = None

    def generate(self, prompt: str) -> str:
        if self.fail_mode:
            raise ProviderUnavailableError("Mock provider configured to simulate an outage.")
        if self.response_file:
            return Path(self.response_file).read_text(encoding="utf-8")
        return self.response
