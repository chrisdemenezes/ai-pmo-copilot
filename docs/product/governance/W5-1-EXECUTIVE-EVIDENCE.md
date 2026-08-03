# W5-1 EXECUTIVE EVIDENCE — Document Advisor (Wave 5)

**Autorização:** "Founder Decision — Technical Design do Document Advisor" (veredito **APPROVED — GO para implementação**), encerrando o ciclo institucional de 6 etapas do novo padrão (D-092): Advisor Specification (D-093) → Domain Blueprint (D-087, considerado atendido per D-094) → Architecture Review (D-088/AR-9, considerado atendido per D-094) → Technical Design (D-095) → **Implementação, este documento** → Executive Review.

**Escopo confirmado:** exclusivamente o Document Advisor, seguindo estritamente a estratégia incremental de 4 passos apresentada na Technical Design (D-095). Nenhuma expansão de escopo além do autorizado.

---

## Escopo entregue

1. **Evolução do contrato `Evidence`** (aditiva, per D-088/AR-9 §2.2) — `source_type`/`source_id`/`source_label`/`content`/`metadata`, substituindo `source_analysis_id`/`source_created_at`/`kind`/`summary`. Confinada a 5 pontos de leitura/escrita: `types.py` (definição), `context_engine.py` (produtor 1), `recommendation_engine.py` (consumidor), `risk_advisor/agent.py` (leitor), `intelligence.py::_risk_advisor_response()` (leitor da rota, achado adicional confirmado durante a Technical Design, D-095 §3.6).
2. **`normalize_rag_evidence()`** (D-086/D-088 §3) — novo método mecânico em `AIContextEngine`, envelopando `ScoredChunk` em `Evidence(source_type="document_chunk", ...)`; passthrough fino correspondente em `AdvisorFramework`.
3. **`DocumentAdvisorAgent`** (novo, `src/agents/document_advisor/`) — implementa `AdvisorContract` sem alteração ao Protocol; prompt dedicado (`prompts/advise.md`); reaproveita `parse_structured_output` (mesmo parser do Risk Advisor).
4. **Rota `POST /document-advisor/ask`** (`src/api/routes/intelligence.py`, mesmo módulo do Risk Advisor) — RBAC via `knowledge.read` (reutilizada, nenhuma migração nova); resposta `{answer, cited_chunks: [{document_id, chunk_id, source_label}, ...]}`.
5. **Nenhuma mudança** a `AdvisorFramework.run()`, Workflow Runtime, Event Pipeline, ou à lógica de `RecommendationEngine`/`ExplanationEngine` além do rename de campo já descrito.

---

## Arquivos alterados

**Backend — produção**
- `src/services/ai_foundation/types.py` — `Evidence` (contrato definitivo).
- `src/services/ai_foundation/context_engine.py` — `gather()` atualizado + `normalize_rag_evidence()` (novo).
- `src/services/ai_foundation/recommendation_engine.py` — `build()` indexa por `source_id`.
- `src/agents/risk_advisor/agent.py` — leitura via `item.content`/`item.source_id`/`item.metadata["created_at"]`.
- `src/api/routes/intelligence.py` — `_risk_advisor_response()` atualizado (mesmos campos HTTP públicos, leitura interna migrada); `DocumentAdvisorRequest`/`CitedChunk`/`DocumentAdvisorResponse` (novos); rota `POST /document-advisor/ask` (nova); import de `DocumentAdvisorAgent`.
- `src/services/advisor_framework/framework.py` — `normalize_rag_evidence()` (novo passthrough).
- `src/agents/document_advisor/__init__.py`, `agent.py`, `prompts/advise.md` (novos).

