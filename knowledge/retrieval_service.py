class RetrievalService:
    """Service responsible for contextual knowledge retrieval."""

    def search(self, query: str):
        return {
            "query": query,
            "context": []
        }
