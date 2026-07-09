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

## AI Development Guidelines

- Maintain prompt versioning
- Document agent behavior
- Validate AI outputs
- Keep humans in decision loops
