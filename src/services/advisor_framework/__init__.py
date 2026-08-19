"""Enterprise Advisor Framework (Wave 3, Digital PMO Intelligence, Fase 3).

Minimum viable execution infrastructure, grounded strictly in the audit of
the existing Risk Advisor (`docs/architecture/TECHNICAL-DESIGN-ENTERPRISE-ADVISOR-FRAMEWORK-FASE3.md`
§1) -- never a business domain, never a workflow engine, never a registry
of Advisors. `AdvisorFramework` is the single entry point a future Advisor
uses; it never exposes `PgVectorRepository`/`EmbeddingProvider` or any
persistence table, only `KnowledgeRepository`-mediated services
(`RagPipeline`, `EnterpriseMemoryService`) and the already-existing Digital
PMO Intelligence Foundation (`AIContextEngine`, `ObservabilityRecorder`,
`AIFoundationAudit`, `RecommendationEngine`, `ExplanationEngine`,
`render_analyst_prompt`).
"""
