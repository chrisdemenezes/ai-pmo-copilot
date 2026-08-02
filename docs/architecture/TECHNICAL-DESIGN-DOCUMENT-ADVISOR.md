# Technical Design — Document Advisor (Epic W5-1, Etapa 4 do ciclo institucional)

**Autorização:** "Founder Authorization — Technical Design do Document Advisor" (veredito **APPROVED — GO para a Etapa 4**), consequência de D-094 (regra institucional permanente de aplicação prospectiva da governança; Domain Blueprint D-087 e Architecture Review D-088/AR-9 considerados atendidos para o Document Advisor).

**Escopo desta missão:** exclusivamente documentação técnica — nenhum código escrito. Todo o desenho abaixo é verificado contra o código real do repositório (grounding, não suposição); toda linha de arquivo citada foi lida diretamente antes de ser referenciada aqui.

**Base institucional já aprovada, não redecidida:** Domain Blueprint (D-087), AR-9/Architecture Review (D-088), Advisor Specification (D-093). Este documento **consolida e detalha a implementação** do que já foi aprovado — não introduz nenhuma decisão arquitetural nova além do já divulgado em D-088 §3 (`normalize_rag_evidence()`).

---

## 1. Como o Document Advisor reutiliza integralmente o `AdvisorFramework`

Nenhuma mudança à assinatura pública de `AdvisorFramework` além do novo passthrough já divulgado em D-088 (§4). Confirmado por leitura direta de `src/services/advisor_framework/framework.py`:

- `AdvisorFramework.__init__(repository, prompt_registry, llm_provider, rag_pipeline)` — construído pela rota exatamente como o Risk Advisor já faz hoje (`src/api/routes/intelligence.py:519`), zero parâmetro novo.
- `gather_rag_context(organization_id, query, top_k=5)` — já existe, chama `RagPipeline.retrieve()`, reutilizado sem alteração.
- `render_prompt(advisor_name, prompt_name, **variables)` / `call_llm(advisor_name, session, prompt)` — já existem, reutilizados sem alteração (mesmo `render_analyst_prompt`/`ObservabilityRecorder` que o Risk Advisor usa).
- `run(advisor, session, question, evidence, rag_context=None, no_evidence_answer=None) -> Explanation` — **byte-for-byte inalterado** (confirmado em §5 abaixo). O Document Advisor é apenas mais um `AdvisorContract` executado por essa mesma função, exatamente como o Risk Advisor.

**Único acréscimo (já divulgado e aprovado em D-088 §3, não uma decisão nova desta etapa):** `AdvisorFramework.normalize_rag_evidence(rag_context: RagContext) -> list[Evidence]`, um passthrough fino para `AIContextEngine.normalize_rag_evidence()` (§2), no mesmo padrão de `gather_context()`/`gather_rag_context()` já existentes na classe (`framework.py:45-56`).

```python
# src/services/advisor_framework/framework.py -- acréscimo aditivo
def normalize_rag_evidence(self, rag_context: RagContext) -> list[Evidence]:
    return self._context_engine.normalize_rag_evidence(rag_context)
```

`DocumentAdvisorAgent` (novo, §4) implementa `AdvisorContract` (`src/services/advisor_framework/types.py:29-39`) sem nenhuma alteração ao Protocol — mesma forma exata que `RiskAdvisorAgent` já usa (`name: str` + `advise(session, question, evidence, rag_context=None) -> dict`).

---

## 2. Implementação de `normalize_rag_evidence()` — responsabilidade exclusivamente mecânica

Vive em `AIContextEngine` (`src/services/ai_foundation/context_engine.py`), ao lado do já existente `gather()`, por ser o componente que D-086 define oficialmente como "responsável pela preparação do contexto de IA": coletar, normalizar, consolidar e estruturar evidências, **sem executar regras de negócio nem interpretar domínio**.

