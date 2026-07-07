def normalize_risks(risks: list[str]) -> list[str]:
    return [risk.strip() for risk in risks if risk.strip()]


def classify_impact(risk_count: int) -> str:
    if risk_count >= 5:
        return "HIGH"
    if risk_count >= 2:
        return "MEDIUM"
    return "LOW"
