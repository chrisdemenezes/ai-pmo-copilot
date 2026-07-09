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

- `alembic upgrade head` reads `DATABASE_URL` the same way `AnalysisRepository` does (env var,
  falling back to `sqlite:///./ai_pmo_copilot.db`), so it targets whatever database the app would
  actually connect to.
- Tests do **not** use Alembic — they call `AnalysisRepository(database_url=...)`, which still runs
  `Base.metadata.create_all()` against an ephemeral SQLite database. This is intentional: fast,
  isolated tests do not need a migration history. Alembic is for evolving a real, persistent
  database (Postgres or a long-lived SQLite file) without dropping data.
- `tests/test_alembic_migration.py` runs `alembic upgrade head` against a temporary SQLite file and
  asserts the resulting schema matches `AnalysisRecord` — this exists specifically to catch drift if
  the model changes without the migration being updated to match.
- Postgres has not been tested against a live instance in this environment (no Postgres available);
  `alembic upgrade head` has only been verified against SQLite. `psycopg2-binary` is in
  `requirements.txt` for when a real Postgres `DATABASE_URL` is configured, but that path is
  currently unverified end-to-end.

To create a new migration after changing `AnalysisRecord`:

```bash
alembic revision --autogenerate -m "description of the change"
```

Review the generated file before committing — autogenerate is a starting point, not a guarantee.