```python
# src/services/ai_foundation/context_engine.py -- método novo
def normalize_rag_evidence(self, rag_context: RagContext) -> list[Evidence]:
    """Mechanical envelope only (D-086): never interprets chunk.text, never
    decides relevance -- ranking/relevance is already RagPipeline's
    responsibility (Fase 2). One Evidence per ScoredChunk, in the same
    order RagContext.chunks already provides."""
    return [
        Evidence(
            source_type="document_chunk",
            source_id=chunk.chunk_id,
            source_label=f"Document {chunk.document_id} / Chunk {chunk.chunk_id}",
            content={"text": chunk.text},
            metadata={
                "document_id": chunk.document_id,
                "score": chunk.score,
                "created_at": chunk.document_version_created_at,
            },
        )
        for chunk in rag_context.chunks
    ]
```

**Por que é mecânico, não interpretativo:** a função apenas reempacota campos já existentes de `ScoredChunk` (`chunk_id`, `document_id`, `text`, `score`, `document_version_created_at` — todos confirmados em `src/services/knowledge_platform/types.py:31-36`) em `Evidence`. Nenhuma decisão de relevância (já decidida por `RagPipeline._rank()`), nenhuma leitura semântica de `chunk.text`, nenhum filtro adicional. A ordem de `rag_context.chunks` (já ranqueada) é preservada.

**Consumidor futuro (D-088 §3, não desta Epic):** o Governance Advisor (segundo Advisor de Classe D) reutilizará este mesmo método sem generalização adicional — resolvendo apenas quando esse Advisor real existir, per "Grounded before Generalized".

---

## 3. Integração do novo contrato `Evidence` sem quebra de compatibilidade com o Risk Advisor

Implementa o contrato definitivo já aprovado em D-088/AR-9 §2.2, confinado a exatamente 4 arquivos:

### 3.1 `src/services/ai_foundation/types.py`

```python
@dataclass(frozen=True)
class Evidence:
    source_type: str
    source_id: int
    source_label: str
    content: dict
    metadata: dict = field(default_factory=dict)
```

Campos removidos como topo do dataclass: `source_analysis_id` (→ `source_id`), `source_created_at` (→ `metadata["created_at"]`), `kind` (→ `metadata["kind"]`, confirmado nunca lido fora de `metadata` por busca global já feita em D-088), `summary` (→ `content`).

### 3.2 `src/services/ai_foundation/context_engine.py` (produtor 1 de 2)

`gather()` passa a construir:

```python
Evidence(
    source_type="analysis_record",
    source_id=record.id,
    source_label=f"AnalysisRecord#{record.id} ({kind})",
    content=model_output,
    metadata={"created_at": record.created_at, "kind": kind},
)
```

### 3.3 `src/services/ai_foundation/recommendation_engine.py` (único consumidor genérico)

```python
by_id = {item.source_id: item for item in evidence}
cited = [by_id[cited_id] for cited_id in cited_ids if cited_id in by_id]
```

Mudança de **nome de campo apenas** (`item.source_analysis_id` → `item.source_id`) — zero mudança de lógica, confirmado por leitura direta de `recommendation_engine.py:18-23`.

### 3.4 `src/agents/risk_advisor/agent.py` (único leitor externo do formato antigo)

```python
"source_analysis_id": item.source_id,
"source_created_at": str(item.metadata["created_at"]),
...
"description": risk.get("description"),  # via item.content.get("risks")
```

Substituições: `item.summary` → `item.content`; `item.source_analysis_id` → `item.source_id`; `item.source_created_at` → `item.metadata["created_at"]`. O prompt (`advise.md`) e a lógica de extração de risco permanecem byte-for-byte idênticos — apenas o caminho de acesso ao campo muda.

### 3.5 Prova de compatibilidade (obrigatória na implementação, não nesta etapa)

