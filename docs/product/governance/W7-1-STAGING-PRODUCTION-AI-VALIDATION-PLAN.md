# W7-1 — Staging & Production AI Validation Plan

**Autorização:** "Founder Decision — W7-1 Staging & Production AI Validation — Próxima Etapa Institucional". A Etapa 6 do Production Embedding Implementation (`W7-1-PRODUCTION-EMBEDDING-EXECUTIVE-EVIDENCE.md`, D-177) está **ratificada como aprovada**, mas o **W7-1 permanece explicitamente NÃO encerrado** — nenhuma chamada real a LLM/Embedding de produção foi feita, nenhum staging foi provisionado, nenhuma validação integrada de IA em staging existe. Esta missão autoriza exclusivamente a produção deste documento de **planejamento executivo/técnico**. Nenhuma infraestrutura provisionada, nenhum deployment executado, nenhuma credencial real usada, nenhuma chamada paga realizada, nenhuma migration executada fora do ambiente de teste já existente, nenhuma implementação adicional sem necessidade comprovada, nenhum código escrito além de correção documental de tooling explicitamente justificada (nenhuma foi necessária — ver Seção 2).

---

## 1. Executive Summary

O W7-1 tem hoje toda a **base técnica implementada e testada** para a validação real de staging/produção, mas **nenhuma validação real jamais foi executada**:

- `ProductionLLMProvider` (Anthropic) implementado, testado com doubles, nunca chamado com credencial real.
- `VoyageEmbeddingProvider` (`voyage-4`, dimensão 1024) implementado, testado com doubles, nunca chamado com credencial real (D-177).
- Configuration Contract (`src/api/startup_config.py`) falha fechado em staging/produção para `DATABASE_URL`, `API_KEY`, `LLM_PROVIDER`/`ANTHROPIC_API_KEY`, `EMBEDDING_PROVIDER`/`VOYAGE_API_KEY`, `CORS_ALLOWED_ORIGINS` — mecanismo real, testado, não hipotético.
- Deployment Contract (`docker-compose.yml`, `PRI-009`) cobre `api`/`web`/`database` (pgvector) como três artefatos containerizados independentes, com `/health`, `/ready`, Release Identity (`RELEASE_SHA`) e Migration Discipline (passo explícito, não bundlado) já implementados.
- Smoke test (`web/e2e/smoke.spec.ts`) já é parametrizável por `PLAYWRIGHT_BASE_URL`/`SMOKE_BACKEND_URL`/`SMOKE_LOGIN_*`, pronto para apontar a um staging real sem alteração de código.

O que falta para o encerramento do W7-1 é **inteiramente execução, não arquitetura**: provisionar um host, popular as credenciais reais (gates de negócio, não técnicos), rodar o protocolo de deployment já existente, e produzir evidência real de cada camada (LLM, Embedding, Knowledge/RAG, Executive Intelligence, Smoke/Browser). Este documento define esse protocolo em detalhe executável, sem executá-lo.

**Dois achados de divergência documental, elevados nesta missão (Seção 2), não corrigidos** (fora do escopo desta missão exclusivamente documental/de planejamento — nenhum é um erro de tooling que bloqueie a produção deste plano).

**Recomendação (Seção 17):** GO para o Founder autorizar a **execução real** do protocolo abaixo, condicionado à resolução dos gates externos (Seção 5). Este documento não inicia nenhuma execução por si só.

---

## 2. Current State (revalidação mecânica, 2026-08-13)

Revalidação feita por leitura direta do código/config/docs atuais em `HEAD` (`1fb0dd0`), não por confiança na Executive Evidence anterior, per mandato explícito desta missão.

