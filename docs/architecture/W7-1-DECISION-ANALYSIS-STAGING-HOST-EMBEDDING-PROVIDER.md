# W7-1 — Decision Analysis: Staging Host + Production Embedding Provider

**Autorização:** "Founder Decision — W7-1 Staging Infrastructure + Production Embedding Decision Gate". O Technical Design do W7-1 (`TECHNICAL-DESIGN-W7-1-STAGING-PRODUCTION-LLM-EMBEDDING-VALIDATION.md`) está **APPROVED como base arquitetural**. Autorizada exclusivamente uma **Decision Analysis** para fechar as duas decisões que esse Technical Design já havia elevado e deixado explicitamente em aberto (§2 e §7 daquele documento) — Staging Host e Production Embedding Provider — sem provisionar, sem implantar, sem implementar, sem usar credenciais reais, sem chamar LLM/embedding de produção, sem iniciar nenhum outro Epic da Wave 7.

Este documento **não decide** — apresenta análise técnica grounded em código real e um Decision Brief objetivo para a escolha do Founder. Nenhuma das duas decisões finais é registrada como Founder Decision na governança (§6); apenas a análise em si é registrada como missão concluída.

---

## Parte 1 — Staging Host

### 1.1 Requisitos herdados do Deployment Contract (W7-5, já aprovado — não reabertos aqui)

Staging precisa rodar exatamente a topologia já definida em `docker-compose.yml`: 3 serviços (`api`, `web`, `database`), sem serviço adicional, via `docker compose` puro — **sem Kubernetes, sem introduzir nova plataforma sem necessidade concreta demonstrada** (restrição já vigente desde o Technical Design W7-5 §4, reafirmada aqui). A pergunta desta análise não é "que topologia usar" (já respondida no Technical Design W7-1 §3) — é **onde rodar essa topologia já definida**.

### 1.2 Matriz de requisitos mínimos

| Dimensão | Requisito mínimo | Base |
|---|---|---|
| **CPU** | 2 vCPU | `database` (Postgres+pgvector, inclui construção de índice vetorial) tipicamente precisa de ~1 vCPU sob carga de validação; `api` (Uvicorn, um processo) e `web` (Next.js standalone) são leves em isolamento, mas os 3 competem pelo mesmo host — 2 vCPU dá margem sem superdimensionar para um ambiente que não é de carga (isso é W7-6, não W7-1) |
| **RAM** | 4 GB | Postgres com pgvector se beneficia de RAM para cache de índice; `api`+`web` juntos tipicamente ficam abaixo de 1 GB combinados em uso de validação — 4 GB dá headroom sem superdimensionar |
| **Storage** | 20-40 GB | Imagens Docker (`python:3.12-slim`, `node:22-slim`, `pgvector/pgvector:pg16`) + volume `aipmo_postgres_data` (20 migrations + dados reais de validação, ainda pequenos nesta fase) + margem de log/backup local |
| **Sistema operacional** | Qualquer Linux com Docker Engine + plugin `docker compose` | Portabilidade é exatamente a garantia que containerização dá — recomendação: Ubuntu LTS (24.04), por ser o mesmo runner que já roda o CI real deste repositório (`.github/workflows/ci.yml`, `ubuntu-latest`), reduzindo superfície de comportamento não testado |
| **Rede/DNS/TLS** | Uma origem alcançável (subdomínio ou IP:porta) para `web` (porta 3000) e `api` (porta 8000); `CORS_ALLOWED_ORIGINS` do `api` deve apontar exatamente para a origem real do `web`. TLS recomendado mas não estruturalmente obrigatório para esta fase — AR-18 §7 já define staging como "ambiente de validação interna, não pré-lançamento público" (acesso controlado, não exposição pública) | `docker-compose.yml` atual, AR-18 §7 |
| **Persistência PostgreSQL** | Volume persistente sobrevivendo a restart de container (`aipmo_postgres_data` já modelado) — nunca dados de produção copiados para cá (AR-18 §7) | `docker-compose.yml`, `PRI-008` |
| **Acesso administrativo** | Acesso restrito (SSH ou console equivalente) a um conjunto nomeado de operadores — nunca um painel administrativo publicamente exposto | Convenção institucional já usada em `PRI-009` |
| **Isolamento de staging** | Host/conta inteiramente distinto de produção — nunca o mesmo processo, nunca a mesma instância de banco (AR-18 §7, já vigente) | AR-18 §7 |
| **Estratégia de deployment** | Reutilizar `PRI-009` §2 (Build → Validate → Migrate → Deploy → Readiness → Smoke → Promote) apontado ao host de staging — nenhuma ferramenta de deploy nova | `PRI-009`, Technical Design W7-5 |

