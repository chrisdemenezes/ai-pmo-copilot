# Wave 3 Domain Blueprint — Digital PMO Intelligence

**Status:** documento mestre da Wave 3. Precede e governa todos os Blueprints subordinados (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md`, `ENTERPRISE-ADVISOR-CATALOG.md`, `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`, `WAVE-3-INTEGRATION-BLUEPRINT.md`) e o `WAVE-3-EXECUTION-PLAN.md`.
**Autorização:** duas Decisões Estratégicas do Founder (2026-07-27) — (1) adoção de Vector Store (`pgvector`) como infraestrutura oficial da Enterprise Knowledge Platform; (2) adoção de um Framework de Orquestração Multiagente para os Enterprise Advisors. Nenhum Epic é implementado por este documento ou por qualquer um de seus subordinados.

---

## 1. Visão geral da arquitetura

A Wave 3 acrescenta **duas camadas de infraestrutura de IA** sobre a base já existente (Enterprise Domain + Digital PMO Intelligence Foundation, ambas da Wave 2/W3-2) — e **nenhum novo domínio de negócio próprio**. As duas camadas:

1. **Enterprise Knowledge Platform** — infraestrutura de conhecimento (ingestão, embeddings, Vector Store, busca semântica, RAG). Serve dado, nunca decide.
2. **Enterprise Advisor Framework** — infraestrutura de execução multiagente (contratos, orquestração, observabilidade, auditoria). Executa Advisors, nunca é um Advisor.

Os **Enterprise Advisors** (8 conceitos já nomeados desde a Wave 3 original, catalogados em `ENTERPRISE-ADVISOR-CATALOG.md`) são o **único** domínio de negócio novo desta Wave — cada um consome as duas infraestruturas acima, mas nenhuma das duas conhece o conceito de "Advisor".

```
┌─────────────────────────────────────────────────────────────┐
│  Enterprise Advisors (domínio)                               │
│  Executive · Strategy · PMO · Portfolio · Delivery ·          │
│  Governance · Risk (já existe) · Document                    │
└───────────────┬───────────────────────────┬───────────────────┘
                │ usa                        │ usa
┌───────────────▼───────────────┐  ┌─────────▼─────────────────┐
│ Enterprise Advisor Framework   │  │ Digital PMO Intelligence   │
│ (infraestrutura de execução)  │  │ Foundation (já existe,      │
│ contratos·orquestração·        │  │ Wave 2/W3-2) -- Context/     │
│ observabilidade·auditoria      │  │ Recommendation/Explanation/ │
└───────────────┬───────────────┘  │ Prompt/Session/Audit/Observ. │
                │ usa               └─────────────────────────────┘
┌───────────────▼───────────────────────────────────────────────┐
│ Enterprise Knowledge Platform (infraestrutura de conhecimento) │
│ Ingestion→Parsing→Chunking→Embeddings→Vector Store(pgvector)→  │
│ Semantic Search→RAG Pipeline→Knowledge Repository              │
└───────────────┬─────────────────────────────────────────────────┘
                │ lê
┌───────────────▼───────────────────────────────────────────────┐
│ Enterprise Domain (Wave 2, já existe): Portfolio/Program/Project│
│ + AnalysisRecord (intelligence já produzida)                    │
└─────────────────────────────────────────────────────────────────┘
```

**Nenhuma seta sobe.** O Enterprise Domain não conhece Knowledge Platform; Knowledge Platform não conhece Advisor Framework; Advisor Framework não conhece nenhum Advisor específico. Cada camada é consumida, nunca consulta a camada acima — o mesmo princípio já estabelecido pela Digital PMO Intelligence Foundation (D-047) e reafirmado pelo Founder nas duas Decisões Estratégicas desta missão ("o domínio não poderá depender diretamente da tecnologia").

---

## 2. Princípios arquiteturais

1. **Infraestrutura nunca é domínio.** Vector Store e Framework de Orquestração são mecanismos de execução — nunca modelam um conceito de negócio, nunca aparecem em um nome de Advisor ou de fluxo de decisão executiva. Diretriz explícita do Founder, reafirmada duas vezes nesta missão.
2. **Toda interação com a Vector Store passa por uma abstração.** Nenhum componente de domínio ou de Advisor importa `pgvector`/SQL de vetor diretamente — sempre via `KnowledgeRepository`/`VectorRepository` (ver `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §4). `pgvector` é a implementação inicial aprovada, substituível sem impacto no domínio.
3. **O domínio nunca depende do Framework de Orquestração.** Cada Enterprise Advisor tem contrato próprio (entrada/saída, responsabilidade, limites) independente de como o Framework o invoca — mesmo princípio de "seam antes de infraestrutura" já usado por `NoOpEventEmitter`/`NoOpNotificationProvider` (Wave 2).
4. **Reaproveitar a Digital PMO Intelligence Foundation integralmente.** `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, `render_analyst_prompt`, `SessionContext`, `AIFoundationAudit`, `ObservabilityRecorder` continuam sendo os únicos componentes de contexto/evidência/recomendação/explicação/prompt/sessão/auditoria/observabilidade. A Knowledge Platform e o Advisor Framework **estendem**, nunca substituem ou duplicam essa infraestrutura.
5. **`PromptRegistry` e `LLMProvider` permanecem os únicos contratos de prompt e de modelo.** Nenhum Model Registry, Provider Router ou Prompt Versioning novo — reafirmado pela Foundation (W3-2) e não revogado por nenhuma das duas Decisões Estratégicas desta missão.
6. **Toda leitura de conhecimento é escopada por organização, sem exceção.** Mesmo padrão de `organization_id` já aplicado a `AnalysisRecord`/`Portfolio`/`Program`/`Project` desde o Épico 1 — nenhuma tabela nova desta Wave foge a essa disciplina.
7. **Nome nunca colide com conceito já existente.** "Enterprise Memory" é auditado explicitamente contra "Executive Memory" (já em produção, V1) em `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §0 — mesma disciplina de D-005/D-009/D-012/D-019/D-055.
8. **Domain Blueprint → Architecture Review → Aprovação do Founder → Implementação incremental → Governança contínua → Testes completos → Atualização documental → Wave Closure Review.** Nenhuma etapa é pulada; nenhum Advisor cria infraestrutura própria (Fase 4 do plano de execução).

