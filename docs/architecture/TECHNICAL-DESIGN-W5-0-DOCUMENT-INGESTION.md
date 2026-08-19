# Technical Design — W5-0: Document Ingestion (Epic habilitador da Wave 5)

**Autorização:** "Founder Decision — AR-9 Approved" (2026-07-30). Veredito: **APPROVED — GO para o Technical Design do W5-0**. Seis decisões oficiais do Founder incorporadas neste documento (§1-§6 abaixo mapeiam 1:1 aos seis pontos da autorização).

**Etapa do ciclo institucional:** 4 de 8 (Domain Blueprint D-087 → Architecture Review AR-9/D-088 → Founder Approval → **Technical Design, este documento** → Founder Approval → Implementação → Executive Review → Encerramento do Epic). **Nenhum código, nenhuma migração escrita ainda** — este documento especifica o suficiente para que a implementação comece somente após aprovação explícita.

**Restrição confirmada (ponto 1 do Founder):** este Epic (W5-0) é exclusivamente Knowledge Platform. **Nenhuma linha deste Technical Design toca `Evidence`, `AIContextEngine`, `AdvisorFramework`, `RecommendationEngine`, `DocumentAdvisorAgent` ou qualquer rota `/document-advisor/*`.** A evolução do contrato `Evidence` e `normalize_rag_evidence()` (aprovados em AR-9) são código do **W5-1** (Technical Design próprio, futuro) — aqui são apenas confirmados/esclarecidos per pontos 3 e 4 da autorização, sem nenhuma implementação.

---

## 1. W5-0 como Epic habilitador — confirmação de escopo

Objetivo exclusivo: disponibilizar um fluxo funcional de Document Ingestion para a Knowledge Platform. Encerra em `document.indexed` → `WorkflowRuntime` (rastreamento de execução já existente, W4-4) — **nunca invoca `AdvisorFramework`, nunca constrói `Evidence`, nunca chama um LLM**. O consumo desse conhecimento pelo Document Advisor é responsabilidade de W5-1, fora deste Epic.

---

## 2. Fluxo oficial (per Founder, verificado contra código real)

```
Upload (usuário autenticado, RBAC)
   │
   ▼
Knowledge Platform
   │  KnowledgeRepository.ingest(organization_id, source_name, text, project_id=None)
   │  -- ZERO mudança de assinatura
   ▼
Document (criado se novo; encontrado por organization_id + source_name)
   │
   ▼
Version (DocumentVersion -- sempre uma nova linha, nunca sobrescrita, §7)
   │
   ▼
Chunks (KnowledgeRepository.index(document_id, correlation_id) -- ZERO mudança de assinatura;
   chunking 500/50 chars, embeddings via EmbeddingProvider, persiste Chunk rows)
   │
   ▼
document.indexed (publicado via EventPublisher -- ZERO mudança; payload
   {document_id, version_id, chunk_count})
   │
   ▼
Workflow Runtime (JÁ REGISTRADO em produção: build_event_publisher() já chama
   document_indexed_workflow.register(dispatcher, runtime) -- confirmado em
   src/api/dependencies.py:30-43. Zero código novo necessário aqui.
   Rastreia a execução em workflow_executions, W4-4.)
   │
   ▼
Document Advisor (W5-1 -- fora do escopo de W5-0; consome via RagPipeline.retrieve(),
   nunca lê workflow_executions diretamente)
```

Cada seta até `document.indexed → Workflow Runtime` já existe em código, testada, sem nenhuma mudança de assinatura — a única peça ausente é o caminho HTTP (Upload) até `ingest()`/`index()`. A última seta (`→ Document Advisor`) é o limite exato do escopo deste Epic — não é implementada aqui.

---

## 3. API Contract

### 3.1 `POST /documents`

