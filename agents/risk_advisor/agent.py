from .processor import normalize_risks, classify_impact
from .schemas import RiskAnalysisResponse

class RiskAdvisorAgent:
    """Analyzes project risks and suggests mitigation actions."""

    def analyze(self, project_name: str, risks: list[str]):
        normalized = normalize_risks(risks)

        return RiskAnalysisResponse(
            risk_level=classify_impact(len(normalized)),
            identified_risks=normalized,
            mitigation_actions=["Review mitigation plan"],
            confidence_score=0.5
        )
