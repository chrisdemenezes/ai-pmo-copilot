# Wave 3, Fase 3 — Enterprise Advisor Framework: Relatório de Governança

**Data:** 2026-07-27
**Autorização:** "Founder Decision — Wave 3 • Fase 3", com 7 condições obrigatórias.
**Escopo:** Framework mínimo viável, grounded na auditoria do Risk Advisor real. **Nenhum Advisor foi migrado ou reimplementado** — `RiskAdvisorAgent`/`ask_risk_advisor` permanecem intocados. Validação arquitetural do Framework fica para a Fase 4 (condição 6).

---

## 1. Artefatos implementados

| Artefato | Caminho |
|---|---|
| Technical Design (contém a auditoria completa, §1-8) | `docs/architecture/TECHNICAL-DESIGN-ENTERPRISE-ADVISOR-FRAMEWORK-FASE3.md` |
| `AdvisorContract` (Protocol) + `AdvisorExecutionError` | `src/services/advisor_framework/types.py` |
| `AdvisorFramework` | `src/services/advisor_framework/framework.py` |
| Testes (8 casos, contra um Advisor de teste mínimo) | `tests/test_advisor_framework.py` |

---

## 2. Responsabilidades extraídas do Risk Advisor (auditoria, condição 2)

Mapeadas linha a linha em `TECHNICAL-DESIGN-ENTERPRISE-ADVISOR-FRAMEWORK-FASE3.md` §1, a partir do fluxo real de `POST /risk-advisor/ask` + `RiskAdvisorAgent.advise()`:

1. Construção de `SessionContext` a partir do `RequestContext` — boilerplate idêntico, hoje inline na rota.
2. Chamada a `AIContextEngine.gather()` — já compartilhado, sem duplicação a resolver.
3. Auditoria incondicional via `AIFoundationAudit.record_question()` — boilerplate idêntico, antes de qualquer decisão de evidência.
4. Checagem de evidência vazia → `RecommendationEngine.no_evidence()` sem chamar o LLM — boilerplate idêntico.
5. Invocação do Agent (`.advise()`), incluindo o acesso ao LLM via `ObservabilityRecorder.record_call()` hoje feito dentro do próprio Agent.
6. Validação da forma da saída (`structured`/`answer`) com `HTTPException(502, ...)` — hoje inline na rota, não reutilizável.
7-8. `RecommendationEngine.build()` + `ExplanationEngine.explain()` — já compartilhados.

**Achado explícito da auditoria:** o Risk Advisor não usa `RagPipeline` hoje — é um requisito direto do Founder (não invenção) que o Framework proveja esse acesso, para a Fase 4 conectá-lo.

---

## 3. Contratos criados

- **`AdvisorContract`** (`Protocol`): `name: str` + `advise(session, question, evidence) -> dict`. Nomeia, verbatim, a forma que `RiskAdvisorAgent.advise()` já implementa hoje por duck typing — nenhum `input_schema`/`output_schema` genérico por Advisor foi introduzido (correção deliberada em relação ao Blueprint original de arquitetura, agora restrito ao que o Risk Advisor realmente prova).
- **`AdvisorFramework`**: 6 métodos finos, cada um mapeado 1:1 a uma responsabilidade explícita do Founder (§4 da Decisão) — `gather_context`, `gather_rag_context`, `render_prompt`, `call_llm`, `run` (execução + auditoria + tratamento de falhas).

---

## 4. Abstrações deliberadamente NÃO criadas

- `input_schema`/`output_schema` genéricos por Advisor.
- Registro/catálogo dinâmico de Advisors (`AdvisorRegistry`).
- Qualquer mecanismo de comunicação, delegação ou roteamento autônomo entre Advisors.
- Política de retry/circuit breaker sobre `LLMProvider` (nenhuma falha recorrente documentada que a justifique).
- Cache de contexto/RAG dentro do Framework (decisão já tomada na Fase 2: cache é responsabilidade da Knowledge Platform, se necessário).
- Qualquer novo provider, factory abstrata, plugin, ou workflow engine.

---

## 5. Testes

`tests/test_advisor_framework.py` (8 casos, banco PostgreSQL real efêmero, contra `_FakeAdvisor` — nunca `RiskAdvisorAgent`):

- Auditoria incondicional, com e sem evidência.
- `run()` retorna `no_evidence()` sem invocar o Advisor quando não há evidência.
- `run()` constrói uma `Recommendation` que descarta citação inventada (id fora da evidência real).
- `run()` levanta `AdvisorExecutionError` para saída malformada.
- `gather_rag_context()` delega corretamente a `RagPipeline` (ingestão + indexação reais).
- `call_llm()` delega a `ObservabilityRecorder`/`LLMProvider`.
- `render_prompt()` compõe o preâmbulo institucional compartilhado com o template do Risk Advisor (reaproveitado apenas como fixture de teste, sem tocar o Agent real).

**Resultado:** `ruff check src tests` limpo; suíte completa **485 testes passando** (8 novos), 97% de cobertura total, 100% no novo pacote `src/services/advisor_framework/`.

---

## 6. Riscos residuais

1. **O Framework ainda não foi exercitado por um Advisor real** — só a Fase 4 (migração do Risk Advisor) prova que os métodos `gather_rag_context`/`call_llm`/`render_prompt` compõem corretamente em um fluxo de produção, não apenas isoladamente contra `_FakeAdvisor`. Risco aceito e explicitamente reconhecido pela condição 6 do Founder.
2. **`AdvisorExecutionError` ainda não está mapeada para HTTP** — a rota `ask_risk_advisor` continua tratando saída malformada inline (`HTTPException(502, ...)`); o mapeamento para o novo tipo de exceção é trabalho da migração (Fase 4), não desta Fase.
3. **Nenhum segundo Advisor real existe ainda** para validar que `AdvisorContract` de fato generaliza além do Risk Advisor — mitigado por ter restringido o contrato exatamente à forma já provada, em vez de especular uma forma mais genérica.

---

## 7. Confirmação de ausência de acesso direto à infraestrutura

Busca global confirma: `PgVectorRepository`/`EmbeddingProvider` e qualquer tabela (`Chunk`/`Document`/`DocumentVersion`/`MemoryRecord`) **não são importados** por `src/services/advisor_framework/` nem por `src/agents/` — apenas citados em comentários/docstrings explicando a fronteira. A cadeia `Advisor → Advisor Framework → RagPipeline/EnterpriseMemoryService → KnowledgeRepository → Infraestrutura` permanece estrutural, sem exceção.

---

## 8. Governança atualizada

- **Decision Log:** D-067 (`docs/product/stratech-v2/DECISION-LOG.md`).
- **CHANGELOG:** entrada "Wave 3 — Fase 3".
- **Mission Control:** `RECENT_DECISIONS`, `PRODUCT_PULSE_TODAY`, detalhe da Wave 3 em `ENTERPRISE_PROGRAM_WAVES` (`web/lib/mock/mission-control-data.ts`).
- **Execution Plan:** `docs/product/WAVE-3-EXECUTION-PLAN.md` — linha de status da Fase 3 e Gate "Fase 3 → Fase 4" marcados cumpridos (tecnicamente; validação arquitetural pendente da migração do Risk Advisor, per condição 6).

**Encerramento:** Fase 3 implementada tecnicamente, testada, documentada. Validação arquitetural completa aguarda a Fase 4.
