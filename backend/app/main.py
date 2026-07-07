from fastapi import FastAPI

app = FastAPI(title="AI PMO Copilot API")

@app.get("/")
def health_check():
    return {"status": "AI PMO Copilot API running"}
