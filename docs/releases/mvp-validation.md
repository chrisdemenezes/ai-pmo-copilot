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

## Evidence Entry 006 - Orphan code stubs removed (TASK-KN-01/TASK-AI-02)

- Source PR: #17 - chore: remove orphan code stubs (TASK-KN-01/TASK-AI-02)
- Merge commit SHA: `193519057842f078bc2926c2aaa3081b74f3ebae`
- Scope evidenced:
  - Removed `src/knowledge/ingestion_pipeline.py`, `knowledge/retrieval_service.py`, and `src/agents/core/agent.py` — confirmed zero references anywhere in the repository (application code or tests) before deletion.
  - Decision recorded in `docs/development/01-project-structure.md`, section "TASK-KN-01 / TASK-AI-02 Decision: orphan stubs removed".
  - This closes Sprint 1 ("Fechar a porta") of the Master Product Backlog: US-SEC-01, US-SEC-02, and this decision are all merged.
- Test evidence: 57/57 tests passing (unchanged), 98.86% coverage (unchanged — none of the removed files had real test coverage), `ruff check src tests` clean.
- CI evidence: verified against the real GitHub Actions run before merge — run [29091266054](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29091266054), all green.

## Evidence Entry 007 - Per-API-key rate limiting (US-SEC-03)

- Source PR: #19 - feat: add per-API-key rate limiting (US-SEC-03)
- Merge commit SHA: `a3e6500a060696ad7f94a5cf2eda65156a719f76`
- Scope evidenced:
  - `src/api/rate_limiter.py::RateLimiter` (in-process sliding window, no external dependency) plus `build_rate_limiter()` singleton via `@lru_cache`, mirroring the `build_repository()` DI pattern.
  - `enforce_rate_limit` applied at the router level after `verify_api_key`; identifies callers by their already-validated `X-API-Key`. 429 on excess, configurable via `RATE_LIMIT_MAX_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS` (default 60/60s).
  - `tests/conftest.py` — autouse bypass extended to `enforce_rate_limit` so pre-existing tests don't share one bucket.
  - `tests/test_rate_limiter.py` (4 unit tests, injectable clock) and `tests/test_rate_limit_api.py` (2 integration tests — real 429, per-key isolation).
- Test evidence: 63/63 tests passing, 99.00% coverage (`rate_limiter.py` 100%), `ruff check src tests` clean.
- CI evidence: verified against the real GitHub Actions run before merge — run [29092947436](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29092947436), all green.
- Known limitation: rate limiting is per-process, in-memory — not shared across multiple API instances, resets on restart. Documented in `docs/technical/04-api-design.md#rate-limiting` as acceptable for the current single-instance deployment.

## Evidence Entry 008 - docker-compose repaired (TASK-INF-02)

- Source PR: #21 - fix: repair docker-compose (TASK-INF-02)
- Merge commit SHA: `a4846b531e022a705fb14334c1fabf7f2592cbd9`
- Scope evidenced:
  - New root `Dockerfile` builds the real `src.main:app` (copies only `src/`, `alembic.ini`, `alembic/`).
  - `docker-compose.yml`: `api` service (runs `alembic upgrade head` before `uvicorn` on start) + `database` (`postgres:16`, named volume). `frontend` service dropped — no code to build.
  - Removed `backend/Dockerfile` and `backend/requirements.txt` (unreferenced after the fix, described a module layout — `app.main:app` — that never existed). `backend/README.md` and vision docs untouched.
  - Decision recorded in `docs/development/01-project-structure.md`, section "TASK-INF-02 Decision".
- Test evidence: 63/63 tests passing (unchanged), 99.00% coverage (unchanged), `ruff check src tests` clean.
- CI evidence: verified against the real GitHub Actions run before merge — run [29093653987](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29093653987), all green.
- Validation method: `docker compose config` (no daemon required) — confirmed YAML syntax and env var interpolation, and caught a real bug before merge (`RATE_LIMIT_MAX_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS` resolving to empty strings when unset on the host, which would have crashed `int("")`/`float("")` on first request — fixed with real numeric defaults in the compose file).
- Known unverified path: this environment has no Docker daemon (`/var/run/docker.sock` missing), so `docker compose up` itself could not be exercised end-to-end here. Real execution against this file is still owed before calling the Docker path production-ready.

## Evidence Entry 009 - Request-correlated structured logging (US-OBS-01)

