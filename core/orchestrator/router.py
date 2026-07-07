class Router:
    """Routes user requests to the appropriate AI capability."""

    def classify(self, request: str) -> str:
        text = request.lower()

        if "reuni" in text or "ata" in text:
            return "MEETING_ANALYSIS"

        if "status" in text or "saúde" in text or "projeto" in text:
            return "PROJECT_HEALTH"

        return "GENERAL_ASSISTANT"
