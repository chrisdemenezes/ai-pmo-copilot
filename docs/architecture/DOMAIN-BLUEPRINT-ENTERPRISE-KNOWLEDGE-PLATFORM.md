# Domain Blueprint — Enterprise Knowledge Platform

**Status:** Blueprint subordinado a `WAVE-3-DOMAIN-BLUEPRINT.md` (documento mestre da Wave 3). Nenhum Epic é implementado por este documento.
**Autorização:** Decisão Estratégica do Founder (2026-07-27) — adoção de Vector Store, implementação inicial aprovada `pgvector`, sempre atrás de uma abstração de domínio.
**Precedente:** `ADR-V2-005` já havia aprovado uma camada de referência de Document Intelligence (não GED nativo), escopada para Release 0.4 e nunca implementada (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §5.2). Este Blueprint substitui esse escopo pendente por um desenho completo e o eleva a infraestrutura oficial da Wave 3 — não há conflito, apenas a primeira concretização.

---

## 0. Escopo e não-escopo

**Escopo:** os 13 sub-itens mandatados pelo Founder — Document Ingestion, Parsing, Chunking, Embeddings, Indexação, Vector Store (pgvector), Semantic Search, RAG Pipeline, Knowledge Repository, Versionamento do conhecimento, Atualização incremental, Políticas de retenção, Estratégia de cache.

**Não-escopo (explícito):**
- Nenhum Enterprise Advisor é implementado aqui — Advisors apenas **consomem** esta plataforma (ver `ENTERPRISE-ADVISOR-CATALOG.md` e `WAVE-3-INTEGRATION-BLUEPRINT.md`).
- Nenhuma classificação de memória (documental/operacional/decisão/aprendizado/organizacional) — isso é `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md`, uma camada que **classifica e organiza** o conteúdo já indexado aqui, nunca uma segunda plataforma de indexação.
- Nenhum detalhe de ranking/grounding/qualidade de resposta do RAG — isso é `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`; este documento define apenas o **Pipeline** como componente de infraestrutura (§2.8), não sua estratégia de recuperação.
- Nenhuma substituição da Digital PMO Intelligence Foundation (`AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`) — a Knowledge Platform é uma **segunda fonte de evidência**, adicionada ao lado da já existente (`WAVE-3-DOMAIN-BLUEPRINT.md` §5.2), nunca sua substituta.

---

## 1. Componentes

### 1.1 Document Ingestion
Ponto de entrada de qualquer fonte de conhecimento corporativo (upload de documento, exportação de reunião, conteúdo textual já existente no domínio — ex.: `AnalysisRecord`, decisões, lições aprendidas). Responsabilidade única: aceitar um documento bruto, atribuí-lo a uma organização (`organization_id`, mesma disciplina de `AnalysisRecord`/`Portfolio`/`Program`/`Project`) e a uma fonte rastreável, e entregá-lo ao Parsing. Não interpreta conteúdo, não decide relevância — isso é responsabilidade de camadas posteriores.

### 1.2 Parsing
Converte o documento bruto (PDF, texto, transcrição, markdown) em texto estruturado normalizado. Falha de parsing é um estado de primeira classe (documento rejeitado com motivo registrado), nunca um valor vazio silencioso — mesmo princípio de tratamento de exceções explícito do CLAUDE.md.

### 1.3 Chunking
Divide o texto normalizado em unidades menores (chunks) adequadas à geração de embeddings. Cada chunk preserva referência ao documento de origem e à posição/offset original, para que uma citação (§2.8, RAG Pipeline) sempre aponte a um trecho real, nunca a um documento inteiro — o mesmo anti-hallucination guard já aplicado a `analysis_id` em `RecommendationEngine.build()` se estende a `chunk_id`.

### 1.4 Embeddings
Serviço que transforma um chunk de texto em um vetor numérico. Acessado exclusivamente através de uma abstração própria (`EmbeddingProvider`, análogo em forma a `LLMProvider(Protocol)` — um único método, ex. `embed(text: str) -> list[float]`), nunca chamando um SDK de terceiro diretamente do domínio ou do Advisor. Se o provedor de embeddings vier a ser o mesmo `ProductionLLMProvider`/`MockLLMProvider` já existente ou um provider dedicado é decisão de Technical Design, não deste Blueprint — mas em nenhum dos dois casos surge um Model Registry ou Provider Router novos (Princípio 5, `WAVE-3-DOMAIN-BLUEPRINT.md` §2).