---

## 3. Bounded Contexts

| Bounded Context | Responsabilidade | Consome | Não conhece |
|---|---|---|---|
| **Enterprise Domain** (Wave 2, existente) | Portfolio/Program/Project como Aggregates reais; `AnalysisRecord` como intelligence já produzida | Postgres via SQLAlchemy | Knowledge Platform, Advisor Framework, Advisors |
| **Digital PMO Intelligence Foundation** (Wave 2/W3-2, existente) | Context/Evidence/Recommendation/Explanation/Prompt/Session/Audit/Observability — infraestrutura cross-cutting já usada pelo Risk Advisor | `AnalysisRepository`, `PromptRegistry`, `LLMProvider` | Knowledge Platform, Advisor Framework |
| **Enterprise Knowledge Platform** (novo, Blueprint desta missão) | Ingestão, embeddings, indexação, busca semântica, RAG sobre documentos e conhecimento corporativo | Enterprise Domain (para metadados de escopo/organização) | Advisor Framework, Advisors |
| **Enterprise Memory Model** (novo, Blueprint desta missão) | Modelo de memória corporativa (documental/operacional/decisão/aprendizado/organizacional) — camada de **classificação e ciclo de vida** sobre o conhecimento já indexado pela Knowledge Platform | Knowledge Platform | Advisor Framework, Advisors |
| **Enterprise Advisor Framework** (novo, Blueprint desta missão) | Contratos, ciclo de vida, orquestração, isolamento, observabilidade, auditoria comuns a todo Advisor | Digital PMO Intelligence Foundation, Knowledge Platform (via abstração) | Um Advisor específico |
| **Enterprise Advisors** (domínio, catalogado nesta missão, não implementado) | Os 8 conceitos de negócio (Executive/Strategy/PMO/Portfolio/Delivery/Governance/Risk/Document Advisor) | Advisor Framework, Knowledge Platform, Foundation | Detalhes de implementação da Vector Store ou do orquestrador |

---

## 4. Relacionamentos entre domínios

```
Enterprise Advisors  ──consome──>  Enterprise Advisor Framework
Enterprise Advisors  ──consome──>  Digital PMO Intelligence Foundation
Enterprise Advisors  ──consome──>  Enterprise Knowledge Platform (via RAG)
Enterprise Memory Model ──classifica/organiza──>  conteúdo da Knowledge Platform
Enterprise Knowledge Platform ──lê metadados de──>  Enterprise Domain (Portfolio/Program/Project/AnalysisRecord)
Enterprise Advisor Framework ──nunca conhece──>  Enterprise Domain diretamente (só via Advisor/Foundation)
```

