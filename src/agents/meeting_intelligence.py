"""Meeting intelligence agent connected to LLM layer."""

class MeetingIntelligenceAgent:
    def analyze(self, transcript, llm):
        return llm.generate(transcript)
