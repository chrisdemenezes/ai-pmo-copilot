# W5-0 EXECUTIVE EVIDENCE — Document Ingestion (Wave 5, Epic habilitador)

**Autorização:** "Founder Decision — Technical Design W5-0" (veredito **APPROVED — GO para implementação**), encerrando o ciclo institucional de 8 etapas: Domain Blueprint (D-087) → Architecture Review AR-9 (D-088) → Founder Approval → Technical Design (D-089) → Founder Approval (D-090) → **Implementação, este documento** → Executive Review → Encerramento do Epic.

**Escopo confirmado (ponto 1 da autorização):** exclusivamente Knowledge Platform. Nenhum arquivo desta implementação importa `Evidence`, `AIContextEngine`, `AdvisorFramework`, `RecommendationEngine` ou qualquer módulo de `src/agents/` — confirmado por revisão de cada arquivo abaixo.

---

## Escopo entregue

- Migração aditiva `0020` — permissões `knowledge.read`/`knowledge.write`, seguindo o padrão de seeding de 0010 (`knowledge.read` para os 4 papéis, `knowledge.write` para `organization_admin`/`pmo`/`project_manager`). Nenhuma tabela nova — `documents`/`document_versions`/`chunks` já existiam desde a migração 0016.
- Extensões aditivas ao `KnowledgeRepository`/`AdministrationRepository`: `chunk_count`/`created_at` em `IngestedDocument`/`DocumentVersionInfo`; novo método `list_documents()`; filtro opcional `entity_type`/`entity_id` em `list_audit_log()`. Zero mudança de assinatura em `ingest()`/`index()`.
- `DocumentIngestionService` (novo, `src/services/knowledge_platform/`) — composição fina de `KnowledgeRepository` + auditoria via `AnalysisRepository.administration` + `sanitize_error()` (reaproveitado de `src/workflows/execution_tracking.py`, zero duplicação).
- Rotas `POST /documents`, `POST /documents/{id}/reindex`, `GET /documents`, `GET /documents/{id}` (`src/api/routes/knowledge.py`), montadas em `src/main.py` sob o mesmo prefixo `/api` de todo o resto da plataforma.
- Interface administrativa mínima (`web/administracao/documentos`): upload (texto/markdown), lista com status/chunk_count, reindexação explícita — mesmo padrão de Convites/Sessões/API Keys.
- Dependência nova adicionada: `python-multipart` (requisito do FastAPI para `UploadFile`/`Form` — biblioteca companion padrão do próprio framework já em uso, não um novo provider/SDK).

---

## Arquivos alterados

**Backend**
- `alembic/versions/0020_w5_0_document_ingestion.py` (novo)
- `src/services/knowledge_platform/types.py` — `chunk_count`/`created_at` aditivos
- `src/services/knowledge_platform/knowledge_repository.py` — `chunk_count` computado em `get_document()`/`list_versions()`; novo `list_documents()`
- `src/services/knowledge_platform/document_ingestion_service.py` (novo)
- `src/database/administration_repository.py` — `list_audit_log()` ganha filtros opcionais
- `src/services/administration_service.py` — passthrough do filtro
- `src/api/routes/knowledge.py` (novo)
- `src/main.py` — registro do `knowledge_router`
- `requirements.txt` — `python-multipart`

**Testes backend**
- `tests/test_migration_0020_w5_0_document_ingestion.py` (novo)
- `tests/test_knowledge_platform.py` — 4 testes novos (`chunk_count`, `list_documents`)
- `tests/test_document_ingestion_service.py` (novo) — inclui **Teste B** mandatado
- `tests/test_documents_api.py` (novo) — inclui **Teste A** e **Teste B** mandatados, na camada HTTP real
- `tests/test_administration_api.py`/`tests/test_administration_repository.py` — 2 asserções pré-existentes atualizadas (viewer agora também tem `knowledge.read`, exatamente como a migração 0020 define)

**Frontend**
- `web/lib/domain/document.ts` + `document.test.ts` (novos)
- `web/lib/hooks/use-admin-documents.ts`, `use-admin-document-mutations.ts` (novos)
- `web/app/api/bff/admin/documents/route.ts` (+ `route.test.ts`), `[id]/route.ts`, `[id]/reindex/route.ts` (novos)
- `web/app/administracao/documentos/page.tsx`, `upload-document-dialog.tsx`, `reindex-document-button.tsx` (novos)
- `web/components/shell/navigation.ts` + `navigation.test.ts` — entrada "Documentos"

**Governança**
- `docs/architecture/TECHNICAL_DEBT.md` — TD-014 (Evidence Confidence, Deferred) + nota de atualização em TD-012
- `docs/product/stratech-v2/DECISION-LOG.md` — D-090 (Decision Proposal "Knowledge Version Resolution" registrada)
- `CHANGELOG.md`, `web/lib/mock/mission-control-data.ts` — espelhados

---

## Migração

