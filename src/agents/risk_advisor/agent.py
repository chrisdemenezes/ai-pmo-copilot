import json

from src.agents.shared.output_parser import parse_structured_output
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext


class RiskAdvisorAgent:
    """Read-only conversational synthesis over already-identified risks.

    Never triggers a new analysis and never receives raw project context --
    only Evidence the Digital PMO Intelligence Foundation's AIContextEngine
    already resolved (Domain Blueprint §4/§6/§7; W3-2 Technical Design §10).

    Migrated (Wave 3 Fase 4) onto `AdvisorFramework`: prompt composition and
    the LLM call are no longer performed directly against
    `render_analyst_prompt`/`ObservabilityRecorder` -- they go through the
    Framework instead. The prompt template and the risk extraction logic
    are byte-for-byte the same as before this migration; `advise()` now
    returns the flat `{"structured": ..., "answer": ..., ...}` dict
    directly, matching `AdvisorContract` (established in Fase 3 against
    `_FakeAdvisor`) -- the old `{"agent": ..., "model_output": ...}`
    wrapper was an artifact of the pre-Framework route, which used to do
    `result["model_output"]` itself; `AdvisorFramework.run()` now does that
    unwrapping implicitly by expecting the flat shape.
    """

    name = "risk_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(
        self,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict:
        risks_json = json.dumps(
            [
                {
                    "description": risk.get("description"),
                    "probability": risk.get("probability"),
                    "impact": risk.get("impact"),
                    "mitigation": risk.get("mitigation"),
                    "escalation_recommendation": item.summary.get("escalation_recommendation"),
                    "source_analysis_id": item.source_analysis_id,
                    "source_created_at": str(item.source_created_at),
                }
                for item in evidence
                for risk in (item.summary.get("risks") or [])
                if isinstance(risk, dict)
            ],
            ensure_ascii=False,
        )
        # Supplementary only (Technical Design §3): never the sole basis for
        # a claim, never introduces a risk not already listed above -- the
        # anti-hallucination guard stays anchored on `risks_json`/`evidence`,
        # unchanged by this Fase. Empty when no RAG context is supplied or
        # nothing was retrieved -- the common case today.
        additional_context_json = json.dumps(
            [
                {"chunk_id": chunk.chunk_id, "document_id": chunk.document_id, "text": chunk.text}
                for chunk in (rag_context.chunks if rag_context else [])
            ],
            ensure_ascii=False,
        )
        final_prompt = self.framework.render_prompt(
            self.name,
            "advise",
            question=question,
            risks_json=risks_json,
            additional_context_json=additional_context_json,
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
