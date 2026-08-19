# Technical Design — Enterprise Knowledge Platform, Fase 2 (Knowledge Services)

**Escopo exato** (per `WAVE-3-EXECUTION-PLAN.md` §2, W3-6b, refinado pela Decisão do Founder desta missão): Semantic Search, RAG Pipeline e Enterprise Memory Model, como **serviços de plataforma** — nenhuma lógica específica de Advisor, nenhum Advisor implementado ou consumido nesta Fase. Versionamento/Atualização incremental já foi entregue na Fase 1 (`DocumentVersion`, reingestão sem sobrescrita, provado por `test_reingestion_creates_a_new_version_not_an_overwrite`) — nenhum trabalho adicional necessário aqui.
**Base aprovada:** `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md`, `WAVE-3-SUCCESS-CRITERIA.md` §1 (Definition of Done da Fase 2).
**Diretrizes do Founder para esta Fase (verbatim, operacionalizadas abaixo):** separação rigorosa infraestrutura/domínio; Semantic Search/RAG Pipeline/Enterprise Memory Model como serviços de plataforma sem lógica de Advisor; nenhum Advisor acessa `PgVectorRepository`/armazenamento vetorial diretamente; todo consumo via `KnowledgeRepository` e os serviços da plataforma; resolução de contexto determinística, auditável, documentada, com rastreabilidade de fontes; Decision Log/CHANGELOG/Mission Control/critérios de execução atualizados ao final.

---

## 0. Onde a Fase 2 termina (limite deliberado com o Advisor Framework)

O fluxo completo de resposta de um Advisor (`WAVE-3-DOMAIN-BLUEPRINT.md` §5.2) é: pergunta → Advisor Framework → `AIContextEngine` + RAG Pipeline → `render_analyst_prompt` → `LLMProvider` → `RecommendationEngine`/`ExplanationEngine` → auditoria. **Nenhum desses passos além do RAG Pipeline pertence a esta Fase** — `render_analyst_prompt`, a composição de prompt e a invocação do `LLMProvider` são lógica de Advisor (Fase 3/4). O `RagPipeline` desta Fase termina exatamente onde a Diretriz 2 do Founder exige: entrega um conjunto de evidência já recuperada, ranqueada e rastreável — nunca compõe um prompt, nunca chama um `LLMProvider`, nunca conhece um Advisor específico.

---

## 1. Semantic Search

Já existe como comportamento (`KnowledgeRepository.search()` → `PgVectorRepository.similarity_search()`, Fase 1). Nesta Fase, o único ajuste é fazer `ScoredChunk` carregar a recência da versão (`document_version_created_at`), necessária para o Ranking (§2) — sem introduzir uma segunda classe de busca paralela. `PgVectorRepository.similarity_search()` já faz `JOIN` com `DocumentVersion` (para obter `document_id`); adicionar `DocumentVersion.created_at` à mesma consulta é uma extensão trivial, sem custo adicional de query.

---

## 2. RAG Pipeline (`src/services/knowledge_platform/rag_pipeline.py`)

```python
@dataclass(frozen=True)
class RagContext:
    query: str
    organization_id: int
    chunks: list[ScoredChunk]  # já ranqueados, cada um com chunk_id/document_id reais

    @property
    def chunk_ids(self) -> frozenset[int]: ...  # usado por um futuro grounding check de Advisor


class RagPipeline:
    def __init__(self, knowledge_repository: KnowledgeRepository): ...

    def retrieve(self, organization_id: int, query: str, top_k: int = 5) -> RagContext:
        """Query Embedding + Semantic Search (via KnowledgeRepository.search,
        nunca PgVectorRepository diretamente) -> Ranking -> retorna um
        RagContext auditável e rastreável. Loga organization_id, query,
        quantidade e ids dos chunks retornados (mesma disciplina de
        logging estruturado já usada em toda escrita de repositório do
        projeto -- nenhum subsistema de auditoria novo)."""
```

**Ranking (Blueprint RAG Architecture §3):** ordena por `(score decrescente, recência da versão decrescente)` — o score de similaridade é a chave primária (não há ainda nenhum Advisor real para calibrar um peso diferente disso), a recência da versão desempata quando dois chunks têm relevância semântica equivalente. Nenhuma heurística de peso inventada sem consumidor real para validá-la — mesma disciplina de "grounding em consumidor real" já aplicada à Foundation e a esta própria Fase 1.

**Determinismo (Diretriz 5 do Founder):** com `MockEmbeddingProvider` (determinístico) e um critério de ordenação total e estável, a mesma pergunta sobre o mesmo estado do banco sempre produz o mesmo `RagContext`.

**Auditabilidade e rastreabilidade (Diretriz 5):** `RagContext.chunk_ids` expõe exatamente o conjunto de fontes legítimas para uma citação futura — um Advisor (Fase 3/4) valida toda citação contra esse conjunto antes de apresentá-la (o mesmo anti-hallucination guard já usado por `RecommendationEngine.build()` para `analysis_id`, estendido a `chunk_id`). Cada chamada a `retrieve()` é logada (`logger.info`) com `organization_id`, a pergunta, e os `chunk_id`s retornados.

**Grounding nesta Fase:** trivialmente garantido — `RagContext.chunks` só pode conter o que `KnowledgeRepository.search()` de fato recuperou (nenhuma invenção possível sem um LLM no caminho, que só entra em cena na Fase 3/4). O "grounding check" que a Blueprint descreve (verificar que uma citação gerada corresponde a um chunk realmente recuperado) é responsabilidade do futuro Advisor, usando `RagContext.chunk_ids` como a fonte da verdade — esta Fase entrega a estrutura que torna esse check possível, não o check em si (que não existe sem um Advisor).

---

