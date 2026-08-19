"""Síntese (Technical Design §7) -- a mechanism only. Reuses, verbatim, the
same institutional prompt composition (`render_analyst_prompt()`, the same
shared preamble -- "never invent data" -- every Advisor already gets) and
observability recording (`ObservabilityRecorder.record_call()`) already
validated across all 8 Advisor institutional cycles -- never a parallel,
unaudited LLM-calling mechanism (Vision, Princípio 7: reuse, never a
destructive or duplicate alternative).

Consumes exclusively the `Explanation`s already collected -- never raw
`Evidence`, never `AIContextEngine`/`DomainService`/Knowledge Platform/the
database. Never introduces a new fact, never re-interprets domain content,
never produces a decision (Vision, Princípios 1/3/6/11).
"""
import json

from src.agents.shared.output_parser import parse_structured_output
from src.llm.providers.base import LLMProvider
from src.prompts.registry import PromptRegistry
from src.services.ai_foundation.observability import ObservabilityRecorder
from src.services.ai_foundation.prompt_composer import render_analyst_prompt
from src.services.ai_foundation.types import SessionContext
from src.services.executive_orchestrator.types import AttributedExplanation

# `agent_name` passed to `render_analyst_prompt()`/`PromptRegistry.get()`
# below -- resolves to `<base_path>/executive_orchestrator/prompts/
# synthesize.md`, the same `base_path/agent_name/prompts/prompt_name.md`
# convention every Advisor already uses (`PromptRegistry` docstring), never
# a new registry. The caller injects its own `PromptRegistry` instance
# (same DI pattern as `AdvisorFramework`), constructed with `base_path=
# "src/services"`, never `"src/agents"` (Vision, Princípio 8: the
# Orchestrator's own prompt never lives among the closed catalog of 8
# Advisors).
ORCHESTRATOR_NAME = "executive_orchestrator"


def synthesize(
    llm_provider: LLMProvider,
    prompt_registry: PromptRegistry,
    session: SessionContext,
    question: str,
    explanations: tuple[AttributedExplanation, ...],
) -> str:
    contributions = json.dumps(
        [
            {
                "advisor": item.advisor_name,
                "answer": item.explanation.recommendation.answer,
                "had_evidence": bool(item.explanation.recommendation.cited_evidence),
            }
            for item in explanations
        ],
        ensure_ascii=False,
    )
    prompt = render_analyst_prompt(
        prompt_registry,
        ORCHESTRATOR_NAME,
        "synthesize",
        question=question,
        contributions_json=contributions,
    )
    raw_output = ObservabilityRecorder.record_call(ORCHESTRATOR_NAME, session, llm_provider, prompt)
    parsed = parse_structured_output(raw_output)
    if parsed.get("structured") and isinstance(parsed.get("synthesis"), str):
        return parsed["synthesis"]
    return raw_output.strip()
