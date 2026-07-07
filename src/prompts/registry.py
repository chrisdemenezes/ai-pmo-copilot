from pathlib import Path


class PromptRegistry:
    """Single prompt registry for all agents.

    Prompts are resolved from: src/agents/<agent_name>/prompts/<prompt_name>.md
    """

    def __init__(self, base_path: str = "src/agents"):
        self.base_path = Path(base_path)

    def get(self, agent_name: str, prompt_name: str) -> str:
        path = self.base_path / agent_name / "prompts" / f"{prompt_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")
