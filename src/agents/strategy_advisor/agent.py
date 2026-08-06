"""Strategy Advisor (Wave 5, fourth Classe B Advisor, eighth and last
Advisor of the Wave), per `TECHNICAL-DESIGN-STRATEGY-ADVISOR.md`.

`evidence` always arrives already composed by `StrategyEvidenceAssembler`
-- a mix of `kind="declared_strategy"` (Portfolio/Program/Project's own
objective field) and `kind="status"`/`"risk"` (Project execution,
including when aggregated into a Program/Portfolio unit). Every record
carries both `"entity_id"` (always the real domain id, `metadata[
"real_entity_id"]`, for the model to name the unit in prose) and
`"source_id"` (always `item.source_id` -- the synthetic, disjoint id for
`declared_strategy`, the real `AnalysisRecord.id` for `status`/`risk`).

`"source_id"` is sent to the LLM strictly as an opaque technical citation
token to echo back in `cited_analysis_ids` -- `RecommendationEngine.build()`
correlates citations exclusively by `Evidence.source_id` (Technical Design
§10.2, no alternate correlation path exists), so this is the only value the
model can cite that resolves back to the right evidence item. Never
interpreted, never displayed -- the model always uses `"entity_name"`/
`"level"` for prose."""
import json

from src.agents.shared.output_parser import parse_structured_output
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext


class StrategyAdvisorAgent:
    name = "strategy_advisor"

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
                    "level": item.metadata["level"],
                    "entity_id": item.metadata["real_entity_id"],
                    "entity_name": item.metadata["entity_name"],
                    "kind": item.metadata["kind"],
                    "content": item.content,
                    "source_id": item.source_id,
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
