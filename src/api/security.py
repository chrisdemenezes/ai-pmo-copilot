import hmac
import logging
import os

from fastapi import Header, HTTPException
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        logger.error("API_KEY is not configured on the server")
        raise HTTPException(status_code=503, detail="API_KEY is not configured on the server")

    if not x_api_key or not hmac.compare_digest(x_api_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# W7-4 Security Hardening, Etapa 3 (F4 -- Founder Decision): safe default
# for the Controlled Pilot -- generous for real markdown/text documents
# (Knowledge Platform only ever accepts UTF-8 text, `src/api/routes/knowledge.py`),
# small enough to bound the memory risk of an unbounded upload. Same
# env-var-with-default pattern already used by RATE_LIMIT_MAX_REQUESTS/
# DB_POOL_SIZE elsewhere in this codebase -- an invalid (non-integer) value
# fails on first use with a plain, uncaught ValueError, exactly like those,
# never a new validation mechanism.
DEFAULT_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MiB


def max_upload_size_bytes() -> int:
    return int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(DEFAULT_MAX_UPLOAD_SIZE_BYTES)))


class MaxUploadSizeMiddleware:
    """W7-4 Security Hardening, Etapa 3 (F4 -- Founder Decision): rejects an
    oversized document upload from its declared `Content-Length` before
    Starlette's multipart parser ever reads the body -- the earliest point
    the current stack allows a request to be rejected (by the time a route
    function runs, the body has already been parsed into `UploadFile`).
    Scoped to exactly the one route that accepts a file
    (`POST /api/documents`) -- never applied globally, since no other
    route's payload carries a comparable risk, and this is not a general
    request-size policy.

    `Content-Length` measures the *entire* `multipart/form-data` request
    (boundary markers, per-part headers, the other form fields), never just
    the file's own bytes -- it is deliberately compared here against the
    limit plus a generous, fixed overhead allowance, never the limit alone,
    so a legitimately small file is never rejected because of multipart
    envelope overhead. It is also a client-declared value, not authoritative
    on its own (absent under chunked transfer-encoding, and not enforced to
    match the real body) -- `upload_document()` additionally performs a
    bounded read (`file.file.read(max_upload_size_bytes() + 1)`), which is
    what actually guarantees this application never materializes more than
    the configured limit in memory, regardless of what any header claims.
    This middleware is only the early, coarse rejection of egregiously
    oversized requests; the bounded read is the precise, authoritative one.
    """

    UPLOAD_PATH = "/api/documents"
    # Generous slack for multipart boundaries/headers/other form fields
    # (`source_name`, `project_id`) -- not exact, deliberately coarse; see
    # class docstring.
    _MULTIPART_OVERHEAD_ALLOWANCE_BYTES = 8192

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"] == self.UPLOAD_PATH
        ):
            declared_size = self._declared_content_length(scope)
            limit = max_upload_size_bytes()
            coarse_threshold = limit + self._MULTIPART_OVERHEAD_ALLOWANCE_BYTES
            if declared_size is not None and declared_size > coarse_threshold:
                logger.warning(
                    "Rejected upload before parsing: declared Content-Length=%d exceeds "
                    "limit=%d (+%d multipart overhead allowance)",
                    declared_size,
                    limit,
                    self._MULTIPART_OVERHEAD_ALLOWANCE_BYTES,
                )
                response = JSONResponse(
                    {"detail": f"File exceeds the maximum upload size of {limit} bytes."},
                    status_code=413,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)

    @staticmethod
    def _declared_content_length(scope) -> int | None:
        raw = Headers(scope=scope).get("content-length")
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            return None
