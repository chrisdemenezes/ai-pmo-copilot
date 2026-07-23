import os
from dataclasses import dataclass, field

from src.llm.providers.base import ProviderConfigError, ProviderUnavailableError, TokenUsage


@dataclass
class ProductionLLMProvider:
    """Production LLM provider using Anthropic.

    The provider fails fast when the required environment variable is not configured
    so the system does not silently return mock output in production.
    """

    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 1200
    env_var: str = "ANTHROPIC_API_KEY"
    # Populated by the most recent generate() call (Digital PMO Intelligence
    # Foundation, W3-2): the token usage Anthropic's API already returns and
    # this provider used to discard (D-041). Duck-typed and optional on
    # purpose -- LLMProvider's Protocol contract (generate(prompt) -> str)
    # is unchanged; MockLLMProvider simply doesn't have this attribute.
    last_usage: TokenUsage | None = field(default=None, init=False, repr=False)

    def generate(self, prompt: str) -> str:
        token = os.getenv(self.env_var)
        if not token:
            raise ProviderConfigError(f"{self.env_var} is required for production LLM execution.")

        try:
            import anthropic
        except ImportError as exc:
            raise ProviderConfigError("Package 'anthropic' is required. Install requirements.txt.") from exc

        client = anthropic.Anthropic(api_key=token)

        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise ProviderUnavailableError(f"Anthropic API call failed: {exc}") from exc

        self.last_usage = TokenUsage(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

        return "\n".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()
