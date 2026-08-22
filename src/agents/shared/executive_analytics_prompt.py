"""Shared serialization of Executive Signal evidence into a prompt
variable (TD-017, V1 Post-Completion Technical Closure) -- used by
`PMOAdvisorAgent`/`ExecutiveAdvisorAgent` only, the same two
organization-wide Advisors Package M already extended (Portfolio/Risk/
Delivery/Strategy/Document/Governance Advisors stay untouched).

Deliberately never merged into `evidence`/`cited_analysis_ids`, same
discipline as `organizational_learning_prompt.py`: an Executive Signal is
a deterministic fact about metric trend/deviation, never a citable
AnalysisRecord-derived fact about one project's narrative content. Keeping
it a separate prompt variable means the Evidence Gate
(`AdvisorFramework.run()`'s `if not evidence`) and every existing
citation-building response field stay exactly as they were before this
module existed -- absence of Executive Signals never changes whether an
Advisor has "evidence" at all.
"""
import json

from src.services.ai_foundation.types import Evidence


def analytics_context_json(signals: list[Evidence]) -> str:
    return json.dumps(
        [
            {
                "signal_type": item.content["signal_type"],
                "severity": item.content["severity"],
                "scope": item.content["scope"],
                "metric": item.content["metric"],
                "current_value": item.content["current_value"],
                "baseline_or_threshold": item.content["baseline_or_threshold"],
                "trend": item.content["trend"],
                "period": item.content["period"],
                "evidence_reference": item.content["evidence_reference"],
            }
            for item in signals
        ],
        ensure_ascii=False,
    )
