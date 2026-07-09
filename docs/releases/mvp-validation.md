# AI PMO Copilot MVP Evidence

This document is the release evidence ledger for MVP claims.

## Evidence Entry 001 - MVP architecture consolidation

- Source PR: #1 - fix: consolidate MVP architecture
- Merge commit SHA: `b5e46ca1b242bf19e544a6a98583bc4a09d4c629`
- Head commit before merge: `a8455d62a90245ccc27467b42c2ef64fc7dc0443`
- Scope evidenced:
  - `src/` defined as official implementation tree
  - FastAPI entrypoint added in `src/main.py`
  - Intelligence API router registered
  - Meeting Intelligence agent connected to prompt registry and model provider
  - Risk Review agent connected to prompt registry and model provider
  - SQLAlchemy repository added
  - CI workflow created for lint and tests
- CI evidence: GitHub Actions workflow `CI` available at `.github/workflows/ci.yml`. The run result must be verified in GitHub Actions before any production-ready claim.

## Evidence Entry 002 - Platform hardening and analysis query API

- Source PR: #3 - feat: platform hardening + analysis query API (Sprint 1 + US-D1/D2)
- Merge commit SHA: `d1335a20b735e4c4aa78b221a8da6b3202dd494b`
- Source PR: #4 - feat: filter analyses by kind and period (US-D3)
- Merge commit SHA: `f28397fd503c71b90ca5f4cef2bdeecad38ea80a`
- Scope evidenced:
  - Prompt templates migrated from `str.format()` to `string.Template.safe_substitute()`
  - Typed provider layer (`LLMProvider` protocol, config/unavailable errors, mock provider, factory via `LLM_PROVIDER`)
  - Global exception handlers (503/502 instead of unhandled 500)
  - Repository dependency cached as a singleton
  - `GET /api/analyses` (list, filterable by `project_name`, `kind`, `created_from`, `created_to`) and `GET /api/analyses/{id}`
- Test evidence: 32/32 tests passing (`pytest -q`), `ruff check src tests` clean, confirmed against real file-based SQLite via manual smoke tests (not only fakes/mocks).
- CI evidence: GitHub Actions workflow `CI` available at `.github/workflows/ci.yml`. The run result must be verified in GitHub Actions before any production-ready claim.

## Evidence Entry 003 - Structured outputs, third agent, coverage gate, Alembic

- Source PR: #5 - chore: retire issue_advisor agent (US-C2) — `dc10ddc19b51dbcea39c131ba3e8ac1016c9ef54`
- Source PR: #6 - feat: add advanced input validation (US-A2) — `13f28ed0779986f8d7d8b7cef1473f2893d63d26`
- Source PR: #7 - feat: structured output for meeting_intelligence (MI-002/003/004/006) — `6540568bd088b95031d5df294828dfea5e2bbaee`
- Source PR: #8 - feat: structured output for risk_review (RI-001) — `cf74690dd6bdda4250f67b99958f254b94432246`
- Source PR: #9 - feat: add Project Status agent (SR-001) — `70f297da7be6cb5755e7dcebe1f6e5565bc115f6`
- Source PR: #10 - chore: enforce 80% test coverage gate in CI — `a908d080aa2e83853f6371314af7f640fc1c02ec`
- Source PR: #11 - feat: add Alembic migrations for schema management — `3f1d273f46e00dafd4d1a6b5a4082db7f0ba7f9b`
- Scope evidenced:
  - `issue_advisor` removed (decision recorded in `docs/development/01-project-structure.md`)
  - `transcript`/`project_context` gain `max_length` and non-whitespace validation
  - Shared `src/agents/shared/output_parser.py` JSON-with-fallback parser, reused by all three agents (meeting_intelligence, risk_review, project_status)
  - New `ProjectStatusAgent` and `POST /api/projects/analyze`
  - `pytest-cov` with `--cov-fail-under=80` enforced in CI; real coverage 98%
  - Alembic migrations (`alembic/`, `alembic.ini`) as the schema evolution mechanism for real deployments, alongside `create_all()` for tests
