from dataclasses import dataclass, field


@dataclass(frozen=True)
class Evidence:
    """One already-persisted, verifiable fact an Enterprise Advisor can cite.

    Generic across source systems (AR-9/D-088): ``source_type`` identifies
    which repository produced this fact (e.g. ``"analysis_record"``,
    ``"document_chunk"``), ``source_id`` is that source's own primary key --
    never reinterpreted across types. ``content`` remains opaque to the
    Foundation on purpose (Domain Blueprint §6): only the Advisor that
    requested this evidence knows how to interpret it. ``metadata`` carries
    auxiliary, source-specific facts (``created_at``, ``document_id``,
    ``score``, ...) without inventing a new top-level field per future
    ``source_type``.
    """

    source_type: str
    source_id: int
    source_label: str
    content: dict
    metadata: dict = field(default_factory=dict)


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
