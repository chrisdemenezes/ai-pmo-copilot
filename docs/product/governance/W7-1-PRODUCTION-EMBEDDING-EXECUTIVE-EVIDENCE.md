# W7-1 Production Embedding Implementation — Executive Evidence

**Autorização:** "Founder Decision — Production Embedding Provider Approval + W7-1 Embedding Implementation Authorization" (D-177). Registra como decisão oficial: **Production Embedding Provider = Voyage AI, Model = `voyage-4`, Vector Dimension = `1024`** — substituindo a recomendação preliminar `voyage-multilingual-2` (D-175/D-176), sem revisão retroativa desses documentos, que permanecem como registro histórico da evolução da decisão. `voyage-context-4` permanece **DEFERRED** (contrato de API estruturalmente diferente do `Protocol` aprovado). Autorizada implementação técnica incremental em 6 etapas, sem provisionar staging.

---

## Etapas executadas

| Etapa | Commit | Escopo |
|---|---|---|
| 1 — Production Embedding Provider | `2163c19` | `VoyageEmbeddingProvider`, fail-fast |
| 2 — Vector Schema Migration | `d299075` | migration 0021: `vector(16)` → `vector(1024)` + proveniência |
| 3 — Ingestion/Persistence | `bb6e44e` | `KnowledgeRepository.index()` persiste provenance |
| 4 — Retrieval Compatibility | `a7c383f` | prova end-to-end com 1024 dimensões |
| 5 — Configuration & Deployment Wiring | `15a944b` | `docker-compose.yml`/`PRI-009`/`.env.example` |
| 6 — Validation | (este commit) | Executive Evidence + governança |

Cada etapa foi implementada, testada isoladamente e verificada contra a suíte completa antes do commit — cada commit foi empurrado para `origin` imediatamente após sua verificação.

---

## Arquivos alterados (13, confirmado por `git diff --stat`)

**Backend**
- `src/services/knowledge_platform/embedding_provider.py` — `VoyageEmbeddingProvider` (novo), `EmbeddingProviderUnavailableError` (novo), `EmbeddingProvider.Protocol` ganha `provider_name`/`model_name`, `MockEmbeddingProvider` ganha os mesmos atributos + correção de bug (ver Riscos Residuais), `get_embedding_provider()` ganha o ramo `"voyage"`
- `src/api/startup_config.py` — fail-fast para `EMBEDDING_PROVIDER=voyage` sem `VOYAGE_API_KEY`
- `src/database/models.py` — `KNOWLEDGE_EMBEDDING_DIM = 1024`; `Chunk` ganha `embedding_provider`/`embedding_model`
- `src/services/knowledge_platform/knowledge_repository.py` — `index()` persiste a proveniência
- `alembic/versions/0021_production_embedding_provider.py` (novo)
- `docker-compose.yml`, `.env.example`, `docs/operations/PRI-009-production-deployment-runbook.md` — wiring

**Testes**
- `tests/test_voyage_embedding_provider.py` (novo, 5 testes)
- `tests/test_migration_0021_production_embedding_provider.py` (novo, 1 teste)
- `tests/test_knowledge_platform.py` (+4 testes: provenance de Mock, seleção de Voyage, provenance persistida, retrieval compatibility)
- `tests/test_startup_config.py` (+2 testes parametrizados: `VOYAGE_API_KEY` ausente; corrigido bug pré-existente na fixture de ambiente válido)
- `tests/test_migration_0016_knowledge_platform.py` (fixado: `upgrade "0016"` em vez de `upgrade "head"`, para não depender do schema atual)

**Governança:** este documento; `docs/product/stratech-v2/DECISION-LOG.md` (D-177); `CHANGELOG.md`; `web/lib/mock/mission-control-data.ts`.

---

## Contrato implementado

`EmbeddingProvider.embed(text) -> list[float]` **preservado exatamente** — `VoyageEmbeddingProvider` é a segunda implementação real desse mesmo `Protocol`, mesmo padrão de `ProductionLLMProvider`/`LLMProvider`. **Nenhum registry novo** — `get_embedding_provider()` ganhou apenas mais um ramo (`"voyage"`), a mesma fábrica de sempre.

**Decisão de implementação (não arquitetural, dentro do já aprovado):** `VoyageEmbeddingProvider` chama a API REST da Voyage diretamente via `httpx` (já dependência do projeto) em vez do SDK oficial `voyageai`, que traz ~30 dependências transitivas pesadas (`numpy`, `pillow`, `tokenizers`, `langchain-core`) para uma única chamada JSON — mesma disciplina de reuso já aplicada em todo o codebase (`requirements.txt` permanece sem alteração).

**Proveniência mínima** (`provider_name`/`model_name`) adicionada ao `Protocol`, implementada por `MockEmbeddingProvider` ("mock"/"mock") e `VoyageEmbeddingProvider` ("voyage"/"voyage-4") — sem interpretação de domínio em `KnowledgeRepository`, que apenas repassa o que o provider injetado já se auto-reporta.

---

