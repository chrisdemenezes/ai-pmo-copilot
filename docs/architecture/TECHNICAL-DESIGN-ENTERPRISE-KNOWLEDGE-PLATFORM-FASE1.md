# Technical Design — Enterprise Knowledge Platform, Fase 1 (Foundation)

**Escopo exato** (per `WAVE-3-EXECUTION-PLAN.md` §2, W3-6a): Document Ingestion + Parsing + Chunking + Embeddings + Vector Store (`pgvector`) + Knowledge Repository. Entregável: `KnowledgeRepository`/`VectorRepository`/`EmbeddingProvider` funcionais e testados, **sem nenhum Advisor consumidor ainda** — o mesmo padrão já usado pela Digital PMO Intelligence Foundation antes do Risk Advisor consumi-la.
**Base aprovada:** `WAVE-3-DOMAIN-BLUEPRINT.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md`, `AR-6-WAVE-3-DOMAIN-BLUEPRINT-REVIEW.md` (aprovado sem ressalvas), `WAVE-3-SUCCESS-CRITERIA.md` §1 (Definition of Done da Fase 1).
**Data:** 2026-07-27.

---

## 1. Pré-requisito de infraestrutura: extensão `pgvector`

`pgvector` é uma extensão nativa do PostgreSQL (não um serviço externo) — precisa existir no binário do servidor antes de qualquer `CREATE EXTENSION`. `CREATE EXTENSION` exige privilégio de superusuário no Postgres vanilla (a extensão não é declarada `trusted`), enquanto o papel `aipmo` (usado pela aplicação e pelos testes, `scripts/rc2-db.sh`) é deliberadamente **não superusuário** (princípio de menor privilégio já estabelecido).

**Solução, sem elevar o privilégio do papel da aplicação:** instalar a extensão **uma única vez em `template1`**, como superusuário, durante o provisionamento (`scripts/rc2-db.sh`, ação `create`, que já roda como superusuário via `_admin_psql`). Todo banco criado a partir de `template1` (o banco `aipmo` real **e** cada banco efêmero de teste criado por `tests/db.py::temp_database_url`, que não passa `TEMPLATE` explícito e portanto usa `template1` por padrão) **herda a extensão automaticamente**, sem que `aipmo` precise de privilégio algum. A migração do Alembic (`CREATE EXTENSION IF NOT EXISTS vector`) roda como `aipmo` e passa a ser um no-op idempotente (a extensão já existe), preservando o padrão de toda migração ser auto-suficiente e não depender de um passo externo silencioso — a idempotência é o que garante que rodar a migração num ambiente que **não** seguiu este provisionamento (ex.: um Postgres gerenciado que já marca `vector` como trusted, ou onde a extensão já vem instalada) simplesmente funcione sem exigir o passo do `template1`.

**Verificado nesta sessão, em Postgres 16 real:** `CREATE EXTENSION vector` em `template1` (como superusuário) + `CREATE DATABASE` subsequente (como `aipmo`, sem privilégio adicional) resulta em um banco com `vector` já disponível; `CREATE EXTENSION IF NOT EXISTS vector` executado por `aipmo` nesse banco sucede como no-op; consultas de distância (`<->`) funcionam.

**Mudanças de infraestrutura (não de domínio, per Princípio 1 do documento mestre):**
- `scripts/rc2-db.sh` (ação `create`): novo passo idempotente `CREATE EXTENSION IF NOT EXISTS vector` em `template1`, via a mesma função `_admin_psql` já existente (nenhuma lógica de conexão nova).
- `.github/workflows/ci.yml` e `docker-compose.yml`: imagem do serviço Postgres trocada de `postgres:16` para `pgvector/pgvector:pg16` (mesma imagem `postgres:16` oficial, com o binário da extensão pré-instalado — projeto oficial do `pgvector`). Nesses dois ambientes o papel `aipmo` já é o superusuário do container (comportamento padrão da imagem Docker do Postgres), então nenhum passo de `template1` é necessário ali — a migração cuida de tudo.
- `requirements.txt`: nova dependência `pgvector>=0.5.0` (biblioteca cliente Python, integração SQLAlchemy — **não é um novo provider/registry**, é o tipo de coluna `Vector` usado exclusivamente dentro de `PgVectorRepository`, nunca importado por um Advisor ou serviço de domínio).

---

## 2. Novo pacote: `src/services/knowledge_platform/`

Mesma árvore já oficial (`src/services/`), mesmo padrão de `ai_foundation/` (Wave 2/W3-2) — subpacote, não uma nova raiz.

```
src/services/knowledge_platform/
  __init__.py
  types.py                 # dataclasses: IngestedDocument, DocumentVersionInfo, ScoredChunk
  embedding_provider.py    # EmbeddingProvider(Protocol) + MockEmbeddingProvider + get_embedding_provider()
  vector_repository.py     # VectorRepository(Protocol) + PgVectorRepository (pgvector-backed)
  knowledge_repository.py  # KnowledgeRepository -- fachada única (ingest/index/search/get_document/list_versions)
```

