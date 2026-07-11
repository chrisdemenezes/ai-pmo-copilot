import os

from src.llm.providers.base import LLMProvider, ProviderConfigError
from src.llm.providers.mock_provider import MockLLMProvider
from src.llm.providers.production_provider import ProductionLLMProvider


def get_provider(env_var: str = "LLM_PROVIDER") -> LLMProvider:
    provider_name = os.getenv(env_var, "anthropic").lower()

    if provider_name == "mock":
        return MockLLMProvider(response_file=os.getenv("MOCK_LLM_RESPONSE_FILE"))
    if provider_name == "anthropic":
        model_name = os.getenv("MODEL_NAME")
        if model_name:
            return ProductionLLMProvider(model=model_name)
        return ProductionLLMProvider()

    raise ProviderConfigError(
        f"Unknown {env_var}={provider_name!r}. Expected 'mock' or 'anthropic'."
    )
