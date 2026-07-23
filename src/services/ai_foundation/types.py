from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Evidence:
    """One already-persisted, verifiable fact an Enterprise Analyst can cite.

    ``summary`` is opaque to the Foundation on purpose (Domain Blueprint §6):
    only the Analyst that requested this ``kind`` knows how to interpret it.
    """

    source_analysis_id: int
    source_created_at: datetime
    kind: str
    summary: dict


@dataclass(frozen=True)
class SessionContext:
    """Ephemeral, request-scoped identity -- never persisted beyond the
    request it was built for (Domain Blueprint §4.6: explicitly not
    Executive Memory)."""

    organization_id: int
    user_id: int
    session_id: str
    project_name: str | None = None


@dataclass(frozen=True)
class Recommendation:
    answer: str
    cited_evidence: list[Evidence] = field(default_factory=list)


@dataclass(frozen=True)
class Explanation:
    recommendation: Recommendation
    rationale: str
