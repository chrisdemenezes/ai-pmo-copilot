# AI PMO Copilot

[![CI](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/workflows/ci.yml)

An intelligent PMO assistant designed to automate project governance, reporting, meeting intelligence and decision support using Artificial Intelligence.

**Status: STRATECH V1 RC-1 — Release Candidate. Feature Freeze: ACTIVE.** The V1 build is
officially closed — see `docs/product/release-candidate/Release-Candidate-Declaration.html` and
`docs/product/release-candidate/RC-1-Manifest.html` for the full gate history and official
composition of this Release Candidate. Only defect fixes, security hardening, documentation, and
observability changes are in scope during this phase — no new Capabilities, no architectural
changes, no UX changes, no new integrations, no functional expansion. Any future functional
proposal belongs exclusively in `docs/product/release-candidate/V2-Candidate-Backlog.html`, not in
this branch. Baseline artifacts (Product Constitution, Architecture Gate, Visual Fidelity Gate,
Release Readiness Review, RC Approval Review, runbooks, ADRs, RFCs) are locked under
`docs/product/release-candidate/Baseline-Configuration.html` — see that document for the formal
version-control rule governing any change to them.

The STRATECH Product Constitution (`docs/product/stratech-constitution/STRATECH-Product-Constitution.html`)
is the platform's single conceptual reference. Earlier release notes (Release 0.2/0.3, the prior
RC-1 for Executive Decision Experience, `docs/releases/RDR-0.2.md`,
`docs/releases/ADR-012-founder-decision-release-0.3.md`) predate the STRATECH V1 consolidation and
are kept for historical traceability only — they no longer describe the platform's current scope
or status.

## Architectural Decision

The official application tree is `src/`.

Legacy or parallel implementations must not be expanded. New code must be added only inside `src/` until the MVP baseline has passing CI evidence.

## Current Scope (STRATECH V1 RC-1)

- FastAPI application entrypoint in `src/main.py`
- Intelligence router in `src/api/routes/intelligence.py`
- Project Status, Risk Review, and Meeting Intelligence agents
- Single prompt registry
- Production LLM provider using Anthropic via environment configuration (or `mock` for Demo Mode, no key required)
- SQLAlchemy persistence repository (SQLite locally, Postgres in production)
- 8 Capabilities on the frontend (`web/`) — see the Product Constitution for the full list
- CI workflow running lint, tests, and E2E (`.github/workflows/ci.yml`)

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

## Run locally (full platform — backend + frontend)

```bash
git clone <this-repo-url> ai-pmo-copilot
cd ai-pmo-copilot
bash scripts/rc1-local-start.sh   # macOS/Linux — one command, no prior setup needed
```

Windows: `setup.bat` once, then `start.bat` (PowerShell equivalents: `setup.ps1` / `start.ps1`).
Stop with `demo/stop-demo.sh` (macOS/Linux) or `stop.bat` (Windows).

This is the single, authoritative path to run the whole platform locally — see
[`docs/product/release-candidate/Local-Installation-Guide.html`](docs/product/release-candidate/Local-Installation-Guide.html)
for the full walkthrough (prerequisites, environment variables, database, troubleshooting) and
[`docs/product/release-candidate/Founder-Quick-Start.html`](docs/product/release-candidate/Founder-Quick-Start.html)
for a one-page version. Validated against a genuinely clean install — see
`docs/product/release-candidate/Installation-Report.html`.

### Backend only

If you're only working inside `src/` and don't need the frontend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export LLM_PROVIDER=mock   # or ANTHROPIC_API_KEY=your-key for the real provider
export API_KEY="choose-a-local-secret"
uvicorn src.main:app --reload
```

By default this uses a local SQLite file with the schema auto-created — no migration needed. To
run against a real Postgres database with a proper migration history instead:

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
curl -G -H "X-API-Key: $API_KEY" http://localhost:8000/api/projects/summary --data-urlencode "project_name=Multilift"
```

Portfolio summary (the same aggregation for every project in one call — see
`docs/technical/04-api-design.md#portfolio-summary-api`):

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/portfolio/summary
```

## Governance Rule

No release or validation document may state that a feature is validated unless it links to the commit and CI/test evidence that supports the claim.