**Backend — testes**
- `tests/test_ai_foundation/test_context_engine.py` — rename (`.kind`/`.summary` → `.metadata["kind"]`/`.content`) + `TestNormalizeRagEvidence` (3 casos novos).
- `tests/test_ai_foundation/test_recommendation_engine.py`, `test_explanation_engine.py` — fixtures `Evidence(...)` no novo formato.
- `tests/test_risk_advisor_agent.py`, `tests/test_advisor_framework.py`, `tests/test_risk_advisor_migration.py` — asserções `.source_id` + `TestNormalizeRagEvidence` (2 casos novos em `test_advisor_framework.py`, incluindo isolamento organizacional).
- `tests/test_document_advisor_agent.py` (novo) — testes unitários do `DocumentAdvisorAgent.advise()`.
- `tests/test_document_advisor.py` (novo) — testes de integração via `AdvisorFramework` real (PostgreSQL real): `no_evidence()` sem chamada ao LLM, citação real, isolamento organizacional, e a **evidência obrigatória de rastreabilidade multi-chunk** (ver seção dedicada abaixo).
- `tests/test_document_advisor_api.py` (novo) — testes HTTP reais: `no_evidence()`, citação real, citação inventada descartada, RBAC (`knowledge.read`), isolamento organizacional, resposta malformada (502), trilha de auditoria.

**Governança**
- `docs/architecture/TECHNICAL_DEBT.md` — TD-015 atualizado para `Status: Deferred`, gatilho oficializado pelo Founder ("segundo Advisor baseado em RAG — Governance Advisor ou equivalente").
- `docs/product/stratech-v2/DECISION-LOG.md`, `CHANGELOG.md`, `web/lib/mock/mission-control-data.ts` — espelhados (D-096).

---

## Arquitetura impactada

**Confirmado por leitura direta de código, não apenas por design:**

| Componente | Confirmação |
|---|---|
| `AdvisorFramework.run()` | Inalterado — `git diff` mostra zero linhas modificadas nesse método; o único acréscimo à classe é `normalize_rag_evidence()`, um método novo, não uma alteração de `run()`. |
| Workflow Runtime | Inalterado — nenhum arquivo de `src/workflows/` tocado; Document Advisor nunca invocado por workflow/evento. |
| Event Pipeline | Inalterado — Document Advisor não publica nem consome eventos; `document.indexed` (W5-0) já alimentou a Knowledge Platform antes deste fluxo. |
| `RecommendationEngine` | Compatível — apenas rename de campo (`item.source_analysis_id` → `item.source_id`); suíte completa do Risk Advisor passa sem nenhuma alteração de expectativa (prova de compatibilidade). |
| `AIContextEngine` (exceto `normalize_rag_evidence()`) | `gather()` inalterado em lógica — apenas os campos do `Evidence` construído mudam de nome, não o comportamento. |

---

## Testes executados e resultados

| Suíte | Resultado |
|---|---|
| Backend completo (`pytest`) | **561 passed**, 0 failed (539 pré-existentes + 22 novos desta Epic) |
| Frontend completo (`vitest`) | **503 passed** (69 arquivos) — nenhum arquivo de frontend tocado nesta Epic |
| `ruff check src tests` | Limpo |
| `npx tsc --noEmit` | Limpo |
| `npx eslint .` | Limpo |

---

## Demonstração funcional completa do Document Advisor

**Fluxo ponta a ponta exercido em `tests/test_document_advisor_api.py::TestRealCitation::test_answers_from_an_indexed_chunk_with_a_real_citation`:** documento real ingerido via `KnowledgeRepository.ingest()`/`.index()` → `POST /document-advisor/ask` real (HTTP, RBAC `knowledge.read` real, sessão institucional real) → `AdvisorFramework.gather_rag_context()` → `normalize_rag_evidence()` → `AdvisorFramework.run()` → `DocumentAdvisorAgent.advise()` → LLM (fake determinístico) → `RecommendationEngine.build()` → resposta HTTP citando `document_id`/`chunk_id` reais, idênticos ao documento efetivamente ingerido.

**`no_evidence()` sem chamada ao LLM** (`TestNoEvidence`): pergunta sem nenhum documento indexado retorna a resposta canônica sem nunca invocar o provider (um `ExplodingProvider` que levantaria `AssertionError` se fosse chamado nunca dispara).

**Citação inventada descartada** (`TestRealCitation::test_discards_a_citation_the_model_invented`): o LLM cita um `chunk_id` real e um inventado (`999999`); a resposta HTTP contém exclusivamente o real.

**Isolamento organizacional** (`TestOrganizationalIsolation`): documento indexado pela Organização B nunca é citado/visível para a Organização A — a busca RAG nunca retorna chunks de outra organização (confirmado tanto na camada de `AdvisorFramework` quanto na camada HTTP).

### Evidência obrigatória de rastreabilidade multi-chunk (item 3 da autorização)

