# Technical Design — Enterprise Advisor Framework, Fase 3 (Minimum Viable Framework)

**Escopo:** contratos e infraestrutura comum de execução de Advisors, grounded estritamente na auditoria do `RiskAdvisorAgent` real (§1). Nenhum Advisor é migrado ou reimplementado nesta Fase — `RiskAdvisorAgent`/`ask_risk_advisor` (`src/api/routes/intelligence.py`) permanecem **intocados**. A validação arquitetural do Framework só ocorre na Fase 4, quando o Risk Advisor for migrado (Founder, condição 6).
**Autorização:** Decisão do Founder "Wave 3 • Fase 3", com 7 condições obrigatórias, todas operacionalizadas abaixo.

---

## 1. Auditoria do Risk Advisor (condição 2, obrigatória antes de qualquer código)

Fluxo real e completo hoje, linha a linha, de `POST /risk-advisor/ask` (`src/api/routes/intelligence.py:476-527`) + `RiskAdvisorAgent.advise()` (`src/agents/risk_advisor/agent.py`):

1. A rota constrói `SessionContext(organization_id, user_id, session_id, project_name)` a partir do `RequestContext` já resolvido — **boilerplate idêntico para qualquer Advisor futuro**.
2. A rota constrói `AIContextEngine(repository)` e chama `.gather(organization_id, project_name, kind="risk")` → `list[Evidence]` — **acesso a contexto já compartilhado pela Foundation** (nenhuma duplicação a resolver).
3. A rota chama `AIFoundationAudit.record_question(repository, session, "risk_advisor", question)` **incondicionalmente, antes de qualquer decisão de evidência** — **boilerplate idêntico**, já compartilhado pela Foundation.
4. Se `not evidence`: `RecommendationEngine.no_evidence(...)` + `ExplanationEngine.explain(...)`, retorna sem chamar o LLM — **boilerplate idêntico** (evita custo e alucinação sobre dado inexistente).
5. Senão, a rota constrói `RiskAdvisorAgent(model_client=provider, prompt_registry=prompts)` e chama `.advise(session, question, evidence)`:
   a. **Específico do Advisor:** extrai `risks_json` da evidência (conhece o vocabulário de risco: `probability`/`impact`/`mitigation`/`escalation_recommendation`).
   b. Chama `render_analyst_prompt(prompt_registry, "risk_advisor", "advise", question=..., risks_json=...)` — compõe o preâmbulo institucional compartilhado com o template próprio do Advisor — **já compartilhado pela Foundation, apenas o nome do agente e as variáveis são específicos**.
   c. Chama `ObservabilityRecorder.record_call("risk_advisor", session, model_client, final_prompt)` — **isto já é o acesso controlado e observado ao LLM**, só que hoje invocado de dentro do próprio Agent em vez de através de um Framework.
   d. Chama `parse_structured_output(raw_output)` — parsing tolerante a cercas de código, nunca lança exceção (fallback `{"structured": False, ...}`) — **já compartilhado** (`src/agents/shared/output_parser.py`).
   e. Retorna `{"agent": "risk_advisor", "model_output": ...}` — **formato ad-hoc, não um contrato formal**.
6. A rota valida `model_output.get("structured")` e `isinstance(model_output.get("answer"), str)`, senão `HTTPException(502, ...)` — **boilerplate idêntico**, hoje inline na rota, não reutilizável.
7. `RecommendationEngine.build(answer, cited_analysis_ids, evidence)` — descarta qualquer citação inventada — **já compartilhado**.
8. `ExplanationEngine.explain(recommendation)` — **já compartilhado**.
9. A rota serializa em `RiskAdvisorResponse` (Pydantic, HTTP-specific) — estruturalmente idêntico ao que qualquer Advisor futuro precisaria (resposta + citações).

### O que já é genuinamente compartilhado (Foundation, Wave 2/W3-2) — nada disto é recriado

`AIContextEngine`, `AIFoundationAudit`, `RecommendationEngine`, `ExplanationEngine`, `ObservabilityRecorder`, `render_analyst_prompt`, `PromptRegistry`, `LLMProvider`, `parse_structured_output`, os tipos `Evidence`/`SessionContext`/`Recommendation`/`Explanation`.