```
Request:  multipart/form-data
  - file: UploadFile (texto/markdown -- decodificado como UTF-8; ver §9 sobre formatos suportados)
  - source_name: str (opcional -- default: nome do arquivo)
  - project_id: int | None (opcional)

Autenticação: RequestContext (per get_request_context) -- organization_id e user_id vêm
  exclusivamente do contexto de autenticação, nunca do corpo da requisição (mesma
  disciplina de toda rota administrativa existente, ex. src/api/routes/administration.py).

RBAC: Depends(require_permission("knowledge.write"))

Fluxo interno:
  1. ingested = knowledge_repository.ingest(organization_id, source_name, text, project_id)
     audita "document.uploaded" {document_id, version_id, source_name}
  2. try: knowledge_repository.index(ingested.id, correlation_id=context.request_id)
     audita "document.indexed" {document_id, version_id, chunk_count}
     (o document.indexed já publicado por index() já dispara Workflow Runtime -- este
     AuditLog é a auditoria administrativa da Knowledge Platform, um mecanismo
     independente e já existente, não duplica o Event Pipeline)
     return 201 {document_id, version_id, chunk_count, status: "indexed"}
  3. except Exception as exc:
     audita "document.index_failed" {document_id, version_id, error: sanitize_error(exc)}
     -- reaproveita src/workflows/execution_tracking.py::sanitize_error, sem duplicação
     raise HTTPException(502, {document_id, version_id, status: "ingested_pending_index",
       detail: "Indexação falhou; documento foi criado e pode ser reindexado"})
     -- a exceção original nunca é engolida silenciosamente: é sanitizada apenas no
     AuditLog (nunca stack trace/payload), mas o erro real é logado via logging padrão
     (mesma disciplina de KnowledgeRepository.index() hoje)
```

### 3.2 `POST /documents/{document_id}/reindex`

Caminho de retry explícito para o estado "ingerido, não indexado" (§3.1 passo 3). Reaproveita `KnowledgeRepository.index(document_id, correlation_id)` — zero código novo no repositório, apenas mais um chamador. RBAC: `knowledge.write`.

### 3.3 `GET /documents`

```
RBAC: Depends(require_permission("knowledge.read"))
Query: project_id: int | None (filtro opcional)
Response: 200 [{document_id, source_name, project_id, latest_version_id, chunk_count,
  status, created_at}, ...]
  -- organization-scoped implicitamente (nunca um parâmetro de query)
```

### 3.4 `GET /documents/{document_id}`

```
RBAC: Depends(require_permission("knowledge.read"))
Response: 200 {document_id, source_name, project_id, versions: [{version_id, chunk_count,
  created_at}, ...], status}
  -- 404 se o documento não existe OU pertence a outra organização (nunca 403 --
  mesma disciplina de get_document()/list_versions(), que já retornam None/[] nesse caso,
  evitando vazamento de existência entre tenants)
```

**Derivação de `status` (nenhuma coluna nova):** "indexed" se a versão mais recente tem `chunk_count > 0`; "ingested_pending_index" se `chunk_count == 0` e não há `document.index_failed` mais recente que a criação da versão; "failed" se a entrada de auditoria mais recente para o `document_id` é `document.index_failed` sem um `document.indexed` subsequente. Fonte: `AuditLog` (extensão aditiva de `list_audit_log()`, §5) + `chunk_count` (extensão aditiva, §4).

---

## 4. Modelo de dados — extensões aditivas, nenhuma migração destrutiva

1. **`chunk_count` por versão:** `KnowledgeRepository.list_versions()`/`get_document()` (já existentes, já tenant-scoped) ganham um `COUNT(Chunk.id)` agrupado por `document_version_id` — extensão aditiva ao método, `DocumentVersionInfo` ganha um campo `chunk_count: int`. Nenhuma coluna nova na tabela `document_versions` (contagem computada, não armazenada — evita um contador que pode dessincronizar).
2. **Nenhuma tabela nova.** `documents`/`document_versions`/`chunks` já existem (Fase 1, Wave 3) e já são suficientes.
3. **Novas linhas em `permissions`** (migração aditiva, mesmo padrão de 0011/0012/0013): `knowledge.write`, `knowledge.read`, atribuídas ao(s) papel(is) administrativo(s) já existente(s) — decisão exata de quais Roles recebem por padrão fica com a migração, seguindo o precedente de `api_keys.manage`/`sessions.manage`.

