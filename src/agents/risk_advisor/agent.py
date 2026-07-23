import json

from src.agents.shared.output_parser import parse_structured_output
from src.services.ai_foundation.observability import ObservabilityRecorder
from src.services.ai_foundation.prompt_composer import render_analyst_prompt
from src.services.ai_foundation.types import Evidence, SessionContext


class RiskAdvisorAgent:
    """Read-only conversational synthesis over already-identified risks.

    Never triggers a new analysis and never receives raw project context --
    only Evidence the Digital PMO Intelligence Foundation's AIContextEngine
    already resolved (Domain Blueprint §4/§6/§7; W3-2 Technical Design §10).
    """

    def __init__(self, model_client, prompt_registry):
        self.model_client = model_client
        self.prompt_registry = prompt_registry

    def advise(self, session: SessionContext, question: str, evidence: list[Evidence]) -> dict:
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
        final_prompt = render_analyst_prompt(
            self.prompt_registry,
            "risk_advisor",
            "advise",
            question=question,
            risks_json=risks_json,
        )
        raw_output = ObservabilityRecorder.record_call(
            "risk_advisor", session, self.model_client, final_prompt
        )
        return {
            "agent": "risk_advisor",
            "model_output": parse_structured_output(raw_output),
        }
