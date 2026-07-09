import pytest

from src.prompts.registry import PromptRegistry


def test_get_reads_existing_prompt_file(tmp_path):
    prompt_dir = tmp_path / "sample_agent" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "analysis.md").write_text("Hello $name", encoding="utf-8")

    registry = PromptRegistry(base_path=str(tmp_path))

    assert registry.get("sample_agent", "analysis") == "Hello $name"


def test_get_raises_file_not_found_for_missing_prompt(tmp_path):
    registry = PromptRegistry(base_path=str(tmp_path))

    with pytest.raises(FileNotFoundError):
        registry.get("unknown_agent", "analysis")


def test_default_base_path_resolves_real_agent_prompts():
    registry = PromptRegistry()

    template = registry.get("meeting_intelligence", "analysis")

    assert "$project_name" in template
