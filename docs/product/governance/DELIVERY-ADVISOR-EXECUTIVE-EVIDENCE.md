# DELIVERY ADVISOR — EXECUTIVE EVIDENCE (Wave 5)

**Autorização:** "Founder Decision — Technical Design do Delivery Advisor" (veredito **APPROVED — GO para implementação, Etapa 5 de 6**), encerrando o ciclo institucional de 6 etapas (D-092): Advisor Specification (D-103) → Domain Blueprint (D-104) → Architecture Review AR-11 (D-105) → Technical Design (D-106) → **Implementação, este documento** → Executive Review.

**Escopo confirmado:** exclusivamente o Delivery Advisor, seguindo estritamente a estratégia incremental de 4 passos apresentada na Technical Design (D-106), com as 7 diretrizes obrigatórias desta autorização.

---

## Executive Summary

O Delivery Advisor foi implementado reutilizando integralmente o `AdvisorFramework` e o `AIContextEngine` — mesma forma exata já provada pelo Risk Advisor (Classe A, `AR-8` §4.2/D-104). `AdvisorFramework.run()` executa o `DeliveryAdvisorAgent` byte-for-byte como já executa os demais Advisors — confirmado por `git diff --stat` vazio em todos os arquivos de Framework/Foundation. A única evidência estrutural é `AnalysisRecord`/`kind="status"`, obtida por uma única chamada a `gather_context()`; nenhuma segunda fonte (risco, reunião, ações, RAG) é consultada em nenhum ponto do código, confirmado por leitura direta e por um teste que faria a suíte inteira falhar caso RAG fosse acidentalmente invocado. A interpretação de recência e de tendência temporal (melhora/estabilidade/deterioração) vive inteiramente no prompt do `DeliveryAdvisorAgent` — nenhum algoritmo de comparação de datas ou de `health_status` foi implementado em código. Os três cenários temporais mandados pelo Founder (melhora, deterioração, registro único) foram comprovados em duas camadas (Framework e HTTP), com timestamps explícitos provando a ordenação e afastando qualquer inversão de tendência. **Recomendação: GO para o encerramento do Epic do Delivery Advisor.**

---

## 1. Preservação da infraestrutura compartilhada (diretriz 1 e 7)

Confirmado por `git diff --stat` vazio nos seguintes arquivos — nenhum foi tocado por esta implementação:

```
src/services/advisor_framework/framework.py
src/services/ai_foundation/context_engine.py
src/services/ai_foundation/recommendation_engine.py
src/services/ai_foundation/explanation_engine.py
src/services/ai_foundation/types.py
src/workflows/
src/services/events/
```

`AdvisorFramework.run()` executa o `DeliveryAdvisorAgent` exatamente como já executa Risk/Document/Governance Advisor. Nenhuma migração criada, nenhum contrato compartilhado alterado (`AdvisorContract`/`Evidence`/`Recommendation`/`Explanation` inalterados) — per diretriz 7 desta autorização.

---

## 2. Fluxo funcional completo

```
Cliente (pergunta em linguagem natural sobre entrega/cronograma/bloqueios de um projeto)
  │
  ▼
POST /delivery-advisor/ask   (src/api/routes/intelligence.py)
  │  RBAC: require_permission("intelligence.read") -- reutilizada do Risk Advisor,
  │  nenhuma migração nova
  ▼
SessionContext(organization_id, user_id, session_id, project_name)
  ▼
AdvisorFramework(repository, prompts, provider, rag_pipeline)  -- construção idêntica
  │
  ▼
framework.gather_context(organization_id, project_name, kind="status")
  │  AIContextEngine.gather() -- zero mudança. Resolve project_name -> project_id,
  │  filtra por organization_id/kind, retorna list[Evidence] já ordenada do mais
  │  recente para o mais antigo (AnalysisRepository.list_analyses(), já ordenada
  │  por created_at.desc() -- garantia estrutural confirmada em AR-11)
  ▼
framework.run(delivery_advisor_agent, session, question, evidence,
               no_evidence_answer="Nenhuma análise de status registrada ainda para este projeto.")
  │  (rag_context nunca construído -- gather_rag_context() nunca chamado nesta rota)
  │
  ├─ AIFoundationAudit.record_question(...)          -- inalterado
  ├─ if not evidence: RecommendationEngine.no_evidence(no_evidence_answer)  -- inalterado
  ├─ DeliveryAdvisorAgent.advise(...)   -- único componente novo desta Epic
  │     → serializa evidence (já ordenada) em status_history_json
  │     → framework.render_prompt(...) → framework.call_llm(...) → LLMProvider
  │     → resposta JSON com "answer" refletindo estado atual + tendência
  ├─ RecommendationEngine.build(answer, cited_analysis_ids, evidence)   -- inalterado
  └─ ExplanationEngine.explain(recommendation)   -- inalterado
  ▼
_delivery_advisor_response(explanation)   -- novo, apenas na rota
  ▼
DeliveryAdvisorResponse{answer, cited_analyses: [...]}   -- CitedAnalysis reaproveitado
                                                              do Risk Advisor, sem alteração
```