## Configuração

- `EMBEDDING_PROVIDER=mock` (default) — DEV/Demo Mode inalterados, nenhuma configuração exigida.
- `EMBEDDING_PROVIDER=voyage` em staging/produção — exige `VOYAGE_API_KEY`; sua ausência falha o boot explicitamente (`EmbeddingProviderConfigError` via `collect_startup_config_problems`), mesmo padrão de `ANTHROPIC_API_KEY`.
- `docker-compose.yml`/`.env.example`/`PRI-009` propagam as duas variáveis ao serviço `api` — nenhuma credencial commitada.

---

## Evidência de dimensão 1024

- `src/database/models.py`: `KNOWLEDGE_EMBEDDING_DIM = 1024`, único ponto de verdade (a migration 0021 carrega sua própria cópia congelada, nunca importa esse valor, disciplina já estabelecida desde a migration 0016).
- `tests/test_migration_0021_production_embedding_provider.py`: prova em PostgreSQL real que a coluna `chunks.embedding` é `vector(1024)` após o upgrade, e `vector(16)` após o downgrade.
- `tests/test_knowledge_platform.py::test_round_trip_persists_and_retrieves_the_approved_production_dimension`: prova que um `Chunk` real, persistido via `KnowledgeRepository.index()`, carrega `len(embedding) == 1024`.

## Evidência de proveniência

- `tests/test_migration_0021_production_embedding_provider.py`: prova que `embedding_provider`/`embedding_model` existem como colunas reais e aceitam valores.
- `tests/test_knowledge_platform.py::test_index_persists_embedding_provenance`: prova que um `Chunk` real, após `index()` com `MockEmbeddingProvider`, persiste `embedding_provider="mock"`/`embedding_model="mock"`.

---

## Preservação arquitetural

Confirmado mecanicamente via `git diff --stat` contra a base pré-missão (`f6d4ed2`): **zero alteração** em `src/services/advisor_framework/`, `src/services/ai_foundation/`, `src/services/executive_orchestrator/`, `src/agents/` (os 8 Enterprise Advisors), `src/workflows/` (Workflow Runtime), `src/services/events/` (Event Pipeline), `src/database/domain_repository.py`/`enterprise_repository.py` (Enterprise Domain), e as rotas de Portfolio/Program/Project Delivery/Administration. As únicas alterações na Knowledge Platform são exatamente as necessárias para suportar o Production Embedding Provider aprovado (`embedding_provider.py`, `knowledge_repository.py`, `models.py`, a migration) — nenhuma mudança de `RAG semantics` além da dimensão/proveniência.

---

## Testes executados e resultados

| Suíte | Resultado |
|---|---|
| Backend completo (`pytest`) | **912 passed**, 0 failed |
| `ruff check` (arquivos novos/alterados) | Limpo — únicos achados são padrões pré-existentes idênticos em todo o codebase (`I001`/boilerplate de migration Alembic/`PLW1510` em `subprocess.run`, todos confirmados via `git stash` como já presentes antes desta missão) |
| Suíte completa da cadeia Knowledge Platform/RAG/Document Advisor (55 testes) | Rodada explicitamente, todas verdes |

### As 10 provas mandatadas

1. **Mock continua funcional em DEV** — `tests/test_startup_config.py::TestDevPermissive`, `tests/test_knowledge_platform.py::TestMockEmbeddingProvider` (todas verdes, nenhuma configuração exigida).
2. **Voyage pode ser selecionado pela configuração** — `test_knowledge_platform.py::TestGetEmbeddingProvider::test_voyage_returns_voyage_provider`.
3. **Staging/produção falham sem credencial/config obrigatória** — `test_startup_config.py::TestStagingAndProductionInvalid::test_voyage_without_api_key` (parametrizado staging+production); `test_voyage_embedding_provider.py::test_missing_api_key_raises_config_error`.
4. **Dimensão persistida = 1024** — `test_migration_0021...py` + `test_knowledge_platform.py::test_round_trip_persists_and_retrieves_the_approved_production_dimension`.
5. **Proveniência persistida corretamente** — `test_migration_0021...py` + `test_knowledge_platform.py::test_index_persists_embedding_provenance`.
6. **Retrieval funciona com o novo schema** — `test_knowledge_platform.py::TestPgVectorRepository`/`TestKnowledgeRepository`, todas contra PostgreSQL/pgvector real.
7. **RAG continua funcional** — `test_rag_pipeline.py`, `test_document_advisor.py`, `test_document_advisor_api.py`, `test_document_ingestion_service.py`, `test_documents_api.py` (55 testes, todos verdes).
8. **Isolamento organizacional permanece intacto** — `test_knowledge_platform.py::test_similarity_search_never_crosses_organizations`, `test_document_advisor.py::TestOrganizationalIsolation` (verdes, sem alteração de lógica de isolamento).
9. **Nenhuma chamada real à Voyage ocorre nos testes** — confirmado por leitura direta de `test_voyage_embedding_provider.py`: todo cenário que alcançaria `httpx.post` o faz sobre um `unittest.mock.patch`, nunca a URL real; cenários sem `VOYAGE_API_KEY` nem chegam a essa linha.
10. **Infraestrutura compartilhada permanece preservada** — suíte completa (912 testes, incluindo Enterprise Domain, RBAC, Identity, Enterprise Administration, os 8 Advisors, Executive Orchestrator, Decision Support, Executive Narrative) verde sem nenhuma regressão; `git diff --stat` confirma zero alteração fora do escopo listado acima.

