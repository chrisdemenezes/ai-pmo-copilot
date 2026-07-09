from string import Template

from src.agents.shared.output_parser import parse_structured_output


class ProjectStatusAgent:
    def __init__(self, model_client, prompt_registry):
        self.model_client = model_client
        self.prompt_registry = prompt_registry

    def analyze(self, project_context: str, project_name: str | None = None) -> dict:
        template = self.prompt_registry.get("project_status", "analysis")
        final_prompt = Template(template).safe_substitute(
            project_name=project_name or "Nao informado",
            project_context=project_context,
        )
        raw_output = self.model_client.generate(final_prompt)
        return {
            "agent": "project_status",
            "project_name": project_name,
            "model_output": parse_structured_output(raw_output),
        }
