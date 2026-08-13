# Technical Design — Production Embedding Contract & Vector Migration

**Autorização:** "Founder Decision — D-175 — W7-1 Staging Architecture Approval + Embedding Production Contract Gate". Staging architecture (VM Linux dedicada, 2 vCPU/4 GB RAM/20-40 GB storage, Docker+Compose, isolamento completo, Deployment Contract do W7-5 reutilizado) está **APPROVED**. `Voyage AI / voyage-multilingual-2` fica registrado como **PREFERRED CANDIDATE**, ainda não aprovado como Production Embedding Provider — condicionado à resolução do achado arquitetural: `chunks.embedding` usa dimensão fixa 16 (proveniente do `MockEmbeddingProvider`), incompatível com qualquer candidato real. Autorizada exclusivamente a produção deste Technical Design. **Nenhum código escrito, nenhuma migration criada, nenhum schema alterado, nenhum staging provisionado, nenhuma credencial real usada, nenhuma API de embedding chamada, nenhum reembedding executado, nenhum outro Epic da Wave 7 iniciado.**

---

## 3. Contrato atual (grounded em código real, linha a linha)

### 3.1 Contrato do provider

`src/services/knowledge_platform/embedding_provider.py`:

```python
class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...
```

Um único método, uma única responsabilidade: texto → vetor. Mesma forma de seam já usada por `LLMProvider`/`ProductionLLMProvider` (`src/llm/providers/base.py`/`factory.py`) — reutilizando um padrão já aprovado, não criando um novo tipo de registry.

`MockEmbeddingProvider.embed()` gera um vetor determinístico via hash SHA-256 do texto normalizado — sem chamada de rede, sem semântica real (o mesmo texto sempre produz o mesmo vetor, mas textos semanticamente próximos não produzem vetores próximos, ao contrário de um modelo real).

`get_embedding_provider()` (fábrica selecionada por `EMBEDDING_PROVIDER`) hoje só aceita `"mock"` — qualquer outro valor levanta `EmbeddingProviderConfigError` **por design**, não por omissão: o código já documenta explicitamente ("no production embedding backend is wired in this Fase") que a escolha real foi deferida para este exato momento.

### 3.2 Onde a dimensão 16 está definida

Exatamente dois lugares, ambos confirmados por leitura direta:

1. `src/database/models.py:37` — `KNOWLEDGE_EMBEDDING_DIM = 16`, usada em `models.py:429` (`embedding = Column(Vector(KNOWLEDGE_EMBEDDING_DIM), nullable=False)`) e reimportada por `embedding_provider.py:23` só para dimensionar o vetor mock.
2. `alembic/versions/0016_enterprise_knowledge_platform_foundation.py:45` — `EMBEDDING_DIM = 16`, uma constante **própria e independente** dentro da migration (não importa de `models.py`). Isso já é o padrão correto e já estabelecido neste repositório: migrations Alembic nunca importam do modelo vivo (que muda ao longo do tempo) — cada migration é um snapshot congelado. Qualquer migration futura que altere a dimensão precisa, pela mesma disciplina já em uso, definir sua própria constante nova, nunca importar `KNOWLEDGE_EMBEDDING_DIM`.

Não existe um terceiro lugar. `chunks` não tem índice ANN (`ivfflat`/`hnsw`) — confirmado por leitura completa de `0016`: apenas índices B-tree em `id`/`document_version_id`/`organization_id`, nenhum índice vetorial. Isso simplifica a migração: não há índice a reconstruir, apenas o tipo da coluna.

### 3.3 Quais componentes assumem essa dimensão

Apenas os dois listados em 3.2. Nenhum outro componente de produção. Em testes, a dimensão aparece hardcoded em 3 lugares, todos cientes de que espelham o valor mock atual, não uma verdade arquitetural:
- `tests/test_knowledge_platform.py:38` — `assert len(provider.embed("hello world")) == 16`;
- `tests/test_knowledge_platform.py:85` — `[0.0] * 16` (vetor de teste para `upsert_vector`);
- `tests/test_migration_0016_knowledge_platform.py:78` — `"[" + ",".join(["0"] * 16) + "]"` (vetor de teste via SQL bruto).

Esses 3 pontos precisarão ser atualizados (não agora) quando a dimensão real for implementada — são o custo de teste da mudança, não um achado de risco.

