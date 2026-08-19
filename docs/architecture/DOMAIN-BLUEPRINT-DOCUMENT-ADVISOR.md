# Domain Blueprint — Document Advisor (primeiro Epic da Wave 5)

**Autorização:** "Founder Decision — AR-8 Approved" (2026-07-30, D-086). O Founder aprovou o AR-8 (modelo arquitetural definitivo dos Enterprise Advisors) com uma emenda na definição do `AIContextEngine`, e escolheu o **Document Advisor** como primeiro Domain Blueprint da Wave 5 — por ser o único Advisor que já possui, hoje, produtor real de evento (`document.indexed`), Knowledge Platform concluída, RAG Pipeline concluído, Event Pipeline validado (Wave 4) e Workflow Runtime validado.

**Etapa do ciclo institucional:** 1 de 8 (Domain Blueprint → Architecture Review → Founder Approval → Technical Design → Founder Approval → Implementação → Executive Review → Encerramento do Epic). **Nenhuma etapa posterior é antecipada por este documento** — nenhum código, nenhuma migração, nenhum Technical Design.

**Método:** toda afirmação abaixo é rastreável a um arquivo e uma linha de código real hoje existente — `src/services/knowledge_platform/`, `src/services/advisor_framework/framework.py`, `src/services/ai_foundation/types.py`, `src/services/ai_foundation/recommendation_engine.py`, `src/agents/risk_advisor/agent.py`, `src/api/routes/intelligence.py`, `src/database/models.py`. Nenhuma conclusão nasce de hipótese.

---

## 0. Escopo e não-escopo deste documento

**Escopo:** definir a arquitetura do primeiro Advisor da Classe D (`AR-8` §4) — objetivo, responsabilidades, contrato, montagem de contexto, integração com o modelo "Framework-Mediated Evidence Assembly" (`AR-8` §9) — e identificar, com evidência de código, qualquer lacuna real que precise ser resolvida antes ou durante a implementação.

**Não-escopo (explícito, per Restrições do ciclo institucional):**
- Nenhum código, nenhuma migração, nenhum endpoint implementado por este documento.
- Nenhum Technical Design (prompt final, payload exato dos schemas Pydantic, testes) — isso é a etapa 4 do ciclo.
- Nenhuma mudança ao `AdvisorFramework`, `AIContextEngine`, `RagPipeline` ou `KnowledgeRepository` além do que a Grounding Audit (§1) demonstrar como estritamente necessário.
- Nenhum Governance Advisor (o segundo Advisor da Classe D) — este documento cobre exclusivamente o Document Advisor.

---

## 1. Grounding Audit — o que já existe, hoje, em código

### 1.1 Knowledge Platform (Wave 3 Fase 1/2) — pronta e testada

- `KnowledgeRepository` (`src/services/knowledge_platform/knowledge_repository.py`) expõe `ingest(organization_id, source_name, text, project_id=None) -> IngestedDocument` e `index(document_id, correlation_id) -> None` (Parsing→Chunking→Embeddings→Indexação, chunk fixo de 500 caracteres com overlap de 50).
- `RagPipeline.retrieve(organization_id, query, top_k=5) -> RagContext` (`src/services/knowledge_platform/rag_pipeline.py`) compõe Semantic Search + ranking determinístico (score, depois recência da versão), retornando `RagContext` com `chunks: list[ScoredChunk]` e a propriedade `chunk_ids: frozenset[int]` — "o conjunto autoritativo contra o qual uma citação futura deve ser validada" (docstring do próprio `RagContext`).
- `ScoredChunk` (`src/services/knowledge_platform/types.py`) carrega `chunk_id`, `document_id`, `text`, `score`, `document_version_created_at` — tudo que uma citação rastreável precisa.
- Tabelas `documents`/`document_versions`/`chunks` (`src/database/models.py:380-426`) já existem, com `organization_id` obrigatório em todas (mesma disciplina de tenant isolation de `AnalysisRecord`/`Portfolio`/`Program`/`Project`), `project_id` opcional em `Document`, e `chunks.organization_id` denormalizado do `Document` proprietário (para busca por similaridade sem join).

### 1.2 Event Pipeline (Wave 4) — já publica `document.indexed`

`KnowledgeRepository.index()` publica `document.indexed` (`{document_id, version_id, chunk_count}`) via `EventPublisher`, **somente após o commit dos chunks** — se `index()` levantar exceção antes desse ponto, nenhum evento é publicado (D-080). `correlation_id` é obrigatório e nunca mintado dentro do método, seguindo a mesma disciplina de `DomainService` (W4-1).