### 1.5 Indexação
Processo que grava o vetor de um chunk, junto de seus metadados (`organization_id`, `document_id`, `chunk_id`, versão), no Vector Store. É a única operação de escrita no armazenamento vetorial — nunca acessada diretamente por um Advisor, sempre através do `KnowledgeRepository` (§3).

### 1.6 Vector Store (pgvector)
Implementação inicial aprovada pelo Founder. Estende o Postgres já oficial (RC-2/D-037) com a extensão `pgvector` — **não é uma infraestrutura de banco nova**, é uma extensão do banco já existente, seguindo o mesmo Postgres que hoje serve `Portfolio`/`Program`/`Project`/`AnalysisRecord`. Nenhum componente de domínio ou de Advisor referencia `pgvector` por nome ou por SQL de similaridade vetorial diretamente — sempre via `KnowledgeRepository`/`VectorRepository` (Princípio 2, `WAVE-3-DOMAIN-BLUEPRINT.md` §2), preparando substituição futura sem impacto no domínio.

### 1.7 Semantic Search
Operação de leitura que, dado um texto de consulta, retorna os chunks mais relevantes por similaridade vetorial, sempre escopada por `organization_id` (Princípio 6) — nunca uma busca cross-tenant. Serve tanto o RAG Pipeline (uso automático, dentro de uma resposta de Advisor) quanto, potencialmente, uma futura busca explícita do usuário (fora do escopo desta Wave — não implementado, apenas não excluído pela arquitetura).

### 1.8 RAG Pipeline
Compõe Semantic Search + os chunks recuperados em evidência utilizável por um Advisor, entregando-a ao mesmo ponto de composição de prompt já usado pela Foundation (`render_analyst_prompt`) como uma **segunda fonte de evidência**, ao lado de `AIContextEngine.gather()` — nunca a substituindo (`WAVE-3-DOMAIN-BLUEPRINT.md` §5.2). O detalhamento de ranking, contexto e grounding é objeto de `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`; aqui o Pipeline é definido apenas como o componente de infraestrutura que existe entre Semantic Search e o Advisor.

### 1.9 Knowledge Repository
A abstração central da plataforma (`KnowledgeRepository`, podendo expor um sub-contrato `VectorRepository` para as operações estritamente vetoriais). Único ponto de acesso a documentos, chunks, embeddings e metadados de versão — análogo em papel a `AnalysisRepository` no Enterprise Domain. Nenhum SQL de Vector Store aparece fora desta classe.

### 1.10 Versionamento do conhecimento
Todo documento reingerido gera uma nova versão, nunca uma sobrescrita silenciosa — o `Knowledge Repository` mantém histórico suficiente para saber qual versão de um chunk fundamentou uma citação passada (auditabilidade, Princípio do Advisor Framework, ver `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md`). Mesma disciplina de nunca perder rastreabilidade já aplicada por `AIFoundationAudit`.

### 1.11 Atualização incremental
Reingestão de uma fonte já conhecida reprocessa apenas o que mudou (novo conteúdo desde a última versão), não a base inteira — decisão de eficiência, não de arquitetura de domínio; o contrato do `KnowledgeRepository` não muda entre uma ingestão completa e uma incremental, apenas o volume processado.

### 1.12 Políticas de retenção
Toda organização tem uma política de retenção de conhecimento indexado (por quanto tempo uma versão obsoleta permanece consultável antes de expirar). É configuração por `organization_id`, nunca um valor global fixo no código — mesmo padrão multi-tenant já aplicado a RBAC/Tenant Isolation (Security Hardening Gate, D-045).

### 1.13 Estratégia de cache
Resultados de Semantic Search para uma mesma consulta recente podem ser cacheados, mas o cache nunca substitui a leitura do Vector Store como fonte de verdade — é uma otimização de latência, invalidada por qualquer nova indexação ou atualização incremental sobre os documentos envolvidos. Nenhum cache de embeddings substitui o registro persistido no Vector Store; cache é sempre descartável sem perda de conhecimento.

---

## 2. Abstração e contrato (`KnowledgeRepository`)

