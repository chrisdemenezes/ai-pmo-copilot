"""Migration 0004 (organization slug) -- additive column, deterministic
backfill, collision disambiguation, and reversibility (EO-015 Organizational
Identity Scope Correction)."""
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


def test_0004_backfills_slug_from_name(tmp_path):
    db_path = tmp_path / "migration_0004.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    _alembic(env, "upgrade", "0003")
    engine = create_engine(database_url)

    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO organizations (name, created_at) VALUES ('Demo Organization', CURRENT_TIMESTAMP)")
        )

    _alembic(env, "upgrade", "0004")

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("organizations")}
    assert "slug" in columns
    assert not columns["slug"]["nullable"]

    with engine.connect() as conn:
        slugs = {
            row.name: row.slug
            for row in conn.execute(text("SELECT name, slug FROM organizations"))
        }
    assert slugs["Organização Principal"] == "organizacao-principal"
    assert slugs["Demo Organization"] == "demo-organization"


def test_0004_disambiguates_colliding_slugs(tmp_path):
    db_path = tmp_path / "migration_0004_collision.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    _alembic(env, "upgrade", "0003")
    engine = create_engine(database_url)

    with engine.begin() as conn:
        # Two distinct names that slugify to the same base string.
        conn.execute(
            text("INSERT INTO organizations (name, created_at) VALUES ('Acme Inc', CURRENT_TIMESTAMP)")
        )
        conn.execute(
            text("INSERT INTO organizations (name, created_at) VALUES ('Acme Inc!', CURRENT_TIMESTAMP)")
        )

    _alembic(env, "upgrade", "0004")

    with engine.connect() as conn:
        slugs = [
            row.slug
            for row in conn.execute(
                text("SELECT slug FROM organizations WHERE name LIKE 'Acme%' ORDER BY id")
            )
        ]
    assert len(slugs) == len(set(slugs))  # no collision reaches the UNIQUE constraint
    assert slugs[0] == "acme-inc"
    assert slugs[1] == "acme-inc-2"


def test_0004_downgrade_removes_the_column_and_is_lossless_otherwise(tmp_path):
    db_path = tmp_path / "migration_0004_downgrade.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    _alembic(env, "upgrade", "head")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        count_before = conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar()

    _alembic(env, "downgrade", "0003")

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("organizations")}
    assert "slug" not in columns

    with engine.connect() as conn:
        count_after = conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar()
    assert count_after == count_before  # rows survive; only the column is gone

    _alembic(env, "upgrade", "head")  # full round trip works
