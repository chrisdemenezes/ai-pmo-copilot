# Technical Design — Governance Advisor (etapa 4 de 6)

**Autorização:** "Founder Decision — AR-10 Governance Advisor" (veredito **APPROVED — GO para o Technical Design**), oficializando: (1) a hierarquia documental de AR-10 permanece definitiva (Decision Log → Technical Debt Register → Mission Control/CHANGELOG → Blueprint/AR/TD quando aprovados pelo Decision Log); (2) essa precedência continua sendo conhecimento de domínio do Governance Advisor, zero lógica adicionada a `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline; (3) TD-015 permanece Deferred, gatilho definitivo: "manutenção arquitetural isolada explicitamente autorizada pelo Founder", nenhum Advisor pode carregá-la incidentalmente; (4) definir, nesta etapa, uma classificação explícita dos estados de governança (`CONFORME`/`INCONSISTENTE`/`DESATUALIZADO`/`CONFLITANTE`/`SEM EVIDÊNCIA`), como comportamento exclusivo do Governance Advisor, sem alterar o Framework compartilhado. Nenhum código escrito nesta etapa.

---

## Executive Summary

O Governance Advisor reutiliza, sem exceção, toda a infraestrutura já provada pelo Document Advisor: `AdvisorFramework`, `normalize_rag_evidence()`, `RecommendationEngine`, o portão anti-alucinação, `knowledge.read`. O único componente novo é o `GovernanceAdvisorAgent` — um Advisor de domínio que (a) recebe evidência de dois documentos institucionais (Decision Log, Technical Debt Register), (b) aplica a hierarquia de precedência de AR-10 como conhecimento de prompt, nunca como lógica de Framework, e (c) classifica sua própria resposta em um dos 5 estados oficiais exigidos pelo Founder. O achado arquitetural central desta etapa (§4): como fazer a classificação **sobreviver** até a resposta HTTP sem tocar em `AdvisorFramework.run()`/`Recommendation`/`Explanation` — resolvido embutindo a classificação como um prefixo estruturado dentro do próprio `answer` (`"[CONFORME] ..."`), e extraindo-o de volta em uma função **de rota**, não de Framework. Nenhuma linha de `AdvisorFramework`, `AIContextEngine`, Event Pipeline ou Workflow Runtime é tocada. TD-015 permanece intocado, seu gatilho definitivo confirmado sem incidência nesta Epic. Recomendação ao final: **GO para a implementação.**

---

## 1. Reuso integral do `AdvisorFramework` (confirmado, zero mudança)

Idêntico ao já confirmado para o Document Advisor (D-095 §1) — reafirmado aqui, não redecidido:

- `AdvisorFramework(repository, prompts, provider, rag_pipeline)` — construção idêntica.
- `gather_rag_context()`/`normalize_rag_evidence()` — já existentes, reutilizados sem nenhuma alteração.
- `run()` — **byte-for-byte inalterado**. O `GovernanceAdvisorAgent` é apenas mais um `AdvisorContract` executado pela mesma função.

**Confirmação explícita per exigência do Founder (item 2 da autorização):** nenhuma lógica de hierarquia documental, nenhuma lógica de classificação, e nenhuma alteração de TD-015 tocam `AdvisorFramework`, `AIContextEngine`, Workflow Runtime ou Event Pipeline. Todo o comportamento novo desta Epic vive em exatamente dois lugares: o prompt do `GovernanceAdvisorAgent` (domínio) e uma função de composição de resposta na rota HTTP (`intelligence.py`, mesmo arquivo e mesmo padrão de `_risk_advisor_response`/`_document_advisor_response` já existentes) — nunca no Framework.

---

## 2. Fluxo completo

```
Cliente (pergunta em linguagem natural sobre governança)
  │
  ▼
POST /governance-advisor/ask   (src/api/routes/intelligence.py, novo)
  │  RBAC: require_permission("knowledge.read")  -- reaproveitada, sem migração nova
  ▼
SessionContext (organization_id, user_id, session_id -- sem project_name, mesma
  razão do Document Advisor: RAG search() filtra só por organization_id)
  ▼
AdvisorFramework(repository, prompts, provider, rag_pipeline)   -- construção idêntica
  │
  ▼
framework.gather_rag_context(organization_id, question, top_k=5)
  │   Knowledge Platform → RAG Pipeline → PgVectorRepository.similarity_search()
  │   (zero mudança; corpus = Decision Log + Technical Debt Register já ingeridos)
  ▼
