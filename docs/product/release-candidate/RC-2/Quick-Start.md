# STRATECH Wave 2 RC-2 — Quick Start

PostgreSQL is the official database from RC-2 onward. This guide takes a fresh clone to a fully
running local environment (backend + frontend + Playwright) with no hidden steps.

```
Clone -> Install -> PostgreSQL -> Migration -> Seed -> Backend -> Frontend -> Homologação
```

## 1. Prerequisites

- Git
- Python 3.11+
- Node.js 22+
- PostgreSQL 16+ — pick one:
  - **Native install**: `apt install postgresql` (Linux), `brew install postgresql@16` (Mac), or
    the [official Windows installer](https://www.postgresql.org/download/windows/).
  - **Docker**: no local install needed — `docker compose up` (see §6) runs Postgres for you.

## 2. Clone and run

```bash
git clone <this-repo-url> ai-pmo-copilot
cd ai-pmo-copilot
make dev
```

That single command:
1. `make setup` — creates `.venv`, installs backend deps (`requirements.txt`) and frontend deps
   (`web/node_modules`).
2. `make db-create` — idempotently creates the `aipmo` Postgres role + `aipmo` database.
3. `make migrate` — runs `alembic upgrade head`: creates the full schema (Organizations, Users,
   Roles, Permissions, Portfolios, Programs, Projects, Audit Log) and seeds it (migrations 0002 +
   0008) with two coherent organizations — "Organização Principal" and "Demo Organization" — each
   with its own Portfolios/Programs/Projects hierarchy.
4. Starts the backend (`uvicorn`, port 8000) and frontend (`next dev`, port 3000).

When it's ready you'll see:

```
Login:     http://localhost:3000/entrar  (password: demo-local-password)
Dashboard: http://localhost:3000/dashboard
Backend:   http://localhost:8000/health
```

Stop everything with `make stop`.

## 3. Database creation — platform notes

`make db-create` connects as a Postgres superuser to create the app role/database. How that
connection authenticates depends on your OS:

- **Native Linux install** (apt/dnf): the `postgres` OS account has peer-auth trust over the unix
  socket. `make db-create` detects this automatically and retries via `sudo -u postgres` if a
  plain connection fails — you may be prompted for your `sudo` password once.
- **Mac (Homebrew/Postgres.app) or the official Windows installer**: usually TCP + password auth.
  Set standard libpq env vars before running `make db-create` if your superuser isn't the
  passwordless default:
  ```bash
  export PGHOST=localhost PGPASSWORD=your-postgres-superuser-password
  make db-create
  ```
- **Docker Compose** (§6): skip `make db-create` entirely — the container creates
  `POSTGRES_DB`/`POSTGRES_USER` on first boot.
- **Managed/remote Postgres** (RDS, Cloud SQL, etc.): set `PG_SUPERUSER_URL` to an admin connection
  string for that instance, or skip `db-create` and create the role/database yourself, then point
  `DATABASE_URL` at it.

## 4. Environment variables

Copy `.env.example` to `.env` and fill in what you need (see the file for the full annotated
list). The variables that matter for this Quick Start:

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | Connection string | `sqlite:///./ai_pmo_copilot.db` (fallback only — set this to Postgres) |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_TIMEOUT_SECONDS` / `DB_POOL_RECYCLE_SECONDS` / `DB_POOL_PRE_PING` | Connection pool tuning (Postgres only) | `5` / `10` / `30` / `1800` / `true` |
| `API_KEY` | Server-to-server key every `/api/*` route requires | none — unset means every protected route 503s |
| `LLM_PROVIDER` | `mock` (no external credential) or `anthropic` | `mock` |

`make dev` uses `demo/.env` (auto-created from `demo/.env.example` on first run, with a generated
`SESSION_SECRET`) for the frontend/session side, and the `DATABASE_URL` you export (or the
Makefile default `postgresql://aipmo:aipmo@localhost:5432/aipmo`) for the database.

## 5. Migrations and seed

```bash
make migrate   # alembic upgrade head
make seed      # alias for migrate -- the seed IS the migrations, not a separate mechanism
make reset-db  # full rebuild: drop, recreate, re-migrate
```

The seed (migrations `0002` and `0008`) is idempotent — running `make migrate` again never
duplicates rows. It produces, per organization:

- 3 Portfolios, 4 Programs, 7 Projects (6 Portfolios / 8 Programs / 14 Projects total across both
  organizations)
- The 4 Épico-1 seed roles (`organization_admin`, `pmo`, `project_manager`, `viewer`) with their
  RBAC permission catalog
- Audit log table ready to receive entries as mutations happen

The demo user (bootstrapped on backend startup, not by the migration) gets the `viewer` role
automatically — including on re-boot of a pre-existing install.

## 6. Alternative: Docker Compose

```bash
export API_KEY="choose-a-local-secret"
docker compose up --build
```

Runs the API (built from the root `Dockerfile`) against a containerized Postgres 16, running
`alembic upgrade head` on container start. The frontend is not part of `docker-compose.yml` today
— run it separately with `cd web && npm install && npm run dev` against
`BACKEND_URL=http://localhost:8000`.

## 7. Tests

```bash
make test-backend   # pytest -- 245 tests, each against its own ephemeral Postgres database
make test-frontend   # vitest -- 436 tests
make test-e2e        # playwright -- 203 tests across 3 device projects
```

`test-e2e` uses `web/e2e/mock-backend.mjs`, a lightweight Node fixture server, instead of the real
Python backend — this is a pre-existing, intentional test-architecture choice (fast, deterministic
frontend E2E, decoupled from Python/DB availability in CI), not something this mission changed.
Backend and frontend unit/integration tests run against real PostgreSQL; only the frontend E2E
layer uses a mock, and only for the backend it talks to — the frontend itself is real code.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `make db-create` hangs or fails with `fe_sendauth: no password supplied` | Postgres requires a password for the superuser and none is set | Set `PGPASSWORD` (and `PGHOST` if not localhost), or run with `sudo -u postgres` |
| `permission denied to terminate process` during `make reset-db` or tests | Non-superuser role can't terminate autovacuum workers | Already handled — `rc2-db.sh` and `tests/db.py` filter to `backend_type = 'client backend'`. If you see this, your Postgres version may lack that column (pre-10) — upgrade Postgres |
| Backend 503 on every `/api/*` call | `API_KEY` not set | Export `API_KEY` before starting, or set it in `demo/.env` |
| Backend 403 on Enterprise Domain routes from Demo Mode | Demo user has no RBAC role | Shouldn't happen — `bootstrap_demo_user` re-ensures the `viewer` role on every boot. If it does, check `alembic upgrade head` actually ran (migration 0006's permission catalog) |
| `make migrate` says relation already exists | Mixing `Base.metadata.create_all()` (used when the app boots against a fresh, unmigrated database) with Alembic on the same database | Always run `make migrate` (or `alembic upgrade head`) as the source of truth; don't let the app create tables first on an environment you intend to manage with Alembic |
| Playwright times out waiting for a webServer | Ports 3100/4100 (E2E only) or 3000/8000 (`make dev`) already in use | `make stop`, or `lsof -ti tcp:PORT \| xargs kill` |
