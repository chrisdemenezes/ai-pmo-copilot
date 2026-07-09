import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes.intelligence import router as intelligence_router
from src.llm.providers.base import ProviderConfigError, ProviderUnavailableError


def _cors_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="AI PMO Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(intelligence_router, prefix="/api", tags=["intelligence"])


@app.exception_handler(ProviderConfigError)
def provider_config_error_handler(request: Request, exc: ProviderConfigError):
    return JSONResponse(status_code=503, content={"error": "provider_config_error", "detail": str(exc)})


@app.exception_handler(ProviderUnavailableError)
def provider_unavailable_error_handler(request: Request, exc: ProviderUnavailableError):
    return JSONResponse(status_code=502, content={"error": "provider_unavailable", "detail": str(exc)})


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "AI PMO Copilot"}
