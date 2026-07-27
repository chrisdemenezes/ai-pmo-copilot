# Wave 3 Execution Plan — Digital PMO Intelligence

**Data:** 2026-07-27. **Supersede** `WAVE-3-EXECUTIVE-PLAN.md` (produzido durante o Wave 2 Closure Review, antes das 2 Decision Proposals serem resolvidas e antes de qualquer Blueprint existir) — aquele documento permanece como histórico, este é o plano vigente, agora fundamentado nos 6 Blueprints aprovados como pré-requisito (`WAVE-3-DOMAIN-BLUEPRINT.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md`, `ENTERPRISE-ADVISOR-CATALOG.md`, `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`, `WAVE-3-INTEGRATION-BLUEPRINT.md`).

**Este plano não autoriza nenhuma implementação.** Aguarda Architecture Review e aprovação explícita do Founder, seguindo o mesmo padrão da Wave 2: Domain Blueprint → Revisão Arquitetural → Aprovação do Founder → Implementação incremental → Governança contínua → Testes completos → Atualização documental → Wave Closure Review.

---

## 0. Estado herdado

| Epic/Marco | Status | Decisão |
|---|---|---|
| W3-1 — Project Identity Unification (TD-008 Fase 3a) | ✅ Concluído | D-040 |
| W3-2 — Digital PMO Intelligence Foundation | ✅ Concluído | D-041/D-047 |
| W3-3 — Risk Advisor (PoC de Enterprise Agent conversacional) | ✅ Concluído | D-046 |
| Security Hardening Gate (RBAC, Tenant Isolation) | ✅ Concluído | D-045 |
| TD-008 Fase 3b (Etapas 1–5, incluindo destrutiva 4b) | ✅ Concluído (Resolvido) | D-060/D-061/D-062 |
| Wave 2 Closure Review (7 entregáveis) | ✅ Concluído — "Wave 3 Ready" declarado | D-062 |
| §15.1 — Decisão de Vector Store | ✅ Resolvida — `pgvector` aprovado | Decisão Estratégica 2026-07-27 |
| §15.2 — Decisão de Framework de Orquestração | ✅ Resolvida — Multi-Agent Orchestration Framework aprovado | Decisão Estratégica 2026-07-27 |
| **W3-4 — Wave 3 Domain Blueprint (8 entregáveis)** | ✅ Concluído nesta missão | Este plano é o entregável 8 |
| AR-6 — Architecture Review do Wave 3 Domain Blueprint | ✅ Aprovado sem ressalvas | D-064 |
| **Fase 1 — Foundation (Enterprise Knowledge Platform)** | ✅ Concluído — `KnowledgeRepository`/`PgVectorRepository`/`EmbeddingProvider` funcionais e testados; nenhum Advisor consumidor ainda | D-065 |
| **Fase 2 — Knowledge Services** | ✅ Concluído — `RagPipeline` (ranking determinístico + rastreabilidade) e `EnterpriseMemoryService` (5 categorias) como serviços de plataforma, sem lógica de Advisor; nenhum Advisor consumidor ainda | D-066 |

Nenhuma pendência bloqueia o início da Fase 1 além da Architecture Review e aprovação explícita deste plano.

---

## 1. Objetivos da Wave 3

1. Entregar a **Enterprise Knowledge Platform** como infraestrutura de conhecimento (nunca como domínio de negócio — Princípio 1, documento mestre).
2. Entregar o **Enterprise Advisor Framework** como infraestrutura de execução multiagente, generalizando o padrão já provado pelo Risk Advisor.
3. Entregar os **7 Enterprise Advisors restantes** (`ENTERPRISE-ADVISOR-CATALOG.md`), cada um com contrato próprio, usando exclusivamente a infraestrutura comum construída nas fases anteriores.
4. Encerrar a Wave 3 sob os mesmos critérios da Wave Completion Policy (D-048).

---

## 2. Ordem recomendada dos Epics

