# AI PMO Copilot

[![CI](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/chrisdemenezes/ai-pmo-copilot/actions/workflows/ci.yml)

An intelligent PMO assistant designed to automate project governance, reporting, meeting intelligence and decision support using Artificial Intelligence.

## Architectural Decision

The official application tree is `src/`.

Legacy or parallel implementations must not be expanded. New code must be added only inside `src/` until the MVP baseline has passing CI evidence.

## Current MVP Scope

- FastAPI application entrypoint in `src/main.py`
- Intelligence router in `src/api/routes/intelligence.py`
- Meeting Intelligence agent
- Project Status agent
- Single prompt registry
- Production LLM provider using Anthropic via environment configuration
- SQLAlchemy persistence repository
- CI workflow running lint and tests

## Repository Structure

```text
.github/workflows/ci.yml
src/
  main.py
  api/routes/intelligence.py
  agents/meeting_intelligence/
  agents/project_status/
  database/repository.py
  llm/providers/production_provider.py
  prompts/registry.py
tests/
docs/
release/
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key"
uvicorn src.main:app --reload
```

To develop without calling the real Anthropic API (no API key or cost required), set
`LLM_PROVIDER=mock` instead of `ANTHROPIC_API_KEY` — see `.env.example`.

Health check:

```bash
curl http://localhost:8000/health
```

Meeting analysis:

```bash
curl -X POST http://localhost:8000/api/meetings/analyze \
  -H "Content-Type: application/json" \
  -d '{"project_name":"Multilift","transcript":"Client approved the handover and requested action tracking."}'
```

## Governance Rule

No release or validation document may state that a feature is validated unless it links to the commit and CI/test evidence that supports the claim.
