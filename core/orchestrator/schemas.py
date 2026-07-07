from pydantic import BaseModel

class OrchestrationRequest(BaseModel):
    request: str
    project_id: str | None = None

class OrchestrationResponse(BaseModel):
    selected_agent: str
    result: dict