- Source PR: #23 - feat: add request-correlated structured logging (US-OBS-01)
- Merge commit SHA: `c9cd4328f834125bb8eabcaec085645c53390758`
- Scope evidenced:
  - `src/api/request_context.py`: `configure_logging()` attaches a `StreamHandler` to the root logger (previously no handler existed anywhere — module-level `logger.info(...)` calls in `src/agents/*`, `src/database/repository.py`, `src/api/security.py`, `src/api/rate_limiter.py` were silently dropped outside interactive/test runs). `RequestIDMiddleware` (raw ASGI, not `BaseHTTPMiddleware`) sets a `request_id` `ContextVar` per request and echoes it as the `X-Request-ID` response header. `RequestIDLogFilter` injects it into every log record — no existing call site needed to change.
  - Wired into `src/main.py`; `RequestIDMiddleware` added last so it wraps CORS too (verified empirically that the last-added middleware is outermost).
  - `tests/test_request_context.py` (new, 5 tests): filter unit tests + generated/echoed/distinct `X-Request-ID` header integration tests.
  - This closes Sprint 3 ("Operar com confiança") of the Master Product Backlog.
- Test evidence: 68/68 tests passing, 98.51% coverage (`request_context.py` 94% — the 2 uncovered lines are the non-HTTP ASGI passthrough branch), `ruff check src tests` clean.
- CI evidence: verified against the real GitHub Actions run before merge — run [29093969775](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29093969775), all green.

## Evidence Entry 010 - Project summary API (US-EXE-01)

- Source PR: #25 - feat: add project summary API (US-EXE-01)
- Merge commit SHA: `3bc8fbdbaaf270d285f44b587318a89839482ad7`
- Scope evidenced:
  - `src/services/project_summary_service.py::ProjectSummaryService` — first real file in `services/` (named in `CLAUDE.md`'s official architecture, previously empty). Aggregates `open_risks`, `pending_action_items`, `latest_health_status` from stored analyses, reading only through `AnalysisRepository`.
  - `GET /api/projects/{project_name}/summary` in `intelligence.py`; unknown/empty project returns 200 with zeros.
  - `src/database/repository.py::list_analyses` — `limit` now accepts `None`; default behavior for existing callers unchanged.
  - Bug found and fixed during this story's own tests: `list_analyses` ordering had no tiebreaker beyond `created_at`, so two records saved in the same instant had non-deterministic order — this silently affected the existing `GET /api/analyses` "newest first" listing too, not just the new service. Fixed with `id.desc()` as a secondary sort key.
  - `tests/test_project_summary_service.py` (6 unit tests, real `sqlite:///:memory:` repository) and `tests/test_project_summary_api.py` (2 integration tests).
- Test evidence: 75/75 tests passing, 98.67% coverage (`project_summary_service.py` 100%), `ruff check src tests` clean.
- CI evidence: verified against the real GitHub Actions run before merge — run [29094363129](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29094363129), all green.

## Evidence Entry 011 - Portfolio summary API (US-EXE-02)

- Source PR: #27 - feat: add portfolio summary API (US-EXE-02)
- Merge commit SHA: `5a10ea55f08434a5ec4da3476166c34f5ced12f9`
- Scope evidenced:
  - `ProjectSummaryService.summarize_portfolio()` — one fetch of every analysis, grouped by `project_name` in memory (no N+1 queries), reusing `summarize()`'s aggregation logic via a shared private `_aggregate()` method. Analyses with no `project_name` excluded.
  - `GET /api/portfolio/summary` in `intelligence.py`; sorted-by-name list, empty list when no analysis has a project name.
  - `tests/test_project_summary_service.py` (3 new tests) and `tests/test_project_summary_api.py` (2 new tests).
  - This closes Sprint 4 ("Primeiro valor executivo") and the Master Product Backlog roadmap through the Pilot Release milestone.
- Test evidence: 80/80 tests passing, 98.73% coverage (`project_summary_service.py` 100%), `ruff check src tests` clean.
- CI evidence: verified against the real GitHub Actions run before merge — run [29094664025](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29094664025), all green.

## Evidence Entry 012 - Real PostgreSQL validation (TASK-INF-01)

- No source PR — this is an environment-level validation, not a code change. No files in the
  repository were modified as part of this entry (`docs/technical/05-database-model.md` was updated
  separately to record the result).
- PostgreSQL 16 was found already installed in this session's environment (`postgresql-16` package,
  a provisioned but stopped cluster at `/var/lib/postgresql/16/main`) — the "no Postgres available"
  caveat carried since Evidence Entry 003 was an environment assumption that turned out to be wrong
  once actually checked, not a hard constraint of the sandbox.