A suíte de testes já existente do Risk Advisor (`tests/test_risk_advisor_*.py` e equivalentes de rota) deve passar **sem nenhuma alteração de expectativa** após o rename — essa é a definição operacional de "compatibilidade total" adotada em D-088 §2.4: `Evidence` é um dataclass interno, nunca serializado para fora da plataforma, com exatamente 2 produtores (`gather()`, `normalize_rag_evidence()`) e 1 consumidor genérico (`RecommendationEngine.build()`) — não há contrato público dependente do nome antigo do campo.

### 3.6 `src/api/routes/intelligence.py::_risk_advisor_response()` — impacto adicional confirmado por leitura de código

Achado não previsto explicitamente em D-088: a função `_risk_advisor_response()` (`intelligence.py:546-556`) lê `item.source_analysis_id`/`item.source_created_at` diretamente para montar `CitedAnalysis`. Após o rename, passa a ler `item.source_id`/`item.metadata["created_at"]`. **Nenhuma mudança ao formato de resposta HTTP do Risk Advisor** (`CitedAnalysis.source_analysis_id`/`source_created_at` permanecem os nomes públicos da API, inalterados) — o remapeamento é só na leitura interna de `Evidence`. Adicionado à lista de 4 arquivos de D-088 §2.4 como um 5º ponto de leitura já identificado (rota, não módulo de domínio) — nenhum arquivo novo além do já mapeado, apenas uma correção de completude desta auditoria.

---

## 4. Fluxo de execução completo

```
Cliente (pergunta em linguagem natural)
  │
  ▼
POST /document-advisor/ask   (src/api/routes/intelligence.py, novo)
  │  RBAC: require_permission("knowledge.read")  -- reaproveitada, sem migração nova (§7)
  ▼
SessionContext (organization_id, user_id, session_id -- sem project_name: RAG search()
  hoje filtra só por organization_id, nunca project_id -- risco já registrado em D-087/D-088,
  não resolvido aqui, ver §8.5)
  ▼
AdvisorFramework(repository, prompts, provider, rag_pipeline)   -- construção idêntica ao Risk Advisor
  │
  ▼
framework.gather_rag_context(organization_id, question, top_k=5)   -- Knowledge Platform → RAG Pipeline
  │   RagPipeline.retrieve() → KnowledgeRepository.search() → PgVectorRepository.similarity_search()
  │   (organization_id-scoped, já existente, zero mudança)
  ▼
framework.normalize_rag_evidence(rag_context)   -- AIContextEngine.normalize_rag_evidence() (novo, §2)
  │   list[ScoredChunk] → list[Evidence(source_type="document_chunk", ...)]
  ▼
framework.run(document_advisor_agent, session, question, evidence, rag_context, no_evidence_answer=...)
  │
  ├─ AIFoundationAudit.record_question(...)          -- auditoria incondicional, inalterada
  ├─ if not evidence: RecommendationEngine.no_evidence(...)   -- portão anti-alucinação, inalterado
  ├─ DocumentAdvisorAgent.advise(session, question, evidence, rag_context)   -- novo Advisor (§5)
  │     → framework.render_prompt(...) → framework.call_llm(...) → LLMProvider (Anthropic, produção)
  ├─ RecommendationEngine.build(answer, cited_analysis_ids, evidence)   -- por source_id (§3.3), inalterado
  └─ ExplanationEngine.explain(recommendation)   -- inalterado
  ▼
DocumentAdvisorResponse{answer, cited_chunks: [{document_id, chunk_id, source_label}, ...]}
  ▼
Resposta fundamentada ao cliente, citando document_id/chunk_id reais
```

Cada seta acima corresponde a uma função já existente e lida diretamente neste Technical Design, exceto as duas marcadas "novo": `normalize_rag_evidence()` (§2, já aprovado em D-088) e `DocumentAdvisorAgent` (§5, novo Advisor, mesma forma de `AdvisorContract`).

---

## 5. `DocumentAdvisorAgent` — novo Advisor

### 5.1 Contrato (`src/agents/document_advisor/agent.py`, novo arquivo)

