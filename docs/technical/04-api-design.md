# API Design

## Purpose
Define communication contracts between application components.

## Core APIs

### Project Analysis API

POST /api/projects/analyze

Input:
- Project data
- Documents
- Context

Output:
- Analysis
- Recommendations

### Meeting Intelligence API

POST /api/meetings/process

Output:
- Summary
- Decisions
- Actions

### Risk Analysis API

POST /api/risks/analyze

Output:
- Risk assessment
- Mitigation plan

### List Analyses API

GET /api/analyses

Query params:
- `project_name` (optional) — filter by project
- `limit` (default 20)
- `offset` (default 0)

Output: list of `{id, kind, project_name, created_at}`, newest first. Empty list (200) when no analyses match — never 404.

Note: `DATABASE_URL=sqlite:///:memory:` is not safe for the running app under FastAPI's threaded request handling — each worker thread gets its own separate in-memory database, so writes from one request may not be visible to another. Use the default file-based SQLite (or Postgres) for anything beyond single-threaded repository unit tests.

### Get Analysis by ID API

GET /api/analyses/{id}

Output: `{id, kind, project_name, created_at, payload}` — the full stored analysis, including the
complete agent result (`payload`), unlike the summary returned by `GET /api/analyses`.

404 (`{"detail": "Analysis not found"}`) when no analysis exists with that id.

## Error Responses

Applies to `/api/meetings/analyze` and `/api/risks/analyze`.

| Status | Body | Cause |
|---|---|---|
| 422 | FastAPI validation error | Request body fails schema validation (e.g. `transcript` shorter than 10 chars) |
| 503 | `{"error": "provider_config_error", "detail": "..."}` | LLM provider is missing required configuration (e.g. `ANTHROPIC_API_KEY` unset, or `LLM_PROVIDER` set to an unknown value) |
| 502 | `{"error": "provider_unavailable", "detail": "..."}` | The LLM provider's upstream call failed (timeout, rate limit, connection error) |

## Local Development Provider

Set `LLM_PROVIDER=mock` (see `.env.example`) to use `MockLLMProvider` instead of calling the real Anthropic API. Useful for local development and manual smoke testing without consuming API credits.
