from src.services.ai_foundation.prompt_composer import render_analyst_prompt


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "some_analyst"
        assert prompt_name == "advise"
        return "Question: $question"


def test_render_analyst_prompt_prepends_the_shared_preamble():
    prompt = render_analyst_prompt(FakePromptRegistry(), "some_analyst", "advise", question="Oi?")

    assert "Digital PMO Intelligence Foundation" in prompt
    assert prompt.endswith("Question: Oi?")
    assert prompt.index("Digital PMO Intelligence Foundation") < prompt.index("Question: Oi?")


def test_render_analyst_prompt_substitutes_every_variable():
    class TwoVarRegistry:
        def get(self, agent_name, prompt_name):
            return "A: $a, B: $b"

    prompt = render_analyst_prompt(TwoVarRegistry(), "x", "y", a="1", b="2")

    assert "A: 1, B: 2" in prompt