- Test evidence: 49/49 tests passing (`pytest -q --cov=src --cov-fail-under=80`), `ruff check src tests` clean. Every PR in this entry was independently verified by checking out `origin/main` fresh (via `git worktree`) after merge and re-running the full suite and, where applicable, a manual end-to-end smoke test with `LLM_PROVIDER=mock` — not just trusted from local pre-merge state.
- Known unverified path: Alembic has only been exercised against SQLite in this environment; the Postgres/`psycopg2-binary` path has no live database to test against here (documented in `docs/technical/05-database-model.md`).
- CI evidence: GitHub Actions workflow `CI` available at `.github/workflows/ci.yml`. The run result must be verified in GitHub Actions before any production-ready claim.

## Evidence Entry 004 - API key authentication + CI pytest sys.path fix (US-SEC-01)

- Source PR: #13 - feat: require X-API-Key on all /api/* routes + fix CI pytest sys.path (US-SEC-01)
- Merge commit SHA: `87473809bac2f1d9825997fc54ab8b796f092472`
- Scope evidenced:
  - `src/api/security.py::verify_api_key` — router-level FastAPI dependency (`APIRouter(dependencies=[...])`) enforcing `X-API-Key` on every `/api/*` route; `hmac.compare_digest` for constant-time comparison; fails closed (503) when `API_KEY` is unset, 401 on missing/wrong key. `/health` stays unauthenticated.
  - `tests/conftest.py` (new) — autouse override so the 49 pre-existing tests needed no per-test edits.
  - `tests/test_api_security.py` (new, 5 tests) — 401/503/200/health-bypass coverage.
  - `pyproject.toml` (new) — `[tool.pytest.ini_options] pythonpath = ["."]`.
- Test evidence: 54/54 tests passing, 98.83% coverage, `ruff check src tests` clean.
- CI evidence: **verified directly against the GitHub Actions run, not just local execution** — run [29058080160](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29058080160) (PR branch, all green) and post-merge run [29058143393](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29058143393) on `main` (all green).

### Correction to Evidence Entries 001-003

While preparing this entry, the actual GitHub Actions run history was checked directly for the
first time this project (previous entries only ever confirmed test results by running `pytest`
*locally*, never by inspecting the Actions run itself). Every recorded CI run on `main` going back
through at least PR #7 had **conclusion: failure**, with `ModuleNotFoundError: No module named
'src'` — the CI step invokes the `pytest` console script directly, which does not add the repo
root to `sys.path`, while all local verification in this project used `python -m pytest` (which
does, via `-m`). The "CI evidence" lines in Entries 001-003 above were therefore aspirational, not
actually satisfied; the "must be verified in GitHub Actions before any production-ready claim"
caveat those entries already carried was accurate and had not yet been checked. The test *content*
of those entries is unaffected (the same 49 tests still pass once the import path is fixed by this
entry's `pyproject.toml`), but no prior entry should be read as having real CI confirmation before
this one.

## Evidence Entry 005 - Minimal CORS support (US-SEC-02)

- Source PR: #15 - feat: add minimal CORS support (US-SEC-02)
- Merge commit SHA: `0e318a63333ffd284590771a0c447c58a294c6c2`
- Scope evidenced:
  - `CORSMiddleware` (`fastapi.middleware.cors`, no new dependency) added in `src/main.py`, restricted to `GET`/`POST` and to the `Content-Type`/`X-API-Key` headers.
  - Allowed origins from `CORS_ALLOWED_ORIGINS` (comma-separated); unset means no origin is allowed — fail-closed, consistent with US-SEC-01.
  - `tests/test_cors.py` (new, 3 tests) — default-closed, allowed-origin, rejected-origin, via `importlib.reload(src.main)` since CORS config is read once at process startup.
- Test evidence: 57/57 tests passing, 98.86% coverage, `ruff check src tests` clean.
- CI evidence: verified against the real GitHub Actions run before merge — run [29058378473](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29058378473), all green.

## Decision: remaining backlog deferred until MVP closure

AP-001, DB-001, and CP-001 are explicitly deferred, not scheduled. See
`docs/development/01-project-structure.md`, section "Decision: AP-001, DB-001, CP-001 deferred
until MVP closure", for the reasoning per item.

## Governance Rule

A feature may only be marked as ready when this file includes:

- commit SHA
- CI run link or workflow reference
- test output or execution log
