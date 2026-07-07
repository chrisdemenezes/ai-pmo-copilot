"""Risk advisor agent."""

class RiskAdvisorAgent:
    def assess(self, risks, llm):
        return llm.generate(str(risks))
