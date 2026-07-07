"""First end-to-end PMO workflow."""

class PMOWorkflow:
    def execute(self, document, ai, repository):
        result = ai.process(document)
        return repository.save(result)
