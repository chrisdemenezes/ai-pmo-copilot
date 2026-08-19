"""Migration 0019 -- Wave 4 Enterprise Operations, Epic W4-4 (Workflow
Runtime + Execution Tracking). Purely additive: creates
`workflow_executions` with `UNIQUE(event_id, workflow_name)` -- the
idempotency key enforced at the database, not only in application code.
Proven on real PostgreSQL -- upgrade creates the table and the
constraint, downgrade removes it, and a re-upgrade round-trips cleanly.
"""
import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

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


def test_0019_upgrade_creates_table_and_downgrade_removes_it():
    with temp_database_url("migration_0019") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        engine = create_engine(database_url)

        _alembic(env, "upgrade", "0018")
        with engine.connect() as conn:
            assert _table_exists(conn, "workflow_executions") is False

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            org_id = conn.execute(
                text(
                    "INSERT INTO organizations (name, slug, created_at) "
                    "VALUES ('Org A', 'org-a', now()) RETURNING id"
                )
            ).scalar()
            conn.execute(
                text(
                    "INSERT INTO events "
                    "(event_id, event_type, correlation_id, timestamp, organization_id, "
                    "origin, payload_version, payload) "
                    "VALUES ('evt-1', 'document.indexed', 'corr-1', now(), :o, "
                    "'knowledge_repository', 1, '{}')"
                ),
                {"o": org_id},
            )
            conn.commit()

        with engine.connect() as conn:
            assert _table_exists(conn, "workflow_executions") is True
            execution_id = conn.execute(
                text(
                    "INSERT INTO workflow_executions "
                    "(event_id, workflow_name, organization_id, correlation_id, status, started_at) "
                    "VALUES ('evt-1', 'wf-example', :o, 'corr-1', 'running', now()) RETURNING id"
                ),
                {"o": org_id},
            ).scalar()
            assert execution_id is not None
            conn.commit()

            # UNIQUE(event_id, workflow_name) enforced at the database.
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO workflow_executions "
                        "(event_id, workflow_name, organization_id, correlation_id, status, started_at) "
                        "VALUES ('evt-1', 'wf-example', :o, 'corr-1', 'running', now())"
                    ),
                    {"o": org_id},
                )
            conn.rollback()

        _alembic(env, "downgrade", "0018")
        with engine.connect() as conn:
            assert _table_exists(conn, "workflow_executions") is False
            # W4-1 tables untouched by this downgrade.
            assert _table_exists(conn, "events") is True
            assert _table_exists(conn, "dead_letter_events") is True

        _alembic(env, "upgrade", "head")
        with engine.connect() as conn:
            assert _table_exists(conn, "workflow_executions") is True

        engine.dispose()
