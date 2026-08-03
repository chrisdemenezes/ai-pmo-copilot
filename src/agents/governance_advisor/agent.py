import json

from src.agents.shared.output_parser import parse_structured_output
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext


class GovernanceAdvisorAgent:
    """Read-only conversational synthesis over already-indexed governance
    documents (Technical Design, `TECHNICAL-DESIGN-GOVERNANCE-ADVISOR.md`
    §3/§4).

    Same Classe D shape as `DocumentAdvisorAgent` (`evidence` here is
    already the normalization of `rag_context`) -- the only domain-specific
    behavior is that `answer`'s first line must be exactly one of the 5
    official governance classifications (§4), applying the AR-10
    institutional precedence (Decision Log > Technical Debt Register >
    Mission Control/CHANGELOG > Epic documents) as prompt knowledge, never
    Framework logic.
    """

    name = "governance_advisor"

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
                    "source_label": item.source_label,
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