### O que é hoje boilerplate duplicável (não uma abstração especulativa — é o que a própria rota já faz, extraível verbatim)

- A sequência fixa: auditoria incondicional → checagem de evidência vazia → invocação do Advisor → validação da forma da saída → `RecommendationEngine.build` → `ExplanationEngine.explain`.
- O acesso ao LLM via `ObservabilityRecorder`, hoje dentro do Agent em vez de mediado por um componente comum.
- O contrato de entrada/saída do Agent (`advise(session, question, evidence) -> dict` com `structured`/`answer`/`cited_analysis_ids`) — já é exatamente essa forma hoje, sem generalização inventada.

### O que NÃO existe hoje e é mandato explícito do Founder para esta Fase (não é invenção especulativa, é requisito direto)

- Acesso a RAG: o Risk Advisor **não usa `RagPipeline` hoje**. O Founder exige que o Framework proveja "acesso controlado ao RAG" (§4) e que o fluxo-alvo da Fase 4 inclua `RagPipeline` (§6, diagrama de validação). Esta Fase constrói a capacidade; a Fase 4 a conecta ao Risk Advisor migrado.

---

## 2. Contrato mínimo (`AdvisorContract`) — nasce exatamente da forma provada em §1

```python
class AdvisorContract(Protocol):
    name: str
    def advise(self, session: SessionContext, question: str, evidence: list[Evidence]) -> dict: ...
```

Idêntico, campo a campo, ao que `RiskAdvisorAgent.advise()` já implementa por duck typing hoje — declarar isso como `Protocol` não introduz uma abstração nova para Advisors hipotéticos, apenas nomeia uma forma já real. **Nenhum `input_schema`/`output_schema` genérico por Advisor é introduzido** (a especulação do Blueprint original, corrigida por esta Decisão do Founder) — a forma de saída (`dict` com `structured`/`answer`/`cited_analysis_ids`) é a mesma para todo Advisor, porque é a mesma exigida pelo `RecommendationEngine.build()` já existente.

---

## 3. `AdvisorFramework` (`src/services/advisor_framework/framework.py`)

Mapeamento direto às 8 responsabilidades do Founder (§4), cada uma um método fino, sem lógica nova além de extrair o que a rota já faz:

| Responsabilidade (Founder §4) | Método | Origem (auditoria §1) |
|---|---|---|
| Contrato de execução | `AdvisorContract` (§2) + `run()` | Passo 5 |
| Contexto | `gather_context()` | Passo 2 (`AIContextEngine`, passthrough) |
| Acesso controlado ao RAG | `gather_rag_context()` | Mandato do Founder (RagPipeline, Fase 2), sem uso hoje |
| Acesso controlado ao LLM | `render_prompt()` + `call_llm()` | Passos 5b/5c (`render_analyst_prompt`/`ObservabilityRecorder`, passthrough) |
| Resultado estruturado | `Explanation`/`Recommendation` (reaproveitados, não duplicados) | Passos 7-8 |
| Rastreabilidade | `Recommendation.cited_evidence` + `RagContext.chunk_ids` (Fase 2) | Passo 7 |
| Auditoria | `run()` chama `AIFoundationAudit.record_question()` | Passo 3 |
| Tratamento de falhas | `run()` levanta `AdvisorExecutionError` uniforme | Passo 6 (hoje inline na rota) |

```python
class AdvisorFramework:
    def __init__(self, repository, prompt_registry, llm_provider, rag_pipeline): ...

    def gather_context(self, organization_id, project_name, kind) -> list[Evidence]: ...
    def gather_rag_context(self, organization_id, query, top_k=5) -> RagContext: ...
    def render_prompt(self, advisor_name, prompt_name, **variables) -> str: ...
    def call_llm(self, advisor_name, session, prompt) -> str: ...

    def run(self, advisor: AdvisorContract, session, question, evidence) -> Explanation:
        """A sequência exata da rota hoje (passos 3-8 de §1), extraída uma
        única vez -- não uma nova orquestração, a mesma."""
```

