# Technical Design — Risk Advisor Migration (Wave 3, Fase 4)

**Escopo:** migrar `RiskAdvisorAgent`/`ask_risk_advisor` para usar `AdvisorFramework`, `RagPipeline`, `KnowledgeRepository` (via `AdvisorFramework`, nunca diretamente) — a única forma de validar arquiteturalmente o que as Fases 1-3 construíram (Founder, condição 1: "não deve criar novas capacidades... validar tudo o que foi construído"). Contrato HTTP (`RiskAdvisorRequest`/`RiskAdvisorResponse`) permanece **byte-idêntico** — nenhuma mudança visível ao frontend.
**Autorização:** "Founder Decision — Wave 3 • Fase 4".

---

## 1. Migração fiel (condição 2) — o que muda e o que não muda

| | Antes (Fase 3 e anteriores) | Depois (Fase 4) |
|---|---|---|
| `RiskAdvisorAgent.__init__` | `(model_client, prompt_registry)` | `(framework: AdvisorFramework)` |
| Composição de prompt | `render_analyst_prompt(...)` chamado diretamente pelo Agent | `self.framework.render_prompt(...)` — mesma função, atrás do Framework |
| Chamada ao LLM | `ObservabilityRecorder.record_call(...)` chamado diretamente pelo Agent | `self.framework.call_llm(...)` — mesma função, atrás do Framework |
| Orquestração da rota (auditoria, checagem de evidência vazia, validação de saída, `RecommendationEngine`/`ExplanationEngine`) | Inline em `ask_risk_advisor` | `framework.run(agent, session, question, evidence, rag_context)` — mesma sequência, extraída |
| Evidência de `AnalysisRecord` (`AIContextEngine`) | `context_engine.gather(...)` inline na rota | `framework.gather_context(...)` — mesma chamada, atrás do Framework |
| Evidência de RAG | **Não existe** | `framework.gather_rag_context(...)` — nova, mandatada pelo Founder para validar a cadeia completa |
| `RiskAdvisorRequest`/`RiskAdvisorResponse` | Pydantic, `answer` + `cited_analyses` | **Inalterado** |
| Regra "nenhuma citação inventada" (`RecommendationEngine.build`) | Aplicada a `analysis_id` | **Inalterada** — RAG não estende esta regra nesta Fase (ver §3) |
| Regra "sem evidência → sem chamada ao LLM" | Baseada em `AnalysisRecord` evidence | **Inalterada** — chave apenas em `evidence` (AnalysisRecord), nunca em `rag_context` (ver §4) |

**Nenhuma capacidade nova é criada** — `AdvisorFramework`, `RagPipeline`, `KnowledgeRepository` já existem (Fases 1-3); esta Fase apenas conecta o Risk Advisor a eles, exatamente como a condição 1 exige.

---

## 2. Extensão mínima do contrato (`AdvisorContract`)

```python
class AdvisorContract(Protocol):
    name: str
    def advise(
        self, session: SessionContext, question: str, evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict: ...
```

`rag_context` é opcional, com default `None` — nenhum Advisor de teste existente (`_FakeAdvisor`, Fase 3) quebra; `AdvisorFramework.run()` ganha o mesmo parâmetro opcional e o repassa a `advisor.advise(...)`. Esta é a única mudança de contrato desta Fase, e existe porque o Founder mandata explicitamente que o RAG apareça na cadeia real (§3 da Decisão) — não é uma abstração especulativa, é o fio que faltava para o RAG já construído (Fase 2) alcançar um Advisor real pela primeira vez.

---

## 3. Onde o RAG entra no prompt do Risk Advisor (sem estender o guard-rail de citação)

`RiskAdvisorAgent.advise()` monta um novo `additional_context_json` a partir de `rag_context.chunks` (lista vazia se `rag_context` for `None` ou não tiver chunks — o caso comum hoje, já que nenhum documento é ingerido para risco). O template `advise.md` ganha uma seção nova, explicitamente instruída como **suplementar, nunca a base isolada de uma afirmação, nunca introduzindo um risco não listado acima** — preserva a postura anti-alucinação já estabelecida, sem estender `RecommendationEngine.build()` para validar `chunk_id`s (isso seria uma capacidade nova, fora do escopo desta Fase). A rastreabilidade de `chunk_id` exigida pela condição 4 é demonstrada de outra forma (§5.1), não pela citação do modelo.

