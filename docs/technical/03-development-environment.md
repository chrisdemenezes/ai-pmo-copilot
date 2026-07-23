# Development Environment

## Required components

- Git
- Node.js 22+
- Python 3.11+
- PostgreSQL 16+ (the official database from RC-2 onward — see below)
- Docker (optional — an alternative to a local PostgreSQL install)

## Local Setup (single command)

```bash
git clone <this-repo-url> ai-pmo-copilot
cd ai-pmo-copilot
make dev
```

`make dev` alone runs the complete, hands-off pipeline for a fresh clone:

```
setup (venv + pip install + npm install)
  -> db-create (idempotent: creates the aipmo role + database)
  -> migrate (alembic upgrade head -- schema + Enterprise Domain seed)
  -> backend (uvicorn, PostgreSQL)
  -> frontend (next dev)
```

No hidden steps: every stage above is also its own `make` target, so any part of the pipeline
can be run in isolation (see below). Stop everything with `make stop`.

Full walkthrough (prerequisites, PostgreSQL install per OS, environment variables,
troubleshooting): `docs/product/release-candidate/RC-2/Quick-Start.md`.

## Available `make` targets

| Target | What it does |
|---|---|
| `make setup` | Python venv + `pip install -r requirements.txt`, `npm install` in `web/` |
| `make db-create` | Idempotent: creates the `aipmo` role + `aipmo` database if missing |
| `make migrate` | `alembic upgrade head` — schema + Enterprise Domain seed (Organizations, Roles, Portfolios, Programs, Projects) |
| `make seed` | Alias for `make migrate` — the seed is embedded in the migrations, not a separate step |
| `make reset-db` | Drops and recreates the database, then re-runs migrations — full rebuild |
| `make dev` | The full pipeline above, then starts backend + frontend |
| `make stop` | Stops the backend/frontend processes started by `make dev` |
| `make health` | Curls `/health` on the running backend |
| `make test-backend` | `pytest` (245 tests, each against its own ephemeral Postgres database) |
| `make test-frontend` | `vitest run` (436 tests) |
| `make test-e2e` | `playwright test` (203 tests across 3 device projects — mocked backend, see below) |
| `make test` | `test-backend` + `test-frontend` |

Windows: no native `make`. Use WSL2 (recommended, gives you `make` directly), or run the
underlying commands by hand — `python -m alembic upgrade head`, `npm run test`,
`npx playwright test` — after `setup.bat`/`setup.ps1`. `scripts/rc2-db.ps1` provides the
PostgreSQL role/database creation for native PowerShell.

## Development Workflow

1. Clone repository
2. `make setup` — install backend + frontend dependencies
3. `make db-create` — provision PostgreSQL (or point `DATABASE_URL` at an existing instance)
4. `make migrate` — apply schema + Enterprise Domain seed
5. `make dev` (or run backend/frontend manually) — start the application
6. `make test` / `make test-e2e` — execute tests

## Database

PostgreSQL is the official database for local development and production. SQLite remains only as
the zero-argument fallback (`DATABASE_URL` unset), useful for a first look at the codebase without
installing Postgres, but it is not a supported deployment target and the automated test suite no
longer uses it (`tests/db.py` creates a real, ephemeral Postgres database per test).

Connection pooling (`src/database/engine.py`) is fully configurable via environment variables —
`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`, `DB_POOL_RECYCLE_SECONDS`,
`DB_POOL_PRE_PING` — see `.env.example`. None of these are hardcoded.

## Environment Separation

- Development — local Postgres via `make db-create`, or `docker compose up`
- Test — ephemeral, per-test Postgres databases (`tests/db.py`), dropped automatically
- Production — a managed/remote Postgres instance, `DATABASE_URL` pointed at it, `alembic upgrade
  head` run as part of deployment (see `docker-compose.yml`'s `api` service for the pattern)

## Configuration Management

Sensitive information (API keys, database credentials, session secrets) must be stored using
environment variables, never hardcoded — see `.env.example` for the full list and
`docs/product/release-candidate/RC-2/Quick-Start.md` for how each one is used.
