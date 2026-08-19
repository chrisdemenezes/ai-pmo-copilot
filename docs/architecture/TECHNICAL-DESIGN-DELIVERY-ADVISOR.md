# Technical Design — Delivery Advisor (etapa 4 de 6)

**Autorização:** "Founder Decision — AR-11 Delivery Advisor" (veredito **APPROVED — GO para o Technical Design**), oficializando: (1) a recência do `AnalysisRecord` continua sendo tratada exclusivamente como conhecimento de domínio do Delivery Advisor, zero lógica adicionada a `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline; (2) o `AnalysisRecord` mais recente representa o estado atual do projeto, registros anteriores utilizáveis apenas como contexto histórico ou tendência; (3) acrescentar nesta etapa uma orientação adicional: quando existirem múltiplos `AnalysisRecord`s de status para o mesmo projeto, o Advisor deve considerar a evolução temporal da sequência para identificar tendências (melhora, estabilidade ou deterioração) — interpretação exclusivamente no prompt do `DeliveryAdvisorAgent`, nenhum algoritmo adicional implementado; (4) preservar integralmente toda a infraestrutura compartilhada. Nenhum código escrito nesta etapa.

---

## Executive Summary

O Delivery Advisor reutiliza, sem exceção, a infraestrutura já provada pelo Risk Advisor — o único outro Advisor Classe A em produção: `AdvisorFramework`, `AIContextEngine.gather()`, o portão anti-alucinação, `intelligence.read`. O único componente novo é o `DeliveryAdvisorAgent` — um Advisor de domínio que (a) recebe todos os `AnalysisRecord`s de `kind="status"` de um projeto, já ordenados do mais recente para o mais antigo (garantia estrutural já existente, confirmada em AR-11), (b) trata o primeiro da lista como o estado atual e os demais como histórico, e (c) quando houver mais de um registro, interpreta a sequência para descrever uma tendência (melhorando, estável, ou deteriorando) — tudo isso **exclusivamente como texto de prompt**, sem nenhum algoritmo de comparação de datas ou de `health_status` implementado em código. Nenhuma linha de `AdvisorFramework`, `AIContextEngine`, Event Pipeline ou Workflow Runtime é tocada. Recomendação ao final: **GO para a implementação.**

---

## 1. Reuso integral do `AdvisorFramework` (confirmado, zero mudança)

Idêntico ao já confirmado para o Risk Advisor (Classe A, referência estrutural direta) e reafirmado para Document/Governance Advisor (D-095/D-101 §1) — reafirmado aqui, não redecidido:

- `AdvisorFramework(repository, prompts, provider, rag_pipeline)` — construção idêntica.
- `gather_context(organization_id, project_name, kind="status")` — já existente, zero mudança de assinatura.
- `run()` — **byte-for-byte inalterado**. O `DeliveryAdvisorAgent` é apenas mais um `AdvisorContract` executado pela mesma função.

**Confirmação explícita per exigência do Founder (item 4 da autorização):** nenhuma lógica de recência, nenhuma lógica de tendência temporal, toca `AdvisorFramework`, `AIContextEngine`, Workflow Runtime ou Event Pipeline. Todo o comportamento novo desta Epic vive em exatamente dois lugares: o prompt do `DeliveryAdvisorAgent` (domínio) e a rota HTTP (`intelligence.py`, mesmo arquivo e mesmo padrão de `_risk_advisor_response`) — nunca no Framework.

---

## 2. Fluxo completo

```
Cliente (pergunta em linguagem natural sobre entrega/cronograma/bloqueios de um projeto)
  │
  ▼
POST /delivery-advisor/ask   (src/api/routes/intelligence.py, novo)
  │  RBAC: require_permission("intelligence.read")  -- reaproveitada do Risk Advisor,
  │  sem migração nova (leitura de análise já existente, nunca cria/edita nada)
  ▼
SessionContext (organization_id, user_id, session_id, project_name)
  ▼
AdvisorFramework(repository, prompts, provider, rag_pipeline)   -- construção idêntica
  │
  ▼
framework.gather_context(organization_id, project_name, kind="status")
  │   AIContextEngine.gather() -- zero mudança. Resolve project_name -> project_id,
  │   filtra por organization_id/kind, retorna list[Evidence] JÁ ORDENADA do mais
  │   recente para o mais antigo (AnalysisRepository.list_analyses() já ordena por
  │   created_at.desc() -- confirmado em AR-11, garantia estrutural pré-existente)
  ▼
framework.gather_rag_context(organization_id, question, top_k=5)   -- suplementar,
  │   opcional, mesmo papel que já ocupa para o Risk Advisor -- nunca a fonte primária
  ▼
