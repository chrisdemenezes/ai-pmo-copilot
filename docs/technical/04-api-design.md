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

## Error Responses

Applies to `/api/meetings/analyze` and `/api/risks/analyze`.

| Status | Body | Cause |
|---|---|---|
| 422 | FastAPI validation error | Request body fails schema validation (e.g. `transcript` shorter than 10 chars) |
| 503 | `{"error": "provider_config_error", "detail": "..."}` | LLM provider is missing required configuration (e.g. `ANTHROPIC_API_KEY` unset, or `LLM_PROVIDER` set to an unknown value) |
| 502 | `{"error": "provider_unavailable", "detail": "..."}` | The LLM provider's upstream call failed (timeout, rate limit, connection error) |

## Local Development Provider

Set `LLM_PROVIDER=mock` (see `.env.example`) to use `MockLLMProvider` instead of calling the real Anthropic API. Useful for local development and manual smoke testing without consuming API credits.