| Item mandatado para revalidação | Estado confirmado | Evidência |
|---|---|---|
| `VoyageEmbeddingProvider` | Presente, implementa `EmbeddingProvider` Protocol via `httpx` REST direto | `src/services/knowledge_platform/embedding_provider.py` |
| Model `voyage-4`, dimensão 1024 | Confirmado (`model_name="voyage-4"`, `dimension=KNOWLEDGE_EMBEDDING_DIM`) | idem; `KNOWLEDGE_EMBEDDING_DIM = 1024` em `src/database/models.py` |
| Migration 0021 | Presente, `vector(16)`→`vector(1024)` + `embedding_provider`/`embedding_model` | `alembic/versions/0021_production_embedding_provider.py` |
| Proveniência persistida | `KnowledgeRepository.index()` grava `embedding_provider`/`embedding_model` em cada `Chunk` | `src/services/knowledge_platform/knowledge_repository.py` |
| `EMBEDDING_PROVIDER` wiring | Presente em `docker-compose.yml` (`api.environment`), default `mock` | `docker-compose.yml:32` |
| `VOYAGE_API_KEY` wiring | Presente em `docker-compose.yml` (`api.environment`), default vazio | `docker-compose.yml:33` |
| `ProductionLLMProvider` | Presente, `model="claude-3-5-sonnet-20241022"` (default ainda não atualizado — fora de escopo mudar aqui), fail-fast sem `ANTHROPIC_API_KEY` | `src/llm/providers/production_provider.py` |
| Config Anthropic | `LLM_PROVIDER`/`ANTHROPIC_API_KEY` presentes em `docker-compose.yml` e no Configuration Contract | `docker-compose.yml:27-28`, `src/api/startup_config.py` |
| `GET /health` | Presente, retorna `release` (`RELEASE_SHA`) em ambos os serviços | `src/main.py`, `web/app/api/health/route.ts` |
| `GET /ready` | Presente, checa problemas de configuração + `SELECT 1` real no banco | `src/main.py` |
| `RELEASE_SHA` | Bake em build-time via `ARG GIT_SHA`/`ENV RELEASE_SHA` — corretamente ausente do bloco `environment:` do `docker-compose.yml` (não é uma variável de runtime) | `Dockerfile`, `web/Dockerfile` |
| Frontend containerizado | Confirmado, serviço `web` separado, build próprio, `depends_on: api` | `docker-compose.yml:47-65` |
| Disciplina de migration | Confirmado: `command:` do serviço `api` não inclui `alembic upgrade head` — passo explícito e separadamente falhável, per `PRI-009` §2 | `docker-compose.yml:45`, `PRI-009` §2 |
| Smoke test parametrizável | Confirmado, `PLAYWRIGHT_BASE_URL`/`SMOKE_BACKEND_URL`/`SMOKE_LOGIN_EMAIL`/`SMOKE_LOGIN_PASSWORD`/`SMOKE_LOGIN_ORGANIZATION`, sem credencial hardcoded | `web/e2e/smoke.spec.ts` |
| Configuration Contract staging/produção + fail-fast | Confirmado: `DATABASE_URL` sqlite/ausente, `API_KEY` ausente, `LLM_PROVIDER=mock`, `LLM_PROVIDER=anthropic` sem `ANTHROPIC_API_KEY`, `EMBEDDING_PROVIDER=mock`, `EMBEDDING_PROVIDER=voyage` sem `VOYAGE_API_KEY`, `CORS_ALLOWED_ORIGINS` ausente — todos geram problema de boot | `src/api/startup_config.py` |
| `docker-compose.yml` atual | Lido por completo nesta revalidação; três serviços (`api`/`web`/`database`), `database` = `pgvector/pgvector:pg16` com `healthcheck: pg_isready` | `docker-compose.yml` |
| Requisitos reais de PostgreSQL/pgvector | Confirmado: `CREATE EXTENSION IF NOT EXISTS vector` já roda na migration `0016`; imagem `pgvector/pgvector:pg16` já traz o binário da extensão pré-instalado | `alembic/versions/0016_*`, `docker-compose.yml:73` |
| `PRI-008`/`PRI-009` | Ambos lidos por completo nesta revalidação | ver divergências abaixo |
| D-170 em diante | Revisados via `DECISION-LOG.md` (D-170 a D-177) — nenhuma decisão anterior contradita pelo código atual, exceto as duas divergências documentais abaixo | `docs/product/stratech-v2/DECISION-LOG.md` |

### Divergências encontradas e elevadas explicitamente (não corrigidas nesta missão)

Per instrução do Founder ("Não assuma que a Executive Evidence anterior continua correta... Qualquer divergência deve ser elevada explicitamente"), dois gaps documentais reais foram encontrados. Nenhum dos dois é um erro de tooling que impeça a produção deste plano, e nenhum dos dois é um bloqueio técnico para a execução real do W7-1 — ambos são apenas texto de runbook desatualizado, registrados aqui como GAP a corrigir em uma missão futura com escopo explícito para isso:

1. **`PRI-009-production-deployment-runbook.md` §4** — o exemplo de `curl -sf http://localhost:8000/health` ainda mostra o corpo de resposta pré-W7-5-Etapa-3 (`{"status":"healthy","service":"AI PMO Copilot"}`), **sem o campo `"release"`** adicionado quando o Release Identity foi implementado. O comportamento real do endpoint está correto (confirmado em `src/main.py`); apenas o exemplo do runbook está desatualizado.
2. **`PRI-008-production-backup-restore-runbook.md` §4** — mesmo gap, mesmo exemplo desatualizado de `/health`, encontrado nesta revalidação (não documentado em nenhuma Executive Evidence anterior).
3. **`.env.example`** — não documenta `ENVIRONMENT` nem `RELEASE_SHA` em lugar nenhum, apesar de `ENVIRONMENT` ser a variável mais estrutural de todo o Configuration Contract (é ela que decide se `staging`/`production` fail-fast está ativo). `RELEASE_SHA` corretamente não pertenceria a um `.env` (é bake de build), mas sua ausência total de menção no arquivo pode confundir quem operar deployment real sem ler o `Dockerfile`.

Nenhuma dessas três divergências bloqueia a produção deste plano nem a execução real do W7-1 — todas são lacunas de exemplo/documentação, não de comportamento. Estão listadas como Risco (Seção 15) e devem ser corrigidas antes ou durante a execução real do W7-1, como item de higiene documental, não como bloqueio.

**Confirmação de Preservação Arquitetural (mandato desta missão, §13):** nenhuma mudança estrutural foi encontrada como necessária em `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, `ExecutiveOrchestrator`, os 8 Enterprise Advisors, Workflow Runtime, Event Pipeline, Enterprise Domain, Knowledge Platform, ou qualquer contrato público existente. Todos os componentes revisados nesta Seção já suportam a validação real descrita neste plano sem alteração de código. Caso a execução real do W7-1 revele necessidade de mudança estrutural, a execução deve parar e o achado deve ser elevado ao Founder — não decidido silenciosamente.

---

## 3. Staging Architecture

Topologia derivada exclusivamente do Deployment Contract já aprovado (D-175, `docker-compose.yml`), sem introdução de Kubernetes, Terraform, service mesh, gerenciador de segredos ou stack de observabilidade nova.

```
                 ┌──────────────────────────────────────────────┐
                 │                  VM staging                   │
                 │      (Linux, Docker + Docker Compose)         │
                 │                                                │
Internet ──HTTP──▶  web (Next.js, :3000)                          │
                 │     │  BACKEND_URL=http://api:8000              │
                 │     ▼                                          │
                 │  api (FastAPI, :8000)                           │
                 │     │  DATABASE_URL=postgresql://…@database:5432│
                 │     ├──HTTPS──▶ Anthropic API (LLM_PROVIDER)    │
                 │     ├──HTTPS──▶ Voyage AI API (EMBEDDING_PROVIDER)
                 │     ▼                                          │
                 │  database (pgvector/pgvector:pg16, :5432)       │
                 │     volume: aipmo_postgres_data                 │
                 └──────────────────────────────────────────────┘
