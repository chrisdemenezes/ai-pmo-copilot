from src.api.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allows_requests_up_to_max():
    clock = FakeClock()
    limiter = RateLimiter(max_requests=3, window_seconds=60, time_func=clock)

    assert limiter.allow("key-a") is True
    assert limiter.allow("key-a") is True
    assert limiter.allow("key-a") is True


def test_blocks_requests_over_max_within_window():
    clock = FakeClock()
    limiter = RateLimiter(max_requests=2, window_seconds=60, time_func=clock)

    assert limiter.allow("key-a") is True
    assert limiter.allow("key-a") is True
    assert limiter.allow("key-a") is False


def test_allows_again_after_window_expires():
    clock = FakeClock()
    limiter = RateLimiter(max_requests=1, window_seconds=60, time_func=clock)

    assert limiter.allow("key-a") is True
    assert limiter.allow("key-a") is False

    clock.advance(61)

    assert limiter.allow("key-a") is True


def test_tracks_identifiers_independently():
    clock = FakeClock()
    limiter = RateLimiter(max_requests=1, window_seconds=60, time_func=clock)

    assert limiter.allow("key-a") is True
    assert limiter.allow("key-a") is False
    assert limiter.allow("key-b") is True