`run()` executa **exatamente um** Advisor por chamada, nunca escolhe entre vários, nunca delega a outro Advisor — não é um workflow engine nem roteamento autônomo (proibições do Founder §5, verificadas caso a caso em §6).

---

## 4. Fronteiras preservadas (condição 3)

`AdvisorFramework` só chama `AIContextEngine`, `RagPipeline`, `AIFoundationAudit`, `ObservabilityRecorder`, `render_analyst_prompt` — nenhuma linha importa `PgVectorRepository`, `EmbeddingProvider`, ou qualquer tabela (`Chunk`/`Document`/`DocumentVersion`/`MemoryRecord`) diretamente. A cadeia obrigatória (`Advisor → Framework → RagPipeline/EnterpriseMemoryService → KnowledgeRepository → Infraestrutura`) permanece estrutural: `gather_rag_context()` chama `RagPipeline.retrieve()`, que só chama `KnowledgeRepository`, exatamente como construído na Fase 2 — nenhuma alteração a essa cadeia.

---

## 5. Restrições de sobre-engenharia (condição 5) — checklist explícita

| Proibição | Verificação |
|---|---|
| Novos providers | Nenhum — `LLMProvider`/`EmbeddingProvider` inalterados. |
| Registries genéricos | Nenhum — nenhum `AdvisorRegistry`; a Fase 4 instancia o Advisor migrado diretamente. |
| Factories abstratas | Nenhuma. |
| Plugins | Nenhum. |
| Workflow engine | Nenhum — `run()` é uma sequência linear fixa, não configurável, não composável em grafo. |
| Roteamento autônomo entre Advisors | Nenhum — `run()` recebe o Advisor já escolhido pelo chamador. |
| Multiagentes / delegação entre agentes | Nenhum — nenhum Advisor pode chamar outro através do Framework. |
| Múltiplos modelos de orquestração | Nenhum — um único método `run()`, uma única forma de execução. |
| Extensibilidade sem consumidor real | `gather_rag_context()`/`call_llm()` têm consumidor real agendado (migração do Risk Advisor, Fase 4) — não especulativo. |

---

## 6. Abstrações deliberadamente NÃO criadas (para o relatório de governança, condição 7)

- `AdvisorContract` com `input_schema`/`output_schema` genéricos por Advisor (estava no Blueprint original — corrigido: a forma de saída é única e fixa, provada pelo Risk Advisor).
- Qualquer registro/catálogo dinâmico de Advisors.
- Qualquer mecanismo de comunicação/delegação entre Advisors.
- Qualquer política de retry/circuit breaker sobre `LLMProvider` (nenhuma falha recorrente documentada que a justifique).
- Qualquer cache de contexto/RAG no Framework (a Fase 2 já decidiu que cache é responsabilidade da Knowledge Platform, se necessário).

---

## 7. Testes (grounding, não migração)

Como nenhum Advisor real é migrado nesta Fase, os testes usam um Advisor de teste mínimo (`_FakeAdvisor`, implementando `AdvisorContract` com uma resposta determinística) — nunca o `RiskAdvisorAgent` real, que permanece intocado. Cobertura: `run()` audita incondicionalmente; `run()` retorna `no_evidence()` sem chamar o Advisor quando não há evidência; `run()` descarta citação inventada; `run()` levanta `AdvisorExecutionError` para saída malformada; `gather_context()`/`gather_rag_context()` delegam exatamente a `AIContextEngine`/`RagPipeline` sem tocar infraestrutura; `call_llm()` delega a `ObservabilityRecorder.record_call()`.

---

## 8. Arquivos criados (checklist)

- `src/services/advisor_framework/__init__.py` (novo)
- `src/services/advisor_framework/types.py` (novo — `AdvisorContract`, `AdvisorExecutionError`)
- `src/services/advisor_framework/framework.py` (novo — `AdvisorFramework`)
- `tests/test_advisor_framework.py` (novo)

**Nenhum arquivo de `src/agents/risk_advisor/`, `src/api/routes/intelligence.py`, frontend, ou migração de banco é tocado nesta Fase.**
