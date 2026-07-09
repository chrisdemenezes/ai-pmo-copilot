import hmac
import logging
import os

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        logger.error("API_KEY is not configured on the server")
        raise HTTPException(status_code=503, detail="API_KEY is not configured on the server")

    if not x_api_key or not hmac.compare_digest(x_api_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
