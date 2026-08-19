"""Migration 0018 -- Wave 4 Enterprise Operations, Epic W4-1 (Event
Model + Event Publisher). Purely additive: creates `events` (Event
Audit) and `dead_letter_events` (minimal Dead Letter Strategy). Proven
on real PostgreSQL -- upgrade creates both tables, downgrade removes
them, and a re-upgrade round-trips cleanly.
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


def _table_exists(conn, table_name: str) -> bool:
    return conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table_name},
    ).scalar() is not None


def test_0018_upgrade_creates_tables_and_downgrade_removes_them():
    with temp_database_url("migration_0018") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        engine = create_engine(database_url)

        _alembic(env, "upgrade", "0017")
        with engine.connect() as conn:
            assert _table_exists(conn, "events") is False
            assert _table_exists(conn, "dead_letter_events") is False

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _table_exists(conn, "events") is True
            assert _table_exists(conn, "dead_letter_events") is True

            org_id = conn.execute(
                text(
                    "INSERT INTO organizations (name, slug, created_at) "
                    "VALUES ('Org A', 'org-a', now()) RETURNING id"
                )
            ).scalar()
            event_id = conn.execute(
                text(
                    "INSERT INTO events "
                    "(event_id, event_type, correlation_id, timestamp, organization_id, "
                    "origin, payload_version, payload) "
                    "VALUES ('evt-1', 'portfolio.created', 'corr-1', now(), :o, "
                    "'domain_service', 1, '{}') RETURNING id"
                ),
                {"o": org_id},
            ).scalar()
            assert event_id is not None

            dead_letter_id = conn.execute(
                text(
                    "INSERT INTO dead_letter_events "
                    "(event_id, organization_id, correlation_id, attempts, last_error, created_at) "
                    "VALUES ('evt-1', :o, 'corr-1', 3, 'boom', now()) RETURNING id"
                ),
                {"o": org_id},
            ).scalar()
            assert dead_letter_id is not None

        _alembic(env, "downgrade", "0017")
        with engine.connect() as conn:
            assert _table_exists(conn, "dead_letter_events") is False
            assert _table_exists(conn, "events") is False
            # Fase 2 tables untouched by this downgrade.
            assert _table_exists(conn, "memory_records") is True

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _table_exists(conn, "events") is True
            assert _table_exists(conn, "dead_letter_events") is True

        engine.dispose()