```python
class DocumentAdvisorAgent:
    name = "document_advisor"

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

Reaproveita `parse_structured_output` (`src/agents/shared/output_parser.py`) — mesmo parser que `RiskAdvisorAgent` já usa, nenhum parser novo.

`rag_context` é aceito por conformidade ao `AdvisorContract`, mas não lido pelo corpo de `advise()` — diferente do Risk Advisor (onde `rag_context` é *suplementar* à evidência principal), aqui `evidence` **é** a normalização de `rag_context` (§2); não há uma segunda fonte a compor. Isso é uma simplificação em relação ao Risk Advisor, não uma divergência de contrato.

### 5.2 Prompt (`src/agents/document_advisor/prompts/advise.md`, novo arquivo)

```
You are an AI PMO Copilot agent that answers questions strictly based on the content of indexed corporate documents.

Answer strictly and exclusively based on the document chunks provided below. Never invent information, a document, or a detail that is not present in this data. If the data does not answer the question, say so plainly instead of guessing.

Question: $question

Indexed document chunks (JSON array, ranked by relevance):
$chunks_json

Respond with a single JSON object only, no extra text before or after it, using exactly this schema:
{
  "answer": "string",
  "cited_analysis_ids": [integer, ...]
}

"cited_analysis_ids" must list the "chunk_id" of every chunk your answer draws from.
```

**Achado de nomenclatura explicitamente divulgado (não bloqueante, registrado como débito técnico cosmético em §8.4):** a chave `"cited_analysis_ids"` é lida literalmente por `AdvisorFramework.run()` (`model_output.get("cited_analysis_ids")`, `framework.py:98`) — o nome é um resquício do vocabulário do Risk Advisor (pré-D-088) e permanece assim porque renomear essa chave literal seria uma mudança a `AdvisorFramework.run()`, que esta Technical Design confirma **inalterado** (§1, §6). Funcionalmente correto (os valores são `chunk_id`, inteiros, compatíveis com `source_id: int`), apenas cosmeticamente enganoso — mesma classe de achado que originou o rename de `Evidence.source_analysis_id` em D-088, mas desta vez a correção pertenceria ao próprio `AdvisorFramework.run()`, fora do escopo desta Epic (alterar `run()` violaria a confirmação de "inalterado" exigida pelo Founder nesta mesma autorização).

---

## 6. Rota HTTP (`src/api/routes/intelligence.py` — mesmo arquivo do Risk Advisor, nenhum arquivo de rota novo)

```python
class DocumentAdvisorRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    _validate_question = field_validator("question")(_ensure_has_content)


class CitedChunk(BaseModel):
    document_id: int
    chunk_id: int
    source_label: str


class DocumentAdvisorResponse(BaseModel):
    answer: str
    cited_chunks: list[CitedChunk]


