"""Embedding backend seam for the Enterprise Knowledge Platform.

Mirrors `src/llm/providers/base.py`/`factory.py` in shape (a `Protocol` +
an env-var-selected factory) without being a second provider *registry* --
`LLMProvider` remains the only contract for text generation; this is a
distinct capability (turning text into a vector).

Production Embedding Provider Approval (Founder Decision, D-177): Voyage
AI (`voyage-4`, dimension 1024) is the approved production backend,
replacing the placeholder-only Fase 1 state where no real backend existed.
`voyage-context-4` (contextualized chunk embeddings, a structurally
different API contract -- whole document in, one vector per chunk out)
remains explicitly DEFERRED, since it does not fit the `embed(text) ->
list[float]` contract this Protocol already committed to.
"""
import hashlib
import os
from dataclasses import dataclass
from typing import Protocol

import httpx

from src.database.models import KNOWLEDGE_EMBEDDING_DIM


class EmbeddingProviderConfigError(Exception):
    """Raised when EMBEDDING_PROVIDER names an unsupported backend, or a
    real backend's required environment variable is not configured."""


class EmbeddingProviderUnavailableError(Exception):
    """Raised when a configured real embedding backend's API call fails at
    runtime (network/HTTP error) -- distinct from a configuration problem."""


class EmbeddingProvider(Protocol):
    # Minimal proveniência (Founder Decision, D-175/D-177): every provider
    # self-reports its own identity so `KnowledgeRepository.index()` can
    # persist which provider/model produced a given `Chunk.embedding`,
    # without `KnowledgeRepository` needing to know about any provider by
    # name (no domain interpretation added).
    provider_name: str
    model_name: str

    def embed(self, text: str) -> list[float]:
        ...


class MockEmbeddingProvider:
    """Deterministic local provider: the same text always yields the same
    vector, no network call, no external dependency -- same role
    `MockLLMProvider` already plays for `LLMProvider`."""

    provider_name = "mock"
    model_name = "mock"

    def embed(self, text: str) -> list[float]:
        normalized = " ".join(text.split()).lower()
        digest = hashlib.sha256(normalized.encode("utf-8")).digest()
        return [(digest[i] / 127.5) - 1.0 for i in range(KNOWLEDGE_EMBEDDING_DIM)]


@dataclass
class VoyageEmbeddingProvider:
    """Production embedding provider using Voyage AI.

    Calls the Voyage REST API directly via `httpx` (already a dependency
    of this codebase) instead of the official `voyageai` SDK, which pulls
    in ~30 transitive packages (numpy, pillow, tokenizers, langchain-core)
    for what is, for this single-call seam, one JSON POST -- the same
    "reuse what's already a dependency" discipline applied everywhere else
    in this codebase, not a new provider registry.

    Fails fast when the required environment variable is not configured,
    mirroring `ProductionLLMProvider`."""

    model_name: str = "voyage-4"
    dimension: int = KNOWLEDGE_EMBEDDING_DIM
    env_var: str = "VOYAGE_API_KEY"
    provider_name: str = "voyage"

    def embed(self, text: str) -> list[float]:
        token = os.getenv(self.env_var)
        if not token:
            raise EmbeddingProviderConfigError(f"{self.env_var} is required for production embedding execution.")

        try:
            response = httpx.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {token}"},
                json={"input": text, "model": self.model_name, "output_dimension": self.dimension},
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingProviderUnavailableError(f"Voyage AI API call failed: {exc}") from exc

        return response.json()["data"][0]["embedding"]


def get_embedding_provider(env_var: str = "EMBEDDING_PROVIDER") -> EmbeddingProvider:
    provider_name = os.getenv(env_var, "mock").lower()

    if provider_name == "mock":
        return MockEmbeddingProvider()
    if provider_name == "voyage":
        return VoyageEmbeddingProvider()

    raise EmbeddingProviderConfigError(
        f"Unknown {env_var}={provider_name!r}. Expected 'mock' or 'voyage'."
    )
