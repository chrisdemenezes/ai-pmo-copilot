# Development Guidelines

## Principles

- Clean architecture
- Automated testing
- Documentation-first approach
- Secure coding practices

## Code Quality

- Version control through Git
- Pull request review
- Automated validation
- Minimum test coverage: 80% (`pytest --cov=src --cov-fail-under=80` in CI, `.github/workflows/ci.yml`).
  As of this gate's introduction, real coverage is 97% — the threshold has headroom, it is not
  a stretch target.

## Observability

- Logging is configured once at startup by `configure_logging()` (`src/api/request_context.py`) —
  before this, module-level `logger.info(...)` calls across the codebase had no handler attached
  and were silently dropped outside of interactive/test runs.
- Every HTTP request gets a `request_id` (from the incoming `X-Request-ID` header, or a generated
  UUID if absent), set on a `contextvars.ContextVar` by `RequestIDMiddleware` and echoed back as the
  `X-Request-ID` response header. A `logging.Filter` injects the current value into every log record
  so `%(request_id)s` in the log format correlates every line emitted while handling one request —
  no per-call-site changes needed in `src/agents/*`, `src/database/repository.py`, etc.
- To correlate a user-reported issue with server logs, ask for (or read from the response) the
  `X-Request-ID` value and grep for it.

## AI Development Guidelines

- Maintain prompt versioning
- Document agent behavior
- Validate AI outputs
- Keep humans in decision loops
