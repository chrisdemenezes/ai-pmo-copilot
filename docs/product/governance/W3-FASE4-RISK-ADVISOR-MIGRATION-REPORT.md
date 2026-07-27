# Wave 3, Fase 4 — Migração do Risk Advisor: Relatório de Governança

**Data:** 2026-07-27
**Autorização:** "Founder Decision — Wave 3 • Fase 4".
**Escopo:** migrar `RiskAdvisorAgent`/`ask_risk_advisor` para usar `AdvisorFramework`/`RagPipeline`/`KnowledgeRepository` — validação arquitetural completa do que as Fases 1-3 construíram. Nenhuma capacidade nova criada (condição 1).

---

## 1. Artefatos implementados

| Artefato | Caminho |
|---|---|
| Technical Design (plano de migração) | `docs/architecture/TECHNICAL-DESIGN-RISK-ADVISOR-MIGRATION-FASE4.md` |
| `AdvisorContract`/`AdvisorFramework` estendidos (`rag_context`, `no_evidence_answer` opcionais) | `src/services/advisor_framework/{types,framework}.py` |
| `RiskAdvisorAgent` migrado | `src/agents/risk_advisor/agent.py` |
| Prompt com seção suplementar de RAG | `src/agents/risk_advisor/prompts/advise.md` |
| Rota `ask_risk_advisor` reescrita + 2 novos DI providers (`build_knowledge_repository`, `build_rag_pipeline`) | `src/api/routes/intelligence.py` |
| Testes de migração dedicados (6 casos) | `tests/test_risk_advisor_migration.py` |
| Testes unitários do Agent atualizados (6 casos, +2 novos para RAG) | `tests/test_risk_advisor_agent.py` |
| Novo teste de regressão 502 na suíte já existente | `tests/test_intelligence_api.py::TestRiskAdvisor::test_returns_502_for_a_malformed_advisor_response` |

---

## 2. Migração fiel (condição 2)

`RiskAdvisorAgent.__init__` passou de `(model_client, prompt_registry)` para `(framework: AdvisorFramework)`. A lógica de extração de risco (`risks_json`), o template de prompt (idêntico, apenas com uma seção suplementar nova) e o formato de retorno (agora o dict achatado — `{"structured", "answer", "cited_analysis_ids"}` — em vez do wrapper legado `{"agent": ..., "model_output": ...}`, um artefato interno que nunca foi visível fora do par Agent↔rota) são preservados. `RiskAdvisorRequest`/`RiskAdvisorResponse` (contrato HTTP) permanecem **byte-idênticos**.

**Achado corrigido durante a implementação:** a primeira versão do `AdvisorFramework.run()` (Fase 3) esperava que `advisor.advise()` retornasse o dict achatado diretamente — exatamente como `_FakeAdvisor` (Fase 3) já fazia — mas o `RiskAdvisorAgent` original ainda devolvia o wrapper `{"agent": ..., "model_output": ...}`, herdado da era pré-Framework (quando a própria rota fazia `result["model_output"]`). Isso quebrava silenciosamente `model_output.get("structured")` (sempre `None`, pois a chave real era aninhada), disparando `AdvisorExecutionError` em todo caminho com evidência. **Detectado pelos testes existentes** (`test_intelligence_api.py::TestRiskAdvisor::test_answers_from_the_latest_risk_analysis_with_citations`, que passou a falhar com 502 em vez de 200) — exatamente o motivo pelo qual a condição 2 exige rodar a suíte já existente sem alterá-la. Corrigido achatando o retorno do Agent.

**Segundo achado corrigido:** `AdvisorFramework.run()` chamava `RecommendationEngine.no_evidence()` sem argumento, perdendo a mensagem específica de domínio "Nenhum risco identificado ainda para este projeto." (o Foundation usa um genérico "Nenhuma evidência identificada..."). Corrigido adicionando o parâmetro opcional `no_evidence_answer` a `run()`, repassado pela rota — preserva exatamente o texto que os testes existentes já esperavam.

Ambos os achados foram identificados **porque a suíte de testes já existente (`test_intelligence_api.py::TestRiskAdvisor`) foi rodada sem nenhuma alteração**, exatamente como a condição 2 exige — nenhuma modificação de teste escondeu uma regressão real.

---

## 3. Validação ponta a ponta (condição 3)

Cadeia implementada literalmente na rota `ask_risk_advisor`:

```
Risk Advisor → Advisor Framework → Gather Context → RagPipeline → KnowledgeRepository
  → Contexto rastreável → LLMProvider → Resposta → Auditoria
```

- **Gather Context:** `framework.gather_context(...)` → `AIContextEngine.gather(...)` (inalterado).
- **RagPipeline → KnowledgeRepository:** `framework.gather_rag_context(...)` → `RagPipeline.retrieve(...)` → `KnowledgeRepository.search(...)`.
- **LLMProvider:** `framework.call_llm(...)` → `ObservabilityRecorder.record_call(...)` → `LLMProvider.generate(...)`.
- **Auditoria:** `AIFoundationAudit.record_question(...)` dentro de `framework.run()`, incondicional.

---

## 4. Evidências dos critérios obrigatórios (condição 4)

### 4.1 Rastreabilidade dos `chunk_id`s
- `tests/test_risk_advisor_migration.py::TestChunkIdTraceability` — ingere um documento real via `KnowledgeRepository`, chama `framework.gather_rag_context(...)` através do mesmo caminho que a rota usa, e comprova que `RagContext.chunk_ids` corresponde exatamente ao chunk real ingerido; um segundo teste comprova que o `RagContext` flui para dentro do prompt do `RiskAdvisorAgent` migrado (texto do chunk aparece no prompt capturado).
- A rota loga `rag_context.chunk_ids` na mesma linha de log de toda pergunta (`organization_id`/`project_name`/`rag_chunk_ids`), tornando o conjunto rastreável no caminho de produção real, não apenas em teste isolado.

