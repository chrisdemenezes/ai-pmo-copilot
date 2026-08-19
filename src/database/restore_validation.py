"""Restore Contract (W7-3 Resilience & Disaster Recovery, Etapa 2 --
Founder Decision, Technical Design `TECHNICAL-DESIGN-W7-3-RESILIENCE-DISASTER-RECOVERY.md`
Section 9): definitively replaces the historical `PRI-008` Section 4 gap
-- post-restore validation that checked only `analysis_records`, the
single table that existed when that runbook was written, never the other
20 tables the real schema has grown to carry.

Expected tables are derived from `Base.metadata` (`src.database.repository`,
which imports `src.database.models` for its side effect of registering
every table) -- never a hardcoded count, per the Founder's explicit
instruction, so this validation never silently drifts from the real
schema as new migrations are added.

`pg_restore` exiting 0 only proves the archive was syntactically applied.
This module is what proves the result is functionally trustworthy:
schema/migration identity, referential integrity, and the production
embedding contract (`vector_dims == KNOWLEDGE_EMBEDDING_DIM`) -- the
concrete substitute mandated for the historical gap.
"""
import logging
from dataclasses import dataclass

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from src.database.models import KNOWLEDGE_EMBEDDING_DIM
from src.database.repository import Base

logger = logging.getLogger(__name__)

# Referential integrity checks a restored database must satisfy
# structurally, regardless of how much data it carries (Technical Design
# Section 9's FK-orphan checks, reused verbatim). Each query returns the
# count of orphaned child rows -- must always be 0.
_ORPHAN_CHECKS: dict[str, str] = {
    "programs.portfolio_id -> portfolios.id": (
        "SELECT COUNT(*) FROM programs p LEFT JOIN portfolios pf ON p.portfolio_id = pf.id "
        "WHERE pf.id IS NULL"
    ),
    "document_versions.document_id -> documents.id": (
        "SELECT COUNT(*) FROM document_versions dv LEFT JOIN documents d ON dv.document_id = d.id "
        "WHERE d.id IS NULL"
    ),
    "chunks.document_version_id -> document_versions.id": (
        "SELECT COUNT(*) FROM chunks c LEFT JOIN document_versions dv ON c.document_version_id = dv.id "
        "WHERE dv.id IS NULL"
    ),
}

# CRITICAL tables (Technical Design Section 4) whose emptiness after
# restoring a source known to have been populated indicates a truncated/
# partial restore -- never checked against a source that might legitimately
# be a fresh, empty install (`expect_populated`, opt-in only).
_CRITICAL_TABLES_FOR_EMPTINESS_CHECK: tuple[str, ...] = ("organizations", "users", "audit_logs", "events")


@dataclass(frozen=True)
class RestoreValidationResult:
    ok: bool
    problems: tuple[str, ...]


def _expected_head_revision(alembic_ini_path: str = "alembic.ini") -> str | None:
    config = Config(alembic_ini_path)
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def validate_restore(engine: Engine, *, expect_populated: bool = False) -> RestoreValidationResult:
    """Structural + functional validation of a just-restored database.
    Never mutates anything -- every check is a read.

    `expect_populated=True` additionally asserts the CRITICAL tables are
    non-empty -- only meaningful when the caller knows the backup's source
    genuinely had data (e.g. a real DR Drill or a Backup Contract
    integrity test), never assumed for an arbitrary restore.
    """
    problems: list[str] = []

    with engine.connect() as conn:
        # 1. Migration head (Failure Scenario L, "restore incompatível com
        # release/schema").
        try:
            expected_head = _expected_head_revision()
        except Exception as exc:  # noqa: BLE001 -- config resolution failure must be reported, never crash
            problems.append(f"could not resolve the expected Alembic head revision: {exc}")
            expected_head = None

        applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if applied is None:
            problems.append("alembic_version has no applied revision -- schema was never migrated")
        elif expected_head is not None and applied != expected_head:
            problems.append(
                f"schema is at revision {applied!r}, expected head {expected_head!r} -- "
                "this restore is from an older/incompatible release and must be migrated "
                "(`alembic upgrade head`) before being trusted"
            )

        # 2. Expected tables present -- derived from Base.metadata, never a
        # hardcoded count (Founder mandate).
        inspector = inspect(engine)
        real_tables = set(inspector.get_table_names())
        expected_tables = set(Base.metadata.tables.keys())
        missing = expected_tables - real_tables
        if missing:
            problems.append(f"missing tables after restore: {sorted(missing)}")
            # Every remaining check below assumes the tables it queries
            # exist -- stop here rather than raising a confusing SQL error.
            return RestoreValidationResult(ok=False, problems=tuple(problems))

        # 3. Referential integrity (structural, always checked).
        for description, query in _ORPHAN_CHECKS.items():
            count = conn.execute(text(query)).scalar()
            if count:
                problems.append(f"{count} orphaned row(s): {description}")

        # 4. Production embedding contract (pgvector dimension).
        bad_dimension_count = conn.execute(
            text("SELECT COUNT(*) FROM chunks WHERE vector_dims(embedding) != :dim"),
            {"dim": KNOWLEDGE_EMBEDDING_DIM},
        ).scalar()
        if bad_dimension_count:
            problems.append(
                f"{bad_dimension_count} chunk(s) with embedding dimension != {KNOWLEDGE_EMBEDDING_DIM}"
            )

        # 5. CRITICAL-table plausibility, opt-in only.
        if expect_populated:
            for table in _CRITICAL_TABLES_FOR_EMPTINESS_CHECK:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if count == 0:
                    problems.append(
                        f"table {table!r} is empty after restoring a source expected to be populated"
                    )

    result = RestoreValidationResult(ok=not problems, problems=tuple(problems))
    if result.ok:
        logger.info("Restore validation passed (expect_populated=%s)", expect_populated)
    else:
        logger.error("Restore validation FAILED: %s", "; ".join(result.problems))
    return result
