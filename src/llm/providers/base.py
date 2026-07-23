from dataclasses import dataclass
from typing import Protocol


class ProviderConfigError(Exception):
    """Raised when a provider is missing required configuration (e.g. an API key)."""


class ProviderUnavailableError(Exception):
    """Raised when a provider's upstream call fails (timeout, rate limit, connection, auth)."""


@dataclass(frozen=True)
class TokenUsage:
    """Token usage from a single provider call (Digital PMO Intelligence
    Foundation, W3-2). Optional, duck-typed on providers via `last_usage` --
    not part of the LLMProvider Protocol itself."""

    input_tokens: int
    output_tokens: int


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...
