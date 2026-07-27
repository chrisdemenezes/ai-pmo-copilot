"""Embedding backend seam for the Enterprise Knowledge Platform (Fase 1).

Mirrors `src/llm/providers/base.py`/`factory.py` in shape (a `Protocol` +
an env-var-selected factory) without being a second provider *registry* --
`LLMProvider` remains the only contract for text generation; this is a
distinct capability (turning text into a vector), approved by the Founder's
Vector Store decision and explicitly anticipated as its own Technical
Design choice by `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.4.

No production embedding backend is wired in this Fase: there is no real
consumer of embedding *quality* yet (no Advisor performs RAG), only of the
`pgvector` wiring being correct end to end -- same "grounding in a real
consumer before adding a real backend" discipline already applied to the
Digital PMO Intelligence Foundation (only justified once the Risk Advisor
became a real consumer, W3-2/AR-3). Selecting and wiring a real embedding
backend is deferred to Fase 2, when the Document Advisor becomes that real
consumer.
"""
import hashlib
import os
from typing import Protocol

from src.database.models import KNOWLEDGE_EMBEDDING_DIM


class EmbeddingProviderConfigError(Exception):
    """Raised when EMBEDDING_PROVIDER names a backend this Fase doesn't support."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class MockEmbeddingProvider:
    """Deterministic local provider: the same text always yields the same
    vector, no network call, no external dependency -- same role
    `MockLLMProvider` already plays for `LLMProvider`."""

    def embed(self, text: str) -> list[float]:
        normalized = " ".join(text.split()).lower()
        digest = hashlib.sha256(normalized.encode("utf-8")).digest()
        return [(digest[i] / 127.5) - 1.0 for i in range(KNOWLEDGE_EMBEDDING_DIM)]


def get_embedding_provider(env_var: str = "EMBEDDING_PROVIDER") -> EmbeddingProvider:
    provider_name = os.getenv(env_var, "mock").lower()

    if provider_name == "mock":
        return MockEmbeddingProvider()

    raise EmbeddingProviderConfigError(
        f"Unknown {env_var}={provider_name!r}. Expected 'mock' -- no production embedding "
        "backend is wired in Wave 3 Fase 1 (deferred to Fase 2, first real RAG consumer)."
    )
