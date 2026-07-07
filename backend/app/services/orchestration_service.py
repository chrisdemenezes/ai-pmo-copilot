from core.orchestrator.router import Router
from core.orchestrator.agent_selector import AgentSelector
from core.orchestrator.workflow import Workflow

class OrchestrationService:
    def __init__(self):
        self.router = Router()
        self.selector = AgentSelector()
        self.workflow = Workflow()

    def execute(self, request: str):
        intent = self.router.classify(request)
        agent = self.selector.select(intent)
        return self.workflow.execute(agent, {"request": request})