Nenhuma relação é bidirecional. O Enterprise Domain nunca importa nada de Knowledge Platform/Advisor Framework/Advisors — a mesma regra de dependência unidirecional já usada entre Portfolio→Program→Project (Wave 2, `DOMAIN-MODEL.md` §4).

---

## 5. Fluxos de informação

### 5.1 Fluxo de ingestão (assíncrono, fora do caminho de resposta a uma pergunta)
```
Documento/fonte → Document Ingestion → Parsing → Chunking → Embeddings →
  Vector Store (pgvector) [+ Knowledge Repository, metadados/versionamento]
```

### 5.2 Fluxo de resposta de um Advisor (síncrono, análogo ao já provado pelo Risk Advisor)
```
Pergunta do usuário
  → Advisor Framework resolve o contrato do Advisor (entrada validada)
  → Advisor chama AIContextEngine (Foundation, evidência estruturada já existente)
     + RAG Pipeline (Knowledge Platform, evidência documental/semântica)
  → Advisor compõe o prompt (render_analyst_prompt, Foundation)
  → ObservabilityRecorder mede a chamada (Foundation)
  → LLMProvider.generate(...) (inalterado)
  → RecommendationEngine.build(...) descarta qualquer citação inventada
    (tanto de AnalysisRecord quanto de chunk de conhecimento — mesmo guard-rail)
  → ExplanationEngine.explain(...)
  → AIFoundationAudit.record_question(...) (sempre, evidência ou não)
  → Resposta ao usuário, citando fontes reais (analysis_id e/ou document chunk id)
```

Este fluxo é uma **extensão aditiva** do fluxo já provado em `POST /risk-advisor/ask` — nenhum passo existente é removido ou substituído; RAG entra como uma segunda fonte de evidência ao lado de `AIContextEngine`, nunca a substituindo.

---

## 6. Dependências entre componentes

| Componente | Depende de |
|---|---|
| Enterprise Advisors (qualquer um) | Advisor Framework (contrato/execução) + Foundation (context/recommendation/explanation) + Knowledge Platform, se o Advisor usa RAG |
| Advisor Framework | Foundation (`SessionContext`, `ObservabilityRecorder`, `AIFoundationAudit` reaproveitados) |
| Knowledge Platform (RAG Pipeline) | Vector Store (`KnowledgeRepository`), `PromptRegistry`/`LLMProvider` (para embeddings, se o provedor de embeddings for o mesmo `LLMProvider` ou um provedor próprio — decisão de Technical Design, não deste Blueprint) |
| Enterprise Memory Model | Knowledge Platform (Knowledge Repository) — nunca substitui Executive Memory (V1, inalterado) |
| Vector Store (`pgvector`) | Postgres já oficial (RC-2/D-037) — nenhuma infraestrutura de banco nova, apenas uma extensão do banco existente |

**Ordem de construção obrigatória** (reafirmada em `WAVE-3-EXECUTION-PLAN.md`): Knowledge Platform → Knowledge Services → Advisor Framework → Advisors. Nenhum Advisor pode ser implementado antes de o Framework existir; nenhum Advisor cria infraestrutura própria.

---

## 7. Critérios de evolução

1. **Nenhum novo Advisor além dos 8 catalogados** sem uma revisão explícita do catálogo (`ENTERPRISE-ADVISOR-CATALOG.md`) e aprovação do Founder — mesma disciplina que impediu "Workspace" de virar uma entidade não planejada (D-055).
2. **Nenhuma segunda Vector Store ou segundo Framework de Orquestração.** Se `pgvector` se mostrar insuficiente no futuro, a substituição ocorre **atrás da abstração já definida** (`KnowledgeRepository`) — nunca introduzindo um segundo provider ao lado do primeiro.
3. **Toda extensão do Enterprise Memory Model** deve provar, antes do código, que não colide em nome ou mecanismo com Executive Memory (V1) — checklist obrigatório em `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §0.
4. **Toda mudança estrutural que remova ou substitua uma tabela/coluna já em produção** segue o padrão aditivo-primeiro/destrutivo-por-último estabelecido por TD-008 (Wave 2) — nunca uma migração de passo único.
5. **Wave 3 só se encerra sob os mesmos critérios da Wave Completion Policy (D-048)**, aplicados por analogia ao Wave 2 Closure Review: 100% do escopo aprovado implementado, testado, documentado; nenhum item tratado como Decision Proposal silenciosamente adiado.
