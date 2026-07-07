class MeetingIntelligenceAgent:
    def __init__(self, model_client, prompt_registry):
        self.model_client = model_client
        self.prompt_registry = prompt_registry

    def analyze(self, transcript: str, project_name: str | None = None) -> dict:
        template = self.prompt_registry.get("meeting_intelligence", "analysis")
        final_prompt = template.format(
            project_name=project_name or "Nao informado",
            transcript=transcript,
        )
        model_output = self.model_client.generate(final_prompt)
        return {
            "agent": "meeting_intelligence",
            "project_name": project_name,
            "model_output": model_output,
        }
