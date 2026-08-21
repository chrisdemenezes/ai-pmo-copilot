"""Shared serialization of Organizational Learning evidence into a prompt
variable (Package M, V1 Product & Capability Completion) -- used by
`PMOAdvisorAgent`/`ExecutiveAdvisorAgent` only, the two Advisors whose own
organizational scope makes a recurring cross-project pattern a meaningful
signal (Portfolio/Risk/Delivery/Strategy/Document/Governance Advisors stay
untouched, per-project or RAG-scoped by design).

Deliberately never merged into `evidence`/`cited_analysis_ids`: an
Organizational Learning is supporting context about a pattern across many
projects, never a citable fact about one project the way an
AnalysisRecord-derived Evidence item is. Keeping it a separate prompt
variable means the Evidence Gate (`AdvisorFramework.run()`'s `if not
evidence`) and every existing citation-building response field stay
exactly as they were before this module existed -- absence of Learnings
never changes whether an Advisor has "evidence" at all.
"""
import json

from src.services.ai_foundation.types import Evidence


def learnings_json(learnings: list[Evidence]) -> str:
    return json.dumps(
        [
            {
                "category": item.content["category"],
                "description": item.content["description"],
                "occurrences": item.content["occurrences"],
                "project_names": item.content["project_names"],
            }
            for item in learnings
        ],
        ensure_ascii=False,
    )
