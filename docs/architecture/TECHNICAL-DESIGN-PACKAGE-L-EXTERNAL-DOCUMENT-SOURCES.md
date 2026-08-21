# Technical Design — Package L: External Document Sources

STRATECH V1 Product & Capability Completion (Founder Mandate), Fase 4.

## 1. Contexto real (audit, não hipótese)

- `Document`/`DocumentVersion`/`Chunk` (`src/database/models.py`) já são o
  modelo estável do Knowledge Platform (Wave 3/5) -- versionamento por linha
  nova em `DocumentVersion`, nunca sobrescrita.
- `DocumentIngestionService.upload(organization_id, user_id, source_name,
  text, correlation_id, project_id)` (`document_ingestion_service.py`) já é
  o único caminho real de ingestão -- hoje alimentado exclusivamente por
  `POST /api/documents` (upload manual de arquivo).
- `EmbeddingProvider` (`embedding_provider.py`) já estabelece o padrão a
  seguir: um `Protocol`, um adaptador Mock, um adaptador real via `httpx`,
  nunca acoplado a um único provedor. Este pacote replica exatamente esse
  padrão para a origem do texto, não para o embedding.

## 2. Contrato mínimo

`src/services/knowledge_platform/external_sources.py` (novo):

- `ExternalDocumentContent` -- `source_name`, `text`, `provider`,
  `external_reference`, `fetched_at`. Exatamente o shape que
  `upload()` já aceita, mais proveniência.
- `ExternalDocumentSource` (`Protocol`) -- `fetch(reference: str) ->
  ExternalDocumentContent`.
- `HttpUrlDocumentSource` -- primeiro (e único, por mandato) adaptador:
  busca uma URL via `httpx`, streaming, com o mesmo teto de tamanho já
  aplicado ao upload manual (`max_upload_size_bytes()`, injetado pelo
  chamador -- este módulo nunca importa `src.api`). Sem credencial, sem
  vínculo a um provedor SaaS específico.

Um adaptador para um provedor SaaS real (SharePoint, Google Drive,
Confluence) é **REAL PROVIDER VALIDATION = PENDING EXTERNAL CREDENTIAL** --
não implementado aqui: exigiria uma credencial real que não existe neste
ambiente (mandato, condição de STOP #12 -- uso de credencial real não
autorizada).

## 3. Serviço

`DocumentIngestionService.ingest_from_external_source(organization_id,
user_id, source, reference, correlation_id, project_id=None,
source_name=None)`: chama `source.fetch()`, então reaproveita `upload()`
literalmente (mesmo Document/DocumentVersion/Chunk, mesma indexação, mesmo
`DocumentIndexingError` em caso de falha de indexação). Proveniência
(`provider`/`external_reference`/`fetched_at`) é registrada apenas na
trilha de auditoria já existente (`record_audit`), nunca uma coluna nova em
`Document`/`DocumentVersion` -- preserva o modelo e o versionamento
intactos.

## 4. API + BFF

- `POST /api/documents/from-url` (`{url, source_name?, project_id?}`) --
  mesma RBAC (`knowledge.write`) do upload manual; 422 se o fetch falhar,
  502 se a indexação falhar (mesmo formato do upload).
- `POST /api/bff/admin/documents/from-url` -- forward JSON simples
  (`forwardDomainRequest`), diferente do upload manual (que precisa de um
  handler multipart dedicado).

## 5. Frontend

`AddDocumentFromUrlDialog` (novo, ao lado de `UploadDocumentDialog` em
`/administracao/documentos`, nunca o substituindo): mesmo padrão de dialog
+ `useMutation`, campo único obrigatório (URL) + nome opcional.

## 6. Testes

- `tests/test_external_document_sources.py` -- `HttpUrlDocumentSource`
  isolado via `httpx.MockTransport` (sem rede real, sem dado corporativo
  real): conteúdo+proveniência, limite de tamanho, conteúdo não-UTF-8,
  conteúdo vazio, erro HTTP.
- `tests/test_documents_api.py::TestFromUrl` -- rota ponta a ponta (mesma
  disciplina de mock de `httpx.stream`), incluindo RBAC (`viewer` não pode).
- Frontend: `page.test.tsx` cobre a presença do novo trigger ao lado do
  upload manual.

## 7. Riscos / Não-Escopo

- Nenhum dado corporativo real é buscado nesta implementação -- toda
  validação usa `httpx.MockTransport`.
- Nenhuma credencial real é usada ou solicitada.
- Um segundo adaptador (SaaS real) permanece como trabalho futuro,
  explicitamente não autorizado a ser implementado neste pacote sem uma
  credencial real disponível.