```

| Aspecto | Definição |
|---|---|
| Recursos mínimos da VM | 2 vCPU, 4 GB RAM, 20-40 GB de storage (aprovado em D-175) |
| SO | Linux (qualquer distribuição com suporte a Docker Engine + Compose plugin) |
| Runtime | Docker + `docker compose` — mesma composição de `docker-compose.yml`, sem alteração de imagens |
| Volumes persistentes | `aipmo_postgres_data` (nomeado, mesmo já definido) — único volume com estado real |
| Rede | Rede padrão do Compose (`bridge`) entre os 3 serviços; **achado de revisão:** o `docker-compose.yml` atual expõe a porta `5432` do `database` ao host (`ports: ["5432:5432"]`) — adequado para desenvolvimento local, mas em um host de staging real exposto à internet essa porta não deveria ser publicamente alcançável (ver Risco, Seção 15) |
| Portas expostas externamente | `8000` (api), `3000` (web) — ou ambas atrás de um proxy reverso simples, se disponível; `5432` deve permanecer interno à rede do Compose em staging real |
| Health/Readiness | `GET /health` (api e web, liveness) + `GET /ready` (api, config + DB real) — já implementados, nenhum mecanismo novo necessário |
| Storage | Volume Docker nomeado é suficiente na escala atual (sem projeção de volume real de cliente corporativo — mesmo ponto já registrado em `PRI-005`) |
| DNS/TLS | **Não necessário nesta etapa** — staging é um ambiente de validação técnica, acessado por Founder/Tech Lead, não por usuários finais; acesso via IP da VM + porta é suficiente para o protocolo de validação deste documento. TLS é recomendado antes de qualquer exposição mais ampla, mas não é um requisito bloqueante para a validação técnica descrita aqui — nenhuma necessidade concreta demonstrada ainda |
| Variáveis de ambiente/segredos | Ver Seção 4 (Configuration & Secrets Checklist) |
| Banco de dados | PostgreSQL real via `pgvector/pgvector:pg16` — mesma imagem já usada em `docker-compose.yml`, extensão `vector` já habilitada pela migration `0016` |
| Migrations | `docker compose run --rm api alembic upgrade head` — passo explícito, antes do `api` subir (já a disciplina corrente, `PRI-009` §2) |
| Identidade de release | `RELEASE_SHA` observável em `GET /health` de ambos os serviços após o build (`--build-arg GIT_SHA=$(git rev-parse HEAD)`) |
| Logs para evidência | `docker compose logs api`/`web`/`database`, correlacionados por timestamp ao `release` observado em `/health` no momento de cada validação (Seção 13) |

Nenhuma decisão de *qual* provedor/conta hospedará a VM é tomada aqui — permanece decisão de procurement (Gate A, Seção 5), como já registrado em D-174/D-175.

---

## 4. Configuration Contract Checklist

Todas as variáveis abaixo são consumidas exclusivamente pelo Configuration Contract já implementado (`src/api/startup_config.py`, `web/lib/startup-config.ts`) e pelo `docker-compose.yml` atual — nenhuma variável nova é proposta. Nenhum valor real é registrado neste documento.

### A. Obrigatórias no boot (staging e produção)

| Variável | Serviço consumidor | Obrigatória? | Condição de fail-fast | Origem esperada |
|---|---|---|---|---|
| `ENVIRONMENT` | api, web | Sim | Valor fora de `dev`/`staging`/`production` | Definida pelo deployment (`staging` neste W7-1) |
| `DATABASE_URL` | api | Sim | Ausente ou apontando para SQLite | Fixo para o serviço `database` do Compose |
| `API_KEY` | api, web | Sim | Ausente | Segredo gerado/provisionado para este ambiente |
| `CORS_ALLOWED_ORIGINS` | api | Sim | Ausente | Origem real do `web` de staging |
| `RELEASE_SHA` | api, web (`/health`) | Sim (para rastreabilidade, não bloqueia boot) | N/A — bake em build-time, não runtime | `git rev-parse HEAD` no momento do build |

### B. Obrigatórias para LLM

| Variável | Serviço consumidor | Obrigatória? | Condição de fail-fast | Origem esperada |
|---|---|---|---|---|
| `LLM_PROVIDER` | api | Sim | `mock` em staging/produção | `anthropic` |
| `ANTHROPIC_API_KEY` | api (`ProductionLLMProvider`) | Sim quando `LLM_PROVIDER=anthropic` | Ausente | Gate C (Seção 5) |

### C. Obrigatórias para Embedding

| Variável | Serviço consumidor | Obrigatória? | Condição de fail-fast | Origem esperada |
|---|---|---|---|---|
| `EMBEDDING_PROVIDER` | api | Sim | `mock` em staging/produção | `voyage` |
| `VOYAGE_API_KEY` | api (`VoyageEmbeddingProvider`) | Sim quando `EMBEDDING_PROVIDER=voyage` | Ausente | Gate B (Seção 5) |

### D. Obrigatórias para o frontend

| Variável | Serviço consumidor | Obrigatória? | Condição de fail-fast | Origem esperada |
|---|---|---|---|---|
| `BACKEND_URL` | web | Sim | N/A (default `http://api:8000` funciona dentro do Compose) | `http://api:8000` (interno ao Compose) |
| `API_KEY` | web | Sim (mesma chave de A) | Ausente | Mesmo valor de A |
| `SESSION_SECRET` | web | Sim | Ausente | Segredo gerado para este ambiente |
| `WORKSPACE_PASSWORD` | web | Depende do modo de acesso configurado no frontend (fora do escopo deste plano alterar) | N/A | A confirmar junto do Gate A quando o host for definido |