`0020_w5_0_document_ingestion.py` — puramente aditiva. Testada em PostgreSQL real: upgrade a partir de `0019` seeda `knowledge.read` (4 papéis) e `knowledge.write` (3 papéis); downgrade remove ambas sem deixar `role_permissions` órfão; re-upgrade não duplica linhas (`tests/test_migration_0020_w5_0_document_ingestion.py`).

---

## Arquitetura impactada

Nenhuma. `AdvisorFramework`/`AIContextEngine`/`Evidence`/`RecommendationEngine` permanecem byte-a-byte inalterados — confirmado por `git diff` vazio nesses arquivos ao longo de toda a implementação. `document.indexed` → `EventDispatcher` → `WorkflowRuntime` → `workflow_executions` permanece exatamente como entregue no Epic W4-4 — nenhuma linha desses componentes foi tocada; a implementação apenas adicionou o caminho HTTP até `KnowledgeRepository.ingest()`/`.index()`, que já existiam desde a Wave 3.

---

## Testes executados e resultados

| Suíte | Resultado |
|---|---|
| Backend completo (`pytest`) | **539 passed**, 0 failed |
| Frontend completo (`vitest`) | **503 passed** (69 arquivos) |
| `ruff check src tests` | Limpo |
| `npx tsc --noEmit` | Limpo |
| `npx eslint .` | Limpo |

**Teste A — Isolamento organizacional completo** (`tests/test_documents_api.py::TestOrganizationalIsolation`, `tests/test_document_ingestion_service.py::TestOrganizationalIsolation`): documento da Organização A retorna 404 em `GET /documents/{id}` e `POST /documents/{id}/reindex` para a Organização B; nunca aparece em `GET /documents` de B; permanece visível para A. Confirmado tanto na camada HTTP real quanto na camada de serviço.

**Teste B — Fluxo ponta a ponta sem intervenção manual** (`tests/test_documents_api.py::TestEndToEndChain`, `tests/test_document_ingestion_service.py::TestEndToEndChain`): uma chamada real a `POST /documents` (e, na variante de serviço, `service.upload()`) produz uma linha `workflow_executions.status="completed"` com o `correlation_id` propagado e `error=None` — nenhuma chamada direta a `EventDispatcher`/`WorkflowRuntime` no teste, comprovando que upload→ingest→index→`document.indexed`→Workflow Runtime→Execution Tracking já funciona de ponta a ponta sem nenhum código novo nesse trecho.

**Achado de regressão corrigido durante a verificação:** a suíte completa revelou que a migração 0020 (`knowledge.read` para o papel `viewer`) invalidava a asserção literal de dois testes pré-existentes (`test_administration_api.py::TestRoles::test_list_role_permissions`, `test_administration_repository.py::TestRoles::test_list_permissions_for_role_matches_migration_0006_and_0010`), que fixavam o conjunto exato de permissões do `viewer`. Corrigido incluindo `knowledge.read` no conjunto esperado — consequência correta e prevista da migração aprovada, não uma regressão real; o segundo teste foi renomeado para `..._matches_migration_0006_0010_and_0020` para refletir a proveniência, seguindo a mesma convenção já usada no nome anterior.

---

## Critérios de aceite do Technical Design (§8) — confirmação

1. ✅ `POST /documents` responde citando `document_id`/`chunk_count` reais.
2. ✅ Falha de indexação retorna estado parcial explícito (`status: "failed"`), nunca escondida; retry via `POST /documents/{id}/reindex` funcional.
3. ✅ Nenhuma alteração a `AdvisorFramework.run()`/`AIContextEngine`/`RagPipeline` além do estritamente planejado (nenhuma, nesta Epic).
4. ✅ `ruff check src tests` limpo; suíte completa verde; testes cobrindo evidência com citação, estado de falha, isolamento de tenant, citação inválida (N/A nesta Epic — não há Advisor aqui).
5. Opção 1 do §5 do Technical Design (rota de ingestão) — implementada.

---

## Riscos residuais (reconfirmados do Technical Design, nenhum resolvido nem escondido)

1. Chunks de versões antigas de um documento reingerido permanecem pesquisáveis via RAG — **Decision Proposal "Knowledge Version Resolution" registrada (D-090)**, não resolvida nesta Epic.
2. `confidence` em `Evidence` — **TD-014, Deferred**, registrado no Technical Debt.
3. Formato de conteúdo limitado a texto/markdown — nenhum parser de PDF/binário introduzido (TD-012 reconfirmado, não resolvido).
4. Naming `knowledge.write`/`knowledge.read` — confirmado definitivo pelo Founder (D-090).

Nenhum risco bloqueia o encerramento do Epic.

---

## Confirmação de encerramento

Todos os critérios de aceite atendidos. Nenhuma expansão de escopo além do autorizado. Nenhuma responsabilidade de Advisor introduzida. **Recomendação: GO para o encerramento do Epic W5-0.**

Per instrução explícita do Founder: retorno obrigatório para Executive Review antes de qualquer trabalho do W5-1 (Document Advisor) — nenhum código desse Epic foi iniciado ou antecipado.