---

## 3. Arquivos alterados

**Backend — produção**
- `src/agents/delivery_advisor/__init__.py`, `agent.py`, `prompts/advise.md` (novos).
- `src/api/routes/intelligence.py` — import de `DeliveryAdvisorAgent`; `DeliveryAdvisorRequest`/`DeliveryAdvisorResponse` (novos); rota `POST /delivery-advisor/ask` (nova); `_delivery_advisor_response()` (nova). Reaproveita `CitedAnalysis` (já definido para o Risk Advisor) sem duplicação.

**Backend — testes**
- `tests/test_delivery_advisor_agent.py` (novo, 8 testes) — unitários do `DeliveryAdvisorAgent.advise()`, incluindo prova de que a ordem já ordenada da evidência nunca é revertida e de que nenhum bloco de RAG suplementar é construído.
- `tests/test_delivery_advisor.py` (novo, 6 testes) — integração via `AdvisorFramework` real (PostgreSQL real): ausência de evidência, chamada única a `gather_context(kind="status")`, os três cenários temporais mandados (melhora/deterioração/registro único), isolamento organizacional.
- `tests/test_delivery_advisor_api.py` (novo, 9 testes) — HTTP real: ausência de evidência, os três cenários temporais, RBAC, isolamento organizacional, resposta malformada (502), trilha de auditoria — com um `RagPipeline` de dependência substituído por um dublê que lança exceção caso `.retrieve()` seja chamado, provando estruturalmente que nenhuma segunda fonte é consultada.

**Governança**
- `docs/product/stratech-v2/DECISION-LOG.md`, `CHANGELOG.md`, `web/lib/mock/mission-control-data.ts` — espelhados (D-107).

---

## 4. Confirmação: `AnalysisRecord` mais recente determina o estado atual (diretriz 2/3)

Comprovado por dois mecanismos independentes, ambos exercidos pelos testes:

1. **Ordenação estrutural, não nova:** `AnalysisRepository.list_analyses()` já ordena por `created_at.desc()` para qualquer `kind` — `AIContextEngine.gather()` preserva essa ordem sem nenhuma mudança de código. Todos os testes usam `created_at` explícitos (diretriz 5) e verificam diretamente `evidence[0].content["health_status"]` como o registro mais recente e `evidence[-1]` como o mais antigo — nunca invertido.
2. **Interpretação exclusivamente de prompt:** o `DeliveryAdvisorAgent` serializa `evidence` para `status_history_json` na exata ordem recebida — nenhuma função de comparação de datas/`health_status` existe em código (confirmado por leitura direta de `src/agents/delivery_advisor/agent.py`). O prompt (`prompts/advise.md`) declara explicitamente: a primeira entrada é o estado atual; entradas seguintes são histórico, do mais recente para o mais antigo; a tendência deve respeitar essa direção temporal — exatamente per diretriz 3.

---

## 5. Evidência dos três cenários temporais mandados (diretriz 4)

Comprovados em **duas camadas** (Framework e HTTP), com timestamps explícitos (diretriz 5) — nenhum cenário depende de ordem de inserção, apenas de `created_at`:

### A. Melhora
`tests/test_delivery_advisor.py::TestTemporalScenarioA_Melhora` / `tests/test_delivery_advisor_api.py::TestTemporalScenarioA_Melhora`

Sequência: antigo **vermelho** (2026-07-01) → intermediário **amarelo** (2026-07-20) → recente **verde** (2026-08-01). `evidence[0].content["health_status"] == "green"`, `evidence[-1].content["health_status"] == "red"` — ordenação comprovada antes mesmo de chamar o LLM. Resposta final reflete `green` como estado atual e `"melhorando"` como tendência, citando os três `source_analysis_id`s na mesma ordem.

### B. Deterioração
`tests/test_delivery_advisor.py::TestTemporalScenarioB_Deterioracao` / `tests/test_delivery_advisor_api.py::TestTemporalScenarioB_Deterioracao`

Sequência: antigo **verde** (2026-07-01) → intermediário **amarelo** (2026-07-20) → recente **vermelho** (2026-08-01). `evidence[0].content["health_status"] == "red"`, `evidence[-1].content["health_status"] == "green"`. Resposta final reflete `red` como estado atual e `"deteriorando"` como tendência.

### C. Registro único
`tests/test_delivery_advisor.py::TestTemporalScenarioC_RegistroUnico` / `tests/test_delivery_advisor_api.py::TestTemporalScenarioC_RegistroUnico`

Um único `AnalysisRecord` de status (`yellow`). Resposta declara o estado atual e afirma explicitamente a ausência de histórico suficiente para avaliar uma evolução — nenhuma tendência inventada; os testes verificam que nem `"melhorando"` nem `"deteriorando"` aparecem na resposta.

