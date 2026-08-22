"""Executive Advisor (Wave 5, third Classe B Advisor -- AR-8 §4.2/D-104),
per `TECHNICAL-DESIGN-EXECUTIVE-ADVISOR.md`.

`evidence` always arrives already composed by `ExecutiveEvidenceAssembler`
-- at most two items per Project (one "status", one "risk"), each already
carrying `project_id`/`project_name` in `metadata`. Unlike
`PortfolioAdvisorAgent`/`PMOAdvisorAgent`, `content` is transported
unflattened (Technical Design §5): `kind="status"` and `kind="risk"` have
structurally different content schemas, so flattening both into one shape
would invent a form that exists in neither -- the `"kind"` field already
tells the model which shape to expect inside `"content"`."""
import json

from src.agents.shared.executive_analytics_prompt import analytics_context_json
from src.agents.shared.organizational_learning_prompt import learnings_json
from src.agents.shared.output_parser import parse_structured_output
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.knowledge_platform.rag_pipeline import RagContext


class ExecutiveAdvisorAgent:
    name = "executive_advisor"

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
                    "kind": item.metadata["kind"],
                    "content": item.content,
                    "source_analysis_id": item.source_id,
                    "source_created_at": str(item.metadata["created_at"]),
                }
                for item in evidence
            ],
            ensure_ascii=False,
        )
        # Package M (V1 Product & Capability Completion): same supporting-
        # context-only discipline as PMOAdvisorAgent -- never merged into
        # `evidence`/`cited_analysis_ids`.
        learnings = self.framework.gather_organizational_learnings(session.organization_id)
        # TD-017 (V1 Post-Completion Technical Closure): same discipline as
        # PMOAdvisorAgent -- never merged into `evidence`/`cited_analysis_ids`.
        analytics = self.framework.gather_executive_analytics_context(session.organization_id)
        final_prompt = self.framework.render_prompt(
            self.name,
            "advise",
            question=question,
            records_json=records_json,
            learnings_json=learnings_json(learnings),
            analytics_context=analytics_context_json(analytics),
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
