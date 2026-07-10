# API Design

## Purpose
Define communication contracts between application components.

## Authentication

Every route under `/api/*` requires an `X-API-Key` header matching the `API_KEY` environment
variable (see `.env.example`). `/health` is exempt — it carries no application data and is used
for uptime checks. Enforced by `verify_api_key` (`src/api/security.py`), applied once at the
router level (`APIRouter(dependencies=[Depends(verify_api_key)])` in
`src/api/routes/intelligence.py`) rather than per-route.

| Status | Body | Cause |
|---|---|---|
| 503 | `{"detail": "API_KEY is not configured on the server"}` | The server has no `API_KEY` set — fails closed rather than accepting any caller |
| 401 | `{"detail": "Invalid or missing API key"}` | `X-API-Key` header missing or does not match the configured key |

## CORS

Cross-origin browser requests are controlled by `CORS_ALLOWED_ORIGINS` (comma-separated, see
`.env.example`). Unset means no origin is allowed — there is no wide-open default. Configured via
`CORSMiddleware` in `src/main.py`, restricted to `GET`/`POST` (the only methods any route uses) and
to the `Content-Type` and `X-API-Key` headers. Read once at process startup, not per request — a
new origin requires restarting the process with the updated env var.

## Rate Limiting

Every route under `/api/*` is limited per API key to `RATE_LIMIT_MAX_REQUESTS` requests per
`RATE_LIMIT_WINDOW_SECONDS` (see `.env.example`; defaults 60 requests / 60 seconds). Enforced by
`enforce_rate_limit` (`src/api/rate_limiter.py`), applied at the router level alongside
`verify_api_key` — auth runs first, so an invalid key never consumes another caller's quota.
Sliding window, in-process (no external store); resets if the process restarts. Not shared across
multiple app instances — acceptable for the current single-instance deployment, revisit if/when the
service is horizontally scaled.

| Status | Body | Cause |
|---|---|---|
| 429 | `{"detail": "Rate limit exceeded"}` | The caller's API key made more than `RATE_LIMIT_MAX_REQUESTS` requests within the current window |

## Core APIs

### Project Status API

POST /api/projects/analyze

Input: `{project_context, project_name}` (same shape as the Risk Analysis API).

Output: `{agent, project_name, model_output}` where `model_output` is one of:
- Structured (model followed the requested JSON schema): `{structured: true, health_status ("green"|"yellow"|"red"), key_findings[], recommendations[]}`
- Fallback (model response wasn't valid JSON): `{structured: false, raw_output}` — same fallback behavior as the other analysis APIs.

### Meeting Intelligence API

POST /api/meetings/analyze

Output: `{agent, project_name, model_output}` where `model_output` is one of:
- Structured (model followed the requested JSON schema): `{structured: true, summary, decisions[], action_items[] ({description, owner, due_date}), issues[], dependencies[]}`
- Fallback (model response wasn't valid JSON): `{structured: false, raw_output}` — the raw text is preserved, the request still returns 200, never fails just because parsing didn't succeed.

### Risk Analysis API

POST /api/risks/analyze

Output: `{agent, project_name, model_output}` where `model_output` is one of:
- Structured (model followed the requested JSON schema): `{structured: true, risks[] ({description, probability, impact, mitigation}), escalation_recommendation}`
- Fallback (model response wasn't valid JSON): `{structured: false, raw_output}` — same fallback behavior as the Meeting Intelligence API.

### List Analyses API

GET /api/analyses

Query params:
- `project_name` (optional) — filter by project
- `kind` (optional) — filter by `"meeting"`, `"risk"`, or `"status"`
- `created_from` / `created_to` (optional, ISO 8601 datetime) — filter by creation period, inclusive
- `limit` (default 20)
- `offset` (default 0)

All filters combine with AND when provided together.

Output: list of `{id, kind, project_name, created_at}`, newest first. Empty list (200) when no analyses match — never 404.

Note: `DATABASE_URL=sqlite:///:memory:` is not safe for the running app under FastAPI's threaded request handling — each worker thread gets its own separate in-memory database, so writes from one request may not be visible to another. Use the default file-based SQLite (or Postgres) for anything beyond single-threaded repository unit tests.

### Get Analysis by ID API

GET /api/analyses/{id}

Output: `{id, kind, project_name, created_at, payload}` — the full stored analysis, including the
complete agent result (`payload`), unlike the summary returned by `GET /api/analyses`.

404 (`{"detail": "Analysis not found"}`) when no analysis exists with that id.

### Project Summary API

GET /api/projects/{project_name}/summary

Aggregates every stored analysis for a project into executive-level counts, so a PMO Manager
doesn't have to read individual analyses. Built by `ProjectSummaryService`
(`src/services/project_summary_service.py`), which only reads `AnalysisRepository` — no new
provider or registry.

Output: `{project_name, total_analyses, open_risks, pending_action_items, latest_health_status}`
where:
- `total_analyses` — count of all analyses for the project, structured or fallback.
- `open_risks` — sum of `risks[]` length across every `risk` analysis with `structured: true`.
- `pending_action_items` — sum of `action_items[]` length across every `meeting` analysis with `structured: true`.
- `latest_health_status` — `health_status` from the most recent `status` analysis with `structured: true`, or `null` if none exists.

Fallback analyses (`structured: false`) are counted in `total_analyses` but contribute nothing to
the other three fields — there's no reliable `risks[]`/`action_items[]`/`health_status` to read from
raw model output that didn't follow the requested schema.

A project with no analyses (or an unknown name) returns 200 with all counts at zero — same
never-404 philosophy as `GET /api/analyses`.

## Error Responses

Applies to `/api/meetings/analyze`, `/api/risks/analyze`, and `/api/projects/analyze`.

| Status | Body | Cause |
|---|---|---|
| 422 | FastAPI validation error | Request body fails schema validation: `transcript`/`project_context` shorter than 10 chars, longer than 20000 chars, or containing only whitespace |
| 503 | `{"error": "provider_config_error", "detail": "..."}` | LLM provider is missing required configuration (e.g. `ANTHROPIC_API_KEY` unset, or `LLM_PROVIDER` set to an unknown value) |
| 502 | `{"error": "provider_unavailable", "detail": "..."}` | The LLM provider's upstream call failed (timeout, rate limit, connection error) |

## Local Development Provider

Set `LLM_PROVIDER=mock` (see `.env.example`) to use `MockLLMProvider` instead of calling the real Anthropic API. Useful for local development and manual smoke testing without consuming API credits.
