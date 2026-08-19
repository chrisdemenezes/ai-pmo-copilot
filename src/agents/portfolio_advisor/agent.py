"""Portfolio Advisor (Wave 5, first Classe B Advisor -- AR-8 §4.2/D-104),
per `TECHNICAL-DESIGN-PORTFOLIO-ADVISOR.md`.

`evidence` always arrives already composed by `PortfolioEvidenceAssembler`
-- one item per Project, already the most recent. This agent never
reorders, never filters, never weighs -- it only serializes to JSON, same
discipline as `RiskAdvisorAgent`/`DeliveryAdvisorAgent`. The order items
appear in `evidence` carries no priority (AR-12 §3); the prompt instructs
the model accordingly, never a structural mechanism."""
import json

from src.agents.shared.output_parser import parse_structured_output
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext


class PortfolioAdvisorAgent:
    name = "portfolio_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(
        self,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict:
        projects_json = json.dumps(
            [
                {
                    "project_id": item.metadata["project_id"],
                    "project_name": item.metadata["project_name"],
                    "program_id": item.metadata["program_id"],
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
            self.name, "advise", question=question, projects_json=projects_json
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