### 3.4 Quais componentes precisariam mudar para um provider real

- `src/services/knowledge_platform/embedding_provider.py` — nova classe (ex. `VoyageEmbeddingProvider`) implementando `EmbeddingProvider`, e um novo ramo no `if` de `get_embedding_provider()`. Mesma forma de `ProductionLLMProvider`.
- `src/database/models.py` — `KNOWLEDGE_EMBEDDING_DIM` passaria a refletir a dimensão real escolhida (usado apenas para o SQLAlchemy `Column` — a migration em si, pela disciplina de 3.2, não importa essa constante).
- Uma migration nova alterando `chunks.embedding` para a nova dimensão (ver §5/§6).
- `requirements.txt` — se o provider escolhido exigir um SDK novo (ex. `voyageai`), uma linha nova, mesma forma de como `anthropic`/`pgvector` já foram adicionados.
- `docker-compose.yml` — `EMBEDDING_PROVIDER` e a credencial real do provider precisam ser propagadas ao serviço `api`. **Achado adicional, pequeno:** confirmado por busca direta que `EMBEDDING_PROVIDER` não aparece hoje em `docker-compose.yml`, `.env.example`, nem em nenhum script de `demo/` — um gap de wiring simples (não arquitetural), a ser fechado junto da implementação real, não agora.
- Os 3 pontos de teste de §3.3.

Nenhum outro componente muda — nem `RagPipeline`, nem `VectorRepository`, nem `DocumentIngestionService`, nem nenhuma rota HTTP.

### 3.5 A dimensão vaza para camadas que deveriam ser provider-agnostic?

**Não.** Confirmado por leitura completa de `KnowledgeRepository` (`ingest`/`index`/`search`), `RagPipeline.retrieve()` e `VectorRepository`/`PgVectorRepository`: nenhum desses componentes lê, compara ou assume o tamanho do vetor — todos tratam `list[float]` como um valor opaco vindo de `EmbeddingProvider.embed()` e o repassam diretamente à coluna ORM (`Chunk(embedding=...)`) ou ao operador `cosine_distance()` do pgvector. A dimensão é imposta exclusivamente pelo tipo da coluna do banco (`Vector(N)`), nunca por lógica de aplicação. Isso significa que a troca de dimensão é estruturalmente uma mudança de schema + configuração, nunca uma mudança de lógica de domínio — a arquitetura já está correta neste ponto; o problema é puramente o valor `16` estar fixado hoje como placeholder de mock.

---

## 4. Comparação de candidatos (dados técnicos atuais, nenhuma escolha feita)

