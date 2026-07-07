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

## Governance Rule

A feature may only be marked as ready when this file includes:

- commit SHA
- CI run link or workflow reference
- test output or execution log