### 1.3 Opção A — VM self-hosted (própria ou de um provedor de infraestrutura genérico)

Uma única máquina virtual (ou física) rodando Docker Engine + `docker compose`, satisfazendo a matriz acima diretamente.

- **Compatibilidade com o Deployment Contract:** total — `docker compose build`/`up`/`run` executam exatamente como já documentado em `PRI-009`, sem tradução para nenhum formato proprietário.
- **Custo operacional esperado:** ordem de grandeza baixa — uma VM de 2 vCPU/4 GB em qualquer provedor de infraestrutura genérico (o nome do provedor é uma decisão de procurement, não arquitetural — §4) tipicamente custa uma fração pequena de um orçamento mensal de plataforma; se já existir hardware próprio disponível, custo marginal é próximo de zero.
- **Riscos:** responsabilidade operacional recai sobre a equipe (patch de SO, renovação de TLS se usado, monitoramento básico de disco/memória) — nenhum desses itens tem automação hoje neste repositório (confirmado: nenhum script de provisionamento além dos já existentes `scripts/prepare-env.sh`/`scripts/rc2-db.sh`, ambos para ambiente local).
- **Esforço de adoção:** mínimo — os mesmos comandos de `PRI-009` funcionam sem alteração.

### 1.4 Opção B — Container hosting gerenciado (ex.: plataformas tipo Fly.io/Render/Railway)

Avaliada exclusivamente porque o Founder pediu comparação — **só deveria ser escolhida se trouxer benefício concreto**, não por padrão.

- **Benefício potencial real:** menos responsabilidade operacional de SO (sem patch manual), TLS/DNS frequentemente automáticos, deploy via `git push`.
- **Custo arquitetural real, não hipotético:** a maioria dessas plataformas não consome `docker-compose.yml` diretamente — exige tradução para um manifesto proprietário (ex.: `fly.toml`, blueprint YAML específico), o que é, na prática, introduzir uma ferramenta de deployment nova, algo que o Technical Design W7-5 explicitamente evitou (§4, "sem introduzir Kubernetes/service mesh/vault/blue-green/GitOps sem gap real"). Uma plataforma de deploy proprietária é o mesmo tipo de introdução, em grau menor.
- **Risco técnico real e não verificado:** nem toda oferta de Postgres gerenciado dessas plataformas suporta a extensão `pgvector` nativamente — isso precisaria ser confirmado *por provedor específico* antes de qualquer compromisso, o que este documento não pode fazer sem escolher um provedor primeiro (dependência circular com a própria decisão de procurement).
- **Custo operacional esperado:** tipicamente mais alto que uma VM equivalente, por cobrar separadamente por serviço (aqui, 2 serviços de app + 1 addon de banco) e por conveniência.
- **Quando faria sentido:** se a equipe operacional real for pequena o suficiente para que o custo de operação manual da Opção A supere a diferença de custo mensal — um julgamento de negócio, não arquitetural.

### 1.5 Opção C — Infraestrutura já disponível no projeto

**Confirmado, por busca direta no repositório, que não existe.** Nenhum arquivo de estado de infraestrutura (`*.tfstate`), nenhum manifesto de plataforma (`fly.toml`, `render.yaml`), nenhum workflow de deploy além do `ci.yml` (que só valida, nunca implanta — achado já registrado no Technical Design W7-5), e nenhuma referência a um provedor de nuvem específico em `docs/` além de menções incidentais sem relação com hospedagem real. **Esta opção não está disponível hoje** — não é recusada por preferência, é inexistente por evidência.

### 1.6 Recomendação técnica

**Opção A (VM self-hosted)** — introduz zero ferramenta de deployment nova (os comandos de `PRI-009` funcionam sem tradução), é a extensão mais direta da decisão de containerização já tomada em W7-5, e evita o risco não verificado de suporte a `pgvector` de um addon gerenciado. A escolha do provedor/conta específico onde essa VM existirá — e se um orçamento existente já cobre isso — é uma decisão de procurement (§4), não arquitetural.

---

## Parte 2 — Production Embedding Provider

### 2.1 Contrato real que um provider de produção deve implementar

Grounded diretamente em `src/services/knowledge_platform/embedding_provider.py` (código real, lido nesta análise, não assumido):

```python
class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...
```

