"""Migration 0022 -- Project financial fields (V1 Product & Capability
Completion, Package K).

Proven on real PostgreSQL: the 3 new nullable columns exist on `projects`
after upgrade, the 7 Projects migration 0008 itself seeds (PJ-001..PJ-007,
in both fixed organizations) get illustrative financial values, a
Project created outside the seed (e.g. by a real user) is never touched,
and downgrade clears those values and drops the columns cleanly.
"""
import os
import subprocess
import sys

from sqlalchemy import create_engine, text

from tests.db import temp_database_url


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    return (
        conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table_name, "c": column_name},
        ).scalar()
        is not None
    )


def test_0022_upgrade_seeds_financial_fields_and_downgrade_removes_them():
    with temp_database_url("migration_0022") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        engine = create_engine(database_url)

        _alembic(env, "upgrade", "0021")
        with engine.connect() as conn:
            assert not _column_exists(conn, "projects", "approved_budget")
            # A Project created outside the seed (e.g. by a real user, via
            # a not-yet-existing organization) must never gain seed values.
            org_id = conn.execute(
                text(
                    "INSERT INTO organizations (name, slug, created_at) "
                    "VALUES ('Org Real', 'org-real', now()) RETURNING id"
                )
            ).scalar()
            own_project_id = conn.execute(
                text(
                    "INSERT INTO projects (organization_id, name, created_at, code) "
                    "VALUES (:o, 'Projeto Próprio', now(), 'PJ-001') RETURNING id"
                ),
                {"o": org_id},
            ).scalar()
            conn.commit()

        _alembic(env, "upgrade", "0022")
        with engine.connect() as conn:
            assert _column_exists(conn, "projects", "approved_budget")
            assert _column_exists(conn, "projects", "actual_cost")
            assert _column_exists(conn, "projects", "forecast_cost")

            for org_name in ("Organização Principal", "Demo Organization"):
                seed_org_id = conn.execute(
                    text("SELECT id FROM organizations WHERE name = :n"), {"n": org_name}
                ).scalar()
                approved, actual, forecast = conn.execute(
                    text(
                        "SELECT approved_budget, actual_cost, forecast_cost FROM projects "
                        "WHERE organization_id = :o AND code = 'PJ-001'"
                    ),
                    {"o": seed_org_id},
                ).one()
                assert approved == 4_200_000.00
                assert actual == 3_100_000.00
                assert forecast == 5_000_000.00

            # Own Project shares the same code ("PJ-001") as a seeded one but
            # belongs to a different organization -- must stay untouched.
            own_approved = conn.execute(
                text("SELECT approved_budget FROM projects WHERE id = :id"),
                {"id": own_project_id},
            ).scalar()
            assert own_approved is None

        _alembic(env, "downgrade", "0021")
        with engine.connect() as conn:
            assert not _column_exists(conn, "projects", "approved_budget")
            assert not _column_exists(conn, "projects", "actual_cost")
            assert not _column_exists(conn, "projects", "forecast_cost")

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            seed_org_id = conn.execute(
                text("SELECT id FROM organizations WHERE name = 'Organização Principal'")
            ).scalar()
            approved = conn.execute(
                text(
                    "SELECT approved_budget FROM projects WHERE organization_id = :o AND code = 'PJ-001'"
                ),
                {"o": seed_org_id},
            ).scalar()
            assert approved == 4_200_000.00

        engine.dispose()
