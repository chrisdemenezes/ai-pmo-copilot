"""RC-2 -- shared PostgreSQL test-database helper.

PostgreSQL is the official database from RC-2 onward (see
docs/architecture/DECISION-LOG.md and the RC-2 mission report). Every test
that used to create its own throwaway SQLite file now creates an equally
isolated, equally throwaway Postgres database instead, through this single
seam -- no test file duplicates the admin-connection/create/drop logic.
"""
import os
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine, text


def _admin_connection_url() -> str:
    return os.environ.get(
        "TEST_POSTGRES_ADMIN_URL",
        "postgresql://aipmo:aipmo@localhost:5432/postgres",
    )


_vector_extension_ready = False


def _ensure_vector_extension_on_template(admin_url: str) -> None:
    """`CREATE DATABASE` clones `template1`, not the admin connection's own
    database -- so the `vector` extension has to exist there, once, before
    any test database is created. Migration 0016's own `CREATE EXTENSION
    IF NOT EXISTS vector` only reaches whichever database `alembic upgrade
    head` is pointed at; it never touches `template1`, and paths that
    provision schema via `Base.metadata.create_all()` (`AnalysisRepository`)
    don't run migrations at all. Idempotent and cached per process."""
    global _vector_extension_ready
    if _vector_extension_ready:
        return
    template_url = admin_url.rsplit("/", 1)[0] + "/template1"
    template_engine = create_engine(template_url, isolation_level="AUTOCOMMIT")
    try:
        with template_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    finally:
        template_engine.dispose()
    _vector_extension_ready = True


@contextmanager
def temp_database_url(prefix: str):
    """Creates a uniquely-named Postgres database, yields its connection
    URL, and drops it afterward -- the Postgres equivalent of a pytest
    tmp_path SQLite file, with the same one-database-per-test isolation."""
    admin_url = _admin_connection_url()
    _ensure_vector_extension_on_template(admin_url)
    db_name = f"{prefix}_{uuid.uuid4().hex[:12]}"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        base_url = admin_url.rsplit("/", 1)[0]
        yield f"{base_url}/{db_name}"
    finally:
        with admin_engine.connect() as conn:
            # Only client backends -- autovacuum/background workers for this
            # database run under the server's own superuser context and a
            # non-superuser admin role (the common case for local Postgres)
            # cannot terminate those, even though it owns the database.
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid() "
                    "AND backend_type = 'client backend'"
                ),
                {"name": db_name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin_engine.dispose()
