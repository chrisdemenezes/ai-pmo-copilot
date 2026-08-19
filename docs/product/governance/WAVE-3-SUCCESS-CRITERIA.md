# Wave 3 Success Criteria — Digital PMO Intelligence

**Status:** artefato obrigatório, exigido pelo Founder ("Founder Decision — Wave 3", 2026-07-27) como precondição explícita antes do primeiro commit de implementação da Fase 1. Define a Definition of Done de cada Fase e os critérios objetivos de encerramento da Wave inteira.
**Publicado antes de qualquer código desta Wave** — nenhuma linha de implementação precede este documento.
**Base:** `WAVE-3-DOMAIN-BLUEPRINT.md` (e os 7 Blueprints subordinados), `AR-6-WAVE-3-DOMAIN-BLUEPRINT-REVIEW.md` (aprovado sem ressalvas), `WAVE-3-EXECUTION-PLAN.md` (ordem mandatória de Fases e Gates).

---

## 0. Diretrizes do Founder que este documento operacionaliza

- Implementar estritamente conforme o Blueprint aprovado.
- Usar o Risk Advisor como primeiro consumidor e referência arquitetural para validação do framework.
- Não introduzir novos providers, registries ou camadas de abstração fora do previsto no Blueprint e no CLAUDE.md.
- Manter Vector Store e Framework de Orquestração como infraestrutura, nunca como domínios de negócio.
- Cada Epic segue o ciclo institucional completo: Domain Blueprint → Revisão Arquitetural → Aprovação do Founder → Implementação → Atualização de Decision Log/CHANGELOG/Mission Control.

Este documento não reabre nenhuma dessas diretrizes — apenas as torna verificáveis por critério objetivo, Fase a Fase.

---

## 1. Definition of Done por Fase

### Fase 1 — Foundation (Enterprise Knowledge Platform: infraestrutura base)

| Critério | Verificável por |
|---|---|
| `pgvector` habilitado como extensão do Postgres já oficial (nenhum banco novo) | Migração testada em PostgreSQL real, upgrade/downgrade íntegros |
| `KnowledgeRepository`/`VectorRepository`/`EmbeddingProvider` implementados como Protocol/abstração, nenhum componente de domínio referencia `pgvector` diretamente | Busca global (`grep`) por importações diretas de `pgvector`/SQL vetorial fora da implementação concreta |
| Toda entidade nova (`Document`, `DocumentVersion`, `Chunk`) escopada por `organization_id` | Teste de isolamento cross-tenant, mesmo padrão de `test_domain_repository.py` |
| Nenhum Advisor ainda consome a plataforma nesta Fase | Busca global confirma zero referência de `src/agents/` a `knowledge_platform` |
| `ruff check src tests` e `pytest` 100% verdes, sem novo skip não justificado | Execução da suíte completa |
| Documentação atualizada (Decision Log, CHANGELOG, Mission Control) | Diff da entrega |

### Fase 2 — Knowledge Services (Semantic Search, RAG Pipeline, Enterprise Memory Model, Versionamento)

| Critério | Verificável por |
|---|---|
| RAG Pipeline funcional ponta a ponta, provado por um Advisor de referência mínimo (Document Advisor) | Teste de integração cobrindo pergunta → recuperação → citação real de `chunk_id` |
| Grounding: nenhuma citação sem chunk real incluído no contexto enviado ao `LLMProvider` | Teste do guard-rail (`RecommendationEngine.build()` estendido), análogo ao já existente para `analysis_id` |
| Enterprise Memory Model implementado com a checklist de colisão (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §0) revalidada e ainda verdadeira | Revisão explícita antes do merge; nenhuma alteração a `web/lib/executive-memory/` |
| Versionamento/atualização incremental funcionando (reingestão não sobrescreve, gera nova versão) | Teste de reingestão comprovando histórico preservado |

### Fase 3 — Enterprise Advisor Framework