Um provider real precisa apenas satisfazer esse `Protocol` — mesma disciplina já usada por `LLMProvider`/`ProductionLLMProvider` (Wave 3), reutilizando o padrão de seam existente, **sem criar um novo registry** (a fábrica `get_embedding_provider()` já existe e só precisa ganhar um novo `if provider_name == "<nome-escolhido>"`, exatamente como `get_provider()` já faz para `LLMProvider`).

### 2.2 Achado crítico, com impacto direto sobre a escolha: dimensionalidade hoje é 16 (mock), não real

`src/database/models.py`:
```python
KNOWLEDGE_EMBEDDING_DIM = 16
...
embedding = Column(Vector(KNOWLEDGE_EMBEDDING_DIM), nullable=False)
```

16 é um valor de teste/mock (`MockEmbeddingProvider` gera um vetor de 16 floats a partir de um hash SHA-256 do texto — determinístico, sem semântica real). **Nenhum provider real de mercado produz vetores de 16 dimensões** — os candidatos avaliados abaixo variam de 512 a 3072. Isso significa que **qualquer escolha de provider real exige uma migration alterando a dimensão da coluna `chunks.embedding`**, e — porque espaços vetoriais de modelos diferentes não são comparáveis entre si — **qualquer chunk já indexado (hoje, apenas com vetores mock de 16 dimensões) precisa ser reembutido (re-embedded) do zero**, não apenas migrado. Isso não é uma perda real de valor: os vetores mock não carregam semântica (não há RAG de produção validado hoje), então não há "relevância de produção" a perder — mas é um custo de implementação real que qualquer escolha, sem exceção, vai pagar. Isso também define a resposta à "estratégia de troca futura" (§2.4): trocar de provider no futuro sempre vai exigir o mesmo custo — reembedding completo — independente de qual provider for escolhido agora.

A busca de similaridade (`vector_repository.py`) já usa `cosine_distance` — a métrica padrão para a esmagadora maioria dos modelos de embedding modernos (todos os candidatos abaixo são otimizados para similaridade de cosseno). Nenhuma mudança de métrica é necessária, apenas de dimensão.

O tamanho de chunk atual (`CHUNK_SIZE_CHARS = 500`, `knowledge_repository.py`) é pequeno o suficiente (≈100-150 tokens) para caber folgadamente na janela de contexto de qualquer candidato abaixo — **limite de contexto não é um fator decisório real nesta comparação**.

A chamada de embedding acontece de forma **síncrona e bloqueante** em dois pontos reais do código: por chunk, dentro do loop de `KnowledgeRepository.index()` (chamado sincronamente por `DocumentIngestionService.upload()` — ou seja, dentro da própria requisição HTTP `POST /documents`), e uma vez por consulta, dentro de `KnowledgeRepository.search()` (chamado sincronamente por `RagPipeline.retrieve()`, que por sua vez está no caminho de qualquer Advisor que use RAG, ex. `POST /api/document-advisor/ask`). **Latência do provider de embedding impacta diretamente a latência percebida pelo usuário em dois fluxos reais**, não é um custo de background isolável hoje.

### 2.3 Comparação de alternativas reais

