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
│   └── prompts/registry.py
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