### E. Operacionais/opcionais

| Variável | Serviço consumidor | Obrigatória? | Default atual |
|---|---|---|---|
| `DB_POOL_SIZE` | api | Não | `5` |
| `DB_MAX_OVERFLOW` | api | Não | `10` |
| `DB_POOL_TIMEOUT_SECONDS` | api | Não | `30` |
| `DB_POOL_RECYCLE_SECONDS` | api | Não | `1800` |
| `DB_POOL_PRE_PING` | api | Não | `true` |
| `RATE_LIMIT_MAX_REQUESTS` | api | Não | `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | api | Não | `60` |
| `GIT_SHA` (build arg, não runtime) | api, web (build) | Não (default `unknown`) | `unknown` |

Nenhuma variável fora desta lista foi encontrada como genuinamente exigida pelo código atual.

---

## 5. Gates Externos

Separação rigorosa entre o que é arquitetura (já resolvida, Seções 3-4) e o que é dependência externa (não decidida por esta missão nem por este Tech Lead).

| Gate | Descrição | Estado |
|---|---|---|
| A. Staging Host | Provedor/conta que hospedará a VM (D-174/D-175: arquitetura aprovada, host específico não escolhido) | **PENDING** — decisão de procurement do Founder |
| B. Voyage API Credential | `VOYAGE_API_KEY` real, associada a uma conta Voyage AI com o Data/DPA aplicável já resolvido | **PENDING** — depende do Gate D |
| C. Anthropic API Credential | `ANTHROPIC_API_KEY` real para o ambiente de staging (pode reutilizar ou não a credencial já usada em outro contexto — decisão do Founder) | **PENDING** |
| D. Data/DPA Approval | Aprovação de tratamento de dados com a Voyage AI (Business/Legal) — já registrada como pendente em D-175/D-177, não resolvida nesta missão | **PENDING** — bloqueia especificamente o envio de qualquer dado corporativo real à Voyage; **não bloqueia** validação com conteúdo sintético/controlado (Seção 8/9) |
| E. Outras dependências externas encontradas | Nenhuma nova identificada nesta revisão além das quatro acima | **NOT REQUIRED** (nenhuma outra dependência externa real encontrada) |

Nenhum desses gates é decidido, procurado ou negociado por esta missão — apenas classificado, per mandato explícito do Founder.

---

## 6. Deployment Protocol

Derivado literalmente do protocolo já registrado em `PRI-009` §2, expandido com os passos de validação de IA mandatados por esta missão (Seções 7-11). Nenhum passo abaixo é executado nesta missão.

| # | Etapa | Input | Comando/mecanismo existente | Resultado esperado | Evidência a coletar | GO | NO-GO | Rollback |
|---|---|---|---|---|---|---|---|---|
| 1 | Build | Código em `HEAD` da branch a promover | `docker compose build --build-arg GIT_SHA=$(git rev-parse HEAD)` | Imagens `api`/`web` construídas com `RELEASE_SHA` correto | Log de build, `RELEASE_SHA` esperado anotado | Build sem erro | Build falha | Não aplicável (nada implantado ainda) |
| 2 | Validate | Imagens construídas | `ruff check src tests` + suíte relevante (já rodada nesta revisão: 912 passed) | Suíte verde na revisão que será promovida | Output do comando | 0 falhas | Qualquer falha | Não promover o build |
| 3 | Release Identity | Imagens construídas | `GET /health` local (`docker compose up` local, se necessário) | `release` no `/health` corresponde ao SHA esperado | Corpo da resposta `/health` | Match confirmado | Mismatch | Rebuild |
| 4 | Provision | Gate A resolvido | Provisionamento da VM (fora do escopo desta missão) | VM com Docker + Compose disponível | Acesso SSH confirmado | VM acessível | VM indisponível | N/A |
| 5 | Configure | Checklist da Seção 4 | Popular `.env`/variáveis reais na VM (nunca commitadas) | Todas as variáveis de A-D presentes | Conferência manual do checklist (sem registrar valores) | Checklist completo | Variável obrigatória ausente | Corrigir antes de prosseguir |
| 6 | Database | VM configurada | `docker compose up -d database`, aguardar `healthcheck: pg_isready` | `database` saudável | `docker compose ps` | `healthy` | `unhealthy`/timeout | Investigar log do container; recriar volume se corrompido (`PRI-008` §5) |
| 7 | Migrate | `database` saudável | `docker compose run --rm api alembic upgrade head` | Schema na revisão `0021` (mais recente) | `alembic current` | Revisão esperada | Erro de migration | `PRI-008` §5 — restaurar backup pré-deploy (não aplicável em staging vazio; recriar `database` do zero) |
| 8 | Deploy API | Migration concluída | `docker compose up -d api` | Container `api` up | `docker compose ps` | Container `running` | Crash loop | Investigar logs; corrigir config; reexecutar passo 5 |
| 9 | Deploy Web | `api` up | `docker compose up -d web` | Container `web` up | `docker compose ps` | Container `running` | Crash loop | Investigar logs; corrigir config |
| 10 | Health | Ambos containers up | `curl /health` (api e web) | `200`, `release` correto em ambos | Corpo das respostas | `200` + release correto | `!= 200` ou release incorreto | Voltar ao passo 1 (rebuild) ou 8/9 (redeploy) |
| 11 | Readiness | `/health` verde | `curl /ready` (api) | `200 {"status":"ready"}` | Corpo da resposta | `200` | `503` com `problems` | Corrigir a variável listada em `problems` (Seção 4), reexecutar passo 5 |
| 12 | Smoke Test | `/ready` verde | `PLAYWRIGHT_BASE_URL=<staging> SMOKE_BACKEND_URL=<staging-api> npx playwright test e2e/smoke.spec.ts` | 4 checks verdes | Relatório do Playwright | Todos os checks verdes | Qualquer check falho | Investigar por camada (Seções 7-11) |
| 13 | AI Validation | Smoke verde | Protocolos das Seções 7-9 | Ver critérios de cada seção | Ver Seção 13 (Evidence Collection Plan) | Todos os protocolos GO | Qualquer protocolo NO-GO | Não promover; investigar a camada específica |
| 14 | Integrated Validation | AI Validation GO | Protocolo da Seção 10 | Cadeia completa exercitada com resposta HTTP válida | Ver Seção 13 | GO | NO-GO | Não promover |
| 15 | Promote/GO ou Rollback/NO-GO | Todos os passos anteriores GO | Decisão humana (Founder/Tech Lead) | W7-1 avança para Executive Evidence final | `docs/product/governance/W7-1-...-EXECUTIVE-EVIDENCE.md` (a produzir na execução real) | Todos os 20 critérios da Seção 14 atendidos | Qualquer critério não atendido | `docker compose down`, preservar logs coletados como evidência do que falhou |

---

## 7. Production LLM Validation

Protocolo mínimo para provar `ProductionLLMProvider` real, sem criar nenhuma chamada paralela direta ao provider — usa exclusivamente a abstração já existente (`get_provider()`, `src/llm/providers/factory.py`).

| Proof point | Como provar |
|---|---|
| Provider real (não mock) | `LLM_PROVIDER=anthropic` no ambiente de staging; confirmar via `GET /ready` que nenhum problema de config é reportado |
| Autenticação real | `ANTHROPIC_API_KEY` real presente (Gate C); uma chamada bem-sucedida já prova a autenticação — nenhum teste de autenticação isolado necessário |
| Chamada real | Disparar qualquer rota já existente que exercite um Advisor (ex.: `POST /risk-advisor/ask`) contra staging, com dados sintéticos |
| Resposta real | Resposta HTTP com conteúdo não determinístico/não idêntico a uma fixture de teste — evidência de que veio do modelo real, não de um double |
| Modelo usado | Confirmar no `TokenUsage`/log que o modelo é `claude-3-5-sonnet-20241022` (default atual do `ProductionLLMProvider`) |
| Latência | Medir o tempo de resposta HTTP da chamada — sem SLA definido ainda, apenas registrar como linha de base |
| Tratamento de erro | Cenário controlado: `ANTHROPIC_API_KEY` temporariamente inválida → confirmar que a rota retorna erro tratado (502, per `AdvisorExecutionError` já mapeado em `intelligence.py`), nunca um erro não tratado/500 cru |
| Observabilidade existente | `docker compose logs api` durante a chamada — nenhum mecanismo de observabilidade novo introduzido |
| Ausência de fallback mock | Confirmar por config (`LLM_PROVIDER=anthropic`, sem `mock` em nenhum ponto do ambiente) — o `get_provider()` factory não tem fallback silencioso, já confirmado por leitura de código |
| Ausência de segredo em log/resposta | Inspecionar manualmente a resposta HTTP e os logs coletados no passo anterior — `ANTHROPIC_API_KEY` nunca deve aparecer em nenhum dos dois |

**Conteúdo usado:** sintético/controlado (ex.: um "projeto de teste" criado especificamente para esta validação), nunca dado corporativo real — mesma restrição do Gate D aplicada aqui por precaução, mesmo que LLM não seja o gate bloqueado.

---

## 8. Production Embedding Validation

Protocolo mínimo para provar `VoyageEmbeddingProvider` real, sem estender o `Protocol` já aprovado (D-177) e sem enviar dado corporativo real antes do Gate D.

| Proof point | Como provar |
|---|---|
| Provider real | `EMBEDDING_PROVIDER=voyage` no ambiente; confirmar via `GET /ready` que nenhum problema de config é reportado |
| Modelo `voyage-4` | Confirmar `chunks.embedding_model = 'voyage-4'` no banco após a indexação (proveniência já persistida, Etapa 3 do D-177) |
| Dimensão exatamente 1024 | Query real: `SELECT vector_dims(embedding) FROM chunks WHERE embedding_provider = 'voyage' LIMIT 1;` deve retornar `1024` |
| Autenticação | `VOYAGE_API_KEY` real presente (Gate B); uma indexação bem-sucedida já prova a autenticação |
| Latência | Medir o tempo da chamada de indexação (log de aplicação ou timestamp do request) — linha de base, sem SLA definido |
| Tratamento de erro | Cenário controlado: `VOYAGE_API_KEY` temporariamente inválida → confirmar que a ingestão falha de forma tratada (`EmbeddingProviderConfigError`/`EmbeddingProviderUnavailableError`, já implementados), nunca um erro não tratado |
| Proveniência | `SELECT embedding_provider, embedding_model FROM chunks WHERE ...` confirma `'voyage'`/`'voyage-4'` persistidos junto do vetor |
| Ausência de fallback mock | Confirmar por config (`EMBEDDING_PROVIDER=voyage`) — `get_embedding_provider()` não tem fallback silencioso, confirmado por leitura de código |
| Ausência de segredo em log | Inspecionar `docker compose logs api` durante a indexação — `VOYAGE_API_KEY` nunca deve aparecer |
| Conteúdo enviado | **Exclusivamente sintético/controlado** (ex.: um documento de teste criado especificamente para esta validação, sem qualquer dado corporativo real) — obrigatório enquanto o Gate D (Data/DPA) permanecer `PENDING` |

---

## 9. Knowledge/RAG Validation

Cenário controlado provando a cadeia completa `documento → ingestão → chunking → embedding Voyage → vector(1024) → PostgreSQL/pgvector → retrieval semântico → contexto RAG → Advisor → citação`, usando exclusivamente os componentes já existentes e já testados com Postgres real (Etapa 4, D-177).

| Passo | Mecanismo existente | Evidência a coletar |
|---|---|---|
| 1. Upload de documento sintético | Rota de ingestão já existente (`documents_api`/`document_ingestion_service`) | ID do documento criado |
| 2. Chunking | `DocumentIngestionService` (já existente) | Contagem de chunks gerados |
| 3. Embedding Voyage | `KnowledgeRepository.index()` → `VoyageEmbeddingProvider.embed()` | `embedding_provider='voyage'`, `embedding_model='voyage-4'` persistidos por chunk |
| 4. Persistência `vector(1024)` | Coluna `chunks.embedding` | `vector_dims(embedding) = 1024` |
| 5. Retrieval semântico | `RagPipeline`/`VectorRepository` (já existentes, provider-agnósticos, confirmado em D-175) | Query de teste retorna os chunks esperados por similaridade semântica real (não por coincidência de mock hash) |
| 6. Contexto RAG no Advisor | `document-advisor/ask` (rota já existente) | Resposta cita o documento sintético carregado |
| 7. Citação | `cited_evidence` na resposta do Advisor | `source_type`/`source_id` apontam para o documento/chunk real |

**Como evidenciar que o embedding real (não mock) foi usado:** (a) proveniência persistida (`embedding_provider='voyage'`) confirmada por query direta no banco — prova definitiva, já implementada; (b) a busca semântica retorna resultados coerentes com o conteúdo real do documento sintético (não apenas o mesmo texto normalizado, como o `MockEmbeddingProvider` determinístico produziria) — prova funcional complementar.

---

## 10. Executive Intelligence Validation

Cenário mínimo ponta a ponta, usando exclusivamente as rotas já em produção (`src/api/routes/intelligence.py`) e a cadeia real já implementada e testada (`ExecutiveOrchestrator` → `AdvisorFramework` → Advisors), sem qualquer alteração a esses componentes.

**Cadeia real confirmada por leitura direta do código** (`src/services/executive_orchestrator/orchestrator.py`, `src/api/routes/intelligence.py`):

```
Evidence → Enterprise Advisor (via AdvisorFramework.run())
        → Explanation (por Advisor)
        → ExecutiveOrchestrator.run(): Seleção (selection_rule) → Execução
        → Correlação (correlate()) → Síntese (synthesize(), só para
          EXECUTIVE_BRIEFING/EXECUTIVE_NARRATIVE/RECOMMENDATION_PACKAGE/
          DECISION_SUPPORT) → Consolidação de Citações
          (_consolidate_citations(), na camada de composição da rota, não
          no Orchestrator) → CompositionTrace
        → Decision Support (POST /decision-support/ask) ou
          Executive Narrative (POST /executive-narrative/generate)
        → Resposta HTTP (DecisionSupportResponse/ExecutiveNarrativeResponse)