| Critério | Verificável por |
|---|---|
| `AdvisorContract` implementado e documentado | Código + testes de contrato |
| `RiskAdvisorAgent` migrado para o novo contrato **sem regressão** | Suíte E2E do Risk Advisor 100% verde antes e depois da migração, contrato HTTP `POST /risk-advisor/ask` inalterado |
| Observabilidade e auditoria uniformes via Framework (nenhum Advisor implementa a própria) | Teste confirmando `ObservabilityRecorder`/`AIFoundationAudit` acionados pela invocação via Framework, não por código do Advisor |
| Isolamento entre Advisors comprovado | Teste simulando falha em um Advisor sem afetar outro |

### Fase 4 — Enterprise Advisors (implementação individual)

| Critério | Verificável por |
|---|---|
| Cada um dos 7 Advisors restantes implementado usando exclusivamente a infraestrutura das Fases 1-3 | Auditoria de código confirmando ausência de infraestrutura própria por Advisor |
| Cada Advisor cita evidência real (nunca alucinada) — mesmo guard-rail do Risk Advisor | Teste por Advisor cobrindo o caminho `no_evidence()` |
| `ENTERPRISE-ADVISOR-CATALOG.md` atualizado de "não implementado" para "implementado" por Advisor, à medida que cada um é concluído | Diff da entrega, Fase a Fase |
| PMO Advisor como segundo Advisor generalizado (após o Risk Advisor), provando o Framework antes da expansão aos demais 6 | Ordem de commits/PRs confirma a sequência |

### W3-8 — Executive Intelligence (após Fase 4)

| Critério | Verificável por |
|---|---|
| Camada de Executive Intelligence consumindo Knowledge Platform + Advisors sobre Portfolio/Program/Project, sem introduzir métrica que o Executive Dashboard (V1) não exiba | Auditoria de consistência Dashboard vs. Executive Advisor |

---

## 2. Guardrails permanentes (válidos em todas as Fases, nunca relaxados)

1. **Infraestrutura nunca é domínio** — Vector Store e Framework de Orquestração jamais aparecem como conceito de negócio em nenhuma camada de apresentação ou nome de Advisor.
2. **Nenhum segundo provider/registry** — `LLMProvider`/`PromptRegistry` permanecem os únicos; `EmbeddingProvider`/`AdvisorContract` são extensões já previstas no Blueprint, nunca uma segunda linha paralela.
3. **Nenhuma seta sobe** — o Enterprise Domain nunca importa Knowledge Platform/Advisor Framework/Advisors; cada camada só é consumida pela camada acima dela.
4. **Nome nunca colide** — toda extensão do Enterprise Memory Model revalida a checklist §0 contra Executive Memory (V1) antes do merge.
5. **Nenhum Advisor cria infraestrutura própria** — Fase 4 usa exclusivamente o que as Fases 1-3 já construíram.
6. **Toda mudança de schema já em produção segue o padrão aditivo-primeiro/destrutivo-por-último** validado por TD-008 — nenhuma migração de passo único que remova dado existente.

---

## 3. Critérios objetivos de encerramento da Wave 3

Idênticos, por analogia, aos já usados para encerrar a Wave 2 (Wave Completion Policy, D-048):

1. 100% das 4 Fases + W3-8 implementadas e funcionais, **ou** formalmente reclassificadas (Governança Concluída/Business Pending com auditoria completa) — nenhum item tratado como Decision Proposal silenciosamente adiado.
2. 100% dos Blueprints desta Wave com Technical Design e implementação correspondentes.
3. Todos os testes (`ruff check src tests`, `pytest`, `tsc`, `eslint`, `vitest`, E2E) aprovados; zero placeholder/TODO/stub; zero skip novo não justificado.
4. `ENTERPRISE-ADVISOR-CATALOG.md` com os 8 Advisors marcados "implementado", cada um com Domain Blueprint próprio se o Founder exigir refinamento adicional por Advisor.
5. Wave 3 Closure Review completo (mesmo rigor de 7 entregáveis usado na Wave 2 — `WAVE-2-CLOSURE-REPORT.md` como referência de formato) antes de declarar a Wave encerrada.

**Nenhuma Fase inicia antes da anterior satisfazer sua própria Definition of Done (§1) e o Gate correspondente (`WAVE-3-EXECUTION-PLAN.md` §7).** Este documento é a referência objetiva para toda futura auditoria de progresso da Wave 3 — inclusive para o próprio Wave 3 Closure Review.
