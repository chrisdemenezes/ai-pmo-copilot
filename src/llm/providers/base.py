from typing import Protocol


class ProviderConfigError(Exception):
    """Raised when a provider is missing required configuration (e.g. an API key)."""


class ProviderUnavailableError(Exception):
    """Raised when a provider's upstream call fails (timeout, rate limit, connection, auth)."""


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...
