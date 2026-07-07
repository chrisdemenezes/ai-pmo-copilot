from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for Large Language Model providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass


class MockLLMProvider(LLMProvider):
    """Temporary provider used until a real LLM integration is configured."""

    def generate(self, prompt: str) -> str:
        return "LLM response placeholder"
