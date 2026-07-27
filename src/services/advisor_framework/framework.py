"""`AdvisorFramework` -- the Enterprise Advisor Framework's single entry
point (Fase 3). Every method is a thin, tested passthrough to a component
that already exists (`AIContextEngine`, `RagPipeline`, `ObservabilityRecorder`,
`AIFoundationAudit`, `render_analyst_prompt`, `RecommendationEngine`,
`ExplanationEngine`) -- extracted from the exact sequence
`POST /risk-advisor/ask` already runs today
(Technical Design, `docs/architecture/TECHNICAL-DESIGN-ENTERPRISE-ADVISOR-FRAMEWORK-FASE3.md`
§1), not a new orchestration invented for hypothetical future Advisors.

`run()` executes exactly one Advisor per call, chosen by the caller --
never a workflow engine, never autonomous routing between Advisors, never
delegation from one Advisor to another (Founder's explicit restrictions,
Fase 3).
"""
from src.database.repository import AnalysisRepository
from src.llm.providers.base import LLMProvider
from src.prompts.registry import PromptRegistry
from src.services.advisor_framework.types import AdvisorContract, AdvisorExecutionError
from src.services.ai_foundation.audit_integration import AIFoundationAudit
from src.services.ai_foundation.context_engine import AIContextEngine
from src.services.ai_foundation.explanation_engine import ExplanationEngine
from src.services.ai_foundation.observability import ObservabilityRecorder
from src.services.ai_foundation.prompt_composer import render_analyst_prompt
from src.services.ai_foundation.recommendation_engine import RecommendationEngine
from src.services.ai_foundation.types import Evidence, Explanation, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext, RagPipeline


class AdvisorFramework:
    def __init__(
        self,
        repository: AnalysisRepository,
        prompt_registry: PromptRegistry,
        llm_provider: LLMProvider,
        rag_pipeline: RagPipeline,
    ):
        self._repository = repository
        self._context_engine = AIContextEngine(repository)
        self._prompt_registry = prompt_registry
        self._llm_provider = llm_provider
        self._rag_pipeline = rag_pipeline

    # -- controlled context access (audit §1, step 2) ----------------------

    def gather_context(
        self, organization_id: int, project_name: str | None, kind: str
    ) -> list[Evidence]:
        return self._context_engine.gather(organization_id, project_name, kind)

    # -- controlled RAG access -- never PgVectorRepository/EmbeddingProvider
    # directly, always through RagPipeline -> KnowledgeRepository ---------

    def gather_rag_context(
        self, organization_id: int, query: str, top_k: int = 5
    ) -> RagContext:
        return self._rag_pipeline.retrieve(organization_id, query, top_k=top_k)

    # -- controlled LLM access (audit §1, steps 5b/5c) ---------------------

    def render_prompt(self, advisor_name: str, prompt_name: str, **variables: str) -> str:
        return render_analyst_prompt(self._prompt_registry, advisor_name, prompt_name, **variables)

    def call_llm(self, advisor_name: str, session: SessionContext, prompt: str) -> str:
        return ObservabilityRecorder.record_call(advisor_name, session, self._llm_provider, prompt)

    # -- execution: the exact sequence audit §1 (steps 3-8) already runs ---

    def run(
        self,
        advisor: AdvisorContract,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
        no_evidence_answer: str | None = None,
    ) -> Explanation:
        # Every question is audited, unconditionally, before any evidence
        # decision -- never the model's answer itself.
        AIFoundationAudit.record_question(self._repository, session, advisor.name, question)

        # The no-evidence gate keys exclusively on AnalysisRecord-derived
        # evidence, exactly as before Fase 4 -- RAG is supplementary and
        # never triggers an LLM call on its own (Founder's fidelity
        # requirement: this behavior must stay byte-for-byte unchanged).
        # `no_evidence_answer` lets the caller preserve an Advisor's own
        # domain wording (e.g. "Nenhum risco identificado...") -- the same
        # override `RecommendationEngine.no_evidence()` already supported
        # before this Framework existed, never a new capability.
        if not evidence:
            return ExplanationEngine.explain(RecommendationEngine.no_evidence(no_evidence_answer))

        model_output = advisor.advise(session, question, evidence, rag_context)

        if not model_output.get("structured") or not isinstance(model_output.get("answer"), str):
            raise AdvisorExecutionError(f"{advisor.name} returned an invalid response")

        recommendation = RecommendationEngine.build(
            model_output["answer"], model_output.get("cited_analysis_ids") or [], evidence
        )
        return ExplanationEngine.explain(recommendation)