---

## 5. Auditoria

Reaproveita `AuditLog`/`AdministrationRepository.record_audit()` sem nenhuma mudança de mecanismo — ações novas: `document.uploaded`, `document.indexed` (auditoria administrativa, independente do Event Pipeline), `document.index_failed` (`details.error = sanitize_error(exc)`, nunca stack trace/payload).

**Extensão aditiva necessária:** `AdministrationRepository.list_audit_log(organization_id, limit)` ganha parâmetros opcionais `entity_type: str | None = None, entity_id: int | None = None` — comportamento por omissão inalterado (todos os call sites existentes continuam funcionando sem modificação), usado apenas pela derivação de `status` (§3.4).

---

## 6. Tratamento de erro

- Exceção de `index()` (ex.: `EmbeddingProvider` indisponível) nunca é engolida — sempre re-lançada ao chamador HTTP como 502, nunca convertida silenciosamente em uma resposta de sucesso.
- Estado parcial "ingerido, não indexado" é de primeira classe — visível via `GET /documents/{id}` (`status: "ingested_pending_index"`), nunca escondido, com caminho de retry explícito (`POST /documents/{id}/reindex`).
- `sanitize_error()` (`src/workflows/execution_tracking.py:28-32`) reaproveitado tal como está — nenhuma duplicação de lógica de sanitização.

---

## 7. Política de versionamento documental (ponto 5 da autorização)

### 7.1 Quando ocorre a ingestão

A cada chamada de `POST /documents` — `KnowledgeRepository.ingest()` sempre cria uma nova `DocumentVersion` (nunca sobrescreve), mesmo se `source_name` já existir para a organização (Blueprint §1.10, comportamento já implementado, zero mudança).

### 7.2 Qual versão é indexada

**Achado confirmado em código:** `KnowledgeRepository.index(document_id, ...)` sempre indexa a **versão mais recente** de um `document_id` (`ORDER BY DocumentVersion.id DESC LIMIT 1`), nunca uma versão específica por `version_id` — não há parâmetro para indexar uma versão anterior. No fluxo síncrono de W5-0 (`ingest()` seguido imediatamente por `index()` na mesma requisição, §3.1), isso é determinístico e correto: a versão criada por `ingest()` é, no momento de `index()`, garantidamente a mais recente.

### 7.3 Comportamento diante de múltiplas versões — achado crítico

**Confirmado em código, não hipótese:** `KnowledgeRepository.search()`/`VectorRepository.similarity_search()` (`vector_repository.py:41-63`) filtram apenas por `organization_id` — **não filtram por versão mais recente**. Chunks de uma `DocumentVersion` antiga permanecem na tabela `chunks` (nunca deletados, per Blueprint §1.10) e permanecem retornáveis por busca semântica indefinidamente, mesmo após uma reingestão criar uma versão mais nova do mesmo documento.

**Impacto concreto na recuperação via RAG:** se um documento for reingerido (mesmo `source_name`) e reindexado, uma consulta ao RAG pode retornar **simultaneamente chunks da versão antiga e da versão nova**, sem preferência pela mais recente e sem nenhuma indicação de que um chunk é obsoleto — um citação poderia se basear em conteúdo já substituído.

### 7.4 Decisão de política para W5-0 (recomendação, não unilateral — para confirmação do Founder)

**Recomendação: W5-0 não introduz nenhuma mudança a `search()`/`similarity_search()`.** Escopo de W5-0 permanece estritamente "ingestão de um documento novo" — a UI/rota mínima não expõe nenhum fluxo deliberado de "reingerir/atualizar documento existente" (Blueprint original já excluía "Atualização incremental" e "políticas complexas de retenção" do escopo). Nada no código impede uma reingestão natural (mesmo `source_name` chamado duas vezes), mas W5-0 não constrói funcionalidade para isso.