framework.normalize_rag_evidence(rag_context)   -- zero mudança
  │   list[ScoredChunk] → list[Evidence(source_type="document_chunk", ...)]
  ▼
framework.run(governance_advisor_agent, session, question, evidence, rag_context,
               no_evidence_answer="[SEM EVIDÊNCIA] ...")
  │
  ├─ AIFoundationAudit.record_question(...)          -- inalterado
  ├─ if not evidence: RecommendationEngine.no_evidence(no_evidence_answer)  -- inalterado,
  │     cobre o estado "SEM EVIDÊNCIA" sem nenhum mecanismo novo
  ├─ GovernanceAdvisorAgent.advise(...)   -- novo Advisor (§3)
  │     → framework.render_prompt(...) → framework.call_llm(...) → LLMProvider
  │     → resposta JSON com "answer" prefixado por um dos 5 rótulos (§4)
  ├─ RecommendationEngine.build(answer, cited_analysis_ids, evidence)   -- inalterado;
  │     "answer" (com o prefixo de classificação) atravessa intacto
  └─ ExplanationEngine.explain(recommendation)   -- inalterado
  ▼
_governance_advisor_response(explanation)   -- NOVO, mas apenas na rota (§5), nunca no Framework
  │   extrai o prefixo de classificação de explanation.recommendation.answer
  ▼