### 2.1 `embedding_provider.py`

```python
class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...

class MockEmbeddingProvider:
    """Determinístico: mesmo texto -> mesmo vetor, sempre. Hash estável do
    texto normalizado, projetado em EMBEDDING_DIM floats em [-1, 1]. Nenhuma
    chamada de rede, nenhuma dependência externa -- mesmo papel que
    MockLLMProvider já cumpre para LLMProvider."""

def get_embedding_provider() -> EmbeddingProvider:
    """Mesma factory por env var já usada por get_provider() (LLM) --
    EMBEDDING_PROVIDER=mock (default). Nenhum valor "production" é
    registrado nesta Fase: não existe hoje nenhum backend de embeddings real
    integrado ao projeto (o único provedor externo já presente,
    `anthropic>=0.34.0`, não expõe uma API pública de embeddings). Escolher
    esse backend é uma decisão de Technical Design explicitamente diferida
    pelo próprio Blueprint (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md`
    §1.4) -- fica como item aberto para quando um Advisor real consumir RAG
    (Fase 2, Document Advisor de referência), o mesmo padrão que W3-2 seguiu
    ao só justificar a Foundation quando o Risk Advisor virou consumidor
    real. Chamar `get_embedding_provider()` com um valor não suportado
    levanta erro explícito, nunca um fallback silencioso."""
```

`EMBEDDING_DIM = 16` (constante do módulo) — dimensão pequena, suficiente para provar a integração `pgvector` (armazenamento, índice, busca por distância) nesta Fase, sem comprometer com uma dimensão real de produção antes de a Fase 2 escolher um backend de verdade. A coluna `Vector` da migração usa a mesma constante.

### 2.2 `vector_repository.py`

```python
class VectorRepository(Protocol):
    def upsert_vector(self, chunk_id: int, embedding: list[float]) -> None: ...
    def similarity_search(self, organization_id: int, query_embedding: list[float], top_k: int) -> list[ScoredChunk]: ...

class PgVectorRepository:
    """Única classe do projeto ciente de `pgvector`. Recebe uma Session via
    construtor (mesmo padrão de injeção de dependência de
    AnalysisRepository/DomainRepository). similarity_search usa
    Chunk.embedding.cosine_distance(query_embedding), sempre filtrado por
    organization_id (Princípio 6) -- nenhuma busca cross-tenant possível."""
```

### 2.3 `knowledge_repository.py`

```python
class KnowledgeRepository:
    """Fachada única do domínio para a Knowledge Platform (contrato definido
    em DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md §2). Compõe
    EmbeddingProvider + VectorRepository + persistência de
    Document/DocumentVersion/Chunk -- nenhum chamador externo enxerga essas
    três peças separadamente.

    def ingest(self, organization_id: int, source_name: str, text: str, project_id: int | None = None) -> IngestedDocument: ...
    def index(self, document_id: int) -> None: ...  # parsing (Fase 1: passthrough de texto já normalizado) -> chunking -> embeddings -> upsert_vector
    def search(self, organization_id: int, query: str, top_k: int = 5) -> list[ScoredChunk]: ...
    def get_document(self, organization_id: int, document_id: int) -> IngestedDocument | None: ...
    def list_versions(self, organization_id: int, document_id: int) -> list[DocumentVersionInfo]: ...
    """
```

**Chunking na Fase 1:** estratégia mínima e determinística — divide o texto normalizado em janelas de tamanho fixo (`CHUNK_SIZE_CHARS`, constante do módulo) com sobreposição pequena, preservando o offset de origem em cada chunk (per `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.3 — toda citação aponta a um trecho real). Refinamento de ranking/contexto fica para `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`, fora do escopo desta Fase.

**Parsing na Fase 1:** aceita texto já normalizado (`str`); parsing de formatos binários (PDF etc., §1.2 do Blueprint) fica fora do escopo desta Fase — nenhum Advisor ainda ingere documentos reais, então não há necessidade comprovada de um parser de PDF agora (mesmo princípio de "grounding em consumidor real" já aplicado à Foundation).

---

## 3. Modelo de dados — `src/database/models.py`

Todo entity ORM do projeto vive centralmente em `models.py` (`Organization`, `Project`, `ApiKey`, `UserSession`, `Invitation`, `AuditLog` etc. -- nenhum precedente de um arquivo de modelo por feature). Reutilizando esse padrão exatamente: `Document`, `DocumentVersion`, `Chunk` são adicionadas como mais 3 classes em `models.py`, não em um módulo novo -- nenhuma arquitetura paralela de persistência.

| Tabela | Colunas-chave | Observação |
|---|---|---|
| `documents` | `id`, `organization_id` (NOT NULL, FK), `project_id` (nullable, FK) , `source_name`, `created_at` | `project_id` é metadado opcional, nunca chave — mesma disciplina definitiva de TD-008 (nunca `project_name`). |
| `document_versions` | `id`, `document_id` (FK), `content`, `created_at` | Uma linha por (re)ingestão; nunca sobrescrita (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.10). |
| `chunks` | `id`, `document_version_id` (FK), `organization_id` (NOT NULL, FK, desnormalizado do documento para permitir filtro direto na busca vetorial sem join), `chunk_index`, `text`, `embedding` (`Vector(16)`) | `organization_id` desnormalizado é a mesma técnica já aplicada a `AnalysisRecord.organization_id` para permitir escopo direto sem join adicional. |

Todas as tabelas seguem o padrão já estabelecido (`Column`, `ForeignKey`, índice em toda FK/`organization_id`) — nenhum padrão novo de modelagem introduzido.

---

## 4. Migração `0016_enterprise_knowledge_platform_foundation.py`

- **Upgrade:** `CREATE EXTENSION IF NOT EXISTS vector` (idempotente, ver §1) → `create_table` para `documents`, `document_versions`, `chunks` (com a coluna `embedding` usando o tipo `Vector` de `pgvector.sqlalchemy`) → índices em `organization_id`/FKs.
- **Downgrade:** `drop_table` das 3 tabelas, na ordem inversa de dependência. **Não remove a extensão `vector`** — é um recurso compartilhado do banco (mesmo princípio de nunca remover algo que outra estrutura possa depender, e custo de manter instalada é nulo); documentado explicitamente no docstring da migração para não surpreender uma auditoria futura.
- **Aditiva por completo** — nenhuma tabela/coluna existente é tocada. Não se aplica o padrão dual-key de TD-008 (não há dado legado a migrar); é simplesmente uma nova capability, testada em PostgreSQL real (upgrade + downgrade) como todas as migrações desde RC-2.

---

## 5. Testes

- `tests/test_migration_0016_knowledge_platform.py` — upgrade cria as 3 tabelas + a extensão; downgrade remove as 3 tabelas (extensão permanece); round-trip completo, banco efêmero real (`tests/db.py`).
- `tests/test_knowledge_platform.py` — `MockEmbeddingProvider` determinístico (mesmo texto → mesmo vetor); `PgVectorRepository` upsert + busca por similaridade, com teste de isolamento cross-tenant (dado de outra `organization_id` nunca retorna); `KnowledgeRepository.ingest`→`index`→`search` round-trip (uma pergunta cujo texto é semelhante a um chunk ingerido recupera esse chunk primeiro).
- `ruff check src tests` + `pytest` completos, sem novo skip.

---

## 6. Não-escopo explícito desta Fase (reafirmado)

- Nenhum Advisor consome esta plataforma ainda (busca global deve confirmar zero referência de `src/agents/` a `knowledge_platform`).
- Nenhum RAG Pipeline, ranking ou grounding — isso é `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`, Fase 2.
- Nenhum Enterprise Memory Model — Fase 2.
- Nenhuma decisão de backend de embeddings de produção — item aberto, sinalizado para a Fase 2 quando o Document Advisor (consumidor de referência) precisar de um.
- Nenhum parser de documento binário (PDF etc.) — sem consumidor real ainda que o exija.

---

## 7. Arquivos alterados/criados (checklist)

**Infraestrutura**
- `scripts/rc2-db.sh` (alterado — passo de `template1`)
- `.github/workflows/ci.yml` (alterado — imagem `pgvector/pgvector:pg16`)
- `docker-compose.yml` (alterado — imagem `pgvector/pgvector:pg16`)
- `requirements.txt` (alterado — `pgvector>=0.5.0`)

**Backend**
- `src/database/models.py` (alterado — 3 novas classes: `Document`, `DocumentVersion`, `Chunk`)
- `alembic/versions/0016_enterprise_knowledge_platform_foundation.py` (novo)
- `src/services/knowledge_platform/__init__.py` (novo)
- `src/services/knowledge_platform/types.py` (novo)
- `src/services/knowledge_platform/embedding_provider.py` (novo)
- `src/services/knowledge_platform/vector_repository.py` (novo)
- `src/services/knowledge_platform/knowledge_repository.py` (novo)

**Testes**
- `tests/test_migration_0016_knowledge_platform.py` (novo)
- `tests/test_knowledge_platform.py` (novo)

**Nenhum arquivo de frontend, rota de API, ou Advisor é tocado nesta Fase** — consistente com "sem nenhum Advisor ainda os consumindo" (Definition of Done da Fase 1, `WAVE-3-SUCCESS-CRITERIA.md` §1).
