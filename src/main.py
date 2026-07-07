from fastapi import FastAPI

from src.api.routes.intelligence import router as intelligence_router

app = FastAPI(title="AI PMO Copilot API", version="0.1.0")

app.include_router(intelligence_router, prefix="/api", tags=["intelligence"])


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "AI PMO Copilot"}
