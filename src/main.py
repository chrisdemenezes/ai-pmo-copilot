import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.api.dependencies import build_repository
from src.api.request_context import RequestIDMiddleware, configure_logging
from src.api.routes.administration import router as administration_router
from src.api.routes.auth import build_auth_service
from src.api.routes.auth import router as auth_router
from src.api.routes.intelligence import router as intelligence_router
from src.api.routes.invitations import router as invitations_router
from src.api.routes.knowledge import router as knowledge_router
from src.api.routes.portfolio import router as portfolio_router
from src.api.routes.program import router as program_router
from src.api.routes.project_delivery import router as project_delivery_router
from src.api.startup_config import (
    collect_startup_config_problems,
    resolve_environment,
    validate_startup_config,
)
from src.database.repository import AnalysisRepository
from src.llm.providers.base import ProviderConfigError, ProviderUnavailableError
from src.services.identity.auth_service import bootstrap_identities

logger = logging.getLogger(__name__)


def _cors_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail-closed at boot (W7-5, Configuration Contract): staging/production
    # never become ready with missing/invalid critical configuration --
    # never lazily, on the first request that would have exercised it.
    # DEV's current permissive behavior is unchanged (validate_startup_config
    # is a no-op there by design).
    validate_startup_config(resolve_environment())
    # Idempotent (Identity Layer, TDS Epic 2 Section 12/16): safe to run on
    # every boot, never recreates or resets an existing user.
    bootstrap_identities(build_auth_service())
    yield


app = FastAPI(
    title="AI PMO Copilot API",
    version="0.3.0",
    description=(
        "STRATECH V2 -- Wave 2 (Enterprise Platform): Enterprise Domain "
        "API (Portfolio/Program/Project Delivery) with RBAC fine-grained "
        "enforcement, plus Enterprise Administration (Organizations, "
        "Users, Roles, Audit Log). All routes are org-scoped via the "
        "X-Stratech-* institutional headers and require both a valid "
        "X-API-Key and the relevant permission. See "
        "docs/architecture/DOMAIN-BLUEPRINT-RBAC.md and "
        "DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)
app.add_middleware(RequestIDMiddleware)

app.include_router(intelligence_router, prefix="/api", tags=["intelligence"])
app.include_router(auth_router, prefix="/api", tags=["identity"])
app.include_router(portfolio_router, prefix="/api", tags=["portfolio"])
app.include_router(program_router, prefix="/api", tags=["program"])
app.include_router(project_delivery_router, prefix="/api", tags=["project-delivery"])
app.include_router(administration_router, prefix="/api", tags=["administration"])
app.include_router(invitations_router, prefix="/api", tags=["administration"])
app.include_router(knowledge_router, prefix="/api", tags=["knowledge"])


@app.exception_handler(ProviderConfigError)
def provider_config_error_handler(request: Request, exc: ProviderConfigError):
    return JSONResponse(status_code=503, content={"error": "provider_config_error", "detail": str(exc)})


@app.exception_handler(ProviderUnavailableError)
def provider_unavailable_error_handler(request: Request, exc: ProviderUnavailableError):
    return JSONResponse(status_code=502, content={"error": "provider_unavailable", "detail": str(exc)})


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "AI PMO Copilot"}


@app.get("/ready")
def readiness_check(repository: AnalysisRepository = Depends(build_repository)):
    """Distinct from `/health` (W7-5, Technical Design S12): "is this
    process alive" versus "is this instance apt to receive real traffic".
    Checks only what is cheap and objectively verifiable -- critical
    configuration (reusing the same Configuration Contract as the boot-time
    fail-fast check) and real database connectivity. Deliberately makes no
    LLM call -- no Technical Design has demonstrated a need for that here,
    and it would make every readiness probe expensive and provider-billed."""
    environment = resolve_environment()
    problems = collect_startup_config_problems(environment)

    try:
        with repository.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 -- readiness must report any broken dependency, never crash
        logger.error("Readiness check: database unreachable: %s", exc)
        problems = [*problems, f"database unreachable: {exc}"]

    if problems:
        return JSONResponse(status_code=503, content={"status": "not_ready", "problems": problems})
    return {"status": "ready"}