framework.run(delivery_advisor_agent, session, question, evidence, rag_context,
               no_evidence_answer="Nenhuma análise de status registrada ainda para este projeto.")
  │
  ├─ AIFoundationAudit.record_question(...)          -- inalterado
  ├─ if not evidence: RecommendationEngine.no_evidence(no_evidence_answer)  -- inalterado
  ├─ DeliveryAdvisorAgent.advise(...)   -- novo Advisor (§3)
  │     → framework.render_prompt(...) → framework.call_llm(...) → LLMProvider
  │     → resposta JSON com "answer" já refletindo estado atual + tendência (§4)
  ├─ RecommendationEngine.build(answer, cited_analysis_ids, evidence)   -- inalterado
  └─ ExplanationEngine.explain(recommendation)   -- inalterado
  ▼
_delivery_advisor_response(explanation)   -- NOVO, mas apenas na rota (§5)
  ▼
DeliveryAdvisorResponse{answer, cited_analyses: [...]}
```

---

## 3. Contrato do `DeliveryAdvisorAgent` (nenhum contrato novo)

```python
class DeliveryAdvisorAgent:
    name = "delivery_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(
        self,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict:
        # `evidence` já chega ordenada do mais recente para o mais antigo
        # (AIContextEngine.gather(), garantia estrutural confirmada em
        # AR-11) -- este código NUNCA reordena, NUNCA calcula tendência.
        # A leitura de "primeiro = atual, demais = histórico" e a inferência
        # de tendência são inteiramente do modelo, orientado pelo prompt (§4).
        status_history_json = json.dumps(
            [
                {
                    "health_status": item.content.get("health_status"),
                    "key_findings": item.content.get("key_findings"),
                    "recommendations": item.content.get("recommendations"),
                    "source_analysis_id": item.source_id,
                    "source_created_at": str(item.metadata["created_at"]),
                }
                for item in evidence
            ],
            ensure_ascii=False,
        )
        # Supplementary only (mesmo papel que já ocupa para o Risk Advisor):
        # nunca a base única de uma alegação, nunca introduz um fato ausente
        # de status_history_json.
        additional_context_json = json.dumps(
            [
                {"chunk_id": chunk.chunk_id, "document_id": chunk.document_id, "text": chunk.text}
                for chunk in (rag_context.chunks if rag_context else [])
            ],
            ensure_ascii=False,
        )
        final_prompt = self.framework.render_prompt(
            self.name,
            "advise",
            question=question,
            status_history_json=status_history_json,
            additional_context_json=additional_context_json,
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
```

Mesma forma exata de `AdvisorContract`, mesmo `parse_structured_output` já usado por Risk/Document/Governance Advisor. Estrutura do método idêntica à de `RiskAdvisorAgent.advise()` (JSON de evidência + contexto suplementar opcional + `render_prompt`/`call_llm`) — nenhuma abstração nova, apenas o conteúdo do JSON e do prompt mudam para o domínio de status de entrega.

---

## 4. Interpretação de recência e tendência temporal — comportamento exclusivo do Advisor

### 4.1 O que já é estrutural, o que é novo nesta etapa

**Já estrutural, confirmado em AR-11, zero mudança aqui:** a ordenação do mais recente para o mais antigo (`list_analyses()` → `AIContextEngine.gather()`) e o timestamp por registro (`Evidence.metadata["created_at"]`).

**Novo nesta etapa, per item 3 da autorização do Founder:** uma instrução explícita no prompt orientando o `DeliveryAdvisorAgent` a (a) tratar o primeiro item de `status_history_json` como o estado atual, os demais como histórico (já decidido em AR-11 §3.3, aplicado aqui); e (b) quando `status_history_json` tiver 2 ou mais entradas, examinar a sequência (`health_status`/`key_findings`, na ordem já fornecida) e descrever uma tendência — melhorando, estável, ou deteriorando — grounded exclusivamente nos registros efetivamente presentes, nunca inferida além deles.

### 4.2 Por que nenhum algoritmo é implementado (confirmação explícita per item 3)

Não há, em nenhum ponto do código desta Epic, uma função que compare `health_status` entre registros, calcule uma diferença de datas, ou decida programaticamente se a tendência é "melhora"/"estabilidade"/"deterioração". `DeliveryAdvisorAgent.advise()` (§3) apenas serializa a lista de evidência, já ordenada, para JSON — a interpretação de "o que essa sequência significa" é inteiramente do modelo de linguagem, seguindo a instrução do prompt (§4.3). Isso é o mesmo princípio já aplicado à hierarquia documental do Governance Advisor (AR-10/Technical Design D-101 §4.2/§7): classificação/interpretação de domínio como conhecimento de prompt, nunca como lógica determinística no Framework ou no próprio Advisor.

### 4.3 Prompt (rascunho, `src/agents/delivery_advisor/prompts/advise.md`, a ser criado na Implementação)

```
You are an AI PMO Copilot agent specialized in project delivery status (schedule, blockers, execution).

Answer strictly and exclusively based on the project status history provided below. Never invent a fact not present in this data, and never assume a risk, action, or blocker that is not already mentioned in it.

The status history is a JSON array, ordered from most recent to oldest. The FIRST entry is the CURRENT state of the project. Any entry after the first is HISTORICAL -- cite it only as historical context or trend, never present it as if it were the current state.

When the status history has 2 or more entries, examine the sequence (health_status and key_findings, in the order given) and describe the trend across it as exactly one of: "melhorando", "estável", or "deteriorando" -- grounded only in the entries actually provided, never inferred beyond them. When only 1 entry exists, there is no trend to report -- describe only the current state, and do not mention a trend.

Question: $question

Project status history (JSON array, most recent first):
$status_history_json

Additional context (optional, supplementary only -- never the sole basis for a claim):
$additional_context_json

Respond with a single JSON object only, no extra text before or after it, using exactly this schema:
{
  "answer": "string",
  "cited_analysis_ids": [integer, ...]
}

"cited_analysis_ids" must list the "source_analysis_id" of every status history entry your answer draws from -- include historical entries you cite for trend, never omit them.
```

Este texto é um rascunho de referência para a Implementação — a Technical Design autoriza sua estrutura e conteúdo, não fixa a redação final palavra por palavra.

### 4.4 Confirmação: recência e tendência não alteram a classificação Classe A

`status_history_json` é construído a partir de uma única chamada a `gather_context(kind="status")` (§3) — múltiplos registros do mesmo `kind` continuam sendo uma única fonte primária de evidência, per definição institucional permanente (D-104/AR-8 §4.2: Classe A é cardinalidade de fontes, não de registros dentro da mesma fonte). Nenhuma segunda chamada estrutural é introduzida por esta interpretação temporal.

---

## 5. Rota HTTP e modelo de resposta (`src/api/routes/intelligence.py`, mesmo arquivo do Risk Advisor)

```python
class DeliveryAdvisorRequest(BaseModel):
    project_name: str
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class DeliveryAdvisorResponse(BaseModel):
    answer: str
    cited_analyses: list[CitedAnalysis]   # reaproveitado do Risk Advisor -- mesmo shape exato


@router.post("/delivery-advisor/ask", response_model=DeliveryAdvisorResponse)
def ask_delivery_advisor(
    request: DeliveryAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    # Read-only: reuses the same permission protecting the Risk Advisor --
    # this agent never creates/edits/triggers an analysis.
    _permission: None = Depends(require_permission("intelligence.read")),
):
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
        project_name=request.project_name,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)

    evidence = framework.gather_context(session.organization_id, session.project_name, kind="status")
    rag_context = framework.gather_rag_context(session.organization_id, request.question, top_k=5)

    agent = DeliveryAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            evidence,
            rag_context=rag_context,
            no_evidence_answer="Nenhuma análise de status registrada ainda para este projeto.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _delivery_advisor_response(explanation)


