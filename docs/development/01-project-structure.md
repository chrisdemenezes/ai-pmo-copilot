# Project Structure

## Architectural Decision

The official implementation tree for the backend is `src/`. As of RFC-001 (Frontend Architecture,
see "RFC-001 Decision" below), `web/` is the equivalent official tree for the frontend.

No new parallel tree should be created beyond these two without a decision recorded here first.

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

## Decision: TASK-AI-01 deferred, at the user's direction

`TASK-AI-01` (a real integration call per agent against the production Anthropic API, to measure the
real `structured: true` vs. fallback rate) is explicitly deferred, not scheduled:

- A real `ANTHROPIC_API_KEY` was provided and tested (Evidence Entry 013). The key authenticated
  successfully — this is not a credential or code problem — but the account behind it has no
  billing/credit configured, so all three calls were rejected with `400: credit balance too low`
  before reaching the model.
- The user chose to proceed with the rest of the roadmap rather than wait for billing to be added.
- What Entry 013 already confirms stands as real evidence: `ProductionLLMProvider` connects
  correctly to the live API, and `ProviderUnavailableError` → 502 fires correctly against a genuine
  upstream rejection. What remains open is specifically the structured-output success rate on a real
  model response — that requires either billing added to the existing key's account or a differently
  funded key, at the user's discretion. This is not blocked by anything in the codebase or this
  environment.

With this deferral, every other item in the Master Product Backlog's roadmap through the Pilot
Release milestone (Sprints 1-4) is closed. See `docs/releases/mvp-validation.md`, Evidence Entries
004-013, for the full record.

## RFC-001 Decision: `web/` as the official frontend tree, Sprint 1 (Design System) delivered

At the user's direction, the session's role shifted from Backend Engineer to Principal Product
Designer / Frontend Architect. RFC-001 was produced first (architecture, stack, security model,
design system, components, routes, states, API integration) and approved before any code was
written, per the same "plan before code" discipline used throughout the backend work. Full RFC
content published as an artifact during the session; this entry is the repository's lasting record.

**Why `web/`, not `frontend/`:** `frontend/` holds only vision documentation (`README.md`,
`90-mvp-web-interface.md`, `91-document-intelligence-workspace.md`) — no real code. Putting a real
Next.js application inside it would mix a working app with aspirational docs in one directory,
confusing for the next engineer (or AI) who opens the repository. `web/` is a clean, unambiguous
home, parallel to `src/`. `frontend/` is untouched.

**Stack** (confirms the pre-existing decision in `docs/technical/02-technology-stack.md`, adds the
rest): Next.js 16 (App Router, TypeScript), Tailwind CSS v4 (CSS-first `@theme` config, not
`tailwind.config.js` — a real breaking change from the version referenced in prior docs). Radix UI
primitives vendored via hand-written wrapper components in `web/components/ui/` (the shadcn/ui CLI
and registry at `ui.shadcn.com` are blocked by this environment's egress policy — reported, not
routed around; the same architectural outcome, Radix + Tailwind owned as our own source, not a
runtime dependency, was achieved by installing the underlying `@radix-ui/react-*` packages directly
via npm and writing the component files by hand). TanStack Query, React Hook Form + Zod, and
Playwright are planned for later sprints per RFC-001 but not yet installed — Sprint 1 has no API
calls and no forms with real submission.

**Security decision carried over from the RFC, not yet implemented:** the backend's single shared
`API_KEY` must never reach the browser. A Backend-for-Frontend pattern (Next.js Route Handlers
holding the real key server-side) is planned for Sprint 2 onward, when API calls are first made —
Sprint 1 has no network calls to the FastAPI backend at all.

**Sprint 1 scope delivered:**
- Design tokens (`web/app/globals.css`) matching RFC-001 Section 5 exactly: indigo accent (distinct
  from the blue/teal used in this project's engineering evidence docs, so the product is never
  visually confused with its own internal audit reports), system font stacks (no `next/font/google`
  — zero network requests for typography, same reasoning already applied to every HTML report this
  session produced), status colors mapped 1:1 to the backend's real `health_status` values
  (`green`/`yellow`/`red`, nothing invented).
- Ten primitives in `web/components/ui/`: Button, Card, Input, Textarea, Badge (with
  `healthStatusVariant()`, a pure function unit-tested directly), Skeleton, Tabs, Dialog, Select,
  Label, plus a Sonner-based Toaster.
- `web/app/style-guide` — a live page exercising every primitive, in both themes.
- Vitest + React Testing Library configured; 9 tests passing (`healthStatusVariant` mapping, Badge
  rendering, Button click/disabled behavior).

**Real bug found and fixed during manual browser verification, not by static checks:** the Dialog's
Cancel/Confirm buttons in the style-guide demo did not close the dialog — only the corner close icon
did, because `DialogClose` was never exported from the primitive. Caught by driving the actual
rendered page with Playwright (already available in this environment) and asserting on real DOM
state, not by `tsc`/`eslint`/the production build, all of which passed while the bug was still
present. Fixed by adding `DialogClose` to `web/components/ui/dialog.tsx` and wrapping the demo
buttons with it.

**Verification performed:** `npx tsc --noEmit`, `npx eslint .`, `npm run build` (both routes
prerendered as static content), `npm test` (9/9), and a full manual pass in a real headless browser
— both color schemes screenshotted, then Select/Tabs/Dialog/Toast/character-counter driven
interactively via Playwright and asserted on real page state, not just visual inspection.
