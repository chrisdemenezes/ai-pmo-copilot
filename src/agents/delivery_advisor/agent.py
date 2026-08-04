"""Delivery Advisor (Wave 5, Classe A -- AR-8 §4.2/D-104), per
`TECHNICAL-DESIGN-DELIVERY-ADVISOR.md`.

Same shape as `RiskAdvisorAgent` -- the reference Classe A implementation --
except this Advisor never receives `rag_context` as anything but `None`:
per Founder Decision ("Technical Design do Delivery Advisor"), RAG is
explicitly out of scope for this Epic, so `advise()` never builds a
supplementary context block, and the route never calls
`AdvisorFramework.gather_rag_context()`.

`evidence` always comes from exactly one call to
`AdvisorFramework.gather_context(organization_id, project_name,
kind="status")`, already ordered most-recent-first
(`AnalysisRepository.list_analyses()`, confirmed in AR-11) -- this agent
never reorders it and never compares `health_status`/dates itself; the
first entry is the current state, and any temporal trend across older
entries is interpreted entirely by the LLM, per the prompt (Founder
Decision -- Technical Design do Delivery Advisor, item 3)."""
import json

from src.agents.shared.output_parser import parse_structured_output
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext


class DeliveryAdvisorAgent:
    name = "delivery_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(
        self,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict:
        status_history_json = json.dumps(
            [
                {
                    "health_status": item.content.get("health_status"),
                    "key_findings": item.content.get("key_findings"),
                    "recommendations": item.content.get("recommendations"),
                    "source_analysis_id": item.source_id,
                    "source_created_at": str(item.metadata["created_at"]),
                }
                for item in evidence
            ],
            ensure_ascii=False,
        )
        final_prompt = self.framework.render_prompt(
            self.name, "advise", question=question, status_history_json=status_history_json
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