**Achado crítico, já registrado em D-080 e reconfirmado aqui:** `KnowledgeRepository.ingest()`/`.index()` **não têm nenhuma rota HTTP chamadora em produção hoje** — confirmado por busca exaustiva em `src/api/routes/` (única referência a `KnowledgeRepository` fora do próprio pacote é `build_knowledge_repository()`/`build_rag_pipeline()` em `src/api/routes/intelligence.py`, usados apenas para prover `RagPipeline` como fonte de leitura, nunca para ingestão). Documentos só entram na plataforma hoje via chamada direta de teste. Isto é tratado em detalhe no §5.

### 1.3 Advisor Framework (Wave 3 Fase 3/4) — o contrato que o Document Advisor deve seguir

- `AdvisorContract` (`src/services/advisor_framework/types.py`): `advise(session, question, evidence, rag_context=None) -> dict`, retornando `{"structured": bool, "answer": str, "cited_analysis_ids": list[int], ...}`.
- `AdvisorFramework.run()` (`src/services/advisor_framework/framework.py`) executa, nesta ordem exata, para qualquer Advisor: (1) `AIFoundationAudit.record_question()` incondicional; (2) **portão anti-alucinação: `if not evidence: return no_evidence()`** — este `if` opera sobre o parâmetro `evidence: list[Evidence]`, não sobre `rag_context`; (3) `advisor.advise(...)`; (4) validação genérica de forma; (5) `RecommendationEngine.build(answer, cited_analysis_ids, evidence)`; (6) `ExplanationEngine.explain(recommendation)`.
- **Achado crítico (grounding desta revisão, refina `AR-8` §4.1):** `RecommendationEngine.build()` (`src/services/ai_foundation/recommendation_engine.py`) filtra citações assim: `by_id = {item.source_analysis_id: item for item in evidence}`, depois `cited = [by_id[cited_id] for cited_id in cited_ids if cited_id in by_id]`. **A chave de correspondência é, sem exceção, `Evidence.source_analysis_id`.** Isso significa, concretamente, que o Document Advisor **precisa** popular `Evidence.source_analysis_id` com o `chunk_id` real (`int`, tipo-compatível, per `Chunk.id: Integer`) para que uma citação sobreviva a `RecommendationEngine.build()`. Isto não é uma sugestão de nomenclatura — é uma exigência estrutural para o portão anti-alucinação funcionar corretamente para este Advisor, exatamente como já apontado como risco residual em `AR-8` §4.1/§10, agora confirmado como bloqueio de Technical Design, não de arquitetura.
- `RiskAdvisorAgent` (`src/agents/risk_advisor/agent.py`) é o precedente direto de implementação: recebe `evidence`/`rag_context` já prontos (nunca os coleta sozinho), monta um JSON estruturado (`risks_json`) para o prompt, chama `framework.render_prompt()` + `framework.call_llm()`, interpreta a saída com `parse_structured_output`. O Document Advisor segue exatamente esta forma (§3).

### 1.4 O que NÃO existe e não será inventado por este documento

- Nenhum `gather_document_context()` ou método fino adicional no `AdvisorFramework` — `gather_rag_context()` já é suficiente.
- Nenhuma alteração ao `AIContextEngine` — o Document Advisor não usa `AnalysisRecord` como fonte (não existe `kind="document"` em `AnalysisRecord`, e não deveria existir).
- Nenhum novo campo em `Evidence`/`Recommendation` — a resolução do achado do §1.3 é de nomenclatura/uso do campo já existente, não de schema novo (ver §6).

---

## 2. Objetivo e responsabilidade (per `ENTERPRISE-ADVISOR-CATALOG.md` §8)

**Objetivo:** responder perguntas em linguagem natural sobre o conteúdo de documentos corporativos já ingeridos, citando sempre `document_id`/`chunk_id` reais.

**Responsabilidade:** o Advisor de referência para uso **primário** do RAG Pipeline (Classe D, `AR-8` §4) — nunca infere além do que o documento diz; se não há evidência documental para a pergunta, retorna `no_evidence()`, nunca alucina uma resposta.

**Entradas:** pergunta do usuário + `organization_id` + escopo opcional (`project_id`, se a busca precisar ser restrita a documentos de um projeto).

**Saídas:** `Explanation` (via `ExplanationEngine`) envolvendo uma `Recommendation` cujo `cited_evidence` aponta exclusivamente para chunks reais.

**Limites de atuação (idênticos aos demais Advisors, `AR-8` §8):** nunca executa regra de negócio, nunca altera entidade, apenas produz inteligência auditável.

