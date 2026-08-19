"""Unit tests for `LoginBruteForceGuard` (W7-4 Etapa 1, F1 -- Founder
Decision). Deterministic (`FakeClock`, no real sleep) -- covers mandate
letters B, C, D, E, F, H, I, K at the guard level; G/J/A are proven at the
HTTP level in `tests/test_login_brute_force_api.py`.
"""
import pytest

from src.api.rate_limiter import LoginBruteForceGuard, LoginLockedError


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _guard(max_attempts=3, window_seconds=60, lockout_seconds=60, clock=None):
    clock = clock or FakeClock()
    return LoginBruteForceGuard(
        max_attempts=max_attempts,
        window_seconds=window_seconds,
        lockout_seconds=lockout_seconds,
        time_func=clock,
    ), clock


class TestCheckAllowsUnknownOrUnlockedIdentity:
    def test_never_seen_identity_is_not_locked(self) -> None:
        guard, _ = _guard()
        guard.check("org-a:user@example.com")  # must not raise


class TestThresholdAndLockout:
    def test_failures_below_threshold_do_not_lock(self) -> None:
        guard, _ = _guard(max_attempts=3)
        guard.record_failure("org-a:user@example.com")
        guard.record_failure("org-a:user@example.com")
        guard.check("org-a:user@example.com")  # 2 failures, threshold 3 -- must not raise

    def test_failures_at_threshold_lock_the_identity(self) -> None:
        guard, _ = _guard(max_attempts=3)
        for _ in range(3):
            guard.record_failure("org-a:user@example.com")
        with pytest.raises(LoginLockedError):
            guard.check("org-a:user@example.com")

    def test_attempt_above_threshold_stays_locked(self) -> None:
        guard, _ = _guard(max_attempts=2)
        guard.record_failure("org-a:user@example.com")
        guard.record_failure("org-a:user@example.com")
        with pytest.raises(LoginLockedError):
            guard.check("org-a:user@example.com")
        # A further failure while already locked must not raise on its own
        # (record_failure never raises) and the identity remains locked.
        guard.record_failure("org-a:user@example.com")
        with pytest.raises(LoginLockedError):
            guard.check("org-a:user@example.com")


class TestExpiration:
    def test_lockout_expires_and_restores_login_possibility(self) -> None:
        clock = FakeClock()
        guard, _ = _guard(max_attempts=2, window_seconds=60, lockout_seconds=60, clock=clock)
        guard.record_failure("org-a:user@example.com")
        guard.record_failure("org-a:user@example.com")
        with pytest.raises(LoginLockedError):
            guard.check("org-a:user@example.com")

        clock.advance(61)

        guard.check("org-a:user@example.com")  # must not raise -- lockout window elapsed

    def test_failure_window_alone_expires_without_reaching_threshold(self) -> None:
        clock = FakeClock()
        guard, _ = _guard(max_attempts=3, window_seconds=60, lockout_seconds=60, clock=clock)
        guard.record_failure("org-a:user@example.com")
        clock.advance(61)
        guard.record_failure("org-a:user@example.com")
        guard.record_failure("org-a:user@example.com")
        # Only 2 failures inside the current window (the first expired) --
        # must not be locked yet.
        guard.check("org-a:user@example.com")


class TestSuccessResetsOnlyItsOwnIdentity:
    def test_success_clears_failure_history(self) -> None:
        guard, _ = _guard(max_attempts=3)
        guard.record_failure("org-a:user@example.com")
        guard.record_failure("org-a:user@example.com")
        guard.record_success("org-a:user@example.com")
        guard.record_failure("org-a:user@example.com")
        guard.record_failure("org-a:user@example.com")
        # 2 failures post-reset, threshold 3 -- must not be locked.
        guard.check("org-a:user@example.com")


class TestIdentityIsolation:
    def test_different_organizations_do_not_contaminate_each_other(self) -> None:
        guard, _ = _guard(max_attempts=2)
        for _ in range(2):
            guard.record_failure("org-a:user@example.com")
        with pytest.raises(LoginLockedError):
            guard.check("org-a:user@example.com")
        guard.check("org-b:user@example.com")  # same email, different org -- must not raise

    def test_different_users_do_not_contaminate_each_other(self) -> None:
        guard, _ = _guard(max_attempts=2)
        for _ in range(2):
            guard.record_failure("org-a:alice@example.com")
        with pytest.raises(LoginLockedError):
            guard.check("org-a:alice@example.com")
        guard.check("org-a:bob@example.com")  # different user, same org -- must not raise
