import logging
import os
import time
from collections import defaultdict
from functools import lru_cache
from threading import Lock
from typing import Callable

from fastapi import Depends, Header, HTTPException

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._time_func = time_func
        self._lock = Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, identifier: str) -> bool:
        now = self._time_func()
        window_start = now - self._window_seconds
        with self._lock:
            hits = [hit for hit in self._hits[identifier] if hit > window_start]
            if len(hits) >= self._max_requests:
                self._hits[identifier] = hits
                return False
            hits.append(now)
            self._hits[identifier] = hits
            return True


@lru_cache
def build_rate_limiter() -> RateLimiter:
    max_requests = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
    window_seconds = float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    return RateLimiter(max_requests=max_requests, window_seconds=window_seconds)


def enforce_rate_limit(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    limiter: RateLimiter = Depends(build_rate_limiter),
) -> None:
    identifier = x_api_key or "unknown"
    if not limiter.allow(identifier):
        logger.warning("Rate limit exceeded for identifier=%s", identifier)
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