`tests/test_document_advisor.py::TestMultiChunkTraceability::test_partial_citation_traces_chunk_to_document_version_and_response` — comprova exatamente o cenário exigido:

1. **Documento → múltiplos chunks:** um documento de ~1550 caracteres (3 seções distintas) é ingerido e indexado, produzindo **múltiplos chunks reais** (`chunk_count >= 3`, verificado via `KnowledgeRepository.get_document()`), não um único chunk artificial.
2. **LLM utiliza apenas parte deles:** de todos os chunks retornados pela busca RAG (`RagContext.chunks`, todos do mesmo documento), o LLM (scriptado deterministicamente no teste) cita **apenas 2 dos 3** — o terceiro (`uncited_id`) é deliberadamente retido pelo teste como "recuperado mas não citado".
3. **A resposta final referencia exclusivamente os chunks efetivamente citados:** `explanation.recommendation.cited_evidence` contém **exatamente** os 2 chunks citados — nem o terceiro chunk recuperado e não citado, nem um `chunk_id` inventado (`invented_id`, nunca presente na evidência) aparecem na resposta.
4. **Rastreabilidade completa chunk → documento → versão → resposta**, verificada com 3 asserções independentes:
   - cada `Evidence` citada carrega `metadata["document_id"]` igual ao `document.id` real ingerido;
   - `source_label` reproduz exatamente `f"Document {document.id} / Chunk {item.source_id}"` — nenhuma informação inventada;
   - consulta direta à tabela `chunks` (`Chunk.id.in_(cited_result_ids)`) confirma que **todo** `chunk_id` citado pertence à mesma `DocumentVersion` (`document.version_id`) do documento ingerido — a cadeia chunk→documento→versão é real, não apenas nomeada.

Este teste, por si só, comprova de forma rastreável e determinística todos os quatro elos exigidos pela autorização do Founder.

---

## Critérios de aceite da Technical Design (D-095) — confirmação

1. ✅ `AdvisorFramework.run()` reutilizado integralmente, confirmado inalterado por leitura de `git diff` (zero linhas).
2. ✅ `normalize_rag_evidence()` implementado, puramente mecânico — nenhuma interpretação de `chunk.text`, nenhuma decisão de relevância.
3. ✅ Contrato `Evidence` integrado sem quebra ao Risk Advisor — suíte completa do Risk Advisor (unitária + migração + HTTP) passa sem nenhuma alteração de expectativa.
4. ✅ Fluxo completo demonstrado ponta a ponta (Knowledge Platform → RAG Pipeline → `normalize_rag_evidence()` → `AdvisorFramework.run()` → Document Advisor → LLM → resposta).
5. ✅ Rastreabilidade de citação, isolamento organizacional, portão anti-alucinação e ausência de regra de negócio em `AIContextEngine` — todos comprovados por teste real, não apenas descritos.
6. ✅ `AdvisorFramework.run()`, Workflow Runtime, Event Pipeline inalterados; `RecommendationEngine` compatível — confirmado.

---

## Riscos residuais (reconfirmados, nenhum bloqueante)

1. **TD-015** (chave literal `"cited_analysis_ids"` em `AdvisorFramework.run()`) — Status atualizado para **Deferred**; gatilho oficializado pelo Founder: o segundo Advisor baseado em RAG (Governance Advisor ou equivalente). Nenhuma alteração a `run()` até esse gatilho.
2. **`top_k=5`** não validado com uso real — revisitar quando houver volume real de perguntas em produção.
3. **Ausência de filtro por `project_id` no RAG** (herdado de D-087/D-088) — Document Advisor sempre responde no escopo de toda a organização.
4. **Knowledge Version Resolution** (D-090, Decision Proposal ainda não resolvida) — chunks de versões antigas permanecem pesquisáveis; o Document Advisor herda esse comportamento sem agravá-lo.

Nenhum risco bloqueia o encerramento do Epic W5-1.

---

## Confirmação de encerramento

Todos os critérios de aceite atendidos. Nenhuma expansão de escopo além do autorizado. **Recomendação: GO para o encerramento do Epic W5-1.**

Per instrução explícita do Founder: retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor (Wave 5) — nenhum código de outro Advisor foi iniciado ou antecipado.
