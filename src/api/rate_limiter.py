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


class LoginLockedError(Exception):
    """Raised when a login identity (organization + email) has exceeded
    the attempt threshold and is still within its lockout window."""


class LoginBruteForceGuard:
    """W7-4 Security Hardening, Etapa 1 (F1 -- Founder Decision): brute-force
    protection scoped to a single login identity (`organization_slug +
    normalized email`), never the whole organization -- deliberately a
    different key than `RateLimiter`/`enforce_rate_limit` above, which is
    keyed by the shared `X-API-Key` and would otherwise let a brute-force
    attempt against one user exhaust the budget for every real user behind
    the same BFF. A nonexistent identity accumulates and locks out exactly
    like a real one (the caller always records a "failure" on any
    `authenticate()` miss, regardless of cause), so a locked response never
    discloses whether the organization or the user exists.

    Process-local, in-memory, single-instance only -- proportional to the
    V1's current single-`api`-container deployment (`docker-compose.yml`).
    **Known limitation, not hidden:** in a future multi-instance deployment,
    each instance would track its own lockout state independently, weakening
    the effective threshold by a factor of the instance count. This is not
    presented as the Enterprise Production answer to brute-force (that would
    need a shared store, e.g. Redis, introduced only when horizontal scaling
    is actually adopted) -- it is the smallest mechanism sufficient for the
    Controlled Pilot's current, single-instance deployment.
    """

    def __init__(
        self,
        max_attempts: int,
        window_seconds: float,
        lockout_seconds: float,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._lockout_seconds = lockout_seconds
        self._time_func = time_func
        self._lock = Lock()
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._locked_until: dict[str, float] = {}

    def check(self, identity_key: str) -> None:
        """Raises `LoginLockedError` if `identity_key` is currently locked
        out. Call before attempting authentication."""
        now = self._time_func()
        with self._lock:
            locked_until = self._locked_until.get(identity_key)
            if locked_until is None:
                return
            if locked_until > now:
                raise LoginLockedError(identity_key)
            # Lockout window elapsed: clear it and the failure history that
            # triggered it, so the identity starts clean, not half-locked.
            del self._locked_until[identity_key]
            self._failures.pop(identity_key, None)

    def record_failure(self, identity_key: str) -> None:
        """Call after any failed authentication attempt (wrong password,
        nonexistent user/organization, inactive account -- every cause
        `AuthService.authenticate()` already treats uniformly)."""
        now = self._time_func()
        window_start = now - self._window_seconds
        with self._lock:
            hits = [hit for hit in self._failures[identity_key] if hit > window_start]
            hits.append(now)
            self._failures[identity_key] = hits
            if len(hits) >= self._max_attempts:
                self._locked_until[identity_key] = now + self._lockout_seconds

    def record_success(self, identity_key: str) -> None:
        """Call after a successful authentication -- clears any failure
        history and lockout for this identity, never for any other."""
        with self._lock:
            self._failures.pop(identity_key, None)
            self._locked_until.pop(identity_key, None)


@lru_cache
def build_login_brute_force_guard() -> LoginBruteForceGuard:
    # Controlled Pilot defaults (Founder Decision, W7-4 F1): 5 failed
    # attempts within a 15-minute window locks the identity out for 15
    # minutes. Not arbitrary -- proportional to a small, trusted pilot
    # population (few genuine retries expected; a real user mistyping a
    # password 5 times in 15 minutes is rare, an attacker sending 5 guesses
    # in 15 minutes is the threat this exists to slow down). Configurable so
    # an operator can tune without a code change, same pattern as
    # RATE_LIMIT_MAX_REQUESTS/RATE_LIMIT_WINDOW_SECONDS above.
    max_attempts = int(os.getenv("LOGIN_LOCKOUT_MAX_ATTEMPTS", "5"))
    window_seconds = float(os.getenv("LOGIN_LOCKOUT_WINDOW_SECONDS", "900"))
    lockout_seconds = float(os.getenv("LOGIN_LOCKOUT_DURATION_SECONDS", "900"))
    return LoginBruteForceGuard(
        max_attempts=max_attempts, window_seconds=window_seconds, lockout_seconds=lockout_seconds
    )