### 4.2 Execução de `no_evidence()` sem chamada ao LLM
- `tests/test_risk_advisor_migration.py::TestNoEvidenceWithoutLlmCall` — usa um `_ExplodingProvider` que falha o teste se `generate()` for chamado; comprova que a mensagem específica de domínio é preservada.
- Já coberto também pela suíte pré-existente `test_returns_a_canned_answer_without_calling_the_llm_when_no_risks_exist` (inalterada, 100% verde).

### 4.3 Ausência de acesso direto à infraestrutura
- `tests/test_risk_advisor_migration.py::TestNoDirectInfrastructureAccess` — lê o arquivo-fonte do Agent migrado e confirma, em tempo de execução (não apenas por busca manual), a ausência de `PgVectorRepository`/`EmbeddingProvider`/import direto de `src.database.models`.
- Confirmado por busca global adicional nesta missão: nenhuma linha em `src/agents/risk_advisor/` ou `src/api/routes/intelligence.py` importa essas classes — apenas `KnowledgeRepository`/`RagPipeline` como composição de DI (mesma disciplina da Fase 3).

### 4.4 Preservação do comportamento funcional
- `tests/test_risk_advisor_migration.py::TestFunctionalEquivalence` — mesma resposta, mesmo filtro de citação inventada (id fora da evidência descartado), contra o Agent real.
- **A suíte pré-existente `test_intelligence_api.py::TestRiskAdvisor` (6 casos) permanece 100% verde sem nenhuma alteração de asserção** — a prova mais forte de fidelidade: o comportamento observável de fora não mudou.

### 4.5 Isolamento entre organizações
- `tests/test_risk_advisor_migration.py::TestOrganizationIsolation` — org A nunca vê `AnalysisRecord`s nem chunks RAG da org B, mesmo com uma pergunta pensada para "vazar" o conteúdo confidencial de B.
- Já coberto também pela suíte pré-existente `test_never_sees_risks_from_another_organization` (inalterada).

### 4.6 Cobertura de testes
`ruff check src tests` limpo; **494 testes passando** (12 novos: 6 em `test_risk_advisor_migration.py`, 2 novos em `test_risk_advisor_agent.py` para RAG, 1 novo 502 em `test_intelligence_api.py`; 4 testes de `test_risk_advisor_agent.py` atualizados para a nova assinatura), 97% de cobertura total.

---

## 5. Riscos residuais

1. **Backend de embeddings de produção ainda não escolhido** (deferido desde a Fase 1/2) — o RAG do Risk Advisor em produção real hoje opera sobre `MockEmbeddingProvider` até essa decisão ser tomada; não bloqueia esta migração (a cadeia é idêntica independentemente do backend).
2. **Nenhum documento é ingerido hoje para o domínio de risco** — o RAG do Risk Advisor sempre retorna um `RagContext` vazio em produção real até que a ingestão de documentos (fora do escopo desta Wave) exista; a seção suplementar do prompt permanece vazia (`[]`), sem efeito observável — comportamento consistente com "migração fiel", não um defeito.
3. **Suíte E2E Playwright não foi re-executada nesta Fase** — o contrato HTTP (`RiskAdvisorRequest`/`RiskAdvisorResponse`) é byte-idêntico e a suíte de regressão de backend (incluindo a suíte `TestRiskAdvisor` pré-existente, via `TestClient`) cobre o mesmo caminho HTTP; risco residual julgado baixo, mas registrado explicitamente.

---

## 6. Critério de encerramento da Wave 3 (condição 5) — avaliação, não declaração

O Founder reservou a si a decisão de encerrar formalmente a Wave 3. Este relatório apresenta o estado de cada critério, sem declará-la encerrada:

| Critério do Founder | Estado |
|---|---|
| Risk Advisor migrado | ✅ Concluído nesta Fase |
| Validação ponta a ponta demonstrada | ✅ Demonstrada (§3, §4) |
| Arquitetura exercitada em produção de código real | ✅ `RiskAdvisorAgent`/`ask_risk_advisor` são código de produção real, não um teste isolado — os testes de migração chamam o Agent e o Framework reais, e a suíte de regressão do endpoint HTTP real permanece verde |
| Contratos do Framework comprovados suficientes sem abstrações adicionais | ✅ Nenhuma abstração nova foi necessária além da extensão mínima já prevista (`rag_context`/`no_evidence_answer` opcionais, ambos defaults `None`) |

**Nenhuma declaração de encerramento da Wave 3 é feita por este relatório** — cabe ao Founder decidir se deseja um Wave 3 Closure Review formal (mesmo padrão de 7 entregáveis da Wave 2) antes de declarar a Wave encerrada, ou se considera os critérios acima suficientes.

---

## 7. Governança atualizada

- **Decision Log:** D-068 (`docs/product/stratech-v2/DECISION-LOG.md`).
- **CHANGELOG:** entrada "Wave 3 — Fase 4".
- **Mission Control:** `RECENT_DECISIONS`, `PRODUCT_PULSE_TODAY`, detalhe da Wave 3 (`web/lib/mock/mission-control-data.ts`).
- **Execution Plan:** `docs/product/WAVE-3-EXECUTION-PLAN.md` — Fase 4 e Gate "Fase 4 → W3-8" atualizados.