```

**Cenário mínimo proposto:** `POST /decision-support/ask` com uma pergunta cujo escopo (`scope`) resolva para um projeto/portfólio sintético já usado nas Seções 8-9 (garantindo que a evidência real recém-indexada via Voyage participe da correlação), contra staging real.

| Proof point | Como provar |
|---|---|
| Anthropic participa (Síntese) | `synthesis`/`answer` não-nulo na resposta, contendo conteúdo coerente e não idêntico a nenhuma fixture de teste |
| Voyage participa (Evidência) | Ao menos uma `citation` na resposta aponta para o documento sintético indexado na Seção 9 (`source_type`/`source_id` do chunk real) |
| `AdvisorFramework`/Advisors reais | `advisors_used` na resposta lista ao menos um Advisor real (não vazio, não hardcoded) |
| `CompositionTrace` | `composition_trace` na resposta contém `selection_signals`, `advisors_used` (com `had_evidence`), `correlations`, `synthesis_source_advisor_names` — todos os campos já implementados |
| Nenhuma alteração a Advisors/Orchestrator | Confirmado nesta missão (Seção 2) — nenhuma mudança necessária para este cenário |

---

## 11. Smoke/Browser Validation

Execução do smoke test já existente (`web/e2e/smoke.spec.ts`) contra o staging real, sem nenhuma alteração de código:

```bash
PLAYWRIGHT_BASE_URL=https://<staging-web> \
SMOKE_BACKEND_URL=https://<staging-api> \
SMOKE_LOGIN_EMAIL=<usuário sintético de staging> \
SMOKE_LOGIN_PASSWORD=<senha sintética> \
SMOKE_LOGIN_ORGANIZATION=<organização sintética> \
npx playwright test e2e/smoke.spec.ts
```

Cobre, pelos 4 checks já implementados: app alcançável (`/entrar`), `/api/health` do frontend saudável, `/ready` do backend verde, fluxo autenticado básico.

**Validação mínima de browser adicional** (manual, não automatizada — fora do escopo criar um novo teste E2E nesta missão): um único percurso humano, uma vez, confirmando visualmente:

```
Login → Dashboard → Decision Support (pergunta do cenário da Seção 10)
      → resposta com citações visíveis → Composition Trace visível/inspecionável
