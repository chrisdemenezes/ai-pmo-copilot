"""External Document Sources -- STRATECH V1 Product & Capability Completion
(Founder Mandate), Fase 4 (Package L).

Architectural foundation for feeding a Document into the Enterprise
Knowledge Platform from an external system, without coupling
`DocumentIngestionService` to any one provider -- same seam
`EmbeddingProvider` (`embedding_provider.py`) already established: a
`Protocol`, one concrete adapter proven end to end here, any future
SaaS-specific adapter (SharePoint/Google Drive/Confluence) a separate,
not-yet-implemented one requiring a real credential this environment does
not have (REAL PROVIDER VALIDATION = PENDING EXTERNAL CREDENTIAL).

This module never imports from `src.api`, `src.agents`, or
`AdvisorFramework` -- fetching an external document is a Knowledge
Platform concern only, the same boundary `DocumentIngestionService`'s own
docstring already states. Fetching (this module) is a step strictly
before ingestion (`DocumentIngestionService.upload()`) -- no
`Document`/`DocumentVersion` row exists yet when `fetch()` runs, so a
fetch failure here carries no partial state to report, unlike
`DocumentIndexingError`.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class ExternalSourceFetchError(Exception):
    """Raised when fetching a reference from an external source fails --
    network error, oversized response, non-UTF-8 content, or an empty
    body. Never partially applied: no Document/DocumentVersion exists yet
    when this is raised."""


@dataclass(frozen=True)
class ExternalDocumentContent:
    """What every ExternalDocumentSource must produce -- exactly the shape
    `DocumentIngestionService.upload()` already accepts (source_name,
    text), plus provenance recorded only in the existing audit trail
    (`record_audit`'s metadata dict), never a new column on
    Document/DocumentVersion."""

    source_name: str
    text: str
    provider: str
    external_reference: str
    fetched_at: datetime


class ExternalDocumentSource(Protocol):
    provider: str

    def fetch(self, reference: str) -> ExternalDocumentContent: ...


class HttpUrlDocumentSource:
    """First adapter (Founder Mandate, Package L): fetches a UTF-8
    text/markdown document from any URL -- no vendor lock-in, no
    credential required, real over-the-wire I/O (never synthetic),
    provenance = the URL itself. Streams and aborts past `max_bytes`, the
    same bounded-read discipline `POST /api/documents` already applies to
    a file upload (W7-4 Security Hardening) -- the caller injects the same
    `max_upload_size_bytes()` limit, no new limit invented."""

    provider = "http_url"

    def __init__(self, max_bytes: int, timeout_seconds: float = 10.0):
        self._max_bytes = max_bytes
        self._timeout_seconds = timeout_seconds

    def fetch(self, reference: str) -> ExternalDocumentContent:
        try:
            with httpx.stream(
                "GET", reference, timeout=self._timeout_seconds, follow_redirects=True
            ) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > self._max_bytes:
                        raise ExternalSourceFetchError(
                            f"Response from {reference} exceeds the maximum size of "
                            f"{self._max_bytes} bytes."
                        )
        except httpx.HTTPError as exc:
            raise ExternalSourceFetchError(f"Failed to fetch {reference}: {exc}") from exc

        try:
            text = bytes(raw).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExternalSourceFetchError(f"Content at {reference} is not UTF-8 text") from exc
        if not text.strip():
            raise ExternalSourceFetchError(f"Content at {reference} is empty")

        source_name = reference.rsplit("/", 1)[-1] or reference
        return ExternalDocumentContent(
            source_name=source_name,
            text=text,
            provider=self.provider,
            external_reference=reference,
            fetched_at=datetime.now(timezone.utc),
        )
