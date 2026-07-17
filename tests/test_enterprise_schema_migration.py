"""Migration 0002 (Enterprise Foundation) -- data migration invariants.

Covers the Founder-mandated edge cases explicitly: NULL, empty, whitespace-only,
surrounding whitespace, capitalization variants, exact duplicates, and special
characters. Verifies the two hard invariants (row count identical before/after;
zero orphans) plus a lossless downgrade.
"""
import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text

LEGACY_NAMES = [
    "Migração SAP S/4HANA",      # special characters, accents
    "Migração SAP S/4HANA",      # exact duplicate -> same project
    "  Migração SAP S/4HANA  ",  # surrounding whitespace -> same project
    "migração sap s/4hana",      # capitalization variant -> DISTINCT project (no folding)
    "CRM Regional",
    None,                          # NULL -> fallback project
    "",                            # empty -> fallback project
    "   ",                         # whitespace-only -> fallback project
]

EXPECTED_PROJECT_NAMES = {
    "Migração SAP S/4HANA",
    "migração sap s/4hana",
    "CRM Regional",
    "(sem projeto)",
}


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result


def _seed_legacy_records(engine):
    with engine.begin() as conn:
        for name in LEGACY_NAMES:
            conn.execute(
                text(
                    "INSERT INTO analysis_records (kind, project_name, payload, created_at) "
                    "VALUES ('project_status', :n, '{}', CURRENT_TIMESTAMP)"
                ),
                {"n": name},
            )


def test_0002_migrates_legacy_records_deterministically(tmp_path):
    db_path = tmp_path / "migration_test.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    _alembic(env, "upgrade", "0001")
    engine = create_engine(database_url)
    _seed_legacy_records(engine)

    with engine.connect() as conn:
        count_before = conn.execute(text("SELECT COUNT(*) FROM analysis_records")).scalar()
    assert count_before == len(LEGACY_NAMES)

    _alembic(env, "upgrade", "head")

    with engine.connect() as conn:
        # Invariant 1: identical row count.
        count_after = conn.execute(text("SELECT COUNT(*) FROM analysis_records")).scalar()
        assert count_after == count_before

        # Invariant 2: zero orphans.
        orphans = conn.execute(
            text("SELECT COUNT(*) FROM analysis_records WHERE project_id IS NULL")
        ).scalar()
        assert orphans == 0

        # Deterministic grouping: exactly the 4 expected projects.
        names = {
            row[0] for row in conn.execute(text("SELECT name FROM projects")).fetchall()
        }
        assert names == EXPECTED_PROJECT_NAMES

        # Original free text untouched, record by record.
        stored = [
            row[0]
            for row in conn.execute(
                text("SELECT project_name FROM analysis_records ORDER BY id")
            ).fetchall()
        ]
        assert stored == LEGACY_NAMES

        # Whitespace variants collapse into the same project; case does not.
        base_pid, spaced_pid, cased_pid = (
            conn.execute(
                text(
                    "SELECT project_id FROM analysis_records WHERE project_name = :n "
                    "ORDER BY id LIMIT 1"
                ),
                {"n": n},
            ).scalar()
            for n in [
                "Migração SAP S/4HANA",
                "  Migração SAP S/4HANA  ",
                "migração sap s/4hana",
            ]
        )
        assert base_pid == spaced_pid
        assert cased_pid != base_pid

        # NULL/empty/whitespace share the single fallback project.
        fallback_ids = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT DISTINCT project_id FROM analysis_records "
                    "WHERE project_name IS NULL OR TRIM(project_name) = ''"
                )
            ).fetchall()
        }
        assert len(fallback_ids) == 1

        # Every project belongs to the seeded default organization.
        org_count = conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar()
        assert org_count == 1
        seeded_roles = {
            row[0] for row in conn.execute(text("SELECT name FROM roles")).fetchall()
        }
        assert seeded_roles == {"organization_admin", "pmo", "project_manager", "viewer"}


def test_0002_downgrade_is_lossless_for_v1(tmp_path):
    db_path = tmp_path / "downgrade_test.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    _alembic(env, "upgrade", "0001")
    engine = create_engine(database_url)
    _seed_legacy_records(engine)

    _alembic(env, "upgrade", "head")
    _alembic(env, "downgrade", "0001")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "analysis_records" in tables
    for gone in [
        "organizations",
        "users",
        "roles",
        "permissions",
        "role_permissions",
        "user_roles",
        "projects",
        "user_project_memberships",
    ]:
        assert gone not in tables

    columns = {col["name"] for col in inspector.get_columns("analysis_records")}
    assert "project_id" not in columns

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM analysis_records")).scalar()
        stored = [
            row[0]
            for row in conn.execute(
                text("SELECT project_name FROM analysis_records ORDER BY id")
            ).fetchall()
        ]
    assert count == len(LEGACY_NAMES)
    assert stored == LEGACY_NAMES

    # Full round trip: base -> head again on the same database works.
    _alembic(env, "downgrade", "base")
    _alembic(env, "upgrade", "head")
