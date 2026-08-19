"""PMO Advisor (Wave 5, second Classe B Advisor -- AR-8 SS4.2/D-104), per
`TECHNICAL-DESIGN-PMO-ADVISOR.md`.

`evidence` always arrives already composed by `PMOEvidenceAssembler` -- up
to five items per Project, each carrying its own `staleness_days`/
`is_stale` already computed. This agent never reorders, never filters,
never recalculates staleness -- it only serializes to JSON, same
discipline as `PortfolioAdvisorAgent`/`DeliveryAdvisorAgent`."""
import json

from src.agents.shared.output_parser import parse_structured_output
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext


class PMOAdvisorAgent:
    name = "pmo_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(
        self,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict:
        records_json = json.dumps(
            [
                {
                    "project_id": item.metadata["project_id"],
                    "project_name": item.metadata["project_name"],
                    "staleness_days": item.metadata["staleness_days"],
                    "is_stale": item.metadata["is_stale"],
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
            self.name, "advise", question=question, records_json=records_json
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
