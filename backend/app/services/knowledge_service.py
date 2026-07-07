from knowledge.retrieval_service import RetrievalService


class KnowledgeService:
    """Provides project context to AI agents."""

    def __init__(self):
        self.retrieval = RetrievalService()

    def get_context(self, query: str):
        return self.retrieval.search(query)
