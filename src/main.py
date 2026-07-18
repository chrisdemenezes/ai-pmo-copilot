import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.request_context import RequestIDMiddleware, configure_logging
from src.api.routes.auth import build_auth_service
from src.api.routes.auth import router as auth_router
from src.api.routes.intelligence import router as intelligence_router
from src.llm.providers.base import ProviderConfigError, ProviderUnavailableError
from src.services.identity.auth_service import bootstrap_identities


def _cors_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent (Identity Layer, TDS Epic 2 Section 12/16): safe to run on
    # every boot, never recreates or resets an existing user.
    bootstrap_identities(build_auth_service())
    yield


app = FastAPI(title="AI PMO Copilot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)
app.add_middleware(RequestIDMiddleware)

app.include_router(intelligence_router, prefix="/api", tags=["intelligence"])
app.include_router(auth_router, prefix="/api", tags=["identity"])


@app.exception_handler(ProviderConfigError)
def provider_config_error_handler(request: Request, exc: ProviderConfigError):
    return JSONResponse(status_code=503, content={"error": "provider_config_error", "detail": str(exc)})


@app.exception_handler(ProviderUnavailableError)
def provider_unavailable_error_handler(request: Request, exc: ProviderUnavailableError):
    return JSONResponse(status_code=502, content={"error": "provider_unavailable", "detail": str(exc)})


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "AI PMO Copilot"}