| Critério | Voyage AI | OpenAI (`text-embedding-3-*`) | Cohere (`embed-v3`, multilingual) | Self-hosted (ex. `sentence-transformers` multilingual, open-source) |
|---|---|---|---|---|
| **Aderência ao contrato atual** | Total — `embed(text) -> list[float]` mapeia 1:1 para uma chamada de API | Total — mesma forma | Total — mesma forma | Total, e sem chamada de rede — roda como função local/serviço interno |
| **Qualidade PT/EN corporativo** | `voyage-multilingual-2` cobre 100+ idiomas incl. PT, projetado para retrieval de domínio corporativo/técnico; parceiro de embeddings recomendado oficialmente pela própria Anthropic (mesma família de provider já usada por `LLM_PROVIDER=anthropic`) | Boa, `text-embedding-3-large` é forte em benchmarks multilíngues gerais | Boa, `embed-v3` tem variante multilingual dedicada, historicamente forte em retrieval corporativo | Variável — modelos multilíngues open-source (ex. `paraphrase-multilingual-mpnet-base-v2`) tendem a ficar atrás dos modelos comerciais mais recentes em benchmarks de retrieval, mas são adequados para validação inicial |
| **Dimensionalidade** | 1024 (`voyage-3`) ou 512 (`voyage-3-lite`) | 1536 (`small`) ou 3072 (`large`) | 1024 | Tipicamente 384-768, dependendo do modelo escolhido |
| **Limite de contexto** | ~32.000 tokens | ~8.191 tokens | ~512 tokens (varia por modelo) | Tipicamente 256-512 tokens | 
| **Latência esperada** | Chamada de rede externa, mesma ordem de grandeza de uma chamada Anthropic já em produção no código (`ProductionLLMProvider`) | Chamada de rede externa, ordem de grandeza comparável | Chamada de rede externa, ordem de grandeza comparável | **Sem chamada de rede** — latência limitada por CPU/GPU local, pode ser mais previsível mas soma carga computacional ao próprio host |
| **Custo** | Cobrança por token, tipicamente competitiva para embeddings | Cobrança por token, mercado mais maduro/competitivo | Cobrança por token, ordem de grandeza comparável | Sem custo por chamada — custo é de infraestrutura (CPU/GPU do host) |
| **Disponibilidade** | SLA de provider comercial | SLA de provider comercial, maior maturidade operacional (mais tempo de mercado) | SLA de provider comercial | Depende inteiramente da disponibilidade do próprio host de staging/produção — sem terceiro no caminho crítico |
| **Segurança/tratamento de dados** | Texto de documentos corporativos sai da infraestrutura própria para o provider — exige revisão de DPA/termos de processamento de dados antes de uso com conteúdo real (decisão de procurement/legal, §4) | Mesma consideração — sai da infraestrutura própria | Mesma consideração — sai da infraestrutura própria | **Nenhum dado sai da infraestrutura própria** — vantagem estrutural real para documentos corporativos sensíveis |
| **Lock-in** | Médio — trocar de provider sempre exige reembedding completo (§2.2), independente de qual for escolhido; nenhum candidato é estruturalmente "mais preso" que outro nesse quesito | Médio, mesma razão | Médio, mesma razão | Baixo quanto a dependência de vendor externo, mas ainda sujeito ao mesmo custo de reembedding ao trocar de modelo |
| **Esforço de implementação** | Baixo — uma classe nova (`VoyageEmbeddingProvider`) implementando o `Protocol` já existente, mesmo padrão de `ProductionLLMProvider`; nenhum SDK novo além do já usado pela família Anthropic (parceria oficial) | Baixo — mesma forma, requer nova dependência (`openai` SDK) não presente em `requirements.txt` hoje | Baixo — mesma forma, requer nova dependência (`cohere` SDK) não presente hoje | Médio-alto — requer decidir *onde* o modelo roda (dentro do próprio container `api`? um serviço novo?), gerenciar download/cache do modelo, e dimensionar CPU/GPU adicional no host de staging/produção |

### 2.4 Impacto sobre documentos já indexados e estratégia de troca futura

- **Impacto imediato de qualquer escolha:** migration de schema (`chunks.embedding`, nova dimensão) + reembedding completo de todo conteúdo já ingerido. Nenhuma perda real de valor (§2.2) — apenas esforço de execução, a ser feito uma única vez na implementação (fora do escopo desta análise).
- **Estratégia de troca futura (qualquer provider → outro):** sempre exige o mesmo procedimento — nova migration de dimensão + reembedding completo de todos os chunks, porque vetores de modelos diferentes não são comparáveis entre si mesmo com a mesma dimensão nominal. Não há forma de tornar uma troca futura "barata" pela escolha de hoje — o único fator que reduz a *probabilidade* de precisar trocar é escolher um modelo de provider estabelecido e improvável de ser descontinuado.

### 2.5 Recomendação técnica

**Voyage AI**, condicionado à confirmação de procurement/legal (§4) — é o único candidato que soma duas vantagens arquiteturais concretas simultaneamente: (1) parceria oficial já reconhecida pela própria Anthropic, cujo SDK/família de conta já está em uso neste codebase para `LLM_PROVIDER=anthropic`, reduzindo a superfície de integração nova; (2) `voyage-multilingual-2` cobre PT/EN nativamente, sem necessidade de um modelo separado por idioma. **Alternativa self-hosted é a segunda recomendação técnica** caso a decisão de procurement/segurança de dados (§4) determine que nenhum texto corporativo pode sair da infraestrutura própria — nesse cenário, o critério de segurança de dados supera o de esforço de implementação.

---

## Parte 3 — Decision Gate

### `STAGING HOST`

