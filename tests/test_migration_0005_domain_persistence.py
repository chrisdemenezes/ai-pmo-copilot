"""Migration 0005 (domain persistence) -- portfolios/programs tables,
Project domain fields (unified per DOMAIN-BLUEPRINT-PROJECT.md instead of a
separate projects_delivery table), and reversibility."""
import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


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


def test_0005_creates_portfolios_and_programs_tables(tmp_path):
    db_path = tmp_path / "migration_0005.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    _alembic(env, "upgrade", "head")
    engine = create_engine(database_url)
    inspector = inspect(engine)

    portfolio_columns = {col["name"] for col in inspector.get_columns("portfolios")}
    assert {"id", "organization_id", "name", "code", "health", "status"} <= portfolio_columns

    program_columns = {col["name"] for col in inspector.get_columns("programs")}
    assert {"id", "portfolio_id", "name", "code", "health", "status"} <= program_columns
    # Program has no organization_id of its own -- scoped transitively via
    # portfolio_id (Foundation Technical Design §3.10).
    assert "organization_id" not in program_columns


def test_0005_extends_projects_table_instead_of_creating_projects_delivery(tmp_path):
    db_path = tmp_path / "migration_0005_project.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    _alembic(env, "upgrade", "head")
    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert "projects_delivery" not in inspector.get_table_names()
    project_columns = {col["name"] for col in inspector.get_columns("projects")}
    assert {"program_id", "code", "health", "status", "progress_percentage"} <= project_columns
    # Pre-existing Épico-1 columns untouched.
    assert {"id", "organization_id", "name", "legacy_project_name"} <= project_columns


def test_0005_new_project_columns_are_nullable_and_dont_break_legacy_rows(tmp_path):
    db_path = tmp_path / "migration_0005_legacy.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    _alembic(env, "upgrade", "0004")
    engine = create_engine(database_url)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO organizations (name, slug, created_at) "
                "VALUES ('Org Legacy', 'org-legacy', CURRENT_TIMESTAMP)"
            )
        )
        org_id = conn.execute(
            text("SELECT id FROM organizations WHERE slug = 'org-legacy'")
        ).scalar()
        conn.execute(
            text(
                "INSERT INTO projects (organization_id, name, created_at) "
                "VALUES (:org_id, 'Legacy Project', CURRENT_TIMESTAMP)"
            ),
            {"org_id": org_id},
        )

    _alembic(env, "upgrade", "head")

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT name, program_id, code FROM projects WHERE name = 'Legacy Project'")
        ).one()
    assert row.name == "Legacy Project"
    assert row.program_id is None
    assert row.code is None


def test_0005_downgrade_is_lossless_and_full_round_trip_works(tmp_path):
    db_path = tmp_path / "migration_0005_downgrade.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    # Pinned to 0005 (this test's subject) since migration 0008 (domain
    # seed) exists: going all the way to head would mix 0008's data
    # seeding/removal into an assertion about 0005's schema losslessness
    # (0008 has its own dedicated tests).
    _alembic(env, "upgrade", "0005")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        projects_before = conn.execute(text("SELECT COUNT(*) FROM projects")).scalar()

    _alembic(env, "downgrade", "0004")

    inspector = inspect(engine)
    assert "portfolios" not in inspector.get_table_names()
    assert "programs" not in inspector.get_table_names()
    project_columns = {col["name"] for col in inspector.get_columns("projects")}
    assert "program_id" not in project_columns
    assert "code" not in project_columns
    assert "start_date" not in project_columns
    assert "planned_end_date" not in project_columns
    assert "actual_end_date" not in project_columns

    with engine.connect() as conn:
        projects_after = conn.execute(text("SELECT COUNT(*) FROM projects")).scalar()
    assert projects_after == projects_before  # rows survive; only columns/tables are gone

    _alembic(env, "upgrade", "head")  # full round trip works, twice in a row
    _alembic(env, "downgrade", "0004")
    _alembic(env, "upgrade", "head")