- Started the cluster (`pg_ctlcluster 16 main start`), created a real `aipmo` role and `aipmo_test`
  database, and ran:
  - `alembic upgrade head` against `postgresql://aipmo:aipmo@localhost:5432/aipmo_test` — succeeded,
    `Context impl PostgresqlImpl`.
  - Schema inspected via `psql \d analysis_records` and `\di` — matches `AnalysisRecord` exactly:
    `id`, `kind`, `project_name`, `payload` (as `json`), `created_at` (`timestamp with time zone`),
    plus `analysis_records_pkey` and `ix_analysis_records_project_name` indexes.
  - The real app (`uvicorn src.main:app`) started against this database with
    `DATABASE_URL` pointed at it, `API_KEY` and `LLM_PROVIDER=mock` set, and was exercised over real
    HTTP: `GET /health`, `POST /api/meetings/analyze`, `GET /api/analyses`, `GET
    /api/projects/{name}/summary`, `GET /api/portfolio/summary`, and an unauthenticated request
    correctly returning 401. Every response was correct; `X-Request-ID` correlation appeared in the
    server logs for each request as designed (Evidence Entry 009).
  - Environment torn down afterward (`DROP DATABASE`, `DROP ROLE`, cluster stopped) — this was a
    verification run, not a persistent addition to the environment.
- This closes `TASK-INF-01` from the Master Product Backlog (Sprint 2, "Validar o que já existe").
  Docker Compose itself (`docker-compose.yml`, Evidence Entry 008) is still unverified end-to-end —
  this session's Docker daemon remains unavailable; the validation above ran directly against
  Postgres, not through `docker compose up`.

## Evidence Entry 013 - Real Anthropic API probe, partial (TASK-AI-01)

- No source PR — environment-level validation, no code changed.
- Ran one real `ProductionLLMProvider.generate()` call per agent (`meeting_intelligence`,
  `risk_review`, `project_status`), routed through the real `PromptRegistry` and each agent's real
  `analyze()` method — the exact code path the API uses, not a standalone SDK smoke test.
- Result: all three calls reached the real Anthropic API and authenticated successfully (not a 401),
  but were rejected with `400 invalid_request_error: Your credit balance is too low to access the
  Anthropic API` — the account backing the provided key has no billing/credit configured.
