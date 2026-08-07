"""Executive Orchestrator, Etapa 4 -- Síntese (Founder Decision
"Implementação do Executive Orchestrator"). Unit tests for `synthesize()`
in isolation -- no database, no real Advisor -- proving the mechanism
reuses the shared institutional prompt composition/observability recording
and consumes exclusively the `Explanation`s it is given, never raw
`Evidence`."""
import ast
import inspect
import json

import pytest

from src.prompts.registry import PromptRegistry
from src.services.ai_foundation.types import Evidence, Explanation, Recommendation, SessionContext
from src.services.executive_orchestrator import synthesis as synthesis_module
from src.services.executive_orchestrator.synthesis import synthesize
from src.services.executive_orchestrator.types import AttributedExplanation


class _FakeLLMProvider:
    def __init__(self, response: str):
        self.response = response
        self.received_prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.received_prompts.append(prompt)
        return self.response


def _explanation(answer: str, cited: list[Evidence] | None = None) -> Explanation:
    return Explanation(
        recommendation=Recommendation(answer=answer, cited_evidence=cited or []),
        rationale="Síntese informativa baseada em 0 evidência(s) já registrada(s).",
    )


def _session() -> SessionContext:
    return SessionContext(organization_id=1, user_id=1, session_id="s-1")


@pytest.fixture()
def prompt_registry() -> PromptRegistry:
    return PromptRegistry(base_path="src/services")


class TestSynthesizeMechanism:
    def test_returns_the_llm_synthesis_field(self, prompt_registry):
        provider = _FakeLLMProvider(json.dumps({"synthesis": "grounded synthesis"}))
        explanations = (
            AttributedExplanation(advisor_name="risk_advisor", explanation=_explanation("risks exist")),
        )

        result = synthesize(provider, prompt_registry, _session(), "any question?", explanations)

        assert result == "grounded synthesis"

    def test_falls_back_to_raw_output_when_not_valid_json(self, prompt_registry):
        provider = _FakeLLMProvider("plain text answer, not json")
        explanations = (
            AttributedExplanation(advisor_name="risk_advisor", explanation=_explanation("risks exist")),
        )

        result = synthesize(provider, prompt_registry, _session(), "any question?", explanations)

        assert result == "plain text answer, not json"

    def test_composes_the_shared_institutional_preamble(self, prompt_registry):
        provider = _FakeLLMProvider(json.dumps({"synthesis": "x"}))
        explanations = (
            AttributedExplanation(advisor_name="risk_advisor", explanation=_explanation("risks exist")),
        )

        synthesize(provider, prompt_registry, _session(), "what is the risk?", explanations)

        assert "STRATECH" in provider.received_prompts[0]  # shared institutional preamble
        assert "what is the risk?" in provider.received_prompts[0]

    def test_contributions_include_every_advisor_and_the_had_evidence_flag(self, prompt_registry):
        provider = _FakeLLMProvider(json.dumps({"synthesis": "x"}))
        grounded = AttributedExplanation(
            advisor_name="risk_advisor",
            explanation=_explanation(
                "risks exist",
                cited=[Evidence(source_type="analysis_record", source_id=1, source_label="A", content={})],
            ),
        )
        empty = AttributedExplanation(advisor_name="delivery_advisor", explanation=_explanation("no status"))

        synthesize(provider, prompt_registry, _session(), "any question?", (grounded, empty))

        prompt = provider.received_prompts[0]
        assert '"advisor": "risk_advisor"' in prompt
        assert '"advisor": "delivery_advisor"' in prompt
        assert '"had_evidence": true' in prompt
        assert '"had_evidence": false' in prompt


class TestNeverRawEvidence:
    def test_synthesize_signature_never_accepts_evidence_directly(self):
        parameters = inspect.signature(synthesize).parameters
        assert "evidence" not in parameters
        assert set(parameters) == {"llm_provider", "prompt_registry", "session", "question", "explanations"}

    def test_module_never_imports_context_engine_or_domain_service(self):
        tree = ast.parse(inspect.getsource(synthesis_module))
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        forbidden = {"AIContextEngine", "DomainService", "AnalysisRepository", "KnowledgeRepository"}
        assert not (imported_names & forbidden)