## 3. Enterprise Memory Model (`src/services/knowledge_platform/enterprise_memory_service.py`)

### 3.1 Revalidação obrigatória da checklist §0 (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md`)

Antes de qualquer código: `EnterpriseMemoryService` é backend, persistido, classifica documentos já ingeridos pela Knowledge Platform, consumido por futuros Advisors — `Executive Memory` (`web/lib/executive-memory/memory-insights.ts`) permanece frontend, stateless, sem persistência, consumida pela UI do Workspace/Dashboard. Nenhuma sobreposição de mecanismo, camada ou consumidor. **Nenhum arquivo de `Executive Memory` é tocado nesta Fase.** Checklist revalidada e ainda verdadeira.

### 3.2 Escopo desta Fase (mínimo, sem lifecycle especulativo)

Do ciclo de vida completo do Blueprint (Captura → Classificação → Consulta → Consolidação → Expiração), esta Fase entrega **Captura + Classificação + Consulta** — o suficiente para que um futuro Advisor classifique e consulte memória real. **Consolidação** (promoção a memória organizacional) e **Expiração automática** ficam explicitamente fora do escopo: não há hoje nenhum consumidor real que precise delas, e construí-las agora seria especulação sem grounding (mesmo princípio já aplicado à Foundation em W3-2/AR-3 e reafirmado na Fase 1 para o backend de embeddings de produção).

```python
class MemoryCategory(str, Enum):
    DOCUMENTAL = "documental"
    OPERACIONAL = "operacional"
    DECISOES = "decisoes"
    APRENDIZADOS = "aprendizados"
    ORGANIZACIONAL = "organizacional"


class EnterpriseMemoryService:
    def __init__(self, session_factory: sessionmaker, knowledge_repository: KnowledgeRepository): ...

    def classify(self, organization_id: int, document_id: int, category: MemoryCategory) -> MemoryRecordInfo:
        """Só classifica um Document que já existe na Knowledge Platform
        (via KnowledgeRepository.get_document -- nenhum acesso a tabela
        fora da fachada). Persiste um novo MemoryRecord -- nunca duplica o
        conteúdo do documento, apenas referencia seu id."""

    def list_by_category(self, organization_id: int, category: MemoryCategory) -> list[MemoryRecordInfo]:
        ...
```

Nenhum Advisor é implementado ou consumido por este serviço — ele é, ele mesmo, "infraestrutura de classificação", consumível por qualquer futuro Advisor exatamente como o `KnowledgeRepository`.

---

## 4. Modelo de dados — `MemoryRecord` (novo, em `src/database/models.py`)

| Coluna | Observação |
|---|---|
| `id` | PK |
| `organization_id` | NOT NULL, FK, escopo obrigatório (Princípio 6) |
| `document_id` | NOT NULL, FK a `documents` — a memória sempre referencia um documento já existente na Knowledge Platform, nunca duplica conteúdo |
| `category` | `String`, um dos 5 valores de `MemoryCategory` |
| `created_at` | timestamp da classificação (evento de "Captura") |

Migração `0016 -> 0017`: aditiva, cria apenas `memory_records`.

---

## 5. Critérios de conformidade com as diretrizes do Founder (checklist explícita)

| Diretriz | Como é cumprida |
|---|---|
| 1. Separação infraestrutura/domínio | `RagPipeline`/`EnterpriseMemoryService` são subpacotes de `src/services/knowledge_platform/`, mesma árvore de infraestrutura da Fase 1; nenhum conceito de negócio (Advisor, decisão executiva) é modelado aqui. |
| 2. Sem lógica específica de Advisor | `RagPipeline.retrieve()` para antes de compor prompt ou chamar `LLMProvider` (§0); `EnterpriseMemoryService` não conhece nenhum Advisor. |
| 3. Nenhum Advisor acessa `PgVectorRepository` diretamente | Não se aplica ainda (nenhum Advisor existe) — mas a arquitetura garante isso estruturalmente: `PgVectorRepository` nunca é exportado fora de `vector_repository.py`, só é injetado dentro de `KnowledgeRepository`. |
| 4. Todo consumo via `KnowledgeRepository` + serviços da plataforma | `RagPipeline` e `EnterpriseMemoryService` só chamam `KnowledgeRepository` (nunca `VectorRepository`/`EmbeddingProvider` diretamente). |
| 5. Resolução de contexto determinística/auditável/rastreável | `RagContext` carrega `chunk_ids`; `MockEmbeddingProvider` determinístico; ranking com chave de ordenação total; `logger.info` em toda chamada. |
| 6. Governança atualizada ao final | Decision Log (D-066, ou o próximo id sequencial), CHANGELOG, Mission Control, Gate "Fase 2 → Fase 3" em `WAVE-3-EXECUTION-PLAN.md`. |

---

## 6. Arquivos alterados/criados (checklist)

**Backend**
- `src/database/models.py` (alterado — `MemoryRecord`)
- `alembic/versions/0017_enterprise_memory_model.py` (novo)
- `src/services/knowledge_platform/types.py` (alterado — `ScoredChunk` ganha `document_version_created_at`; `MemoryRecordInfo` novo)
- `src/services/knowledge_platform/vector_repository.py` (alterado — `similarity_search` seleciona `DocumentVersion.created_at`)
- `src/services/knowledge_platform/rag_pipeline.py` (novo)
- `src/services/knowledge_platform/enterprise_memory_service.py` (novo)

**Testes**
- `tests/test_migration_0017_enterprise_memory_model.py` (novo)
- `tests/test_rag_pipeline.py` (novo)
- `tests/test_enterprise_memory_service.py` (novo)

**Nenhum arquivo de frontend, rota de API, ou Advisor é tocado** — mesma disciplina da Fase 1.
