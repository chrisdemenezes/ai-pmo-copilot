"""External Document Sources (V1 Product & Capability Completion, Package L).

Unit-level: `HttpUrlDocumentSource` never touches the real network -- every
test injects an `httpx.MockTransport` so behavior is exercised through real
`httpx` request/response handling, without any external dependency or real
corporate data.
"""
import httpx
import pytest

from src.services.knowledge_platform import external_sources as module
from src.services.knowledge_platform.external_sources import (
    ExternalSourceFetchError,
    HttpUrlDocumentSource,
)


def _patch_transport(monkeypatch, handler):
    def fake_stream(method, url, **kwargs):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        return client.stream(method, url)

    monkeypatch.setattr(module.httpx, "stream", fake_stream)


def test_fetch_returns_content_with_provenance(monkeypatch):
    def handler(request):
        return httpx.Response(200, text="# Governanca de Fornecedores\n\nConteudo real.")

    _patch_transport(monkeypatch, handler)

    source = HttpUrlDocumentSource(max_bytes=1_000_000)
    content = source.fetch("https://intranet.example.com/docs/governanca.md")

    assert content.text == "# Governanca de Fornecedores\n\nConteudo real."
    assert content.provider == "http_url"
    assert content.external_reference == "https://intranet.example.com/docs/governanca.md"
    assert content.source_name == "governanca.md"
    assert content.fetched_at is not None


def test_fetch_rejects_response_over_the_size_limit(monkeypatch):
    def handler(request):
        return httpx.Response(200, text="x" * 100)

    _patch_transport(monkeypatch, handler)

    source = HttpUrlDocumentSource(max_bytes=10)
    with pytest.raises(ExternalSourceFetchError, match="exceeds the maximum size"):
        source.fetch("https://example.com/big.md")


def test_fetch_rejects_non_utf8_content(monkeypatch):
    def handler(request):
        return httpx.Response(200, content=b"\xff\xfe\x00\x01")

    _patch_transport(monkeypatch, handler)

    source = HttpUrlDocumentSource(max_bytes=1_000_000)
    with pytest.raises(ExternalSourceFetchError, match="not UTF-8 text"):
        source.fetch("https://example.com/binary.bin")


def test_fetch_rejects_empty_content(monkeypatch):
    def handler(request):
        return httpx.Response(200, text="   ")

    _patch_transport(monkeypatch, handler)

    source = HttpUrlDocumentSource(max_bytes=1_000_000)
    with pytest.raises(ExternalSourceFetchError, match="is empty"):
        source.fetch("https://example.com/empty.md")


def test_fetch_wraps_http_error_status(monkeypatch):
    def handler(request):
        return httpx.Response(404)

    _patch_transport(monkeypatch, handler)

    source = HttpUrlDocumentSource(max_bytes=1_000_000)
    with pytest.raises(ExternalSourceFetchError, match="Failed to fetch"):
        source.fetch("https://example.com/missing.md")