---

## 3. Modelo aplicado — Framework-Mediated Evidence Assembly, Classe D

Per `AR-8` §9, o Document Advisor segue exatamente o mesmo modelo definitivo de todos os 7 Advisors, sem exceção nem variante:

```
Rota HTTP (POST /document-advisor/ask, análoga a /risk-advisor/ask)
   │  constrói SessionContext; invoca a Montagem de Contexto do Document Advisor
   ▼
Montagem de Contexto (Document Advisor) -- decide O QUÊ buscar
   │  1. framework.gather_rag_context(organization_id, question, top_k=5) -> RagContext
   │  2. envolve cada ScoredChunk em um Evidence:
   │       Evidence(
   │         source_analysis_id=chunk.chunk_id,          # ver achado §1.3 -- exigência estrutural
   │         source_created_at=chunk.document_version_created_at,
   │         kind="document_chunk",
   │         summary={"chunk_id": chunk.chunk_id, "document_id": chunk.document_id, "text": chunk.text},
   │       )
   │  3. NÃO chama framework.gather_context() -- não há AnalysisRecord de kind="document"
   │  evidence = [Evidence(...), ...]  (vazio se RagPipeline não retornar nada -- aciona no_evidence() corretamente)
   ▼
AdvisorFramework.run(document_advisor, session, question, evidence, rag_context)
   │  compartilhado/invariante -- auditoria, portão anti-alucinação, validação, RecommendationEngine.build(),
   │  ExplanationEngine.explain() -- byte-for-byte igual ao que já roda para o Risk Advisor
   ▼
DocumentAdvisorAgent.advise(session, question, evidence, rag_context) -- domínio
   │  monta prompt a partir dos chunks (texto + document_id, nunca reinterpretado como "risco" ou
   │  qualquer vocabulário de outro Advisor), chama framework.render_prompt()/call_llm(),
   │  interpreta a resposta (parse_structured_output), devolve cited_analysis_ids = chunk_ids citados
```

**Ponto que confirma a decisão do AR-8 na prática:** o portão anti-alucinação em `AdvisorFramework.run()` opera sobre `evidence`, nunca sobre `rag_context` isoladamente — por isso a Montagem de Contexto do Document Advisor **precisa** envolver os chunks em `Evidence` antes de chamar `run()`. Se a Montagem de Contexto passasse apenas `rag_context` e `evidence=[]`, `run()` cairia sempre em `no_evidence()`, mesmo com chunks relevantes recuperados — o que provaria a Opção A (coleta dentro do Advisor) incompatível também neste caso, e reforça por que a camada de Montagem de Contexto (§2 do AR-8) precisa existir como responsabilidade nomeada, não implícita.

---

## 4. Contrato do `DocumentAdvisorAgent`

Mesma forma de `AdvisorContract` já provada pelo `RiskAdvisorAgent` — nenhum contrato novo:

```
class DocumentAdvisorAgent:
    name = "document_advisor"
    def __init__(self, framework: AdvisorFramework): ...
    def advise(self, session, question, evidence, rag_context=None) -> dict:
        # monta prompt a partir de evidence (chunks), chama framework.render_prompt()/call_llm(),
        # retorna {"structured": ..., "answer": ..., "cited_analysis_ids": [...]}
```

Prompt resolvido via `PromptRegistry.get("document_advisor", "advise")` (`src/agents/document_advisor/prompts/advise.md`, convenção idêntica a `src/agents/risk_advisor/prompts/`) — conteúdo do prompt é decisão de Technical Design, não deste documento.

---

## 5. Achado que exige decisão do Founder: gap de Document Ingestion

A Knowledge Platform já implementa `ingest()`/`index()` (§1.1), e o Blueprint que a originou (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.1) já descreve Document Ingestion como componente da plataforma. **Porém nenhuma rota HTTP os expõe hoje.** Sem uma forma de organizações reais ingerirem documentos, o Document Advisor teria, na prática, o mesmo destino da Classe C (Strategy Advisor, `AR-8` §4) — sempre `no_evidence()`, por falta de dado, não por falha de arquitetura.

Duas opções, ambas compatíveis com a arquitetura já aprovada, apresentadas para decisão do Founder na Architecture Review deste Epic (etapa 2 do ciclo):