`Template.safe_substitute()` ignora uma variável extra não referenciada — templates de teste existentes (`FakePromptRegistry`, `tests/test_intelligence_api.py`) continuam funcionando sem alteração.

---

## 4. A regra "sem evidência → sem LLM" permanece intacta (condição 4)

`AdvisorFramework.run()` decide `no_evidence()` **exclusivamente** com base em `evidence` (a lista de `AnalysisRecord`), nunca em `rag_context` — exatamente o comportamento hoje. Isso preserva byte a byte o teste já existente `test_returns_a_canned_answer_without_calling_the_llm_when_no_risks_exist` (usa um `ExplodingProvider` que falha se `generate()` for chamado).

---

## 5. Validação ponta a ponta exigida (condição 3)

```
Risk Advisor → Advisor Framework → Gather Context → RagPipeline → KnowledgeRepository
  → Contexto rastreável → LLMProvider → Resposta → Auditoria
```

Implementado literalmente na rota `ask_risk_advisor`: `framework.gather_context(...)` (AIContextEngine) + `framework.gather_rag_context(...)` (RagPipeline → KnowledgeRepository) → `framework.run(agent, ..., rag_context)` (que audita, invoca o Advisor — que usa `framework.render_prompt`/`framework.call_llm`, ou seja, `LLMProvider` — e constrói a `Recommendation`/`Explanation`).

### 5.1 Rastreabilidade de `chunk_id`s (condição 4)

A rota loga `rag_context.chunk_ids` na mesma linha de log já existente (`organization_id`/`project_name`), tornando o conjunto de chunks realmente recuperados auditável no caminho de produção real — não apenas em teste isolado (Fase 3). O teste de migração (`tests/test_risk_advisor_migration.py`) ingere um documento real via `KnowledgeRepository`, faz uma pergunta através do Agent+Framework já migrados (não `_FakeAdvisor`), e comprova que os `chunk_id`s retornados por `gather_rag_context` correspondem exatamente ao chunk ingerido.

---

## 6. Novas dependências de injeção (`src/api/routes/intelligence.py`)

```python
def build_knowledge_repository(repository: AnalysisRepository = Depends(build_repository)) -> KnowledgeRepository:
    vector_repository = PgVectorRepository(repository.SessionLocal)
    return KnowledgeRepository(repository.SessionLocal, get_embedding_provider(), vector_repository)

def build_rag_pipeline(knowledge_repository: KnowledgeRepository = Depends(build_knowledge_repository)) -> RagPipeline:
    return RagPipeline(knowledge_repository)
```

Mesma composição de dependências já usada por `build_project_summary_service` — nenhum padrão novo de DI.

---

## 7. Confirmação de fronteiras (condição 4 — ausência de acesso direto à infraestrutura)

`ask_risk_advisor` e `RiskAdvisorAgent` seguem sem importar `PgVectorRepository`/`EmbeddingProvider`/qualquer tabela da Knowledge Platform — só `AdvisorFramework`/`RagPipeline`/`KnowledgeRepository` como classes de composição de DI (a mesma disciplina de Fase 3, agora exercitada por um Advisor real, não um `_FakeAdvisor`).

---

## 8. Arquivos alterados (checklist)

- `src/services/advisor_framework/types.py` (alterado — `rag_context` opcional)
- `src/services/advisor_framework/framework.py` (alterado — `run()` repassa `rag_context`)
- `src/agents/risk_advisor/agent.py` (alterado — usa `AdvisorFramework`)
- `src/agents/risk_advisor/prompts/advise.md` (alterado — seção suplementar de contexto)
- `src/api/routes/intelligence.py` (alterado — DI providers + `ask_risk_advisor` reescrita; `RiskAdvisorRequest`/`RiskAdvisorResponse` inalterados)
- `tests/test_advisor_framework.py` (alterado — `_FakeAdvisor` ganha `rag_context` opcional)
- `tests/test_risk_advisor_migration.py` (novo)
- `tests/test_intelligence_api.py::TestRiskAdvisor` — **inalterado**, deve permanecer 100% verde sem nenhuma modificação (prova de fidelidade funcional).