@router.post("/document-advisor/ask", response_model=DocumentAdvisorResponse)
def ask_document_advisor(
    request: DocumentAdvisorRequest,
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
    logger.info(
        "Document Advisor question organization_id=%s rag_chunk_ids=%s",
        session.organization_id,
        sorted(rag_context.chunk_ids),
    )

    agent = DocumentAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            evidence,
            rag_context=rag_context,
            no_evidence_answer="Nenhum documento relevante foi encontrado para responder a esta pergunta.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _document_advisor_response(explanation)


def _document_advisor_response(explanation) -> DocumentAdvisorResponse:
    return DocumentAdvisorResponse(
        answer=explanation.recommendation.answer,
        cited_chunks=[
            CitedChunk(
                document_id=item.metadata["document_id"],
                chunk_id=item.source_id,
                source_label=item.source_label,
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )
```

Reaproveita, sem alteração: `build_prompt_registry`, `build_provider`, `build_repository`, `build_rag_pipeline` (todas já definidas em `intelligence.py:145-166`), `get_request_context`, `require_permission`, `AdvisorFramework`, `AdvisorExecutionError`. Nenhuma nova função de DI além das já existentes — nenhum arquivo de rota novo, a rota entra no mesmo `intelligence.py` que já hospeda `/risk-advisor/ask`, por ser o mesmo tipo de recurso (Advisor).

**Ausência deliberada de `project_name`/`project_id` na request (achado explícito, não uma omissão):** `KnowledgeRepository.search()` (`knowledge_repository.py:162-164`) e `PgVectorRepository.similarity_search()` filtram exclusivamente por `organization_id` — nunca por `project_id` — confirmado por leitura direta de código. Diferente do Risk Advisor, que exige `project_name` porque `gather_context()` escopa por projeto, o Document Advisor não chama `gather_context()` — apenas `gather_rag_context()`/`normalize_rag_evidence()` — logo não há campo de projeto para receber. Este é exatamente o risco já registrado em D-087 ("filtro por project_id ainda não suportado") e em D-088 (risco residual, não bloqueante) — esta Technical Design não o resolve, apenas confirma seu efeito concreto na forma da request.

---

## 7. RBAC — nenhuma migração nova

`knowledge.read` (migração `0020`, já concedida a `organization_admin`/`pmo`/`project_manager`/`viewer`) é reutilizada como a permissão que protege `POST /document-advisor/ask` — mesmo padrão já usado pelo Risk Advisor (`/risk-advisor/ask` reutiliza `intelligence.read`, "seu próprio recurso de leitura, este Advisor nunca cria/edita/dispara uma análise"). O Document Advisor lê exclusivamente dados já indexados pela Knowledge Platform — `knowledge.read` é a permissão semanticamente correta e já existente, resolvendo o risco #3 de AR-9 §5 ("naming definitivo da permissão RBAC") **sem criar uma permissão nova**, per CLAUDE.md ("nunca criar novo registry" — e, por extensão do mesmo princípio, nenhuma permissão nova sem necessidade real).

---

## 8. Garantias exigidas pela autorização do Founder

### 8.1 Rastreabilidade das citações

`RecommendationEngine.build()` só permite citar um `source_id` presente na `evidence` efetivamente entregue (`by_id = {item.source_id: item for item in evidence}` — §3.3) — uma citação inventada pelo LLM (um `chunk_id` que não está em `evidence`) é descartada silenciosamente, nunca aparece em `cited_chunks`. `DocumentAdvisorResponse.cited_chunks` sempre carrega `document_id`/`chunk_id` reais, extraídos de `Evidence.metadata`/`Evidence.source_id` — nunca inventados pela rota.

### 8.2 Isolamento por organização

Estrutural, em dois pontos de construção, ambos já `organization_id`-scoped (confirmado por leitura de código, D-088 §2.5 reafirmado): `KnowledgeRepository.search(organization_id, ...)` (`knowledge_repository.py:162`) e `PgVectorRepository.similarity_search(organization_id, ...)` — nenhum chunk de outra organização chega a existir em `RagContext.chunks`, logo nunca chega a existir em `Evidence`. `Evidence` não carrega `organization_id` como campo (decisão reafirmada de D-088 §2.5) porque o isolamento já é garantido antes de `Evidence` existir.

### 8.3 Preservação do portão anti-alucinação

`AdvisorFramework.run()` (`framework.py:89-90`) continua testando `if not evidence:` antes de qualquer chamada ao LLM — nenhuma mudança de código, apenas uma nova forma de o parâmetro `evidence` ser preenchido (via `normalize_rag_evidence()` em vez de `gather_context()`). Confirmado por leitura direta: o gate opera sobre a lista, nunca sobre nomes de campo internos de cada item.

### 8.4 Ausência de regras de negócio no `AIContextEngine`

`normalize_rag_evidence()` (§2) nunca lê o conteúdo semântico de `chunk.text` além de copiá-lo para `content["text"]`; nunca decide relevância (já decidida por `RagPipeline._rank()`); nunca filtra por domínio. É reempacotamento estrutural puro — a mesma garantia que `gather()` já oferece para `AnalysisRecord`.

**Débito técnico cosmético registrado (não bloqueante):** a chave literal `"cited_analysis_ids"` em `AdvisorFramework.run()`/nos prompts de todo Advisor permanece com vocabulário herdado do Risk Advisor mesmo após D-088 renomear `Evidence.source_analysis_id` → `source_id` — ver §5.2. Não afeta funcionalidade; registrado no Technical Debt (§11) para eventual limpeza de nomenclatura quando um terceiro Advisor tornar o padrão maduro o suficiente para generalizar sem risco de "Generalized before Grounded".

### 8.5 `top_k` para RAG como fonte única (risco herdado de D-087/D-088, não resolvido aqui)

Mantido em `5` (mesmo default de `RagPipeline.retrieve()`/`gather_rag_context()`, já usado pelo Risk Advisor) — não há ainda dado real de uso do Document Advisor para justificar um valor diferente. Registrado como item a revisitar quando houver volume real de perguntas em produção (mesmo princípio "Grounded before Generalized" já aplicado a TD-014).

---

## 9. Confirmações explícitas exigidas pela autorização

| Componente | Confirmação |
|---|---|
| `AdvisorFramework.run()` | **Inalterado.** Nenhuma linha modificada — verificado por leitura direta de `framework.py:68-100`; o único acréscimo à classe é o passthrough `normalize_rag_evidence()` (§1), uma função nova, não uma alteração de `run()`. |
| Workflow Runtime | **Inalterado.** O Document Advisor nunca é invocado por `WorkflowRuntime`, nunca se registra como handler de `EventDispatcher` — mesma restrição permanente de AR-8 §8, reafirmada, não uma nova verificação. Nenhum arquivo de `src/workflows/` é tocado por esta Epic. |
| Event Pipeline | **Inalterado.** O Document Advisor não publica nem consome eventos — não há `EventPublisher`/`EventDispatcher` na cadeia descrita em §4. `document.indexed` (produzido por `KnowledgeRepository.index()`, W5-0) já alimentou a Knowledge Platform antes deste fluxo começar; o Document Advisor apenas lê o resultado já indexado via `RagPipeline`. |
| `RecommendationEngine` | **Compatível, com rename de campo apenas** (§3.3) — nenhuma mudança de lógica; a prova operacional é a suíte de testes existente do Risk Advisor passando inalterada após a implementação (§3.5), verificação obrigatória antes de qualquer commit. |

---

## 10. Testes planejados (plano, não implementação — per instrução do Founder: nenhum código nesta etapa)

1. **Citação real:** pergunta com chunk relevante indexado → resposta cita `document_id`/`chunk_id` presentes em `Evidence` normalizada.
2. **`no_evidence()`:** pergunta sem chunk relevante (busca vazia) → resposta genérica (`"Nenhum documento relevante foi encontrado..."`), `cited_chunks=[]`, nenhuma chamada ao LLM (mesmo comportamento do portão, já provado para o Risk Advisor).
3. **Citação inventada descartada:** `cited_analysis_ids` do LLM contém um `chunk_id` ausente de `evidence` → descartado por `RecommendationEngine.build()`, resposta não quebra.
4. **Isolamento organizacional (mandado por AR-9 §2.5):** chunk de Organização A nunca aparece em `Evidence` normalizada para pergunta feita por Organização B — mesmo padrão de teste do Security Hardening Gate (D-045) e do Teste A de W5-0 (D-090).
5. **Regressão do Risk Advisor:** suíte de testes já existente (`test_risk_advisor_agent.py`/rota) passa **sem nenhuma alteração de expectativa** após o rename de `Evidence` (§3) — prova de compatibilidade obrigatória.
6. **`RecommendationEngine`/`ExplanationEngine`:** testes unitários atualizados para os novos nomes de campo (`source_id`, `content`, `metadata`), mesma cobertura de casos já existente.
7. **Migração de nenhuma migração:** nenhum teste de migração é necessário — esta Epic não adiciona nem altera nenhuma tabela/permissão (§7).

---

## 11. Riscos residuais

1. **`top_k=5` não validado com uso real** (§8.5) — não bloqueante, revisitar com dado de produção.
2. **Débito técnico cosmético `"cited_analysis_ids"`** (§5.2/§8.4) — nome de chave literal em `AdvisorFramework.run()` permanece com vocabulário do Risk Advisor; funcionalmente correto, cosmeticamente desatualizado. Registrar no Technical Debt Register nesta mesma missão.
3. **Ausência de filtro por `project_id` no RAG** (herdado de D-087/D-088, reafirmado em §6) — não resolvido aqui; Document Advisor sempre responde no escopo de toda a organização, nunca de um projeto específico.
4. **Knowledge Version Resolution (D-090, Decision Proposal ainda não resolvida)** — chunks de versões antigas de um documento reingerido continuam pesquisáveis; o Document Advisor herda esse comportamento sem agravá-lo nem resolvê-lo.

Nenhum risco listado bloqueia a implementação.

---

## 12. Estratégia incremental de implementação

1. **Passo 1 — Evolução do contrato `Evidence`** (§3): rename em `types.py`/`context_engine.py`/`recommendation_engine.py`/`risk_advisor/agent.py`/`intelligence.py::_risk_advisor_response()` (achado §3.6) → suíte completa do Risk Advisor passando inalterada → commit isolado, testável independentemente do Document Advisor.
2. **Passo 2 — `normalize_rag_evidence()`** (§2, §1): novo método em `AIContextEngine` + passthrough em `AdvisorFramework` → teste unitário de mapeamento `ScoredChunk`→`Evidence` + teste de isolamento organizacional (§10.4).
3. **Passo 3 — `DocumentAdvisorAgent` + rota** (§5, §6): novo agente + prompt + rota `/document-advisor/ask` → testes de citação real, `no_evidence()`, citação inventada descartada (§10.1-10.3).
4. **Passo 4 — Verificação final:** suíte backend completa, `ruff check src tests`, governança (Decision Log, CHANGELOG, Mission Control, Technical Debt), Executive Evidence.

Cada passo é independentemente testável e reversível — nenhum passo depende de código do passo seguinte para ser validado isoladamente.

---

## 13. Executive Summary

O Document Advisor reutiliza integralmente o `AdvisorFramework` já provado pelo Risk Advisor, sem nenhuma mudança a `AdvisorFramework.run()`, `RecommendationEngine`'s lógica, `ExplanationEngine`, Workflow Runtime ou Event Pipeline. O único acréscimo estrutural é `normalize_rag_evidence()` — já divulgado e aprovado em D-088 §3 — que envelopa mecanicamente `ScoredChunk`s em `Evidence`, sem interpretar domínio. O contrato `Evidence` evolui de forma aditiva (`source_type`/`source_id`/`source_label`/`content`/`metadata`), confinado a 4 arquivos de domínio + 1 ponto de leitura na rota do Risk Advisor (achado §3.6, mesma classe de mudança, agora completo). Nenhuma migração nova é necessária — a permissão `knowledge.read` (já existente desde W5-0) protege a nova rota. Rastreabilidade de citação, isolamento organizacional e o portão anti-alucinação são garantidos estruturalmente, sem depender de nenhuma verificação nova além das já existentes na plataforma.

---

## 14. Recomendação Go/No-Go para iniciar a implementação

**GO.** Todos os 6 pontos exigidos pela autorização do Founder foram detalhados com evidência de código real, rastreável linha a linha. Nenhum risco residual (§11) bloqueia o início da implementação. Estratégia incremental (§12) permite validação independente de cada passo antes do commit final.

Per instrução explícita do Founder: nenhuma implementação foi iniciada nesta etapa; retorno obrigatório para Executive Review ao final da implementação, antes de qualquer trabalho subsequente da Wave 5.