- What this **does** confirm: `ProductionLLMProvider` connects to the real API correctly, and the
  error-handling path (`ProviderUnavailableError` → 502, `src/main.py`'s exception handler) fires
  exactly as designed for a real upstream rejection — not a hypothetical, an actual one.
- What this does **not** confirm: the happy path — whether the model's real output reliably parses
  as `structured: true` under `parse_structured_output`. That remains open until a call succeeds.
- The API key used for this probe was pasted in plaintext in the requesting conversation; it was
  used only in-process for this one run (never written to any file, `.env`, or committed) and the
  user was advised to revoke and reissue it after this entry was recorded, per standard practice for
  any credential that has appeared in plaintext outside a secrets manager.
- `TASK-AI-01` remains open pending either billing being added to that account or a differently
  funded key.

## Evidence Entry 014 - Pilot Release readiness audit + MODEL_NAME fix

- Independent readiness audit performed at the user's request: fresh `git worktree` off
  `origin/main`, an isolated venv, `ruff check` and `pytest -q --cov=src --cov-fail-under=80` run
  from scratch (80/80, 98.73%, matching every locally-reported number in this file), the last 5
  `push`-event CI runs on `main` confirmed `completed`/`success` (not just PR checks), and all 30
  merged PRs (#2-#31) confirmed to have `merged_at` set — no abandoned or reverted PRs in the
  history. Full report published as an artifact; summarized here for the repo's own record.
- Finding from that audit: `.env.example` documented `MODEL_NAME` but nothing in `src/` read it —
  the model was fully hardcoded in `ProductionLLMProvider.model`.
- Source PR: #32 - fix: wire up MODEL_NAME env var (readiness audit finding)
- Merge commit SHA: `263c447bfcd6e014745effce3f79b34f362bf5f5`
- Scope evidenced: `get_provider()` (`src/llm/providers/factory.py`) now passes `MODEL_NAME` through
  to `ProductionLLMProvider`'s existing `model` field when set; falls back to the dataclass default
  when unset (no behavior change for existing deployments). `tests/test_provider_factory.py` gained
  2 tests (honors `MODEL_NAME` when set, uses the default when unset).
- Test evidence: 82/82 tests passing, 98.74% coverage (`factory.py` 100%), `ruff check src tests`
  clean.
- CI evidence: verified against the real GitHub Actions run before merge — run
  [29109796944](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29109796944), all
  green.
- Also confirmed still open, not addressed in this entry: the real Anthropic model ID's currency is
  unknown (Entry 013's probe failed on billing before reaching model resolution), and ~87
  documentation files across the repo (`docs/`, `release/`, and 11 top-level vision directories)
  remain unlabeled by implementation status — both are pre-existing, low-priority items, not new
  regressions.

## Evidence Entry 015 - FS-001 Dashboard Executivo (Release 0.2), T1-T9

- Branch: `claude/cleanup-orphaned-files-xtvwrj`. Source PR: #35 -
  [chrisdemenezes/ai-pmo-copilot#35](https://github.com/chrisdemenezes/ai-pmo-copilot/pull/35)
  against `main` — **not yet merged**; open pending Code Review, QA Review, Release Review and
  Retrospective per the AI-PEF gate sequence.
- Commits (chronological): `412fa6e` (T1 session gate, T2 BFF route, T3 data layer, T4-T7 widgets),
  `63957d3` (T8 dashboard states), `cd93d1d` (fix: cached data survives a failed background
  refetch), `9d77b59` (T9 E2E suite), `bd46fb3` (retry:false Product Behavior Decision), `a716dc3`
  (T10 docs), `2fcf329` (pre-PR wording/traceability adjustments).
- CI evidence: GitHub Actions run
  [29129935972](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/runs/29129935972) against
  head commit `2fcf329`, both jobs green — `validate` (backend, unaffected by this PR) and
  `frontend` (`tsc`, `eslint`, `npm test`, `npm run build`). Note: CI's `frontend` job does not run
  the Playwright E2E suite (`npm run test:e2e`) — that evidence is local-only, per the job
  definition in `.github/workflows/ci.yml`. `main` unchanged by this PR (no merge performed).
- Traceability of the process artifacts (FS-001 Revisão 5, TIP-001, UX Review): versioned in this
  repository rather than linked externally — the artifact-hosting URLs used during authoring are
  private by default and not a durable reference for a future engineer or auditor.
  `docs/product/fs-001/FS-001-feature-specification.html`,
  `docs/product/fs-001/TIP-001-implementation-plan.html`,
  `docs/product/fs-001/UX-REVIEW-FS001.html` — self-contained, open directly in a browser.
- Scope evidenced:
  - `web/proxy.ts`, `web/lib/session.ts` — Nível 1 workspace session (HMAC-signed cookie, single
    shared password, 12h TTL, emergency kill switch via `DISABLE_WORKSPACE_SESSION_GATE`)
  - `web/app/api/bff/dashboard/route.ts` — BFF proxy to `GET /api/portfolio/summary`, `X-API-Key`
    injected server-side only, 8s timeout, no detail leaked on error
  - `web/lib/hooks/use-portfolio-summary.ts` — TanStack Query, `staleTime: 30s`,
    `refetchInterval: 60s`, `retry: false` (Product Behavior Decision, see below)
  - `web/lib/dashboard/aggregate.ts` + 4 components — W1 Portfolio Summary Strip, W2 Project Health
    Grid, W3 Health Status Distribution, W5 Risk Concentration Ranking (W4 adiado by UX Review)
  - `web/app/dashboard/page.tsx` + `error.tsx` — loading/vazio/erro/parcial/sucesso states
- **Product Behavior Decision:** `retry: false` scoped to `usePortfolioSummary()` only, approved by
  the Product Owner from evidence produced by this entry's own E2E run — default retry (3 attempts,
  exponential backoff) measured at ~7.9s (backend down) / ~40.2s (backend timeout) before the error
  state appeared; after the change, ~0.7s / ~8.9s. Full analysis (current config, alternatives,
  UX/backend-load trade-offs) presented to the Product Owner before implementation, not applied
  unilaterally.
- Test evidence: 48/48 unit + component tests (`npm test`, 10 files), 33/33 E2E tests (`npm run
  test:e2e`, 11 scenarios × 3 breakpoints — mobile/md/lg per RFC-001), `npx tsc --noEmit` clean,
  `npx eslint .` clean, `npm run build` succeeds (`/dashboard`, `/entrar`, `/api/bff/dashboard`,
  `/api/bff/session` all compile; Proxy/Middleware compiles).
- E2E tests run against a standalone HTTP mock of the backend contract (`web/e2e/mock-backend.mjs`)
  mirroring the already-tested `GET /api/portfolio/summary` shape — no new product endpoint, `src/`
  untouched.
- CI evidence: not yet available — this entry will be updated with the GitHub Actions run link once
  the PR for this branch opens, per this repo's Governance Rule below.
- Known limitations, not new regressions: single shared workspace password (no per-user auth, no
  logout endpoint); `GET /api/portfolio/summary` has no backend pagination (FS-001 §17, Médio); no
  "atualizado há Xmin" staleness indicator (RFC-001, deferred by design); W4 Recent Analyses Feed
  not built (adiado to fast-follow by UX Review).

## Decision: remaining backlog deferred until MVP closure

AP-001, DB-001, and CP-001 are explicitly deferred, not scheduled. See
`docs/development/01-project-structure.md`, section "Decision: AP-001, DB-001, CP-001 deferred
until MVP closure", for the reasoning per item.

## Governance Rule

A feature may only be marked as ready when this file includes:

- commit SHA
- CI run link or workflow reference
- test output or execution log
