from pathlib import Path


class PromptManager:
    """Loads and manages versioned AI prompts."""

    def load_prompt(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")