def _delivery_advisor_response(explanation) -> DeliveryAdvisorResponse:
    return DeliveryAdvisorResponse(
        answer=explanation.recommendation.answer,
        cited_analyses=[
            CitedAnalysis(
                source_analysis_id=item.source_id,
                source_created_at=item.metadata["created_at"],
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )
```

**Reuso confirmado, não duplicado:** `CitedAnalysis` (já definido para o Risk Advisor) é reaproveitado sem alteração — mesmo shape (`source_analysis_id`/`source_created_at`) atende integralmente ao Delivery Advisor.

---

## 6. RBAC — nenhuma migração nova

`intelligence.read` protege `POST /delivery-advisor/ask`, exatamente como já faz para `/risk-advisor/ask` — mesma justificativa: síntese de leitura sobre análises já existentes, nunca cria/edita/dispara uma análise nova.

---

## 7. `no_evidence_answer` de domínio

`"Nenhuma análise de status registrada ainda para este projeto."` — wording próprio do Delivery Advisor (distinto do genérico de risco), decisão reservada a este Technical Design per Domain Blueprint §8, risco 2.

---

## 8. Garantias (reafirmadas, mesma prova já aplicada aos demais Advisors)

- **Rastreabilidade de citação:** `RecommendationEngine.build()` descarta qualquer `source_analysis_id` não presente na `evidence` entregue — idêntico, inalterado.
- **Isolamento organizacional:** estrutural, no único ponto de construção já `organization_id`/`project_id`-scoped (`AIContextEngine.gather()`).
- **Portão anti-alucinação:** `if not evidence:` em `run()`, inalterado — cobre a ausência de status sem mecanismo novo.
- **Nenhuma segunda fonte estrutural (Classe A, D-104):** confirmado por leitura de código do `DeliveryAdvisorAgent`/rota (§3/§5) — uma única chamada a `gather_context()`.
- **Ausência de algoritmo de tendência:** confirmado por leitura de código (§4.2) — nenhuma função de comparação de datas/`health_status` implementada.

---

## 9. Testes planejados (plano, não implementação)

1. **Estado atual sem histórico:** um único `AnalysisRecord` de status → resposta descreve apenas o estado atual, sem mencionar tendência.
2. **Estado atual com histórico, tendência de melhora:** três `AnalysisRecord`s de status (`red` mais antigo → `yellow` → `green` mais recente) → resposta reflete `green` como estado atual e descreve tendência de melhora, citando os três `source_analysis_id`s.
3. **Estado atual com histórico, tendência de deterioração:** sequência inversa (`green` → `yellow` → `red` mais recente) → resposta reflete `red` como estado atual e descreve deterioração — **critério de sucesso mandado por AR-11**: nenhuma resposta apresenta um registro antigo como se fosse o estado atual.
4. **Ausência de evidência:** nenhum `AnalysisRecord` de `kind="status"` para o projeto → resposta canônica, sem chamada ao LLM.
5. **Citação inventada descartada:** mesmo padrão já provado (Risk/Document/Governance Advisor).
6. **Isolamento organizacional:** mesmo padrão já provado.
7. **Nenhuma segunda consulta estrutural:** verificação por leitura de código (assert de que `gather_context()` é chamado exatamente uma vez por requisição, com `kind="status"`).
8. **`AdvisorFramework`/`AIContextEngine`/`Recommendation`/`Explanation` inalterados:** confirmado por `git diff` vazio nesses arquivos ao final da implementação — mesma prova já usada em W5-1/Governance Advisor.

---

## 10. Riscos residuais

1. **Qualidade da interpretação de tendência pelo LLM (§4)** — depende inteiramente da aderência do modelo à instrução do prompt; mitigado pelos testes dedicados de melhora/deterioração (§9.2-9.3). Não bloqueante.
2. **Volume de `AnalysisRecord`s de status sem `limit`** — já registrado no Domain Blueprint/AR-11, não agravado; avaliação de um `limit` explícito reservada para além desta Epic, se um caso real exigir.
3. **`top_k` de RAG suplementar não validado** — mesmo risco residual já registrado para os demais Advisors que usam RAG suplementar.
4. **TD-015** — não incide neste Advisor (Classe A via `gather_context()`, não `normalize_rag_evidence()`).

Nenhum risco bloqueia a implementação.

---

## 11. Estratégia incremental de implementação

1. **Passo 1 — `DeliveryAdvisorAgent` + prompt:** novo agente (`src/agents/delivery_advisor/`), reaproveitando `parse_structured_output`/`render_analyst_prompt`/`ObservabilityRecorder` sem duplicação — testes unitários (§9.1-9.3, mock de `AdvisorFramework`).
2. **Passo 2 — Rota + modelo de resposta:** `POST /delivery-advisor/ask`, `DeliveryAdvisorRequest`/`DeliveryAdvisorResponse`, reaproveitando `CitedAnalysis` — testes de integração via `AdvisorFramework` real (§9.4, §9.6-9.7).
3. **Passo 3 — Testes de tendência temporal (evidência obrigatória desta Epic, análoga à evidência CONFLITANTE do Governance Advisor):** cenário real de melhora e cenário real de deterioração (§9.2-9.3), em duas camadas — Framework (`AdvisorFramework.run()` direto) e HTTP (`TestClient` real) — comprovando que o registro mais recente sempre determina o estado atual reportado.
4. **Passo 4 — Verificação final:** suíte backend completa, `ruff`/`tsc`/`eslint`, confirmação de `AdvisorFramework`/`AIContextEngine`/`Recommendation`/`Explanation` inalterados via `git diff`, governança (Decision Log/CHANGELOG/Mission Control), Executive Evidence.

Cada passo é independentemente testável — nenhum passo depende de código do passo seguinte para validação isolada.

---

## 12. Recomendação GO/NO-GO para implementação

**GO.** Todos os pontos exigidos pela autorização do Founder foram resolvidos com evidência de código real: recência confirmada como conhecimento de domínio, zero lógica nova em Framework/`AIContextEngine` (§1, §4); o `AnalysisRecord` mais recente tratado como estado atual (§4.1); interpretação de tendência temporal definida exclusivamente como conteúdo de prompt, nenhum algoritmo implementado (§4.2-4.3); toda a infraestrutura compartilhada (`AdvisorFramework`, `AIContextEngine`, Workflow Runtime, Event Pipeline) preservada integralmente (§1, §8). Nenhum risco residual (§10) bloqueia o início da implementação.

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de qualquer implementação.
