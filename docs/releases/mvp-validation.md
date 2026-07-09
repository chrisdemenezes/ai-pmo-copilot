# AI PMO Copilot MVP Evidence

This document is the release evidence ledger for MVP claims.

## Evidence Entry 001 - MVP architecture consolidation

- Source PR: #1 - fix: consolidate MVP architecture
- Merge commit SHA: `b5e46ca1b242bf19e544a6a98583bc4a09d4c629`
- Head commit before merge: `a8455d62a90245ccc27467b42c2ef64fc7dc0443`
- Scope evidenced:
  - `src/` defined as official implementation tree
  - FastAPI entrypoint added in `src/main.py`
  - Intelligence API router registered
  - Meeting Intelligence agent connected to prompt registry and model provider
  - Risk Review agent connected to prompt registry and model provider
  - SQLAlchemy repository added
  - CI workflow created for lint and tests
- CI evidence: GitHub Actions workflow `CI` available at `.github/workflows/ci.yml`. The run result must be verified in GitHub Actions before any production-ready claim.

## Evidence Entry 002 - Platform hardening and analysis query API

- Source PR: #3 - feat: platform hardening + analysis query API (Sprint 1 + US-D1/D2)
- Merge commit SHA: `d1335a20b735e4c4aa78b221a8da6b3202dd494b`
- Source PR: #4 - feat: filter analyses by kind and period (US-D3)
- Merge commit SHA: `f28397fd503c71b90ca5f4cef2bdeecad38ea80a`
- Scope evidenced:
  - Prompt templates migrated from `str.format()` to `string.Template.safe_substitute()`
  - Typed provider layer (`LLMProvider` protocol, config/unavailable errors, mock provider, factory via `LLM_PROVIDER`)
  - Global exception handlers (503/502 instead of unhandled 500)
  - Repository dependency cached as a singleton
  - `GET /api/analyses` (list, filterable by `project_name`, `kind`, `created_from`, `created_to`) and `GET /api/analyses/{id}`
- Test evidence: 32/32 tests passing (`pytest -q`), `ruff check src tests` clean, confirmed against real file-based SQLite via manual smoke tests (not only fakes/mocks).
- CI evidence: GitHub Actions workflow `CI` available at `.github/workflows/ci.yml`. The run result must be verified in GitHub Actions before any production-ready claim.

## Governance Rule

A feature may only be marked as ready when this file includes:

- commit SHA
- CI run link or workflow reference
- test output or execution log