---

## Achado operacional corrigido durante a implementação (não mascarado)

Ao aumentar `KNOWLEDGE_EMBEDDING_DIM` para 1024, um bug real em `MockEmbeddingProvider.embed()` foi exposto: o método indexava diretamente `digest[i]` sobre um hash SHA-256 (32 bytes fixos), o que sempre funcionou por acidente enquanto a dimensão era ≤32 (16), mas levanta `IndexError` em qualquer dimensão maior. Corrigido para ciclar pelo digest (`digest[i % len(digest)]`), preservando o determinismo (mesmo texto → mesmo vetor) em qualquer dimensão. Corrigido como parte da Etapa 2, por ser consequência mecânica direta da mudança de dimensão, não uma nova funcionalidade.

## Achado de sequenciamento próprio, corrigido (transparência)

Durante a Etapa 1, a migration 0021 foi escrita diretamente em `alembic/versions/` enquanto uma execução da suíte completa em background ainda estava em andamento — bancos de teste temporários criados a partir desse momento captaram a nova migration antes do código do provider (`MockEmbeddingProvider`) ter sido atualizado para a nova dimensão, causando 8 falhas de `DataError` (dimensão incompatível) nessa execução específica. Diagnosticado corretamente como ruído do próprio processo, não uma regressão: o arquivo de migration foi temporariamente removido do diretório real, uma reexecução limpa confirmou 909/909 (Etapa 1 isolada, sem a migration presente), e a migration só foi reintroduzida já na Etapa 2, junto da mudança de dimensão que a torna consistente. Nenhuma falha real foi mascarada — apenas isolada corretamente da sua causa.

---

## Riscos residuais

1. **Nenhuma chamada real à API da Voyage foi feita** — o contrato REST foi implementado a partir da documentação oficial (verificada em D-176), mas nunca exercitado contra credenciais reais. A validação real de LLM/Embedding (camadas 3-7 do Production AI Validation Model, AR-18 §8) permanece inteiramente pendente do W7-1's Etapa de "Provision Staging" em diante.
2. **`input_type` (query vs. document) do Voyage não é diferenciado** — a API da Voyage aceita um parâmetro opcional `input_type` (`"query"`/`"document"`) que ajusta a qualidade de retrieval assimétrica, mas o `Protocol` atual (`embed(text) -> list[float]`) não carrega essa distinção, e `KnowledgeRepository` chama `embed()` identicamente em `index()` e `search()`. Omitido deliberadamente (parâmetro não enviado) para respeitar exatamente o contrato já aprovado, sem introduzir uma extensão de `Protocol` não mandatada. Registrado como oportunidade de melhoria futura, não um blocker.
3. **Migration 0021 apaga qualquer chunk pré-existente** — aceitável e explicitamente instruído pelo Founder (dados mock sem valor semântico), mas qualquer ambiente com conteúdo real precisará reindexar após o deploy desta migration — nenhum mecanismo automático de reindexação em massa foi construído (fora de escopo desta missão).
4. **Achado de `reindex()` não deletar chunks antigos** (já registrado em D-175/D-176) permanece uma dívida concreta, não ampliada nem resolvida nesta missão, conforme instruído — só se tornaria um bloqueador real se um cutover futuro precisasse reindexar dados reais já existentes sem antes limpar a tabela.

## Gates externos ainda pendentes

- **Data/DPA:** aprovação de tratamento de dados/DPA com a Voyage AI continua pendente (Business/Legal Operational Gate, D-175/D-176) — nenhum documento real deve ser enviado à Voyage até essa aprovação.
- **Staging real:** nenhum ambiente provisionado nesta missão — a topologia/host (D-174/D-175) e agora o Production Embedding Provider estão prontos tecnicamente, mas nunca exercitados fora deste repositório local.
- **Credencial real:** `VOYAGE_API_KEY` real nunca foi usada ou obtida nesta missão.

---

## GO/NO-GO para `Provision Staging`

**GO tecnicamente** — a implementação do Production Embedding Provider está completa, testada e verificada sem regressão; o Configuration Contract já a governa corretamente; o schema já reflete a dimensão aprovada. **Mas o provisionamento em si não está autorizado por esta missão** (per restrição explícita do Founder) e depende adicionalmente dos dois gates externos ainda pendentes acima (host de staging — procurement; Data/DPA — legal). Nenhum provisionamento, deployment real, ou chamada real a Voyage foi executado. Nenhum outro Epic da Wave 7 foi iniciado.

Retornando obrigatoriamente para Executive Review.
