# Database Model

## Main Entities

### User
- id
- name
- role
- permissions

### Project
- id
- name
- status
- health indicators

### Document
- id
- project_id
- content
- metadata

### AI Analysis
- id
- project_id
- agent_type
- result
- created_at

## Vector Knowledge Store

Used for semantic search and contextual retrieval of project knowledge.

## Current MVP Implementation

The entities above describe the target data model. What is actually implemented today
(`src/database/repository.py`) is a single table:

### analysis_records
- `id` (int, primary key)
- `kind` (string — `"meeting"`, `"risk"`, or `"status"`)
- `project_name` (string, nullable, indexed)
- `payload` (JSON — the full agent result)
- `created_at` (datetime, UTC)

No `User`, `Project`, or `Document` tables exist yet; `project_name` is a free-text field, not a
foreign key to a `Project` entity.

## Schema Migrations

Alembic manages schema evolution for real deployments (`alembic/`, config in `alembic.ini`).

- **PostgreSQL is the official database from RC-2 onward** (see
  `docs/product/release-candidate/RC-2/Quick-Start.md`). `alembic upgrade head` and
  `AnalysisRepository` both resolve `DATABASE_URL` through the single shared helper
  `src/database/engine.py::resolve_database_url`, falling back to
  `sqlite:///./ai_pmo_copilot.db` only when `DATABASE_URL` is unset -- SQLite is kept solely as a
  zero-dependency default, never as a deployment target.
- **Tests run against real, ephemeral PostgreSQL databases**, not SQLite. `tests/db.py` provides
  `temp_database_url(prefix)`, a context manager that creates a uniquely-named Postgres database
  (the same one-database-per-test isolation a SQLite tmp file used to give), yields its URL, and
  drops it afterward. Every test that touches the database -- repository tests, API tests, and the
  migration-invariant tests below -- uses this one seam instead of each file hand-rolling its own
  SQLite file. Requires a reachable local Postgres (`TEST_POSTGRES_ADMIN_URL`, default
  `postgresql://aipmo:aipmo@localhost:5432/postgres`).
- `tests/test_alembic_migration.py` runs `alembic upgrade head` against a fresh Postgres database
  and asserts the resulting schema matches the SQLAlchemy models -- this exists specifically to
  catch drift if a model changes without the migration being updated to match.
- Verified end-to-end against a real PostgreSQL 16 instance as part of the RC-2 mission: full
  `alembic upgrade head` / `downgrade base` / re-`upgrade head` round trip, the complete pytest
  suite (245 tests) running with each test against its own ephemeral Postgres database, and a live
  `uvicorn` + `next dev` stack smoke-tested over real HTTP (login, `/api/portfolios`,
  `/api/programs`, `/api/projects-delivery`, RBAC 403 enforcement, `/health`) -- all against the
  same Postgres instance, no SQLite involved. See
  `docs/product/release-candidate/RC-2/Release-Validation-Checklist.md` for the full record.

To create a new migration after changing `AnalysisRecord`:

```bash
alembic revision --autogenerate -m "description of the change"
```

Review the generated file before committing — autogenerate is a starting point, not a guarantee.
