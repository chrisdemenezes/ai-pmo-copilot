# AR-3 — Architecture Review: W3-2 Digital PMO Intelligence Foundation Blueprint

**Escopo:** revisão arquitetural do `DOMAIN-BLUEPRINT-W3-2-Digital-PMO-Intelligence-Foundation.md` antes da Technical Design, per o fluxo institucional obrigatório (Domain Blueprint → Revisão Arquitetural → Technical Design → Implementação).
**Data:** 2026-07-23

---

## 1. Consistência com a arquitetura oficial (CLAUDE.md)

| Regra | Verificação |
|---|---|
| Nunca criar arquitetura paralela | ✅ `src/services/ai_foundation/` é um subpacote de `src/services/`, pasta já oficial — não uma nova árvore de topo. |
| Nunca duplicar código | ✅ O propósito inteiro da Epic é eliminar a duplicação que já existe hoje (a lógica de contexto/evidência/recomendação/auditoria só está implementada dentro de `ask_risk_advisor`) — a Foundation move essa lógica para um único lugar, não a duplica em outro. |
| Nunca criar novo provider | ✅ `LLMProvider` Protocol permanece inalterado; `ProductionLLMProvider`/`MockLLMProvider` continuam sendo os únicos 2 providers; a extensão de `last_usage` é aditiva, não um provider novo. |
| Nunca criar novo registry | ✅ `PromptRegistry` permanece o único registry; `render_analyst_prompt` é uma função de composição por cima dele, não um registry paralelo. |
| Reutilizar componentes existentes | ✅ `AnalysisRepository`, `ProjectSummaryService`, `AdministrationRepository.record_audit`, `parse_structured_output`, `RequestContext`/`get_request_context`, `require_permission` — todos reaproveitados sem alteração de contrato. |
| SOLID / Dependency Injection | ✅ Cada componente (`AIContextEngine`, `RecommendationEngine`, etc.) recebe suas dependências via construtor/parâmetro, mesmo padrão já usado em `ProjectSummaryService(repository)`, `RiskAdvisorAgent(model_client, prompt_registry)`. |

## 2. Checagem item a item da lista de proibições do Founder

Vector Store, pgvector, embeddings, RAG, Knowledge Platform, Executive Memory permanente, Multi-Agent Framework, planejamento autônomo, reflexão autônoma, auto-execução, agentes colaborativos — **nenhum aparece em nenhum componente do Blueprint** (Seção 3 do Blueprint lista essa mesma checagem explicitamente). `SessionContext` é explicitamente efêmero (não persistido); `AIContextEngine` só lê `AnalysisRecord` já persistido via os repositórios existentes, nunca busca semântica.

## 3. Checagem contra a avaliação anterior de W3-2 (D-041)

D-041 avaliou e adiou Provider Strategy, Model Registry, Model Routing e Prompt Versioning por ausência de consumidor real. Este novo Blueprint **não reabre nenhuma dessas 4 sub-áreas** — nenhum componente da Foundation seleciona entre múltiplos providers, cataloga modelos, roteia entre modelos, ou versiona prompts. O único ponto de sobreposição é Observability/Cost — e ali, o Blueprint é explícito: usa `logging` estruturado já existente no projeto, não uma tabela de métricas ou dashboard novo, evitando reabrir a mesma especulação que D-041 rejeitou (nenhum "AI Governance Dashboard").

## 4. Grounding: existe consumidor real hoje?

Sim — o Risk Advisor (Epic W3-3, já implementado e em produção nesta branch) é o consumidor real e imediato. O Blueprint exige explicitamente (Seção 8/9) que o Risk Advisor seja migrado para consumir a Foundation como parte desta própria Epic, não apenas planejado para "algum analyst futuro hipotético" — isso é o que distingue esta Epic da especulação que reprovou o W3-2 anterior.

## 5. Risco de sobre-engenharia

Avaliado e mitigado: cada componente (Context/Evidence/Recommendation/Explanation/Audit/Observability) corresponde a uma linha de código **já existente e duplicável** dentro de `ask_risk_advisor` hoje — nenhum componente é inventado para um problema hipotético. `Evidence.summary` permanece um `dict` opaco à Foundation (não um schema fortemente tipado por domínio), evitando que a Foundation precise "conhecer" o domínio de cada Analyst futuro — a abstração certa para o problema real (múltiplos domínios, uma única esteira de execução), não mais que isso.

## 6. Impacto em código existente

- `src/api/routes/intelligence.py::ask_risk_advisor` — refatorado para consumir a Foundation em vez da lógica inline atual. Contrato HTTP (`RiskAdvisorRequest`/`RiskAdvisorResponse`) **inalterado** — nenhuma migração de frontend/BFF necessária.
- `src/llm/providers/production_provider.py` — aditivo (`last_usage`), sem quebra de compatibilidade.
- Nenhuma migração de banco de dados.
- Nenhuma mudança de permissão (RBAC do Risk Advisor permanece `intelligence.read`).

## 7. Veredito

**Aprovado para Technical Design, sem ressalvas.** Nenhum conflito arquitetural encontrado. Nenhuma Decision Proposal necessária — a Foundation está inteiramente dentro do escopo que o próprio Founder autorizou nesta janela.
