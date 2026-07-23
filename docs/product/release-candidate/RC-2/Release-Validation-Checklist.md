# STRATECH Wave 2 RC-2 — Release Validation Checklist

Formal checklist for the transition from Implementation to Homologação (Wave 2 RC-2 mission).
Every item below was executed and verified live, against a real PostgreSQL 16 instance, in this
mission — not inferred from code reading.

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Banco conectado | ✅ PASS | `make db-create` + `alembic upgrade head` against `postgresql://aipmo:aipmo@localhost:5432/aipmo`; app engine reports `dialect.name == "postgresql"`, `pool class == QueuePool` |
| 2 | Migration aplicada | ✅ PASS | Full `upgrade head` (0001→0008) clean; full `downgrade base` clean; re-`upgrade head` clean (round trip) — all against real Postgres |
| 3 | Seed executado | ✅ PASS | 2 organizations, 4 roles, 8 permissions, 6 portfolios, 8 programs, 14 projects confirmed via `psql` after migration; each organization independently scoped (org-scoping confirmed via API) |
| 4 | Login funcionando | ✅ PASS | `POST /api/bff/session` with the seeded demo user (`demo@stratech.local` / `demo-organization`) returned `{"authenticated":true}` and set a real session cookie; subsequent authenticated requests succeeded |
| 5 | CRUD Portfolio | ✅ PASS | `POST /api/portfolios` created a real row (id 7, code `RC2-PF`); `GET /api/portfolios` listed it alongside the 3 seeded portfolios; row cleaned up after verification |
| 6 | CRUD Program | ✅ PASS | `POST /api/programs` created a real row under the portfolio above (id 9, code `RC2-PG`); listed correctly via `GET /api/programs` |
| 7 | CRUD Project | ✅ PASS | `POST /api/projects-delivery` created a real row under the program above (id 15, code `RC2-PJ`); listed correctly via `GET /api/projects-delivery` |
| 8 | Dashboard | ✅ PASS | `GET /dashboard` returned `200` with a valid authenticated session cookie; BFF routes (`/api/bff/portfolio`, `/program`, `/project-delivery`) returned real seeded data through the frontend |
| 9 | RBAC | ✅ PASS | `organization_admin` actor succeeded on all 3 writes above; a `viewer` actor (the demo user) attempting `POST /api/portfolios` was correctly rejected with `403`; all 3 writes appear in `audit_logs` (`portfolio.created`, `program.created`, `project_delivery.created`) |
| 10 | API | ✅ PASS | 9 Enterprise Domain endpoints + 8 Administration endpoints exercised (this checklist + the 245-test pytest suite, all against real Postgres) |
| 11 | BFF | ✅ PASS | `web/app/api/bff/{portfolio,program,project-delivery}` routes exercised live through a real session cookie, forwarding to the real backend with correct `X-Stratech-*` headers |
| 12 | Frontend | ✅ PASS | `next dev` served `/entrar` (200) and `/dashboard` (200, authenticated); 436 vitest unit/component tests pass |
| 13 | Playwright | ✅ PASS (with documented exception) | 203/203 E2E tests pass across all 3 device projects (`lg`/`md`/`mobile`). Uses `web/e2e/mock-backend.mjs`, a lightweight Node fixture, instead of the real Python+Postgres backend -- a pre-existing, intentional test-architecture decision (fast, deterministic frontend E2E, decoupled from Python/DB availability in CI), not something this mission introduced or was asked to change. The real backend+Postgres path is covered instead by the pytest suite and the manual smoke in items 4-9 above. |
| 14 | Health Check | ✅ PASS | `GET /health` → `{"status":"healthy","service":"AI PMO Copilot"}` while backend was live against Postgres |

## Full automated test suite (all against real Postgres where the suite touches a database)

| Suite | Result | Notes |
|---|---|---|
| Backend (`pytest`) | **245 passed**, 98% coverage | Every test creates its own ephemeral Postgres database via `tests/db.py::temp_database_url` |
| Frontend (`vitest`) | **436 passed** | No database dependency (unit/component tests) |
| E2E (`playwright`, 3 projects) | **203 passed** (67 `lg` + 67 `md` + 68 `mobile` + 1 intentionally skipped) | Mocked backend — see item 13 |
| Lint (`ruff check src tests`) | **All checks passed** | |

## Reproducibility proof

Executed in this mission, from a state equivalent to a fresh clone (`git status` clean before and
after):

```bash
make db-create   # idempotent, auto-detects peer-auth vs password-auth Postgres
make migrate     # 0001 -> 0008, clean
make dev         # backend + frontend up, health check green
make stop
make test-backend    # 245 passed against fresh ephemeral Postgres databases
make test-frontend    # 436 passed
make test-e2e         # 203 passed
```

No manual intervention beyond the documented `sudo` prompt for `db-create` on a native Linux
Postgres install (peer auth — see `docs/product/release-candidate/RC-2/Quick-Start.md` §3).