| Critério | **Voyage AI** | OpenAI | Cohere | Self-hosted open-source |
|---|---|---|---|---|
| Modelo recomendado | `voyage-multilingual-2` (ou `voyage-3` para uso predominantemente EN) | `text-embedding-3-large` | `embed-multilingual-v3.0` | ex. `paraphrase-multilingual-mpnet-base-v2` (sentence-transformers) |
| Suporte PT/EN | Nativo — `multilingual-2` cobre 100+ idiomas incl. PT, treinado para retrieval de domínio técnico/corporativo | Bom, multilíngue geral, sem foco declarado em PT | Bom, variante multilingual dedicada, historicamente forte em retrieval corporativo | Variável — modelos abertos multilíngues tendem a ficar atrás dos modelos comerciais recentes em benchmarks de retrieval, adequados para validação |
| Dimensão nativa/configurável | Fixa por modelo: 1024 (`voyage-3`) ou 512 (`voyage-3-lite`) — sem parâmetro de truncagem confirmado nesta análise | `text-embedding-3-*` suporta um parâmetro `dimensions` que trunca o vetor de saída preservando qualidade razoável (Matryoshka) — 3072 nativo, truncável | Fixa em 1024, sem truncagem configurável confirmada | Fixa pelo modelo escolhido, tipicamente 384-768 |
| Limite de contexto | ~32.000 tokens | ~8.191 tokens | ~512 tokens (varia por modelo) | Tipicamente 256-512 tokens |
| API contract | `embed(texts: list[str]) -> list[list[float]]`, HTTP/SDK — mapeia 1:1 para o `Protocol` existente (uma chamada por texto, ou lote) | Mesma forma | Mesma forma | Chamada de função local/in-process — sem HTTP, sem chave de API |
| Custo esperado | Cobrança por token, historicamente competitiva para embeddings | Cobrança por token, mercado mais maduro/competitivo | Cobrança por token, ordem de grandeza comparável | Sem custo por chamada — custo é de infraestrutura (CPU/GPU do host) |
| Latência esperada | Chamada de rede externa — mesma ordem de grandeza da chamada Anthropic já em produção no código (`ProductionLLMProvider`) | Chamada de rede externa, ordem de grandeza comparável | Chamada de rede externa, ordem de grandeza comparável | Sem chamada de rede — latência limitada por CPU/GPU local, soma carga computacional ao próprio host de staging/produção |
| Tratamento/retenção de dados | Texto de documentos corporativos sai da infraestrutura própria — exige revisão de DPA/termos de retenção antes de uso com conteúdo real | Mesma consideração | Mesma consideração | **Nenhum dado sai da infraestrutura própria** — vantagem estrutural para documentos corporativos sensíveis |
| Disponibilidade | SLA de provider comercial | SLA de provider comercial, maior maturidade operacional | SLA de provider comercial | Depende inteiramente da disponibilidade do próprio host — sem terceiro no caminho crítico |
| Versionamento do modelo | Nome do modelo é parte da chamada; providers comerciais tipicamente mantêm uma janela de deprecação após lançar um modelo novo, mas eventualmente descontinuam versões antigas — exige monitorar avisos de deprecação do vendor | Mesma consideração | Mesma consideração | Controle total — a organização fixa a revisão exata do modelo (ex. um commit específico de um repositório de pesos); o único risco de versão é a própria cadência de upgrade da organização |
| Impacto sobre reindexação | Qualquer modelo, de qualquer candidato, exige reembedding completo ao ser adotado ou trocado (§6/§7) — nenhum candidato desta lista escapa desse custo | Idêntico | Idêntico | Idêntico |
| Lock-in | Médio — specífico do vendor Voyage, mas a mesma reembedding obrigatória de troca já neutraliza a diferença entre candidatos comerciais nesse quesito | Médio, mesma razão | Médio, mesma razão | Baixo quanto a dependência de vendor externo; mesmo custo de reembedding ao trocar de modelo |
| Esforço estimado de integração | Baixo — uma classe nova implementando o `Protocol` já existente (§3.4), mesmo padrão de `ProductionLLMProvider`; sem SDK novo além da família já usada por `LLM_PROVIDER=anthropic` (parceria oficial reconhecida pela Anthropic) | Baixo — mesma forma, requer nova dependência (`openai`) não presente em `requirements.txt` hoje | Baixo — mesma forma, requer nova dependência (`cohere`) não presente hoje | Médio-alto — requer decidir onde o modelo roda (dentro do container `api`? um serviço novo?), gerenciar download/cache do modelo, dimensionar CPU/GPU adicional no host |

**Nenhum candidato é escolhido aqui.** Esta tabela existe para a decisão do Founder (Decision Brief, seção final), não para decidir por ele.

---

## 5. Vector Schema Strategy

### A. Dimensão fixa pelo modelo escolhido

Migration altera `chunks.embedding` de `vector(16)` diretamente para `vector(N)`, onde `N` é a dimensão do modelo aprovado (ex. 1024 para Voyage, 1536/3072 para OpenAI). Simples, direto, mesmo padrão de coluna tipada já usado desde `0016` — apenas um `N` diferente.

**Trade-off:** ao trocar de provider/modelo no futuro, uma nova migration de dimensão é sempre necessária (não é evitável — ver §5.C sobre por que isso é aceitável).

### B. Dimensão normalizada/configurável (avaliada e não recomendada)

Considerada: usar um `vector(N_max)` compartilhado (a maior dimensão entre candidatos, hoje 3072 do OpenAI `large`) e preencher com zero-padding os modelos de dimensão menor, para evitar migration a cada troca.

