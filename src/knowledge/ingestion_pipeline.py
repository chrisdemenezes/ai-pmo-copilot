"""Enterprise knowledge ingestion pipeline foundation."""

class KnowledgePipeline:
    def ingest(self, document):
        return {"document": document, "embedded": True}
