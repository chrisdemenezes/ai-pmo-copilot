import json

from src.agents.shared.output_parser import parse_structured_output
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext


class DocumentAdvisorAgent:
    """Read-only conversational synthesis over already-indexed document
    chunks (Technical Design, `TECHNICAL-DESIGN-DOCUMENT-ADVISOR.md` §5).

    RAG is this Advisor's only and primary evidence source (Classe D, AR-8
    §4) -- `evidence` here is already the normalization of `rag_context`
    (`AdvisorFramework.normalize_rag_evidence()`), not a second, separate
    input. `rag_context` is accepted for `AdvisorContract` conformance but
    unused by `advise()` itself.
    """

    name = "document_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(
        self,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict:
        chunks_json = json.dumps(
            [
                {
                    "chunk_id": item.source_id,
                    "document_id": item.metadata.get("document_id"),
                    "text": item.content.get("text"),
                }
                for item in evidence
            ],
            ensure_ascii=False,
        )
        final_prompt = self.framework.render_prompt(
            self.name, "advise", question=question, chunks_json=chunks_json
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
