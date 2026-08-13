"""Tests for VoyageEmbeddingProvider (Founder Decision -- Production
Embedding Provider Approval, D-177). No real network call is made in any
test here -- `httpx.post` is patched with fakes/doubles throughout, per
the Founder's explicit restriction against calling Voyage AI for real in
this mission.
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.database.models import KNOWLEDGE_EMBEDDING_DIM
from src.services.knowledge_platform.embedding_provider import (
    EmbeddingProviderConfigError,
    EmbeddingProviderUnavailableError,
    VoyageEmbeddingProvider,
)


class TestVoyageEmbeddingProviderConfig:
    def test_missing_api_key_raises_config_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
        provider = VoyageEmbeddingProvider()
        with pytest.raises(EmbeddingProviderConfigError, match="VOYAGE_API_KEY"):
            provider.embed("hello world")

    def test_defaults_to_voyage_4_and_provider_name(self) -> None:
        provider = VoyageEmbeddingProvider()
        assert provider.model_name == "voyage-4"
        assert provider.provider_name == "voyage"
        assert provider.dimension == KNOWLEDGE_EMBEDDING_DIM


class TestVoyageEmbeddingProviderHappyPath:
    def test_embed_returns_the_vector_from_the_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VOYAGE_API_KEY", "fake-test-key-not-real")
        fake_vector = [0.1] * KNOWLEDGE_EMBEDDING_DIM
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {"data": [{"embedding": fake_vector, "index": 0}]}

        with patch(
            "src.services.knowledge_platform.embedding_provider.httpx.post",
            return_value=fake_response,
        ) as mock_post:
            provider = VoyageEmbeddingProvider()
            result = provider.embed("hello world")

        assert result == fake_vector
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer fake-test-key-not-real"
        assert call_kwargs["json"]["model"] == "voyage-4"
        assert call_kwargs["json"]["output_dimension"] == KNOWLEDGE_EMBEDDING_DIM
        assert call_kwargs["json"]["input"] == "hello world"


class TestVoyageEmbeddingProviderFailure:
    def test_http_error_raises_unavailable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VOYAGE_API_KEY", "fake-test-key-not-real")

        with patch(
            "src.services.knowledge_platform.embedding_provider.httpx.post",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            provider = VoyageEmbeddingProvider()
            with pytest.raises(EmbeddingProviderUnavailableError, match="Voyage AI API call failed"):
                provider.embed("hello world")

    def test_non_2xx_response_raises_unavailable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VOYAGE_API_KEY", "fake-test-key-not-real")
        fake_response = MagicMock()
        fake_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
        )

        with patch(
            "src.services.knowledge_platform.embedding_provider.httpx.post",
            return_value=fake_response,
        ):
            provider = VoyageEmbeddingProvider()
            with pytest.raises(EmbeddingProviderUnavailableError):
                provider.embed("hello world")
