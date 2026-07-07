class AgentSelector:
    """Selects specialized agents based on classified intent."""

    AGENTS = {
        "MEETING_ANALYSIS": "meeting_intelligence",
        "PROJECT_HEALTH": "project_intelligence"
    }

    def select(self, intent: str):
        return self.AGENTS.get(intent, "general")
