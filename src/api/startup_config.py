"""Startup Configuration Contract (W7-5, Technical Design
`docs/architecture/TECHNICAL-DESIGN-W7-5-DEPLOYMENT-ENVIRONMENT-RELEASE-DISCIPLINE.md`
S5/S7): distinguishes DEV from STAGING/PRODUCTION and fails the process
closed, at boot, when critical configuration is missing or resolves to a
dev-only default outside DEV.
"""
import logging
import os
from typing import Literal

logger = logging.getLogger(__name__)

Environment = Literal["dev", "staging", "production"]

_VALID_ENVIRONMENTS: tuple[Environment, ...] = ("dev", "staging", "production")


class StartupConfigError(Exception):
    """Raised when ENVIRONMENT is invalid, or critical configuration is
    missing/invalid for ENVIRONMENT in {staging, production}."""


def resolve_environment(env_var: str = "ENVIRONMENT") -> Environment:
    raw = os.getenv(env_var, "dev").strip().lower()
    if raw not in _VALID_ENVIRONMENTS:
        raise StartupConfigError(f"{env_var}={raw!r} is invalid. Expected one of {_VALID_ENVIRONMENTS}.")
    return raw  # type: ignore[return-value]


def collect_startup_config_problems(environment: Environment) -> list[str]:
    if environment == "dev":
        return []

    problems: list[str] = []

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        problems.append("DATABASE_URL is not set (would silently fall back to SQLite).")
    elif database_url.startswith("sqlite"):
        problems.append(f"DATABASE_URL={database_url!r} resolves to SQLite, not permitted outside dev.")

    if not os.getenv("API_KEY"):
        problems.append("API_KEY is not set.")

    llm_provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
    if llm_provider == "mock":
        problems.append("LLM_PROVIDER=mock is not permitted outside dev.")
    elif llm_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        problems.append("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.")

    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    if embedding_provider == "mock":
        problems.append("EMBEDDING_PROVIDER=mock is not permitted outside dev.")
    elif embedding_provider == "voyage" and not os.getenv("VOYAGE_API_KEY"):
        problems.append("EMBEDDING_PROVIDER=voyage but VOYAGE_API_KEY is not set.")

    if not os.getenv("CORS_ALLOWED_ORIGINS"):
        problems.append("CORS_ALLOWED_ORIGINS is not set (no browser origin would be allowed).")

    return problems


def validate_startup_config(environment: Environment) -> None:
    problems = collect_startup_config_problems(environment)
    if problems:
        for problem in problems:
            logger.error("Startup configuration error (ENVIRONMENT=%s): %s", environment, problem)
        raise StartupConfigError(
            f"{len(problems)} critical configuration problem(s) for ENVIRONMENT={environment!r}: "
            + "; ".join(problems)
        )
    logger.info("Startup configuration validated for ENVIRONMENT=%s", environment)
