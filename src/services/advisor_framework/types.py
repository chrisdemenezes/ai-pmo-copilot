"""Contract types for the Enterprise Advisor Framework (Fase 3).

`AdvisorContract` is not a speculative abstraction for hypothetical future
Advisors -- it names, verbatim, the shape `RiskAdvisorAgent.advise()`
already implements today by duck typing (audit, Technical Design §1/§2).
No generic `input_schema`/`output_schema` per Advisor is introduced: every
Advisor's output is the same `dict` shape already required by
`RecommendationEngine.build()`.
"""
from typing import Protocol

from src.services.ai_foundation.types import Evidence, SessionContext


class AdvisorExecutionError(Exception):
    """Raised by `AdvisorFramework.run()` when an Advisor's output does not
    match the shape `RecommendationEngine.build()` requires (`structured`
    truthy, `answer` a str) -- the same validation the Risk Advisor route
    already performs inline today, centralized here."""


class AdvisorContract(Protocol):
    name: str

    def advise(self, session: SessionContext, question: str, evidence: list[Evidence]) -> dict:
        ...