- **RECOMMENDED:** Opção A — VM self-hosted, satisfazendo a matriz de §1.2 (2 vCPU / 4 GB RAM / 20-40 GB storage / Ubuntu LTS / Docker + `docker compose`), reaproveitando o Deployment Contract de `PRI-009` sem tradução.
- **ALTERNATIVES:** Opção B (container hosting gerenciado — só se benefício operacional concreto superar o custo de introduzir uma ferramenta de deploy nova e o risco não verificado de suporte a `pgvector`); Opção C — confirmada inexistente, não é uma alternativa real hoje.
- **DECISION REQUIRED:** qual conta/provedor específico hospedará a VM (ou, se a Opção B for preferida, qual plataforma gerenciada) — **decisão de procurement/infraestrutura, não arquitetural**. Este documento não pode nomear um provedor sem essa escolha do Founder.

### `EMBEDDING PROVIDER`

- **RECOMMENDED:** Voyage AI (`voyage-multilingual-2` ou `voyage-3`), condicionado à aprovação de tratamento de dados.
- **ALTERNATIVES:** OpenAI (`text-embedding-3-large`) ou Cohere (`embed-v3` multilingual) — paridade técnica próxima, ambos introduzem um vendor/SDK novo sem a vantagem de parceria já existente com Anthropic; self-hosted open-source — preferível apenas se a restrição de dados corporativos não poderem sair da infraestrutura própria for confirmada como não-negociável.
- **DECISION REQUIRED:** aprovação formal de tratamento de dados/DPA com o provider externo escolhido (ou confirmação de que dados corporativos não podem sair da infraestrutura, forçando a alternativa self-hosted) — **decisão de procurement/segurança/legal, não arquitetural**. A dimensão exata do vetor (dependente do modelo escolhido dentro do provider) também é uma decorrência dessa escolha, não uma decisão arquitetural separada.

---

## Parte 4 — Impacto sobre o W7-1: sequência proposta

A sequência mandatada pelo Founder foi verificada contra o código real (Deployment Contract de `PRI-009`, Configuration Contract e Readiness de W7-5, e as duas análises acima) e **nenhum ajuste é necessário** — nada no código demonstra que outra ordem seja obrigatória:

```
Provision Staging → Deploy → /health + /ready → Smoke Test →
Production LLM Validation → Production Embedding Provider Implementation →
Embedding Validation → Integrated AI Validation → Evidence
```

Notas de grounding, sem alterar a sequência:

- **"Deploy"** aqui corresponde à execução completa do procedimento já documentado em `PRI-009` §2 (Build → Validate → Migrate → Deploy), não um passo novo — nenhuma expansão necessária neste documento.
- **"Production LLM Validation" não depende de "Production Embedding Provider Implementation"** — confirmado por código: `ProductionLLMProvider` (Anthropic) e `EmbeddingProvider` são seams inteiramente independentes, sem import cruzado, sem variável de ambiente compartilhada além de `ENVIRONMENT`. Isso significa que, tecnicamente, os dois poderiam correr em paralelo assim que staging existir — mas a sequência proposta pelo Founder (LLM primeiro, embedding depois) não está errada, apenas não é a única ordem tecnicamente válida. Mantida como está, por não haver evidência de código que a torne incorreta.
- **"Embedding Provider Implementation" inclui, obrigatoriamente, a migration de dimensão + reembedding completo** (§2.2/§2.4) — não é apenas escrever uma classe nova.
- **"Integrated AI Validation" tem uma pré-condição de risco já registrada** (Technical Design W7-1 §4, não reaberta aqui): o gap de observability (`correlation_id` ausente em `ai_foundation/observability.py`/`audit_integration.py`/`executive_orchestrator/orchestrator.py`) limita a capacidade de diagnosticar essa etapa ponta a ponta — mencionado aqui apenas como risco herdado, não resolvido nesta análise.

---

## O que não foi feito nesta missão (verbatim das restrições do Founder)

Nenhum staging foi provisionado. Nenhum deployment foi executado. Nenhum código foi implementado (nenhuma classe `EmbeddingProvider` nova, nenhuma migration). Nenhuma credencial real foi utilizada. Nenhuma chamada a LLM/embedding de produção foi realizada. Nenhum outro Epic da Wave 7 foi iniciado.

---

## Registro de governança

Esta missão — a produção da Decision Analysis em si — está concluída e é registrada em `docs/product/stratech-v2/DECISION-LOG.md` (D-174). **As duas escolhas finais (provedor de host de staging; provedor de embedding de produção) não são registradas como Founder Decision** — permanecem explicitamente pendentes da escolha do Founder, per instrução direta desta missão.
