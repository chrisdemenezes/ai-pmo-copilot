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
