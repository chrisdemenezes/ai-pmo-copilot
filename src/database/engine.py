"""Shared engine construction for the AI PMO Copilot.

Centralizes DATABASE_URL resolution and connection-pool configuration so
AnalysisRepository (runtime) and Alembic (migrations) never diverge on how
the app connects to its database -- one seam, reused everywhere.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

DEFAULT_DATABASE_URL = "sqlite:///./ai_pmo_copilot.db"


def resolve_database_url(database_url: str | None = None) -> str:
    """Same precedence everywhere: explicit argument, then DATABASE_URL, then
    the SQLite fallback used by installs that haven't configured Postgres."""
    return database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def build_engine(database_url: str) -> Engine:
    """SQLite needs check_same_thread=False for the multi-threaded FastAPI dev
    server and has no meaningful pool to size. Postgres (the official
    environment from RC-2 onward) gets a configurable pool instead of
    SQLAlchemy's defaults -- every value is an env var, never a hardcoded
    constant, per the connection-pool review required for this Release
    Candidate."""
    if database_url.startswith("sqlite"):
        return create_engine(database_url, connect_args={"check_same_thread": False})

    return create_engine(
        database_url,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "30")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
        pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() != "false",
    )