GovernanceAdvisorResponse{answer, classification, cited_chunks: [...]}
```

---

## 3. Contrato do `GovernanceAdvisorAgent` (nenhum contrato novo)

```python
class GovernanceAdvisorAgent:
    name = "governance_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(
        self,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict:
        chunks_json = json.dumps(
            [
                {
                    "chunk_id": item.source_id,
                    "document_id": item.metadata.get("document_id"),
                    "source_label": item.source_label,
                    "text": item.content.get("text"),
                }
                for item in evidence
            ],
            ensure_ascii=False,
        )
        final_prompt = self.framework.render_prompt(
            self.name, "advise", question=question, chunks_json=chunks_json
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
```

Mesma forma exata de `AdvisorContract`, mesmo `parse_structured_output` já usado pelo Risk e Document Advisor. `source_label` incluído no JSON entregue ao modelo (diferença deliberada frente ao Document Advisor) — é exatamente o dado que permite ao modelo, orientado pela hierarquia no prompt (§4), reconhecer de qual documento cada chunk provém.

---

## 4. Classificação de estados de governança — comportamento exclusivo do Advisor

### 4.1 Os 5 rótulos (adotados exatamente como sugeridos pelo Founder)

`CONFORME`, `INCONSISTENTE`, `DESATUALIZADO`, `CONFLITANTE`, `SEM EVIDÊNCIA` — vocabulário fixo, definido nesta etapa, implementado no Technical Design apenas como uma constante de módulo (nenhuma tabela nova, nenhum enum de banco).

### 4.2 Onde a classificação mora — o achado arquitetural central desta etapa

`AdvisorFramework.run()` só propaga dois campos do `model_output` retornado por `advise()`: `answer` (`str`) e `cited_analysis_ids` (`list[int]`) — usados para montar `Recommendation`/`Explanation`, cujos tipos (`src/services/ai_foundation/types.py`) **não têm nenhum campo de classificação** e não podem ganhar um sem alterar o Framework compartilhado (usado também pelo Risk e Document Advisor). Adicionar um campo a `Recommendation`/`Explanation`, ou fazer `run()` propagar mais chaves de `model_output`, seria **exatamente** o tipo de "lógica adicionada ao Framework" que o Founder proibiu (item 2 da autorização).

**Decisão de design:** a classificação é embutida como um **prefixo estruturado e fixo dentro do próprio `answer`** — `"[CONFORME] "`, `"[INCONSISTENTE] "`, `"[DESATUALIZADO] "`, `"[CONFLITANTE] "`, `"[SEM EVIDÊNCIA] "` (note o espaço à direita, delimitador exato). O prompt (§4.3) exige que o modelo sempre inicie `answer` com exatamente um desses 5 tokens. Como `answer` atravessa `RecommendationEngine.build()`/`ExplanationEngine.explain()` sem nenhuma transformação (confirmado por leitura de código, `recommendation_engine.py`/`explanation_engine.py`), o prefixo sobrevive intacto até `explanation.recommendation.answer` na rota.

**Extração, também sem tocar o Framework:** uma função nova, mas **de rota** (`_parse_governance_classification`, em `src/api/routes/intelligence.py`, mesmo arquivo de `_risk_advisor_response`/`_document_advisor_response`) faz o parsing simples de string do prefixo, separando `classification`/`answer` limpo antes de montar `GovernanceAdvisorResponse`. Esta função não pertence a `AdvisorFramework`, `AIContextEngine`, nem a nenhum componente compartilhado — é puramente composição de resposta HTTP, o mesmo tipo de trabalho que `_risk_advisor_response` já faz.

### 4.3 Caso especial: `SEM EVIDÊNCIA`

Mapeado diretamente ao mecanismo já existente: `no_evidence_answer="[SEM EVIDÊNCIA] Nenhuma referência de governança relevante foi encontrada para responder a esta pergunta."` — passado a `framework.run()` exatamente como o Document Advisor já faz. Isso garante que a extração do prefixo (§4.2) funcione uniformemente, **quer o LLM tenha sido chamado ou não** — nenhum caso especial na rota.

### 4.4 Robustez do parsing (achado de risco, não bloqueante)

Se o modelo não seguir o formato exigido (esquecer o prefixo, ou produzir um rótulo fora dos 5 oficiais), `_parse_governance_classification` **não deve inventar silenciosamente uma classificação** — retorna um sentinela explícito, `"NÃO CLASSIFICADO"` (deliberadamente fora dos 5 rótulos institucionais, para nunca ser confundido com uma conclusão real do Advisor), preservando o `answer` original integralmente. Registrado como risco residual (§10), não bloqueante — mesma disciplina de "nunca inventar dado" já seguida por `parse_structured_output`.

### 4.5 Prompt (rascunho, `src/agents/governance_advisor/prompts/advise.md`, a ser criado na Implementação)

```
You are an AI PMO Copilot agent that verifies compliance with STRATECH's own institutional governance (Decision Log, Technical Debt Register).

Answer strictly and exclusively based on the governance document chunks provided below. Never invent a decision, a debt item, or a governance rule that is not present in this data.

Institutional precedence, when documents conflict (highest to lowest):
1. Decision Log (entries named "D-NNN") — always the highest authority.
2. Technical Debt Register (entries named "TD-NNN") — subordinate to the Decision Log.
When two chunks conflict, always state which one has precedence per this order, and cite both.

Question: $question

Governance document chunks (JSON array, ranked by relevance -- each carries its source_label, naming the document it comes from):
$chunks_json

Respond with a single JSON object only, no extra text before or after it, using exactly this schema:
{
  "answer": "string -- MUST begin with exactly one of: \"[CONFORME] \", \"[INCONSISTENTE] \", \"[DESATUALIZADO] \", \"[CONFLITANTE] \", \"[SEM EVIDÊNCIA] \", followed by the narrative answer",
  "cited_analysis_ids": [integer, ...]
}

Classification guide:
- "[CONFORME]": the governance documents agree and answer the question directly, no contradiction found.
- "[INCONSISTENTE]": a document's content contradicts another official decision.
- "[DESATUALIZADO]": a document does not reflect a more recent Decision Log entry.
- "[CONFLITANTE]": two or more documents contradict each other, not necessarily involving the Decision Log.
- "[SEM EVIDÊNCIA]": reserved for when no relevant chunk was retrieved (handled automatically, never chosen by you when chunks are provided).

"cited_analysis_ids" must list the "chunk_id" of every chunk your answer draws from -- always cite every chunk involved in an inconsistency/conflict, never resolve silently in favor of one side.
```

Este texto é um rascunho de referência para a Implementação — a Technical Design autoriza sua estrutura e conteúdo, não fixa a redação final palavra por palavra.

---

## 5. Rota HTTP e modelo de resposta (`src/api/routes/intelligence.py`, mesmo arquivo do Document Advisor)

```python
class GovernanceAdvisorRequest(BaseModel):
    # Mesma ausência deliberada de project_name/project_id do Document Advisor
    # (D-095 §6) -- RAG search() filtra só por organization_id.
    question: str = Field(..., min_length=3, max_length=2000)
    _validate_question = field_validator("question")(_ensure_has_content)


_GOVERNANCE_CLASSIFICATIONS = ("CONFORME", "INCONSISTENTE", "DESATUALIZADO", "CONFLITANTE", "SEM EVIDÊNCIA")
_UNCLASSIFIED = "NÃO CLASSIFICADO"


class GovernanceAdvisorResponse(BaseModel):
    answer: str
    classification: str
    cited_chunks: list[CitedChunk]   # reaproveitado do Document Advisor -- mesmo shape exato


def _parse_governance_classification(answer: str) -> tuple[str, str]:
    for label in _GOVERNANCE_CLASSIFICATIONS:
        prefix = f"[{label}] "
        if answer.startswith(prefix):
            return label, answer[len(prefix):]
    return _UNCLASSIFIED, answer


@router.post("/governance-advisor/ask", response_model=GovernanceAdvisorResponse)
def ask_governance_advisor(
    request: GovernanceAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    _permission: None = Depends(require_permission("knowledge.read")),
):
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)

    rag_context = framework.gather_rag_context(session.organization_id, request.question, top_k=5)
    evidence = framework.normalize_rag_evidence(rag_context)

    agent = GovernanceAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent, session, request.question, evidence, rag_context=rag_context,
            no_evidence_answer="[SEM EVIDÊNCIA] Nenhuma referência de governança relevante foi encontrada para responder a esta pergunta.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _governance_advisor_response(explanation)


