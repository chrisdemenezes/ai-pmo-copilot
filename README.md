# AI PMO Copilot

[![CI](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/workflows/ci.yml)

An intelligent PMO assistant designed to automate project governance, reporting, meeting intelligence and decision support using Artificial Intelligence.

**Status: STRATECH V2 — Wave 3 (Enterprise Intelligence) in progress.** Wave 2 (Enterprise
Foundation, RBAC, Portfolio/Program/Project domain, Enterprise Administration incl. User
Management) is fully closed (Decision Log D-038). PostgreSQL is the official database for local
development and production (see `docs/product/release-candidate/RC-2/Quick-Start.md`) — `make dev`
takes a fresh clone to a fully running platform in one command. Wave 3 opened with Architecture
Review AR-2 (`docs/architecture/AR-2-WAVE-3-ARCHITECTURE-REVIEW.md`); see
`docs/product/ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` for the full Wave/Epic plan and
`docs/product/stratech-v2/DECISION-LOG.md` for the current decision trail.
See `docs/product/STRATECH_V2_MASTER_ROADMAP.md` for current status across all Releases/Épicos/
Capabilities, and `docs/architecture/DOMAIN-MODEL.md` for the domain reference. The backend (`src/`)
is untouched by this V2 frontend domain work — no migration, no new provider/registry (see
`docs/governance/GOVERNANCE_MODEL.md` for the full Product-First governance flow).

The V1 RC-1 baseline artifacts below (Product Constitution, Architecture Gate, Visual Fidelity
Gate, Release Readiness Review, RC Approval Review, runbooks, ADRs, RFCs, gate history in
`docs/product/release-candidate/`) remain the historical record of the V1 closure and are kept for
traceability — they describe the platform's state before STRATECH V2 began, not its current scope.

The STRATECH Product Constitution (`docs/product/stratech-constitution/STRATECH-Product-Constitution.html`)
remains the V1 conceptual reference. Earlier release notes (Release 0.2/0.3, the prior
RC-1 for Executive Decision Experience, `docs/releases/RDR-0.2.md`,
`docs/releases/ADR-012-founder-decision-release-0.3.md`) predate the STRATECH V1 consolidation and
are kept for historical traceability only — they describe neither V1's final scope nor STRATECH
V2's current status.

## Architectural Decision

The official application tree is `src/`.

Legacy or parallel implementations must not be expanded. New code must be added only inside `src/` until the MVP baseline has passing CI evidence.

## Current Scope

### Backend (`src/`) — STRATECH V1 RC-1 baseline, unchanged by V2 so far

- FastAPI application entrypoint in `src/main.py`
- Intelligence router in `src/api/routes/intelligence.py`
- Project Status, Risk Review, and Meeting Intelligence agents
- Single prompt registry
- Production LLM provider using Anthropic via environment configuration (or `mock` for Demo Mode, no key required)
- SQLAlchemy persistence repository — PostgreSQL is official from RC-2 onward, SQLite kept only as a zero-dependency fallback default (`src/database/engine.py`)
- Enterprise Foundation schema (Organization/User/Role/Permission/Project, multi-tenant) — STRATECH V2 Épico 1-2
- CI workflow running lint, tests, and E2E (`.github/workflows/ci.yml`)

### Frontend (`web/`) — V1's 8 Capabilities + STRATECH V2 Release 0.2 additions

- The original 8 Capabilities — see the Product Constitution for the full list
- STRATECH V2 Executive Cockpit (Portfolio/Program situation, Program Execution, Executive Focus, Decision Center) and Mission Control (Founder governance panel)
- Portfolio, Program, and Project as a real DDD domain layer (`web/lib/domain/`) — see `docs/architecture/DOMAIN-MODEL.md`

## Repository Structure

```text
.github/workflows/ci.yml
Makefile
alembic.ini
alembic/
  env.py
  versions/
scripts/
  rc2-db.sh / rc2-db.ps1
  prepare-env.sh
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

## Run locally (full platform — backend + frontend, PostgreSQL)

```bash
git clone <this-repo-url> ai-pmo-copilot
cd ai-pmo-copilot
make dev
```

`make dev` alone runs the complete pipeline for a fresh clone — installs dependencies, provisions
PostgreSQL, applies migrations (schema + Enterprise Domain seed: Organizations, Roles, Portfolios,
Programs, Projects), then starts backend and frontend. Stop with `make stop`.

This is the single, authoritative path to run the whole platform locally — see
[`docs/product/release-candidate/RC-2/Quick-Start.md`](docs/product/release-candidate/RC-2/Quick-Start.md)
for the full walkthrough (PostgreSQL install per OS, environment variables, migrations, seed,
troubleshooting) and
[`docs/product/release-candidate/RC-2/Release-Validation-Checklist.md`](docs/product/release-candidate/RC-2/Release-Validation-Checklist.md)
for the formal homologation checklist. `docs/technical/03-development-environment.md` lists every
`make` target.

Windows: no native `make` — use WSL2, or run the underlying commands by hand after
`setup.bat`/`setup.ps1` (see the Quick Start above). The V1-era `scripts/rc1-local-start.sh` /
`start.bat` / `stop.bat` flow (SQLite, no Postgres/Docker) still works unchanged for a
zero-dependency quick look — see
[`docs/product/release-candidate/Local-Installation-Guide.html`](docs/product/release-candidate/Local-Installation-Guide.html).

### Backend only

If you're only working inside `src/` and don't need the frontend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://aipmo:aipmo@localhost:5432/aipmo"   # official from RC-2 onward
export LLM_PROVIDER=mock   # or ANTHROPIC_API_KEY=your-key for the real provider
export API_KEY="choose-a-local-secret"
alembic upgrade head
uvicorn src.main:app --reload
```

Leaving `DATABASE_URL` unset falls back to a local SQLite file with the schema auto-created (no
migration, no seed) — useful for a quick look, not a supported deployment target. See
`docs/technical/05-database-model.md` and `docs/technical/03-development-environment.md` for
details.

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