**Rejeitada.** `pgvector` não tem um modo "dimensão variável" nativo — o tipo `vector(N)` é fixo por design, e essa é a forma que dá os operadores/performance testados que este repositório já usa (`cosine_distance`). Zero-padding introduziria: (1) desperdício de armazenamento e I/O permanente para todo modelo menor que o máximo; (2) uma convenção de padding que precisaria ser aplicada de forma absolutamente consistente entre escrita e leitura, sob risco de corromper silenciosamente a similaridade de cosseno se qualquer parte do sistema esquecer de aplicá-la; (3) uma camada de abstração nova só para evitar um custo (a migration) que o próprio Founder já sinalizou como aceitável ("o objetivo não é tornar troca de provider gratuita"). **Não introduzida por não haver necessidade real demonstrada** — mesma disciplina já aplicada a toda a Wave 7.

### C. Versionamento da representação vetorial

Avaliado: registrar `provider`/`model`/`dimension`/`version` junto a cada vetor.

**Recomendação: versão mínima, não um sistema.** Duas colunas novas e simples em `chunks` — `embedding_provider` (string) e `embedding_model` (string), ambas nullable — sem uma tabela de versionamento separada, sem uma abstração de "schema de vetor" nova. Isso é suficiente para responder, a qualquer momento, "quais chunks foram embutidos com qual modelo" (útil para uma futura reindexação controlada — filtrar `WHERE embedding_model != '<atual>'`), sem construir nenhum mecanismo de coexistência multi-modelo (que este produto não precisa: apenas um provider está ativo por ambiente a qualquer momento, hoje e no horizonte previsível). Rejeitada explicitamente uma tabela de versionamento dedicada, ou qualquer forma de dual-write — **abstração além dessas duas colunas seria introduzida apenas por elegância, não por necessidade demonstrada**, violando a mesma restrição que rejeitou a Estratégia B.

**Recomendação final combinada:** Estratégia A (dimensão fixa pelo modelo escolhido) + a versão mínima de C (duas colunas de proveniência). Estratégia B rejeitada.

---

## 6. Migration & Reembedding Plan

Ponto de partida real, confirmado por código: **os embeddings atuais são 100% mock** (`MockEmbeddingProvider`, hash determinístico sem semântica) — nenhum ambiente hoje tem RAG de produção validado (AR-18, Embedding = Not Ready). Isso significa que os vetores hoje armazenados em `chunks.embedding` **não têm valor a preservar**. Essa constatação simplifica materialmente o plano abaixo.

### 6.1 Migration (schema)

Uma migration nova (não criada nesta missão), seguindo a disciplina já estabelecida (constante própria, sem importar `models.py`):
1. `DROP COLUMN embedding` (o `vector(16)` mock existente) — descartar os dados mock é seguro, por não terem valor semântico.
2. `ADD COLUMN embedding vector(N) NOT NULL` — **só é possível manter `NOT NULL` diretamente se a tabela `chunks` estiver vazia no momento da migration**, o que é o caso hoje em qualquer ambiente real (nenhuma produção existe ainda). Se, no futuro, houver dados reais na tabela no momento de uma troca de provider, a coluna precisaria ser adicionada `nullable=True` primeiro, populada via reembedding, e só então promovida a `NOT NULL` numa migration subsequente — cenário diferente do atual, tratado em §7.
3. Adicionar `embedding_provider`/`embedding_model` (nullable, §5.C).

A alteração de tipo em si é DDL transacional (Postgres/Alembic já assumem DDL transacional neste projeto, confirmado pelos próprios logs de execução do Alembic já vistos em toda a suíte de testes) — **atômica apenas para o schema**, não para o reembedding (que segue, §6.2, fora da transação de schema, por envolver chamadas de rede reais).

### 6.2 Reembedding (operacional, fora da transação de schema)

Como a migration de 6.1 esvazia `chunks`, o reembedding é, na prática, uma **reingestão completa**: para cada `DocumentVersion` já existente (o texto original em `document_versions.content` nunca é apagado por nada deste plano), reexecutar o equivalente de `KnowledgeRepository.index()` contra o novo `EmbeddingProvider` real.