```

Explicitamente **não** um redesenho de UX nem uma certificação cross-browser — ambos fora de escopo (pertencem a um Epic próprio da Wave 7, se necessário).

---

## 12. Failure & Rollback Matrix

| Falha | Detecção | Impacto | Stop/Continue | Recuperação | Rollback | Evidência |
|---|---|---|---|---|---|---|
| `DATABASE_URL` inválida | `/ready` retorna 503 com `problems` | `api` não fica pronto | Stop | Corrigir variável, reiniciar `api` | N/A (nada em produção ainda) | Corpo do `/ready` |
| Falha de migration | `alembic upgrade head` retorna erro | Schema inconsistente | Stop | Investigar erro específico da migration | Recriar `database` do zero (staging não tem dado real a preservar) — em produção real seguiria `PRI-008` §5 (restaurar backup pré-deploy) | Log do comando `alembic` |
| API não fica ready | `/ready` 503 persistente após correção de config | Deploy bloqueado | Stop | Ver `problems` retornado, corrigir item específico (Seção 4) | Não promover `api` | Corpo do `/ready` |
| Frontend indisponível | `/health` do `web` não responde ou `!= 200` | Usuários sem acesso à UI | Stop | Investigar log do container `web` | `docker compose restart web`; se persistir, rollback de imagem | `docker compose logs web` |
| Falha de autenticação Anthropic | Chamada a Advisor retorna 502 (`AdvisorExecutionError` já mapeado) | Nenhuma resposta de IA gerada | Stop (para o cenário de validação) | Confirmar `ANTHROPIC_API_KEY` (Gate C) | N/A | Corpo da resposta 502, log da chamada |
| Falha de autenticação Voyage | Ingestão falha com `EmbeddingProviderConfigError`/`EmbeddingProviderUnavailableError` | Nenhum embedding real gerado | Stop | Confirmar `VOYAGE_API_KEY` (Gate B) | N/A | Log da chamada de ingestão |
| Dimensão de embedding incompatível | `pg_restore`/insert falha com erro de dimensão do pgvector, ou `vector_dims(embedding) != 1024` | Retrieval quebrado | Stop | Confirmar que a migration `0021` foi aplicada (`alembic current`) | Reexecutar migration; se persistir, investigar se o Voyage retornou dimensão diferente da configurada (`output_dimension=1024` no payload) | Query `vector_dims`, log da chamada Voyage |
| Falha do pgvector | `CREATE EXTENSION vector` ausente/erro | Nenhuma busca semântica possível | Stop | Confirmar imagem `pgvector/pgvector:pg16` (não `postgres:16` puro) | Recriar `database` com a imagem correta | Log de `alembic upgrade`/erro de extensão |
| Falha de ingestão | Erro em qualquer passo de `DocumentIngestionService` | Documento sintético não indexado | Stop (para o cenário de validação) | Investigar log do erro específico | Reexecutar upload | Log da API |
| Falha de retrieval | Busca RAG não retorna o chunk esperado | Advisor sem evidência (`insufficient_basis`) | Continue (é um resultado válido do sistema, não um crash) — mas reportar como GAP se inesperado | Confirmar que a indexação (Seção 9) realmente persistiu o chunk | N/A | Resposta do Advisor, `composition_trace` |
| Falha de Advisor | `AdvisorExecutionError` não relacionada a LLM/Embedding (ex.: erro de domínio) | Resposta 502 | Stop (para o cenário específico) | Investigar log específico do Advisor | N/A | Log da API |
| Falha de Executive Intelligence | `ExecutiveOrchestrator` retorna `insufficient_basis` inesperadamente | Decision Support/Executive Narrative sem resposta útil | Continue se for `SELECTION_EMPTY`/`COLLECTION_EMPTY` legítimo; investigar como GAP se inesperado | Revisar `signals`/`scope` do cenário de teste | N/A | `composition_trace` completo da resposta |
| Falha do smoke test | Qualquer um dos 4 checks falha | Staging não promovível | Stop | Investigar o check específico (mapeia diretamente a uma das falhas acima) | Não promover | Relatório do Playwright |

**GAP registrado (não mascarado):** nenhum mecanismo de rollback automatizado existe hoje para nenhum dos cenários acima além de "recriar o container/volume" — não há blue/green, não há canary, não há rollback de schema automatizado além do já descrito em `PRI-008` §5 (que por sua vez já registra suas próprias lacunas — Seção 6 desse runbook). Aceitável para o escopo do W7-1 (validação técnica, não operação de produção com usuários reais), mas deve ser revisitado antes de qualquer promoção de produção real com clientes.

---

## 13. Evidence Collection Plan

Toda evidência da execução real do W7-1 deve ser coletada e anexada à Executive Evidence final (`docs/product/governance/W7-1-STAGING-PRODUCTION-AI-VALIDATION-EXECUTIVE-EVIDENCE.md`, a ser produzida somente na execução real, não nesta missão):

| Camada | Evidência mínima a coletar |
|---|---|
| Deployment | Log de `docker compose build`/`up`, `docker compose ps` (todos `healthy`/`running`), `RELEASE_SHA` observado |
| Readiness | Corpo de `GET /health` e `GET /ready` de cada serviço, com timestamp |
| Migration | Output de `alembic current` pós-migração |
| Production LLM | Corpo de uma resposta real de Advisor, latência medida, confirmação de ausência de segredo no log/resposta |
| Production Embedding | Query `SELECT embedding_provider, embedding_model, vector_dims(embedding) FROM chunks LIMIT 5;`, latência medida |
| Knowledge/RAG | IDs de documento/chunks sintéticos criados, resposta do Advisor citando-os |
| Executive Intelligence | Corpo completo de uma resposta de `/decision-support/ask` (incluindo `composition_trace`) |
| Smoke/Browser | Relatório do Playwright + captura de tela do percurso manual (Seção 11) |
| Falhas encontradas | Qualquer entrada da Matriz (Seção 12) realmente disparada durante a execução, com log correspondente |

---

## 14. W7-1 Closure Criteria

O W7-1 só pode ser recomendado **COMPLETED** com evidência real de todos os 20 itens abaixo. Ausência de evidência para qualquer item mantém o W7-1 **aberto**, ou o classifica explicitamente como parcialmente concluído — nunca presumido como sucesso.

| # | Critério | Como se prova (ref.) |
|---|---|---|
| 1 | Staging provisionado | Seção 6, passo 4 |
| 2 | Release identificável | `RELEASE_SHA` em `/health`, Seção 6 passo 3/10 |
| 3 | Migrations executadas | `alembic current` = `0021`, Seção 6 passo 7 |
| 4 | `/health` verde | Seção 6 passo 10 |
| 5 | `/ready` verde | Seção 6 passo 11 |
| 6 | Smoke test verde | Seção 6 passo 12, Seção 11 |
| 7 | `ProductionLLMProvider` realmente executado | Seção 7 |
| 8 | `VoyageEmbeddingProvider` realmente executado | Seção 8 |
| 9 | `voyage-4`/1024 provado | Seção 8 (`vector_dims`) |
| 10 | Knowledge/RAG real provado | Seção 9 |
| 11 | Retrieval pgvector real provado | Seção 9, passo 5 |
| 12 | Ao menos um Advisor usando a cadeia real aplicável | Seção 10 |
| 13 | Executive Intelligence exercitada | Seção 10 |
| 14 | Citações/rastreabilidade preservadas | Seção 10 (`composition_trace`, `citations`) |
| 15 | Percurso essencial de browser validado | Seção 11 |
| 16 | Ausência de fallback mock no caminho certificado | Seção 7/8 (`LLM_PROVIDER`/`EMBEDDING_PROVIDER` reais, confirmados por config) |
| 17 | Falhas relevantes tratadas ou classificadas | Seção 12 |
| 18 | Rollback/recuperação aplicável documentado | Seção 12 (incl. GAP registrado onde não existe) |
| 19 | Segredos não expostos | Seção 7/8 (checagem explícita de logs/respostas) |
| 20 | Executive Evidence produzida | Seção 13 (documento a produzir na execução real) |

---

## 15. Risks

| Risco | Descrição | Mitigação proposta |
|---|---|---|
| Porta `5432` exposta ao host em `docker-compose.yml` | Em um staging real acessível pela internet, isso expõe o Postgres publicamente | Antes do deploy real, remover/restringir o mapeamento `ports: ["5432:5432"]` do serviço `database` para staging (mudança de configuração, não de arquitetura — a decidir na execução real, não nesta missão documental) |
| `POSTGRES_PASSWORD: aipmo` hardcoded em `docker-compose.yml` | Senha fraca e fixa no arquivo versionado — adequada apenas para desenvolvimento local | Para staging/produção real, sobrescrever via variável de ambiente no host (o `docker-compose.yml` já permite isso: bastaria trocar o valor fixo por `${POSTGRES_PASSWORD:?}` na execução real — mudança de configuração pontual, fora do escopo desta missão documental) |
| Documentação desatualizada (`PRI-008`/`PRI-009` §4, `.env.example`) | Pode confundir quem operar o deployment real sem ler o código-fonte | Corrigir antes ou durante a execução real do W7-1, como item de higiene documental (Seção 2) |
| `voyage-context-4` mais recente que `voyage-4` | Modelo mais novo existe mas tem contrato de API incompatível — decisão já tomada (D-176/D-177) de não adotá-lo agora | Nenhuma ação — DEFERRED é uma decisão consciente, não um risco não tratado |
| DNS/TLS ausente | Staging acessível apenas por IP/porta, sem criptografia em trânsito para tráfego de browser | Aceitável para validação técnica interna (Founder/Tech Lead); revisitar antes de qualquer exposição mais ampla |
| Nenhum mecanismo de rollback automatizado além de recriar containers/volume | Recuperação manual em qualquer falha real | Aceitável no escopo do W7-1 (ambiente de validação, não produção com clientes); GAP já registrado na Seção 12 |
| Reindexação (`reindex()`) ainda não deleta chunks antigos | Dívida já registrada em D-175/D-177 | Não bloqueia o W7-1 (dataset de staging será sempre novo); só se torna relevante se um dia reindexar dados reais existentes — permanece fora de escopo até então |

---

## 16. Blockers

Nenhum **bloqueio técnico novo** foi encontrado nesta revalidação — toda a base de código/config necessária já existe e está testada. Os únicos bloqueios reais para a execução do W7-1 são **externos** (Seção 5):

- Gate A (Staging Host) — **PENDING**
- Gate B (Voyage API Credential) — **PENDING**
- Gate C (Anthropic API Credential) — **PENDING**
- Gate D (Data/DPA Approval) — **PENDING** (bloqueia apenas dado corporativo real, não a validação sintética descrita neste plano)

Nenhum desses quatro gates é resolvido, provisionado ou negociado por esta missão.

---

## 17. GO/NO-GO Recommendation

**GO técnico para a execução real do protocolo descrito neste documento (Seções 6-11), condicionado exclusivamente à resolução dos Gates A-C (Seção 5) pelo Founder** — a arquitetura, o código, a configuração e os testes já suportam essa execução sem nenhuma mudança adicional.

**NO-GO para qualquer envio de dado corporativo real à Voyage AI** até o Gate D (Data/DPA) ser resolvido — a validação de Embedding/Knowledge/RAG/Executive Intelligence deste plano usa exclusivamente conteúdo sintético/controlado, precisamente para permitir a execução técnica sem depender do Gate D.

**Nenhum trabalho subsequente inicia automaticamente a partir deste documento** — nem provisionamento de staging, nem uso de credencial real, nem chamada real a LLM/Embedding, nem início de qualquer outro Epic da Wave 7. Esta missão produziu exclusivamente o plano; a decisão de autorizar a execução real retorna obrigatoriamente ao Founder no Executive Review.