```
KnowledgeRepository (Protocol/ABC — análogo em papel a AnalysisRepository)
  - ingest(organization_id, source) -> Document
  - index(document) -> None                 # Parsing→Chunking→Embeddings→Indexação
  - search(organization_id, query, top_k) -> list[ScoredChunk]
  - get_document(organization_id, document_id) -> Document | None
  - list_versions(organization_id, document_id) -> list[DocumentVersion]

VectorRepository (sub-contrato, usado internamente por KnowledgeRepository)
  - upsert_vector(chunk_id, embedding, metadata) -> None
  - similarity_search(organization_id, query_embedding, top_k) -> list[ScoredChunk]

EmbeddingProvider (Protocol, análogo a LLMProvider)
  - embed(text: str) -> list[float]
```

Nenhum Advisor, rota de API ou serviço de domínio importa `pgvector`, driver de banco vetorial ou SDK de embeddings diretamente — todos consomem `KnowledgeRepository`. A implementação concreta (`PgVectorKnowledgeRepository`, nome de Technical Design, não deste Blueprint) é a única classe ciente de `pgvector`.

---

## 3. Modelo de dados (nível de Blueprint, não de schema)

Toda entidade nova desta plataforma carrega `organization_id`, seguindo exatamente a disciplina já estabelecida por `Portfolio`/`Program`/`Project`/`AnalysisRecord`:

| Entidade (conceitual) | Chave de escopo | Observação |
|---|---|---|
| `Document` | `organization_id` | Fonte ingerida; pode referenciar um `project_id` opcional (metadado, não obrigatório) |
| `DocumentVersion` | `organization_id` + `document_id` | Uma linha por reingestão; nunca sobrescrita |
| `Chunk` | `organization_id` + `document_id` + `document_version_id` | Unidade de embedding e de citação |
| `Embedding`/vetor (`pgvector`) | `organization_id` + `chunk_id` | Armazenado via `VectorRepository`, nunca lido fora dele |

Qualquer introdução real de tabela segue o padrão aditivo-primeiro já validado por TD-008 (Wave 2): nova tabela/coluna primeiro, nenhuma migração destrutiva de dado já em produção sem o mesmo rigor de condições aplicado à Etapa 4b (downgrade íntegro, testado em Postgres real, validado pelo Founder).

---

## 4. Integração com a Foundation e os Advisors

A Knowledge Platform nunca é chamada diretamente por um usuário final ou por uma rota de API fora do fluxo de um Advisor — ela é consumida (a) pelo RAG Pipeline dentro do fluxo de resposta de um Advisor (`WAVE-3-DOMAIN-BLUEPRINT.md` §5.2) e (b) potencialmente pelo Enterprise Memory Model, que classifica e organiza o conteúdo já indexado aqui sem duplicar o mecanismo de indexação. O detalhamento de como cada domínio existente (Portfolio, Program, Project, Decision Center, Actions, Risks, Lessons Learned, Workspace) alimenta ou consome esta plataforma é objeto de `WAVE-3-INTEGRATION-BLUEPRINT.md`.

---

## 5. Critérios de evolução específicos desta camada

1. **Nenhum segundo Vector Store.** Uma eventual substituição de `pgvector` ocorre atrás de `VectorRepository`, nunca como um segundo provider ao lado do primeiro (Princípio 2 do documento mestre).
2. **Nenhum componente novo desta plataforma acessa Postgres fora de `KnowledgeRepository`.** Mesma disciplina de seam única já usada por `AnalysisRepository.resolve_scope_id` no Enterprise Domain.
3. **Toda nova política de retenção ou estratégia de cache é configuração, nunca lógica condicional espalhada** pelo código dos Advisors — vive inteiramente dentro da implementação do `KnowledgeRepository`.
4. **Nenhuma extensão desta plataforma introduz um Model Registry, Provider Router ou Prompt Versioning** — `EmbeddingProvider`/`LLMProvider` permanecem os únicos contratos de modelo (Princípio 5 do documento mestre).
5. **Esta plataforma é infraestrutura por definição** — se qualquer extensão futura começar a modelar uma decisão de negócio (ex.: "quais documentos importam para o Portfolio X"), essa lógica pertence a um Enterprise Advisor ou ao Enterprise Memory Model, nunca a este Blueprint.