A ordem é **mandatória**, conforme diretriz do Founder — nenhuma fase inicia antes da anterior estar completa e testada:

### Fase 1 — Foundation (Enterprise Knowledge Platform: infraestrutura base)
- **W3-6a.** Document Ingestion + Parsing + Chunking + Embeddings + Vector Store (`pgvector`) + Knowledge Repository (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.1–1.6, §1.9).
- Entregável: `KnowledgeRepository`/`VectorRepository`/`EmbeddingProvider` funcionais, testados, sem nenhum Advisor ainda os consumindo.

### Fase 2 — Knowledge Services
- **W3-6b.** Semantic Search + RAG Pipeline (`DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md` completo) + Enterprise Memory Model (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md`) + Versionamento/Atualização incremental (§1.10–1.11 da Knowledge Platform).
- Entregável: um Advisor de referência mínimo (recomenda-se o **Document Advisor**, por depender obrigatoriamente do RAG — `ENTERPRISE-ADVISOR-CATALOG.md` §8) prova o pipeline ponta a ponta, análogo ao papel que o Risk Advisor cumpriu para a Foundation em W3-3.

### Fase 3 — Enterprise Advisor Framework
- **W3-7a.** Contratos (`AdvisorContract`) + ciclo de vida + orquestração + isolamento + compartilhamento de contexto + observabilidade + auditoria (`DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` completo).
- Entregável: o `RiskAdvisorAgent` já existente é migrado para o novo contrato (prova de generalização sem regressão), antes de qualquer Advisor novo ser escrito.

### Fase 4 — Enterprise Advisors (implementação individual)
- **W3-7b.** Os 7 Advisors restantes, cada um usando exclusivamente a infraestrutura já construída nas Fases 1–3 — nenhum cria infraestrutura própria (regra absoluta do Founder).
- Ordem recomendada dentro da Fase 4, por proximidade ao domínio já implementado (menor risco primeiro): **PMO Advisor** → **Delivery Advisor** → **Portfolio Advisor** → **Governance Advisor** → **Strategy Advisor** → **Executive Advisor** → **Document Advisor** (se ainda não coberto como referência na Fase 2).

### Após a Fase 4
- **W3-8 — Executive Intelligence**, consumindo os Advisors e a Knowledge Platform sobre Portfolio/Program/Project (`WAVE-3-INTEGRATION-BLUEPRINT.md` §5, §11) — só inicia com W3-6/W3-7 completos.
- **Wave 3 Closure Review** — mesmo rigor de 7 entregáveis usado na Wave 2.

---

## 3. Dependências técnicas

- **Fase 2 depende de Fase 1 completa e testada** — RAG não existe sem Vector Store/Embeddings/Knowledge Repository funcionais.
- **Fase 3 depende de Fase 1 e 2** — o Advisor Framework orquestra Advisors que já podem consumir Foundation *e* Knowledge Platform; construir o Framework antes seria orquestrar infraestrutura incompleta.
- **Fase 4 depende de Fase 3 completa** — nenhum Advisor é escrito antes do contrato (`AdvisorContract`) e da infraestrutura comum (observabilidade/auditoria/isolamento) existirem.
- **W3-8 depende de Fase 4** — Executive Intelligence consome Advisors que ainda não existem antes disso.
- **Nenhuma fase desta Wave depende de nada além da baseline já fechada na Wave 2** (RBAC, Tenant Isolation, `project_id` como identidade única, Foundation).

---

## 4. Riscos

1. **Pular a ordem mandatória (ex.: construir um Advisor antes do Framework) reintroduziria exatamente o duck typing que este Blueprint elimina.** Mitigação: nenhuma PR de Advisor é aceita antes da Fase 3 estar mergeada e testada.
2. **`pgvector` sob carga real (múltiplos documentos, múltiplas organizações) pode exigir tuning de índice não coberto por este Blueprint** (nível de infraestrutura, não de arquitetura) — mitigação: Fase 1 inclui teste de carga básico antes de avançar à Fase 2.
3. **Migração do `RiskAdvisorAgent` para o novo contrato (Fase 3) pode introduzir regressão no único fluxo de IA hoje em produção** (`POST /risk-advisor/ask`) — mitigação: suíte de testes E2E do Risk Advisor deve permanecer 100% verde antes e depois da migração, sem nenhum novo skip.
4. **Superengenharia do Advisor Framework** se o desenho não for estritamente informado pelo que o Risk Advisor já prova funcionar — mitigação: `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` §0 documenta o estado herdado exatamente para ancorar o Technical Design nele.
5. **Colisão de nome/mecanismo entre Enterprise Memory Model e Executive Memory** — já mitigado arquiteturalmente pela checklist obrigatória (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §0); risco residual é apenas de não revalidar a checklist se um dos dois conceitos mudar durante a implementação.

---

## 5. Critérios de conclusão

Idênticos aos já estabelecidos pela Wave Completion Policy (D-048), aplicados à Wave 3:

- 100% das 4 Fases implementadas e funcionais, ou formalmente reclassificadas (nunca uma Decision Proposal silenciosamente adiada).
- 100% dos Blueprints desta missão com Technical Design e implementação correspondentes.
- Todos os testes (`ruff check src tests`, `pytest`, TypeScript, ESLint, Vitest, E2E) aprovados; zero placeholder/TODO/stub; zero novo skip não justificado.
- Wave 3 Closure Review completo antes de declarar a Wave encerrada.

---

## 6. Estratégia incremental de implementação

Cada Fase segue o mesmo padrão de entrega usado na Wave 2 e em TD-008: **aditivo primeiro, nunca big-bang.**

1. Cada Fase é dividida em incrementos pequenos e testáveis (ex.: dentro da Fase 1, `EmbeddingProvider` antes de `VectorRepository`, antes de `KnowledgeRepository` completo).
2. Nenhuma Fase é declarada concluída sem suíte de testes verde e documentação atualizada — mesmo padrão de "full suite green per group" já usado em TD-008 Etapa 4a.
3. O primeiro Advisor generalizado (migração do Risk Advisor, Fase 3) e o primeiro Advisor novo (recomendado: PMO Advisor, Fase 4) funcionam como PoCs de validação do Framework antes da expansão aos demais 6 — mesma disciplina de "PoC primeiro" já usada com sucesso em W3-3.

---

## 7. Gates de aprovação entre Epics

| Gate | Critério de passagem |
|---|---|
| Fase 1 → Fase 2 | ✅ **Cumprido (D-065).** `KnowledgeRepository` funcional e testado (unitário + integração real com Postgres/`pgvector`); nenhum Advisor ainda necessário |
| Fase 2 → Fase 3 | ✅ **Cumprido parcialmente (D-066).** `RagPipeline` e `EnterpriseMemoryService` funcionais e testados como serviços de plataforma (ranking determinístico, checklist §0 revalidada). A prova ponta a ponta por um Advisor de referência (Document Advisor) fica para a Fase 4, após o Advisor Framework (Fase 3) existir — nenhum Advisor pode ser construído antes dele. |
| Fase 3 → Fase 4 | `RiskAdvisorAgent` migrado ao novo contrato sem regressão (suíte E2E 100% verde); `AdvisorContract` documentado e estável |
| Fase 4 → W3-8 | Todos os 7 Advisors restantes implementados, testados, catalogados como "implementado" (não mais "não implementado nesta etapa") em `ENTERPRISE-ADVISOR-CATALOG.md` |
| W3-8 → Wave 3 Closure Review | Executive Intelligence funcional sobre Portfolio/Program/Project; nenhum item da Wave 3 pendente sem classificação |

Cada Gate exige aprovação explícita do Founder antes da fase seguinte iniciar — mesmo padrão de governança contínua já aplicado a toda a Wave 2.