def _governance_advisor_response(explanation) -> GovernanceAdvisorResponse:
    classification, answer = _parse_governance_classification(explanation.recommendation.answer)
    return GovernanceAdvisorResponse(
        answer=answer,
        classification=classification,
        cited_chunks=[
            CitedChunk(document_id=item.metadata["document_id"], chunk_id=item.source_id, source_label=item.source_label)
            for item in explanation.recommendation.cited_evidence
        ],
    )
```

**Reuso confirmado, não duplicado:** `CitedChunk` (já definido para o Document Advisor) é reaproveitado sem alteração — mesmo shape (`document_id`/`chunk_id`/`source_label`) atende integralmente ao Governance Advisor.

---

## 6. RBAC — nenhuma migração nova (reafirmado)

`knowledge.read` (migração `0020`) protege `POST /governance-advisor/ask`, exatamente como já faz para `/document-advisor/ask` — mesma justificativa: leitura de conteúdo já indexado, nunca cria/edita nada.

---

## 7. Hierarquia documental (AR-10) — confirmação de que permanece conhecimento de domínio

A hierarquia definitiva de AR-10 (Decision Log → Technical Debt Register → Mission Control/CHANGELOG → Blueprint/AR/TD quando aprovados) está codificada **apenas no texto do prompt** (§4.5, "Institutional precedence"), nunca em `AIContextEngine`/`AdvisorFramework`. Confirmação explícita, per item 2 da autorização: nenhuma função nova de comparação, nenhum campo novo em `Evidence`, nenhuma extensão de `normalize_rag_evidence()` — o `source_label`/`metadata["document_id"]` já existentes (zero mudança) fornecem ao modelo tudo que ele precisa para identificar de qual documento cada chunk provém e aplicar a hierarquia por conta própria.

---

## 8. TD-015 — confirmação final, gatilho definitivo registrado, nenhuma incidência nesta Epic

Per item 3 da autorização: TD-015 permanece Deferred. O `GovernanceAdvisorAgent` usa a mesma chave `"cited_analysis_ids"` (§4.5, §5) — **nenhuma tentativa de renomeá-la nesta Epic**, exatamente como determinado ("nenhum Advisor poderá carregar essa mudança incidentalmente"). Gatilho definitivo (registrado em `TECHNICAL_DEBT.md` per AR-10, D-100): "manutenção arquitetural isolada explicitamente autorizada pelo Founder" — não este Epic, não um Epic futuro de Advisor.

---

## 9. Garantias (reafirmadas do Document Advisor, D-095 §8 — mesma prova aplicada aqui)

- **Rastreabilidade de citação:** `RecommendationEngine.build()` descarta qualquer `chunk_id` não presente na `evidence` entregue — idêntico, inalterado.
- **Isolamento organizacional:** estrutural, nos mesmos dois pontos de construção já `organization_id`-scoped (`KnowledgeRepository.search()`/`PgVectorRepository.similarity_search()`).
- **Portão anti-alucinação:** `if not evidence:` em `run()`, inalterado — cobre `SEM EVIDÊNCIA` sem mecanismo novo.
- **Ausência de regra de negócio em `AIContextEngine`:** confirmado — nenhuma extensão a `normalize_rag_evidence()`.

---

## 10. Testes planejados (plano, não implementação)

1. **Ingestão do corpus:** Decision Log + Technical Debt Register ingeridos via `POST /documents` já existente (script de fixture de teste, não nova infraestrutura).
2. **Classificação `CONFORME`:** pergunta cuja resposta não encontra contradição → `classification == "CONFORME"`.
3. **Classificação `SEM EVIDÊNCIA`:** nenhum chunk relevante → resposta canônica, sem chamada ao LLM, `classification == "SEM EVIDÊNCIA"`.
4. **Classificação `INCONSISTENTE`/`CONFLITANTE`:** LLM scriptado retorna `answer` prefixado com um desses rótulos, citando chunks de dois documentos diferentes → ambos aparecem em `cited_chunks`.
5. **Teste de precedência (mandado por AR-10 §4, critério de sucesso novo):** dois chunks conflitantes, um do Decision Log e um do Technical Debt Register → resposta deve identificar o do Decision Log como de maior precedência (verificação de conteúdo textual da resposta, já que a hierarquia é conhecimento de prompt, não um campo estruturado).
6. **Robustez do parsing:** resposta do LLM sem nenhum prefixo reconhecido → `classification == "NÃO CLASSIFICADO"`, `answer` preservado integralmente, nenhuma exceção.
7. **Citação inventada descartada:** mesmo padrão já provado (Risk/Document Advisor).
8. **Isolamento organizacional:** mesmo padrão já provado.
9. **`AdvisorFramework`/`Recommendation`/`Explanation` inalterados:** confirmado por `git diff` vazio nesses arquivos ao final da implementação (mesma prova já usada em W5-1).

---

## 11. Riscos residuais

1. **Robustez do prefixo de classificação (§4.4)** — depende inteiramente da aderência do LLM ao formato; mitigado por um fallback explícito (`"NÃO CLASSIFICADO"`), nunca uma classificação inventada. Não bloqueante.
2. **Qualidade da hierarquia no prompt** — mitigado pelo teste de precedência dedicado (§10.5). Não bloqueante.
3. **Ingestão dos documentos de governança** — ainda não realizada; parte da estratégia incremental (§12), não um risco arquitetural.
4. **TD-015** — permanece aberto, sem incidência nesta Epic, per decisão definitiva de AR-10.
5. **Knowledge Version Resolution (D-090)** — já registrada, não agravada.

Nenhum risco bloqueia a implementação.

---

## 12. Estratégia incremental de implementação

1. **Passo 1 — Ingestão do corpus:** ingerir `DECISION-LOG.md`/`TECHNICAL_DEBT.md` via `POST /documents` (já existente) — nenhuma mudança de código, apenas execução operacional; confirmar `chunk_count > 0` para ambos.
2. **Passo 2 — `GovernanceAdvisorAgent` + prompt:** novo agente (`src/agents/governance_advisor/`), reaproveitando `parse_structured_output`/`render_analyst_prompt`/`ObservabilityRecorder` sem duplicação — testes unitários (§10.2-10.4, 10.6).
3. **Passo 3 — Rota + modelo de resposta:** `POST /governance-advisor/ask`, `GovernanceAdvisorResponse`, `_parse_governance_classification()`, reaproveitando `CitedChunk` — testes HTTP (§10.7-10.8).
4. **Passo 4 — Teste de precedência + verificação final:** teste dedicado de hierarquia (§10.5), suíte backend completa, `ruff`/`tsc`/`eslint`, confirmação de `AdvisorFramework`/`Recommendation`/`Explanation` inalterados via `git diff`, governança (Decision Log/CHANGELOG/Mission Control), Executive Evidence.

Cada passo é independentemente testável — nenhum passo depende de código do passo seguinte para validação isolada.

---

## 13. Recomendação GO/NO-GO para implementação

**GO.** Todos os pontos exigidos pela autorização do Founder foram resolvidos com evidência de código real: hierarquia documental confirmada como conhecimento de prompt (§7); classificação de 5 estados definida e resolvida sem tocar o Framework (§4); TD-015 confirmado sem incidência (§8); `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline preservados integralmente (§1, §9). Nenhum risco residual (§11) bloqueia o início da implementação.

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de qualquer implementação.