**Risco residual explicitamente registrado (não resolvido aqui):** se e quando reingestão deliberada de um documento existente se tornar um caso de uso real do Document Advisor (W5-1) ou de um Advisor futuro, a recuperação via RAG **pode retornar chunks obsoletos lado a lado com os atuais**. A resolução correta (filtrar `similarity_search()` para a versão mais recente por documento, ou marcar chunks de versões supersedidas) é uma decisão de arquitetura que deve ser tomada quando esse caso de uso for real — per "Grounded before Generalized" — não antecipada especulativamente por W5-0. **Este documento não decide essa resolução; apenas a torna visível para decisão futura do Founder**, exatamente como pedido ("nenhuma decisão unilateral").

---

## 8. Ponto 3 — avaliação do campo `confidence` em `Evidence`

**Recomendação: postergar.** Tecnicamente é aditivo e barato (`confidence: float | None = None` não quebra nada), mas não há consumidor real hoje:

- Nenhuma função em `RecommendationEngine`, `ExplanationEngine` ou qualquer Advisor lê ou filtra por confiança hoje.
- O campo seria **honesto apenas para `source_type="document_chunk"`** (o `score` de similaridade do cosseno, já calculado por `VectorRepository.similarity_search()`, é um sinal real). Para `source_type="analysis_record"` (Risk Advisor e demais), não existe nenhum sinal de confiança equivalente hoje — populá-lo exigiria um valor fixo arbitrário (ex. `1.0` sempre), repetindo exatamente o padrão que o Founder já rejeitou em AR-9 (usar um campo de forma "funcionalmente conveniente, mas semanticamente incorreta" para uma fonte que não o possui naturalmente).
- Mesmo princípio já aplicado a `gather_memory` (AR-8, risco residual #2) e a Event Metrics (D-079/D-083): adicionar um campo sem consumidor real e sem sinal genuíno para todas as fontes é generalização prematura, não uma necessidade demonstrada.

**Quando revisitar:** no Technical Design do W5-1 (Document Advisor), se um caso de uso real exigir filtrar ou exibir confiança de citação (ex.: ocultar chunks abaixo de um limiar de similaridade) — nesse momento, `confidence: float | None = None` é uma extensão aditiva trivial ao dataclass já aprovado em AR-9, populado a partir de `chunk.score` apenas para `source_type="document_chunk"`, permanecendo `None` para `analysis_record` até essa fonte também ganhar um sinal real. Não é uma decisão que este documento tome — é uma recomendação para confirmação do Founder.

---

## 9. Ponto 4 — confirmação de `normalize_rag_evidence()`

**Confirmado: permanece exclusivamente uma função de normalização mecânica.** Transforma cada `ScoredChunk` (já produzido e já ranqueado por `RagPipeline`) em um `Evidence(source_type="document_chunk", source_id=chunk.chunk_id, source_label=..., content={"text": chunk.text}, metadata={...})` — nenhuma decisão de relevância (já decidida pelo ranking do `RagPipeline`), nenhuma interpretação do texto do chunk, nenhum vocabulário de domínio (não sabe o que é um "risco" ou uma "resposta válida"). É estruturalmente idêntica em natureza a `AIContextEngine.gather()` — envelopa, nunca interpreta. **Esta função não é implementada por W5-0** (§1) — pertence ao Technical Design de W5-1, onde seu código real será escrito.

---

## 10. Testes (plano, não implementação)

1. Upload → `ingest()` + `index()` bem-sucedidos → `document.indexed` publicado → `workflow_executions` rastreado (reaproveita o teste já existente de W4-4, apenas confirmando que um chamador HTTP real produz o mesmo resultado que os testes diretos de hoje).
2. Falha de `index()` (ex.: `EmbeddingProvider` mockado para levantar exceção) → Document/DocumentVersion persistidos → `document.index_failed` auditado com erro sanitizado → nenhum `document.indexed` publicado → resposta HTTP 502.
3. `POST /documents/{id}/reindex` após falha → sucesso subsequente → `status` muda de "failed" para "indexed".
4. Tenant isolation: `GET /documents/{id}` de outra organização → 404 (nunca 403, nunca vazamento de existência).
5. RBAC: chamador sem `knowledge.write`/`knowledge.read` → 403.
6. `chunk_count` correto após indexação; `status` derivado corretamente nos 3 estados (`ingested_pending_index`, `indexed`, `failed`).
7. Reingestão do mesmo `source_name` → nova `DocumentVersion` criada, versão anterior preservada (não sobrescrita) — teste que documenta explicitamente o achado do §7.3 (chunks antigos continuam retornáveis por `search()`), sem asserir que isso é um bug — é o comportamento hoje deliberadamente aceito e registrado como risco residual.

---

## 11. Riscos residuais

1. **Chunks obsoletos permanecem pesquisáveis após reingestão** (§7.3/§7.4) — não resolvido por W5-0, resolução fica para quando um caso de uso real (W5-1 ou posterior) demonstrar a necessidade.
2. **`confidence` postergado** (§8) — resolver apenas com consumidor real comprovado.
3. **Formato de conteúdo aceito limitado a texto/markdown** — nenhum parser de PDF/binário é introduzido (fora de escopo, já excluído como "OCR avançado" e extensões correlatas); documentos não-texto exigem um Epic futuro de Parsing, não antecipado aqui.
4. **Naming definitivo de `knowledge.write`/`knowledge.read`** — proposto por esta revisão seguindo o padrão `resource.verb` já usado por `intelligence.read`/`intelligence.write`; confirmação final ocorre na migração, sem impacto arquitetural se o nome mudar.

Nenhum risco bloqueia a implementação.

---

## 12. Estratégia incremental

1. Migração aditiva: permissões `knowledge.write`/`knowledge.read` + extensão de `list_versions()`/`get_document()` com `chunk_count` + extensão de `list_audit_log()` com filtro opcional por entidade.
2. Rota `POST /documents` (upload → `ingest()` → `index()` → auditoria) + `POST /documents/{id}/reindex`.
3. Rotas de consulta `GET /documents`/`GET /documents/{id}` com derivação de `status`.
4. Interface administrativa mínima (mesmo padrão de Convites/Sessões/API Keys) — formulário de upload + lista com status/chunk_count.
5. Testes (§10) + suíte completa + verificação (`ruff`, `pytest`, `tsc`, `eslint`).
6. Executive Review + Encerramento do Epic W5-0 → abre caminho para o Technical Design do W5-1 (Document Advisor).

---

## 13. Executive Summary

W5-0 entrega o único elo faltante entre a Knowledge Platform (Wave 3, já pronta) e o Document Advisor (W5-1, autorizado mas ainda não iniciado): um caminho HTTP autenticado, auditado e org-isolado até `KnowledgeRepository.ingest()`/`.index()`, que já publicam `document.indexed` já integralmente conectado ao Event/Workflow Pipeline em produção. Nenhum mecanismo novo é introduzido — upload, status, auditoria e tratamento de erro reaproveitam componentes já existentes e testados (`AuditLog`, `sanitize_error()`, `get_document()`/`list_versions()`), com apenas três extensões aditivas pequenas (`chunk_count`, filtro de auditoria por entidade, duas novas permissões). Um achado arquitetural real foi identificado e registrado, não escondido: chunks de versões antigas de um documento reingerido permanecem pesquisáveis via RAG indefinidamente, sem preferência pela versão mais recente — risco aceito e documentado, não resolvido especulativamente. O campo `confidence` em `Evidence` foi avaliado e recomendado para postergação, por falta de consumidor real e por seria semanticamente falso para evidência de `AnalysisRecord` hoje. `normalize_rag_evidence()` confirmado como puramente mecânico, sua implementação real pertence ao Technical Design de W5-1.

---

## 14. Recomendação Go/No-Go para implementação

**GO** — condicionado à aprovação explícita do Founder sobre: (a) a recomendação de postergar `confidence`; (b) a política de versionamento do §7.4 (aceitar o risco de chunks obsoletos como residual, não resolvido por W5-0); (c) o naming `knowledge.write`/`knowledge.read`. Nenhuma linha de código será escrita antes dessa aprovação, per instrução explícita do Founder.
