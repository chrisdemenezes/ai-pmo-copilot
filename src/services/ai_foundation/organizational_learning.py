"""Organizational Learning -> Executive Intelligence (STRATECH V1 Product &
Capability Completion, Founder Mandate, Fase 5, Package M).

Deliberate cross-language mirror of `web/lib/organizational-intelligence/
organizational-learnings.ts` (the "Aprendizados" page's own rule): same
deterministic algorithm -- exact textual equality of `description`, cut at
3+ distinct projects, sorted by occurrences desc then description asc.
Reimplemented here in Python (not shared code, since the frontend module
cannot be imported by the backend) so a recurring pattern already visible
to a human in the "Aprendizados" page reads as the SAME pattern when it
reaches an Advisor as evidence -- never two different rules computing two
different answers to "what recurs".

Consumes the exact same, already-tested accessors
(`ProjectSummaryService.list_latest_risks()`/`list_action_items()`) the
"Aprendizados" page's own BFF route already serves -- zero new query, zero
new repository method. Risks: latest analysis per project only (same
"current state" semantics `list_latest_risks()` already enforces). Actions:
every meeting-derived action item, no dedup (same "history of asks"
semantics `list_action_items()` already enforces) -- this asymmetry is
`ProjectSummaryService`'s own existing rule, not invented here.
"""
from dataclasses import dataclass

MIN_OCCURRENCES = 3
MAX_LEARNINGS = 5


@dataclass(frozen=True)
class OrganizationalLearning:
    category: str  # "risco" | "acao"
    description: str
    occurrences: int
    project_names: tuple[str, ...]


def _group_by_description(entries: list[dict]) -> dict[str, set[str]]:
    by_description: dict[str, set[str]] = {}
    for entry in entries:
        # Evidence First: an entry with no real project name is never
        # citable, so it never counts toward recurrence (same rule as
        # organizational-learnings.ts's groupByDescription()).
        project_name = entry.get("project_name")
        if project_name is None:
            continue
        description = entry.get("description")
        if not isinstance(description, str):
            continue
        by_description.setdefault(description, set()).add(project_name)
    return by_description


def _sorted_learnings(
    by_description: dict[str, set[str]], category: str
) -> list[OrganizationalLearning]:
    learnings = [
        OrganizationalLearning(
            category=category,
            description=description,
            occurrences=len(projects),
            project_names=tuple(sorted(projects)),
        )
        for description, projects in by_description.items()
        if len(projects) >= MIN_OCCURRENCES
    ]
    learnings.sort(key=lambda learning: (-learning.occurrences, learning.description))
    return learnings


def build_recurring_risks(risks: list[dict]) -> list[OrganizationalLearning]:
    return _sorted_learnings(_group_by_description(risks), "risco")


def build_recurring_actions(actions: list[dict]) -> list[OrganizationalLearning]:
    return _sorted_learnings(_group_by_description(actions), "acao")


def select_top_learnings(
    risk_learnings: list[OrganizationalLearning],
    action_learnings: list[OrganizationalLearning],
    limit: int = MAX_LEARNINGS,
) -> list[OrganizationalLearning]:
    """Fixed category order (risks before actions, same as the
    "Aprendizados" page's own UX Flow) -- never a global re-sort across
    categories, never fabricates fewer than the real count to reach
    `limit`."""
    return (risk_learnings + action_learnings)[:limit]