**Prova adicional de fidelidade de direção temporal** (`test_delivery_advisor_agent.py::test_advise_sends_status_history_in_the_exact_order_evidence_was_given` / `test_advise_never_reverses_a_deteriorating_sequence`): o JSON literal enviado ao LLM é inspecionado diretamente — uma implementação que revertesse a sequência (ex.: enviasse `[red, yellow, green]` para o cenário de melhora) falharia esses testes.

---

## 6. Busca comprovando ausência de segunda fonte (diretriz 2/6)

**Busca direta no código-fonte, evidência concreta:**

```
$ grep -n "gather_rag_context\|gather_context" src/agents/delivery_advisor/agent.py src/api/routes/intelligence.py
```

Resultado: `gather_rag_context` **nunca aparece invocado** em nenhum dos dois arquivos — a única menção é o tipo `RagContext` no type hint do parâmetro `rag_context: RagContext | None = None` (exigido pelo `AdvisorContract` Protocol, nunca instanciado ou usado). `gather_context()` aparece **exatamente uma vez** na rota, sempre com `kind="status"` — nenhuma chamada com `kind="risk"`, `"meeting"`, ou `"action_items"`.

**Prova estrutural em teste, não apenas busca textual:**
- `tests/test_delivery_advisor.py::TestSingleSourceOnly` — grava as chamadas reais a `gather_context()` durante uma execução completa e confirma `calls == ["status"]`.
- Todos os testes de `tests/test_delivery_advisor.py` constroem o `AdvisorFramework` com `rag_pipeline=None`: qualquer chamada acidental a `gather_rag_context()` levantaria `AttributeError` imediatamente, derrubando a suíte inteira — a suíte passando é, em si, a prova.
- `tests/test_delivery_advisor_api.py` substitui a dependência `build_rag_pipeline` por um dublê cujo `.retrieve()` lança `AssertionError` — os 9 testes do arquivo passam porque a rota nunca invoca esse método.

**Risco residual do Technical Design revisado (diretriz 6):** o item "`top_k` de RAG suplementar não validado" (`TECHNICAL-DESIGN-DELIVERY-ADVISOR.md` §10.3) é **removido** dos riscos residuais desta implementação — evidência concreta de código (acima) confirma que RAG nunca foi introduzido nesta Epic; o risco era residual do desenho anterior (que previa RAG opcional, como no Risk Advisor) e não se aplica à implementação final, per instrução explícita desta autorização.

---

## 7. Testes executados e resultados

| Suíte | Resultado |
|---|---|
| Backend completo (`pytest`) | **603 passed**, 0 failed (580 pré-existentes + 23 novos desta Epic: 8 unitários + 6 integração Framework + 9 HTTP) |
| Frontend completo (`vitest`) | **503 passed** (69 arquivos) — nenhum arquivo de frontend tocado nesta Epic |
| `ruff check src tests` | Limpo |
| `npx tsc --noEmit` | Limpo |
| `npx eslint .` | Limpo |

---

## 8. Critérios de aceite da Technical Design (D-106) — confirmação

1. ✅ Reuso integral do `AdvisorFramework`/`AIContextEngine` — confirmado, `git diff` vazio.
2. ✅ Classe A preservada — uma única chamada a `gather_context(kind="status")`, nenhuma segunda fonte (§6).
3. ✅ Recência e tendência resolvidas exclusivamente no prompt — nenhum algoritmo de comparação implementado (§4).
4. ✅ Três cenários temporais comprovados, com timestamps explícitos, em duas camadas (§5).
5. ✅ `CitedAnalysis` reaproveitado sem duplicação; RBAC `intelligence.read` reutilizada, nenhuma migração nova.
6. ✅ RAG explicitamente ausente — busca de código + prova estrutural em teste (§6); risco residual correspondente removido.
7. ✅ `ruff check src tests` limpo; suíte completa verde; testes cobrindo evidência real, ausência de evidência, isolamento de tenant, os três cenários temporais mandados.

---

## 9. Riscos residuais (reconfirmados, nenhum bloqueante)

1. **Qualidade da interpretação de tendência pelo LLM** — mitigado pelos testes dedicados de melhora/deterioração/registro único (§5); o modelo real (fora dos testes com provider scriptado) pode variar na qualidade da síntese, mas a estrutura de dados que ele recebe é comprovadamente correta e não-invertida.
2. **Volume de `AnalysisRecord`s de status sem `limit`** — já registrado no Domain Blueprint/AR-11/Technical Design, não agravado; nenhum caso real até aqui exige um `limit` explícito.
3. **TD-015** — não incide neste Advisor (Classe A via `gather_context()`, não `normalize_rag_evidence()`).
4. ~~`top_k` de RAG suplementar não validado~~ — **removido** (§6), RAG confirmadamente ausente desta implementação.

Nenhum risco bloqueia o encerramento do Epic.

---

## 10. Confirmação de encerramento

Todos os critérios de aceite atendidos. Nenhuma expansão de escopo além do autorizado. **Recomendação: GO para o encerramento do Epic do Delivery Advisor.**

Per instrução explícita do Founder: retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor.