**Achado operacional importante, a ser respeitado pela implementação futura (não corrigido agora):** `DocumentIngestionService.reindex()` já existe como caminho de retry explícito, mas `KnowledgeRepository.index()` **não deleta chunks existentes antes de inserir novos** — ele apenas adiciona. Chamar `reindex()` ingenuamente em um documento que já tem chunks duplicaria linhas. Como a migration de 6.1 já esvazia a tabela inteira, esse risco não se materializa neste cenário específico (não há chunks pré-existentes para duplicar) — mas fica registrado como um comportamento real do código que uma rotina de reembedding futura, operando sobre dados reais já existentes (cenário de §7), precisaria tratar explicitamente (deletar chunks da versão antes de reindexar, ou estender `index()`), não descoberto silenciosamente em produção.

### 6.3 Falha parcial

Reembedding é uma reingestão documento por documento — `index()` já commita todos os chunks de um documento numa única transação, e só publica `document.indexed` após esse commit (comportamento já existente, confirmado no código). Uma falha no documento N não corrompe os documentos 1..N-1 já reembutidos; o documento N fica sem chunks, seu `get_status()` (já existente) reporta `ingested_pending_index`/`failed`, e é reprocessável via `reindex()` — nenhum mecanismo novo necessário, apenas reexecução do caminho já existente sobre os documentos pendentes.

### 6.4 Documentos novos durante a migração

Risco real de incompatibilidade: se uma instância antiga do `api` (ainda esperando `vector(16)`) continuar recebendo tráfego depois que o schema já migrou para `vector(N)`, uma inserção com vetor mock de 16 posições falharia contra a nova coluna. **Isso já é estruturalmente evitado pela Migration Discipline do W7-5** (Etapa 5): `docker-compose.yml` já executa a migração como etapa explícita e separada, ANTES do `up` do serviço `api` (`docker compose run --rm api alembic upgrade head` seguido de `docker compose up -d api web database`) — não há deploy "rolling" nesta topologia, então nenhuma instância antiga do `api` continua servindo tráfego depois que a nova migration já foi aplicada. Nenhum mecanismo novo é necessário — o Deployment Contract já aprovado em W7-5 já cobre esse risco.

### 6.5 Atomicidade e rollback

- **Atomicidade real:** o passo de schema (6.1) é atômico; o passo de reembedding (6.2) não é — é uma sequência de chamadas de rede reais, uma por documento.
- **Rollback "leve" (recomendado como padrão):** reverter `EMBEDDING_PROVIDER` para `mock` (mudança de configuração apenas, instantânea) se o provider real se mostrar inviável durante a validação — aceitável porque, neste momento (staging pré-lançamento, sem dependência de produção real), um corpus temporariamente vazio ou parcial não é um incidente de disponibilidade.
- **Rollback "completo":** uma migration de downgrade reverte `chunks.embedding` para `vector(16)` — só necessário se o próprio schema precisar ser desfeito, cenário mais raro (ex. decisão de abandonar completamente a direção do provider escolhido).

### 6.6 Validação pós-migration

Confirmar: (1) contagem de `chunks` reflete a cobertura esperada de `document_versions` (nenhum documento órfão sem chunk); (2) uma chamada real a `POST /api/document-advisor/ask` sobre um documento conhecido retorna citação real, plausível — não apenas "sem erro", mas evidência de que a busca por similaridade está de fato retornando o chunk relevante, não um resultado aleatório (validação de qualidade mínima, não apenas de integridade estrutural).

### 6.7 Compatibilidade aplicação/schema durante o deploy

Já coberta em 6.4 — reaproveitando a Migration Discipline do W7-5, sem mecanismo novo.

---

## 7. Provider Switching — resposta objetiva

**Se, daqui a 12 meses, a STRATECH trocar o modelo de embedding, o que precisa acontecer:**

