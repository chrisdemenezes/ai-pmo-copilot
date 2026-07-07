class RiskReviewAgent:
    def __init__(self, model_client, prompt_registry):
        self.model_client = model_client
        self.prompt_registry = prompt_registry

    def analyze(self, project_context: str, project_name: str | None = None) -> dict:
        template = self.prompt_registry.get("risk_review", "analysis")
        final_prompt = template.format(
            project_name=project_name or "Nao informado",
            project_context=project_context,
        )
        model_output = self.model_client.generate(final_prompt)
        return {
            "agent": "risk_review",
            "project_name": project_name,
            "model_output": model_output,
        }