- **Opção 1 — Epic inclui uma rota mínima de ingestão** (`POST /admin/documents` ou equivalente, reutilizando `KnowledgeRepository.ingest()` + `.index()` sem nenhuma mudança de assinatura), permitindo validar o Document Advisor ponta a ponta com dado real desde o primeiro Epic.
- **Opção 2 — Epic cobre apenas o Advisor** (rota `/document-advisor/ask` + `DocumentAdvisorAgent`), assumindo que a ingestão de documentos reais é resolvida por um Epic separado (ou por dado de teste/seed), e o Document Advisor nasce funcionalmente correto mas sem consumidor real até essa segunda peça existir.

Este documento **não decide** entre as duas — apresenta o achado grounded para a Architecture Review resolver, exatamente como o Founder instruiu ("se surgir qualquer inconsistência arquitetural, interrompa e apresente para decisão").

---

## 6. Riscos e decisões que ficam para o Technical Design (não bloqueiam este Blueprint)

1. **Nomenclatura `Evidence.source_analysis_id`/`cited_analysis_ids` usada para `chunk_id`** (§1.3) — funcionalmente correto (tipo-compatível), mas semanticamente confuso para um leitor futuro. Technical Design deve decidir: manter e documentar explicitamente, ou propor um ADR de renomeação neutra (`source_id`/`cited_ids`) que beneficiaria todos os Advisors, não só este.
2. **Escopo do `no_evidence_answer`** — o Document Advisor deve fornecer sua própria mensagem de "nenhum documento relevante encontrado" (mesmo padrão de `RiskAdvisorAgent`/`no_evidence_answer` opcional em `run()`), não usar a mensagem genérica default de `RecommendationEngine.NO_EVIDENCE_ANSWER` ("Nenhuma evidência identificada ainda para este projeto" — redação de domínio de risco, incorreta para documentos).
3. **`project_id` como filtro opcional** — `RagPipeline.retrieve()` hoje não aceita filtro por `project_id`, apenas `organization_id`; `Document.project_id` existe mas `KnowledgeRepository.search()`/`VectorRepository.similarity_search()` não o utilizam. Se o Technical Design decidir que o Document Advisor precisa escopar por projeto, isso é uma extensão aditiva ao `KnowledgeRepository`/`VectorRepository` (mais um parâmetro opcional), nunca uma mudança de responsabilidade.
4. **Volume de chunks vs. `top_k`** — nenhum teste real de volume existe ainda para a Knowledge Platform; `top_k=5` (default de `RagPipeline.retrieve()`) é o mesmo usado hoje pelo uso suplementar do Risk Advisor, não validado para um Advisor onde RAG é a única fonte. Fica para o Technical Design avaliar se `top_k` precisa de um valor diferente para este Advisor.

Nenhum destes riscos é uma inconsistência arquitetural — todos são detalhamento de Technical Design, coerente com o precedente de `AR-8` §10.

---

## 7. Fora de escopo (explícito)

- Governance Advisor (segundo Advisor da Classe D) — Domain Blueprint próprio, quando autorizado.
- Qualquer alteração ao modelo definitivo de `AR-8` — este Blueprint apenas aplica o modelo já aprovado, não o revisa.
- Políticas de retenção, estratégia de cache, atualização incremental (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.11-§1.13) — infraestrutura da Knowledge Platform, não deste Epic.
- Interface de usuário para upload de documentos — se a Opção 1 do §5 for aprovada, o escopo desta Epic é a rota, não necessariamente uma tela dedicada (decisão de Technical Design/UX, não deste Blueprint).

---

## 8. Critérios de sucesso do Epic (para a etapa de Executive Review, ao final)

1. `POST /document-advisor/ask` responde citando `document_id`/`chunk_id` reais — nunca uma afirmação sem chunk correspondente.
2. Pergunta sem nenhum documento relevante retorna `no_evidence()` com mensagem de domínio apropriada (não a mensagem genérica de risco).
3. Nenhuma alteração a `AdvisorFramework.run()`, `AIContextEngine`, `RagPipeline` além do estritamente necessário identificado no Technical Design (nenhuma generalização especulativa).
4. `ruff check src tests` limpo, suíte de testes backend completa verde, testes novos cobrindo: resposta com evidência, `no_evidence()` sem chunks, tenant isolation (chunk de outra organização nunca aparece), citação inventada pelo modelo é descartada por `RecommendationEngine.build()`.
5. Se a Opção 1 do §5 for aprovada: rota de ingestão testada end-to-end (ingest → index → document.indexed publicado → chunk pesquisável via `/document-advisor/ask`).

---

## 9. Próximo passo

Architecture Review deste Domain Blueprint (etapa 2 do ciclo institucional), resolvendo explicitamente o achado do §5 (Opção 1 vs. Opção 2) antes de qualquer Technical Design. Nenhuma etapa posterior será antecipada.
