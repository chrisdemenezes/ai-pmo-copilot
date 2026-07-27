"""Enterprise Knowledge Platform (Wave 3, Digital PMO Intelligence, Fase 1).

Infrastructure only -- never a business domain (Founder directive,
`WAVE-3-DOMAIN-BLUEPRINT.md` Princípio 1). `KnowledgeRepository` is the
single entry point every future caller (an Advisor, via the Advisor
Framework) uses; `VectorRepository` and `EmbeddingProvider` are internal
collaborators, never imported outside this package.
"""