| Mudança | Necessária? | Por quê |
|---|---|---|
| Apenas configuração (`EMBEDDING_PROVIDER`) | **Nunca suficiente sozinha** | O valor do vetor muda de espaço semântico — nenhuma troca de embedding é "apenas configuração", diferente de, por exemplo, trocar `MODEL_NAME` dentro do mesmo `LLM_PROVIDER=anthropic` |
| Código (`embedding_provider.py`) | Sim, se o novo modelo não for servido pela mesma classe já implementada (ex. trocar de Voyage para OpenAI); **não necessária** se for apenas um modelo novo do mesmo provider já integrado (ex. `voyage-3` → uma versão futura de `voyage-3`), desde que a mesma classe já saiba parametrizar o nome do modelo | Troca de vendor sempre precisa de uma implementação nova do `Protocol`; troca de modelo dentro do mesmo vendor pode ser só um parâmetro, se a classe já foi desenhada para aceitar o nome do modelo como configuração (mesmo padrão que `ProductionLLMProvider.model` já usa) |
| Migration de banco (dimensão) | Sim, **sempre que a nova dimensão for diferente da atual** — o que é o caso comum entre modelos/vendors diferentes | `vector(N)` é fixo por coluna; qualquer `N` novo exige `ALTER`/recriação da coluna |
| Reembedding | **Sempre, sem exceção — mesmo se a dimensão nominal coincidir por acaso entre dois modelos diferentes** | Espaços vetoriais de modelos diferentes não são comparáveis entre si, mesmo com o mesmo número de dimensões — um vetor de 1024 posições do modelo A não tem relação matemática com um vetor de 1024 posições do modelo B. Coincidência de dimensão nunca implica compatibilidade semântica |
| Reindexação (índice ANN) | Não aplicável hoje (§3.2 — nenhum índice `ivfflat`/`hnsw` existe ainda); **se um índice desse tipo for adicionado no futuro** (ex. por necessidade de performance identificada em W7-6), ele precisaria ser reconstruído após qualquer reembedding completo | Índices de busca aproximada são treinados sobre a distribuição real dos vetores — trocar os vetores invalida o índice |

**Conclusão explícita, respondendo à pergunta do Founder:** a troca de provider nunca é gratuita — sempre implica, no mínimo, reembedding completo. O que esta análise torna previsível é exatamente *o quê* muda e *por quê*, listado linha a linha acima, e não algo descoberto ad-hoc no momento da troca.

---

## 8. Impacto sobre o W7-1 — sequência verificada

A sequência proposta pelo Founder foi verificada contra o código real (Deployment Contract de W7-5, comportamento de `index()`/`reindex()`, achados de §3-§7) e **confirmada sem alteração** — nenhum achado de código a torna incorreta:

```
Provision Staging → Deploy → Readiness → Smoke Test →
Production LLM Validation → Embedding Implementation/Migration → Reembedding →
Production Embedding Validation → Integrated AI Validation → Executive Evidence
```

Notas de grounding, sem alterar a ordem:

- **"Deploy"** cobre o Deployment Contract completo já documentado em `PRI-009` (Build → Validate → Migrate → Deploy) — a topologia inicial sobe ainda com `EMBEDDING_PROVIDER=mock`/schema atual (`vector(16)`), suficiente para validar `Readiness`/`Smoke Test`/`Production LLM Validation`, que não dependem de embedding.
- **"Embedding Implementation/Migration"** é, na prática, um segundo ciclo de deploy sobre a mesma staging (não um ambiente novo) — aplicando a migration de §6.1 e o código do provider escolhido, atomicamente (schema + app juntos, per §6.4/§6.7, reaproveitando a Migration Discipline do W7-5).
- **"Reembedding"** é o passo operacional de §6.2 — explicitamente fora da transação de schema, sujeito a falha parcial recuperável (§6.3).
- **"Production Embedding Validation"** reaproveita o protocolo de 5 camadas já definido no Technical Design W7-1 anterior (`TECHNICAL-DESIGN-W7-1-STAGING-PRODUCTION-LLM-EMBEDDING-VALIDATION.md` §6.2), agora desbloqueado.
- **Observação, sem forçar reordenação:** "Production LLM Validation" continua não dependendo de nenhuma decisão de embedding (achado já confirmado na análise anterior, D-174) — a ordem dada já reflete essa independência corretamente, apenas tornando-a sequencial em vez de paralela, o que a instrução do Founder já autoriza explicitamente ("ajuste somente com evidência do código" — nenhuma evidência exige paralelismo obrigatório, apenas o permite).

### Blockers para esta sequência prosseguir além do Technical Design

1. Escolha final do host de staging (procurement — D-173/D-174, ainda pendente).
2. Escolha final e aprovação de tratamento de dados do Production Embedding Provider (procurement/legal — pendente, este documento não decide).
3. Nenhum blocker técnico novo identificado por este Technical Design — o contrato já é limpo (§3.5), a estratégia de schema é mínima e justificada (§5), e o plano de migração/reembedding é executável com os componentes já existentes (§6), sem depender de nenhuma capability ainda não construída.

