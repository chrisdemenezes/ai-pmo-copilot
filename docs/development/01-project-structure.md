# Project Structure

## Architectural Decision

The official implementation tree for the MVP is `src/`.

No new parallel tree should be created until the MVP has passing CI evidence and the P0 corrections are closed.

## Repository Organization

```text
ai-pmo-copilot
|
├── .github/workflows
│   └── ci.yml
├── src
│   ├── main.py
│   ├── api/routes/intelligence.py
│   ├── agents
│   │   ├── meeting_intelligence
│   │   ├── project_status
│   │   ├── risk_review
│   │   └── shared/output_parser.py
│   ├── database/repository.py
│   ├── llm/providers/production_provider.py
│   ├── prompts/registry.py
│   └── services/project_summary_service.py
├── tests
├── docs
└── release
```

## Implementation Rules

1. New runtime code must be created under `src/`.
2. Agent prompts must be loaded through `src/prompts/registry.py`.
3. API routes must be registered through `src/main.py`.
4. Release or validation documents must include commit and CI evidence before using validated/pronto/concluido language.

## Cleanup v3 Notes

- `issue_advisor` was introduced during the consolidation cycle as a temporary domain-safe substitute for the blocked `risk_advisor` path. The official active risk implementation is now `risk_review`.
- Recursive deletion of legacy folders must be completed in a local Git environment or a CI-capable workspace because the connector can only delete concrete files one by one.
- Remaining legacy cleanup should not introduce new functionality.

## US-C2 Decision: issue_advisor retired

`issue_advisor` was removed (`src/agents/issue_advisor/`, `tests/test_issue_advisor_agent.py`). It
was never wired to any API route and duplicated the purpose of `risk_review`, the official risk
implementation. Per its own documented status above (a temporary substitute superseded once
`risk_review` was connected), keeping it around as untested-in-production dead code was not
justified. If issue-specific analysis distinct from risk review is needed in the future, it should
be scoped as a new decision, not a revival of this agent.

## Decision: AP-001, DB-001, CP-001 deferred until MVP closure

Three backlog items from the tracked spreadsheet are explicitly deferred, not implemented, not
scheduled:

- **AP-001 (Plano Inteligente / Action Plan)** — scope was never made concrete; no equivalent
  exists in the current architecture to extend.
- **DB-001 (Dashboard KPIs)** — requires a real frontend. `frontend/` today is documentation only
  (no Next.js code); this is a separate project setup, not an incremental story.
- **CP-001 (Chat PMO)** — requires multi-turn conversational orchestration with context memory,
  which is the "Phase 3" work explicitly out of scope until the MVP (Sprint 1 + Sprint 2 platform
  hardening, structured agent outputs, coverage gate, Alembic) is closed and stable.

MVP state at the time of this decision: all Sprint 1/Sprint 2 stories (US-E1 through US-A2),
MI-001 through MI-006, RI-001, SR-001, the 80% coverage gate, and Alembic migrations are merged to
`main` and verified from clean checkouts (not just locally). See `docs/releases/mvp-validation.md`
for commit-level evidence.

## TASK-KN-01 / TASK-AI-02 Decision: orphan stubs removed

Three code stubs were removed — none were ever imported by any application code or referenced by
any test:

- `src/knowledge/ingestion_pipeline.py` (`KnowledgePipeline.ingest`) — a 4-line stub, no chunking,
  no embedding call, no storage backend. Not a foundation to build on, just a placeholder.
- `knowledge/retrieval_service.py` (`RetrievalService.search`) — same shape, hardcoded empty result.
- `src/agents/core/agent.py` (`Agent(ABC)`) — never adopted as the base class of
  `meeting_intelligence`, `risk_review`, or `project_status`, which all follow their own identical
  `__init__(model_client, prompt_registry)` / `analyze(...)` shape instead.

Same reasoning as the `issue_advisor` removal (US-C2): unreferenced, untested-in-production code
does not earn its keep by existing. If Knowledge/RAG or a shared `Agent` base class become real
work, they should be scoped and built against then-current requirements, not resurrected from these
stubs. The documentation-only placeholders under `knowledge/` (`vector_store/`, `documents/`,
`embeddings/` READMEs) are unaffected — they are declared as vision docs, not code pretending to be
an implementation.

## TASK-INF-02 Decision: docker-compose fixed, not removed

`docker-compose.yml` referenced two broken build contexts: `./backend` (`Dockerfile` pointed at
`app.main:app`, a module that has never existed since `src/` became the official tree) and
`./frontend` (no `Dockerfile` at all — `frontend/` is still documentation only, per the DB-001/CP-001
deferral above). Fixed rather than removed, because a working Compose stack also gives anyone with a
local Docker daemon a way to close `TASK-INF-01` (Alembic vs. a real Postgres) themselves:

- Added a root `Dockerfile` building the real `src/main:app` (only `src/`, `alembic.ini`, and
  `alembic/` are copied in — not the whole repo).
- `docker-compose.yml` now has two services: `api` (built from the root `Dockerfile`, runs `alembic
  upgrade head` before `uvicorn` on every start) and `database` (`postgres:16`, with a named volume
  so data survives `docker compose down`). The `frontend` service was dropped — there is no code to
  build.
- Removed `backend/Dockerfile` and `backend/requirements.txt` — nothing referenced them anymore
  after the fix, and they described a module layout (`app.main:app`) that was never real.
  `backend/README.md` and the numbered vision docs under `backend/` are untouched.

Known limitation: this environment has no Docker daemon available (`/var/run/docker.sock` missing),
so `docker compose up` itself could not be exercised end-to-end here. Verified instead via `docker
compose config` (confirms YAML syntax and env var interpolation resolve correctly — this is how an
env-var default bug in the rate-limit settings was actually caught before merge) and manual review
of the Dockerfile against the already-working local run instructions in `README.md`. Real `docker
compose up` execution against this file is still owed before calling Docker support production-
ready.
