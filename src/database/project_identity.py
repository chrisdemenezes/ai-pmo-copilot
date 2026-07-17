"""Deterministic rules that map a legacy free-text project name to a Project.

These rules are the single source of truth for the application. The 0002
migration carries a frozen inline copy of the same rules on purpose:
migrations must keep producing the historical result even if this module
evolves later (Blueprint ADR-V2-003 -- one Project per distinct name,
original text preserved, no similarity-based merging).

Rule, in order:
1. None stays None (no name given).
2. Leading/trailing whitespace is stripped -- surrounding spaces are treated
   as accidental input, not identity.
3. An empty result (was empty or whitespace-only) maps to None.
4. Everything else -- capitalization, accents, special characters -- is
   preserved exactly: "Projeto ALFA" and "projeto alfa" are two different
   Projects until an admin reconciles them (future mechanism, ADR-V2-003).

A None key is stored under the single fallback Project FALLBACK_PROJECT_NAME.
"""

DEFAULT_ORGANIZATION_NAME = "Organização Principal"
FALLBACK_PROJECT_NAME = "(sem projeto)"


def normalize_project_name(raw: str | None) -> str | None:
    """Return the canonical Project name for a legacy free-text value.

    None means "no identifiable project" -- the caller must use the fallback
    Project rather than invent a name.
    """
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped if stripped else None
