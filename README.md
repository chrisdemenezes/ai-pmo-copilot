# AI PMO Copilot

[![CI](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/workflows/ci.yml)

An intelligent PMO assistant designed to automate project governance, reporting, meeting intelligence and decision support using Artificial Intelligence.

**Status: Release 0.3 – Planning.** Opened ahead of Validation Sprint completion by explicit Founder
decision — see `docs/releases/ADR-012-founder-decision-release-0.3.md`. Release 0.2 (Dashboard
Executivo) is merged and live; see `docs/releases/RDR-0.2.md`.

## Architectural Decision

The official application tree is `src/`.

Legacy or parallel implementations must not be expanded. New code must be added only inside `src/` until the MVP baseline has passing CI evidence.

## Current MVP Scope

- FastAPI application entrypoint in `src/main.py`
- Intelligence router in `src/api/routes/intelligence.py`
- Meeting Intelligence agent
- Project Status agent
- Single prompt registry
- Production LLM provider using Anthropic via environment configuration
- SQLAlchemy persistence repository
- CI workflow running lint and tests

## Repository Structure

```text
.github/workflows/ci.yml
alembic.ini
alembic/
  env.py
  versions/
src/
  main.py
  api/routes/intelligence.py
  agents/meeting_intelligence/
  agents/project_status/
  database/repository.py
  llm/providers/production_provider.py
  prompts/registry.py
web/
  app/
  components/ui/
tests/
docs/
release/
```

Backend (`src/`) and frontend (`web/`) are two separate applications with independent dependency
trees — see `web/README.md` for frontend setup and RFC-001 (referenced in
`docs/development/01-project-structure.md`) for its architecture.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key"
export API_KEY="choose-a-local-secret"
uvicorn src.main:app --reload
```

To develop without calling the real Anthropic API (no API key or cost required), set
`LLM_PROVIDER=mock` instead of `ANTHROPIC_API_KEY` — see `.env.example`.

By default the app uses a local SQLite file with the schema auto-created. To run against a real
Postgres database with a proper migration history instead:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/ai_pmo_copilot"
alembic upgrade head
```

See `docs/technical/05-database-model.md` for details on when to use Alembic vs. auto-created
tables.

## Run with Docker Compose

Runs the API (built from the root `Dockerfile`) against a real Postgres, migrated via `alembic
upgrade head` on container start:

```bash
export API_KEY="choose-a-local-secret"
docker compose up --build
```

Set `ANTHROPIC_API_KEY` in the environment first if you want `LLM_PROVIDER=anthropic` instead of
the `mock` default. See `docker-compose.yml` for the full list of env vars passed through.

Health check:

```bash
curl http://localhost:8000/health
```

Meeting analysis (every `/api/*` route requires the `X-API-Key` header — see
`docs/technical/04-api-design.md#authentication`):

```bash
curl -X POST http://localhost:8000/api/meetings/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"project_name":"Multilift","transcript":"Client approved the handover and requested action tracking."}'
```

Project summary (aggregated counts across every stored analysis for a project — see
`docs/technical/04-api-design.md#project-summary-api`):

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/projects/Multilift/summary
```

Portfolio summary (the same aggregation for every project in one call — see
`docs/technical/04-api-design.md#portfolio-summary-api`):

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/portfolio/summary
```

## Governance Rule

No release or validation document may state that a feature is validated unless it links to the commit and CI/test evidence that supports the claim.
