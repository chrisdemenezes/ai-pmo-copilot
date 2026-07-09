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
│   │   └── risk_review
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
