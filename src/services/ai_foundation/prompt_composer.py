from pathlib import Path
from string import Template

from src.prompts.registry import PromptRegistry

_PREAMBLE_PATH = Path(__file__).parent / "prompts" / "analyst_preamble.md"


def render_analyst_prompt(
    prompt_registry: PromptRegistry, agent_name: str, prompt_name: str, **variables: str
) -> str:
    """Composes the one shared institutional preamble (Digital PMO philosophy
    + never-invent-data instruction) with an Analyst's own specialized
    template -- PromptRegistry.get()'s contract is untouched; this only
    composes over it (Domain Blueprint §4.5, no new registry)."""
    preamble = _PREAMBLE_PATH.read_text(encoding="utf-8")
    template = prompt_registry.get(agent_name, prompt_name)
    return Template(f"{preamble}\n\n{template}").safe_substitute(**variables)
