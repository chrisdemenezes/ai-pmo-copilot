import json
from string import Template

from src.agents.shared.output_parser import parse_structured_output


class RiskAdvisorAgent:
    """Read-only conversational synthesis over already-identified risks.

    Never triggers a new analysis and never receives raw project context --
    only the already-structured risk list a caller resolved beforehand
    (Domain Blueprint §4/§6/§7).
    """

    def __init__(self, model_client, prompt_registry):
        self.model_client = model_client
        self.prompt_registry = prompt_registry

    def advise(self, question: str, risks: list[dict]) -> dict:
        template = self.prompt_registry.get("risk_advisor", "advise")
        risks_json = json.dumps(
            [
                {
                    "description": risk.get("description"),
                    "probability": risk.get("probability"),
                    "impact": risk.get("impact"),
                    "mitigation": risk.get("mitigation"),
                    "escalation_recommendation": risk.get("escalation_recommendation"),
                    "source_analysis_id": risk.get("source_analysis_id"),
                    "source_created_at": str(risk.get("source_created_at")),
                }
                for risk in risks
            ],
            ensure_ascii=False,
        )
        final_prompt = Template(template).safe_substitute(
            question=question,
            risks_json=risks_json,
        )
        raw_output = self.model_client.generate(final_prompt)
        return {
            "agent": "risk_advisor",
            "model_output": parse_structured_output(raw_output),
        }