---

## O que não foi feito nesta missão (verbatim das restrições do Founder)

Nenhum código foi implementado. Nenhuma migration foi criada. Nenhum schema foi alterado. Nenhum staging foi provisionado. Nenhuma credencial real foi usada. Nenhuma API de embedding foi chamada. Nenhum reembedding foi executado. Nenhum outro Epic da Wave 7 foi iniciado.

---

## 9. Decision Brief

### EMBEDDING CONTRACT
- **Current State:** `EmbeddingProvider.embed(text) -> list[float]`, único método, implementado apenas por `MockEmbeddingProvider` (vetor de 16 posições, hash determinístico, zero semântica). Dimensão vazando para exatamente 2 lugares (`models.py`, migration `0016`), nunca para lógica de domínio (`KnowledgeRepository`/`RagPipeline`/`VectorRepository` são todos provider-agnostic, confirmado).
- **Required State:** uma segunda implementação real do mesmo `Protocol` (sem novo registry), dimensão da coluna `chunks.embedding` alterada para a dimensão real do modelo escolhido, `embedding_provider`/`embedding_model` registrados como proveniência mínima.
- **Delta:** uma classe nova + fábrica atualizada; uma migration de dimensão; 3 testes a atualizar; wiring de `EMBEDDING_PROVIDER`/credencial em `docker-compose.yml` (gap pequeno, hoje ausente).

### VECTOR SCHEMA
- **Recommended Strategy:** A (dimensão fixa pelo modelo escolhido) + versão mínima de C (colunas `embedding_provider`/`embedding_model`, sem tabela de versionamento).
- **Alternatives:** B (dimensão normalizada/configurável via zero-padding) — avaliada e **rejeitada** por introduzir complexidade e risco de correção sem necessidade demonstrada.
- **Trade-offs:** Estratégia A garante troca de provider previsível (sempre migration + reembedding, nunca surpresa), ao custo de sempre pagar esse preço — aceito explicitamente pelo Founder como objetivo ("impedir que seja arquiteturalmente imprevisível", não "tornar grátis").

### PROVIDER
- **Recommended:** Voyage AI (`voyage-multilingual-2`) — permanece a recomendação técnica desta análise, não uma decisão.
- **Alternatives:** OpenAI (`text-embedding-3-large`, único candidato com truncagem de dimensão configurável confirmada); Cohere (`embed-multilingual-v3.0`); self-hosted open-source (recomendado apenas se dados corporativos não puderem sair da infraestrutura própria).
- **Decision Required:** aprovação de tratamento de dados/DPA com o provider externo escolhido (ou confirmação de que a alternativa self-hosted é obrigatória) — decisão de procurement/segurança/legal, não arquitetural. **Não decidida por esta missão.**

### MIGRATION
- **Migration:** `DROP`+`ADD COLUMN embedding vector(N) NOT NULL` (tabela vazia hoje, sem dado real a preservar) + colunas de proveniência nullable.
- **Reembedding:** reingestão completa de todo `DocumentVersion` existente contra o provider real, documento por documento, com falha parcial recuperável via `reindex()` já existente (com a ressalva operacional de §6.2 sobre duplicação, relevante apenas em cenários futuros com dados reais).
- **Rollback Strategy:** padrão leve (reverter `EMBEDDING_PROVIDER` para `mock`, instantâneo); completo (migration de downgrade) apenas se o próprio schema precisar ser desfeito.

### W7-1
- **Updated Execution Sequence:** `Provision Staging → Deploy → Readiness → Smoke Test → Production LLM Validation → Embedding Implementation/Migration → Reembedding → Production Embedding Validation → Integrated AI Validation → Executive Evidence` — **confirmada sem alteração**, nenhum achado de código a invalida.
- **Blockers:** host de staging (procurement, pendente); provider de embedding + aprovação de dados (procurement/legal, pendente). Nenhum blocker técnico novo.

### GO/NO-GO
**GO para que o Founder decida o Production Embedding Provider** com base neste Decision Brief. **NO-GO para qualquer implementação, migration ou provisionamento** até essa decisão — nenhuma etapa de execução do W7-1 inicia automaticamente. Retornando obrigatoriamente para Executive Review.
