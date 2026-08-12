# Technical Design — W7-5: Deployment / Environment / Release Discipline

**Missão:** exclusivamente documental. Nenhum código, nenhum provisionamento, nenhuma implementação. Continuação direta de AR-18 (D-170, aprovada), que autorizou exclusivamente a abertura do ciclo técnico de W7-5 e mandatou este Technical Design como único artefato desta missão. W7-1, W7-3, W7-4 e W7-7 permanecem não autorizados para execução.

---

## 1. Executive Summary

W7-5 deve estabelecer disciplina técnica de configuração, build, deployment, migration, release e rollback — reproduzível e auditável — como fundação direta para W7-1 (Staging & Production LLM/Embedding Validation). O inventário real do repositório (§2) mostra que boa parte do mecanismo já existe e é reutilizável (Dockerfile do backend, `docker-compose.yml`, 21 migrations Alembic idempotentes, `PRI-008`/`PRI-009` documentando backup/deploy/rollback reais, CI real com Postgres+pgvector), mas **nenhuma configuração crítica falha rápido hoje** — `DATABASE_URL` ausente cai silenciosamente para SQLite, `API_KEY`/`ANTHROPIC_API_KEY`/`EMBEDDING_PROVIDER` só falham no primeiro uso real, nunca no boot — e **não existe modelo de ambiente**: dev/local, staging e produção leem exatamente as mesmas variáveis, sem nenhuma separação, sem endpoint de readiness distinto de liveness, e sem identidade de release (nenhuma tag/versão desde V1).

Este Technical Design propõe: um modelo DEV → STAGING → PRODUCTION explícito; um Configuration Contract classificando cada variável real hoje existente; regras de fail-fast que fecham a lacuna mais concreta encontrada (validação apenas no startup para staging/produção, nunca lazy); um Deployment Contract reaproveitando `PRI-009` em vez de recriá-lo; disciplina de migration que não resolve DR/backup (pertence a W7-3) mas identifica as dependências reais; um modelo de release/promoção que impede rebuild silencioso entre staging e produção; separação conceitual entre health/readiness/smoke test; e um modelo de rollback que não declara prontidão só porque o Git permite reverter um commit.

**Uma única Founder Decision é elevada como bloqueante real para a conclusão do Deployment/Build Contract do frontend:** hospedagem do frontend (§17, item 4) — decisão já registrada como aberta desde `RFC-001-frontend-architecture.html`, confirmada ainda aberta por `PRI-009`, e confirmada novamente aberta nesta inspeção (`web/` não tem `Dockerfile`, `vercel.json`, nem entrada em `docker-compose.yml`). As demais 6 questões do AR-18 não impactam diretamente este Technical Design e permanecem abertas, endereçadas por seus próprios Epics.

**Recomendação: GO** para implementação incremental de W7-5, condicionado à decisão de hospedagem de frontend antes da etapa que a exige (§18, Etapa 4).

---

## 2. Current-State Inventory

Inspeção direta do repositório real, sem assumir ausência ou existência — cada item confirmado por código/documentação:

| Item | Estado confirmado |
|---|---|
| **Docker/Docker Compose** | `docker-compose.yml` real: serviço `api` (build local, porta 8000, `alembic upgrade head && uvicorn` como comando único) + serviço `database` (`pgvector/pgvector:pg16`, healthcheck `pg_isready`, volume nomeado `aipmo_postgres_data`). Sem serviço de frontend. |
| **Dockerfile** | Um único, para o backend (`python:3.12-slim`, `pip install -r requirements.txt`, copia `src/`+`alembic/`, `CMD uvicorn`). Nenhum `Dockerfile` em `web/`. |
| **Scripts de setup/start/stop** | `scripts/prepare-env.sh` (venv + deps, idempotente, checa Python 3.11+/Node), `scripts/rc1-local-start.sh` (delega para `demo/start-demo.sh`), `scripts/rc2-db.sh`/`.ps1` (criação/reset idempotente de role/database Postgres), `demo/start-demo.sh`/`stop-demo.sh` (bring-up real de backend+frontend como processos com PID/log), `setup.ps1`/`.bat`, `start.ps1`/`.bat`, `stop.bat` (equivalentes Windows). |
| **Configuração backend** | Espalhada em `os.getenv()` por 10 arquivos (`rate_limiter.py`, `security.py`, `database/engine.py`, `llm/providers/factory.py`, `llm/providers/production_provider.py`, `main.py`, `services/identity/auth_service.py`, `services/identity/password_hashing.py`, `services/knowledge_platform/embedding_provider.py`) — **nenhum módulo central de configuração/settings existe**. |
| **Configuração frontend** | `BACKEND_URL`, `API_KEY`, `WORKSPACE_PASSWORD`, `SESSION_SECRET` (consumidos por `web/lib/session.ts` e pelo BFF), confirmados em `demo/start-demo.sh` e `PRI-009`. |
| **Variáveis de ambiente / `.env.example`** | `.env.example` real na raiz, documenta cada variável do backend com comentário do efeito quando ausente — boa prática já existente, mas cobre apenas o backend; não há `web/.env.example` equivalente documentado no mesmo padrão. |
| **Migrations** | 21 arquivos em `alembic/versions/` (`0001_initial` a `0020_w5_0_document_ingestion` + uma adicional), `alembic/env.py` reusa a mesma resolução de `DATABASE_URL` do runtime (`resolve_database_url()`), garantindo que migração e app nunca divergem de alvo. |
| **Database bootstrap** | `bootstrap_identities()` roda em todo boot do `lifespan()` do FastAPI — idempotente, nunca recria usuário existente; seed do Enterprise Domain embutido nas migrations 0002/0008. |
| **Health checks** | `GET /health` existe, retorna `{"status":"healthy","service":"AI PMO Copilot"}` — **liveness apenas, nenhuma verificação de dependência** (DB, LLM, config crítica). |
| **Readiness checks** | **Não existem** — nenhum endpoint distinto de `/health` verifica se a aplicação está pronta para tráfego real. |
| **Deployment artifacts** | Imagem Docker do backend (via `docker-compose build`), nunca publicada/taggeada em registry. Nenhum artifact de frontend. |
| **CI/CD existente** | `.github/workflows/ci.yml` real: job `validate` (Postgres+pgvector real como serviço, `ruff check`, `pytest --cov-fail-under=80`) + job `frontend` (`tsc`, `eslint`, `npm test`, `npm run build`, Playwright Chromium `--project=lg`) — em PR e push para `main`. **Valida, nunca publica nem implanta** — zero passo de CD. |
| **Build frontend** | `next build` já roda dentro do CI como parte da validação; nenhum artefato resultante é publicado/promovido. |
| **Build backend** | Imagem Docker construída localmente por `docker-compose build`; nenhuma etapa de CI constrói ou publica essa imagem hoje. |
| **Demo Mode** | `demo/start-demo.sh`: cria `demo/.env` a partir de `demo/.env.example` com `SESSION_SECRET` **gerado automaticamente** se ausente; SQLite por padrão (sem Docker) a menos que `DATABASE_URL` seja setado; roda `alembic upgrade head` incondicionalmente; sobe backend+frontend como processos em background com PID/log. |
| **RC-1 local startup** | `scripts/rc1-local-start.sh` = `prepare-env.sh` + `demo/start-demo.sh` — um único comando, ainda funcional, documentado em `Local-Installation-Guide.html`. |
| **`make dev` (fluxo RC-2)** | `setup → db-create → migrate → demo/start-demo.sh` — **reusa o mesmo script de Demo Mode**; a única diferença entre "ambiente local Postgres RC-2" e "Demo Mode" é se `DATABASE_URL` está setado antes de chamar o mesmo script. |
| **Documentação operacional** | `PRI-008-production-backup-restore-runbook.md` (backup/restore real via `pg_dump`/`pg_restore`, rotulado "STRATECH V1", nunca revisado para o schema de 21 migrations da V2) e `PRI-009-production-deployment-runbook.md` (deploy/rollback/smoke-test real via `docker-compose`, mesma origem V1) — **ambos substanciais e reaproveitáveis**, não recriados por este Technical Design. |
| **Rollback existente** | Documentado em `PRI-009` §3: reverter tag/imagem do backend; se a migração alterou schema, restaurar backup pré-deploy (nunca `alembic downgrade` manual em produção); confirmado por AR-18 como **nunca exercitado**. |
| **Versionamento/release** | Tags Git existem apenas para V1 (`v1.0.0-rc.1`, `v1.0.0-rc.2`) — **nenhuma tag/identidade de release para V2**; nenhuma etapa de CI associa um build a uma versão/commit de forma rastreável para deployment. |
| **Secrets/configuration** | `.env`/`demo/.env` apenas; nenhum vault; `demo/start-demo.sh` gera `SESSION_SECRET` automaticamente quando ausente — comportamento correto e documentado para Demo Mode, mas que precisa ser estruturalmente impossível de vazar para staging/produção (§7). |
| **Configuração de LLM** | `LLM_PROVIDER` (default **`anthropic`** se ausente, não `mock`), `ANTHROPIC_API_KEY`, `MODEL_NAME` (opcional). `ProductionLLMProvider.generate()` só falha (`ProviderConfigError`) na primeira chamada real — **nunca no boot**. |
| **Configuração de embedding** | `EMBEDDING_PROVIDER` (default `mock` se ausente). Único backend implementado é `MockEmbeddingProvider` (TD-011, AR-18 dimensão #14) — fora do escopo de W7-5 escolher o backend real. |
| **Diferenças conhecidas dev/demo vs. produção** | SQLite vs. Postgres; mock LLM/embedding vs. real; secret auto-gerado vs. real; processos locais com PID vs. containers; **nenhum mecanismo de separação de ambiente existe hoje** — as mesmas variáveis, os mesmos defaults, o mesmo comportamento lazy se aplicam indiferentemente a qualquer ambiente. |

**Achado central desta inspeção:** nenhuma configuração crítica (`DATABASE_URL`, `API_KEY`, `ANTHROPIC_API_KEY`, `EMBEDDING_PROVIDER`) impede o processo de subir quando ausente ou inválida — todas falham de forma lazy, no primeiro uso real, nunca no boot. Este é o gap mais concreto e acionável identificado, e a base do Fail-Fast Model (§7).

---

## 3. Scope / Non-Scope

**No escopo de W7-5:**
- Modelo de ambientes (DEV/STAGING/PRODUCTION) — definição, não implementação.
- Configuration Contract e Secrets Boundaries.
- Regras de fail-fast para configuração crítica em staging/produção.
- Build Model, Deployment Contract, Migration Discipline (participação no deploy, não backup/DR).
- Release/Promotion Model, Health/Readiness Model, Smoke-Test Model, Rollback Model.
- Decisão de hospedagem de frontend (elevada ao Founder, §17).

**Fora do escopo de W7-5 (pertence a outros Epics):**
- Provisionamento real de staging (W7-1).
- Validação real de LLM/embedding de produção (W7-1).
- RTO/RPO, estratégia de backup/restore/DR, drill de recuperação (W7-3).
- Política de delete RESTRICT/CASCADE (TD-002, W7-3).
- Security headers, dependency/secret scanning, rate limiting do BFF (W7-4).
- Observability, `correlation_id` threading, baseline de performance (W7-2).
- Cross-browser CI (W7-7).
- Backend de embedding de produção (W7-1/TD-011).

W7-5 **não é um projeto genérico de DevOps** — cada componente proposto está ligado a um gap real do AR-18 (dimensões #6 Deployment, #12 Secrets/Configuration, #21 Upgrade parcial, #22 Rollback) ou a uma pré-condição declarada de W7-1.

---

## 4. Environment Model

### DEV / LOCAL (já existe, apenas formalizado aqui — nenhuma alteração)
| Aspecto | Definição |
|---|---|
| Propósito | Iteração individual do desenvolvedor; Demo Mode |
| Configuração | `demo/.env` (gerado automaticamente a partir de `demo/.env.example`) |
| Isolamento | Nenhum — processo local, efêmero |
| Banco | SQLite por padrão (sem Docker), ou Postgres local via `docker-compose`/`make dev` |
| Secrets | Auto-gerados (`SESSION_SECRET`), nenhuma credencial real necessária |
| Providers externos | Mock por padrão (`LLM_PROVIDER`/`EMBEDDING_PROVIDER` podem ser mock ou reais se o desenvolvedor optar) |
| Build | Nenhum — `next dev` (servidor de desenvolvimento) + `uvicorn` direto |
| Deployment | N/A — processos diretos, rastreados por PID (`demo/*.pid`) |
| Migrations | `alembic upgrade head` automático a cada start |
| Dados | Seed do Enterprise Domain (migrations 0002/0008) |
| Logging | Arquivos locais (`demo/logs/*.log`) |
| Health/Readiness | Checagem manual (`curl localhost:8000/health`) |
| Acesso | `localhost` apenas |
| Promoção | N/A — código é promovido via Git, não estado de ambiente |
| Rollback | N/A — reinício do processo |

### STAGING (definido nesta missão, não implementado)
| Aspecto | Definição proposta |
|---|---|
| Propósito | Primeira validação real com configuração de produção para LLM/embedding (Blocker B, AR-18) |
| Configuração | Fonte de configuração própria, distinta de `.env`/`demo/.env` — nunca reaproveitar arquivo de dev (§5) |
| Isolamento | Infraestrutura própria, sem overlap de rede/processo com dev/produção |
| Banco | Instância Postgres dedicada (`pgvector/pgvector:pg16`, mesma versão de produção), sem dados de produção |
| Secrets | Reais, injetados pelo mecanismo de configuração do ambiente — **nunca auto-gerados** (violaria §7) |
| Providers externos | `LLM_PROVIDER=anthropic` com chave real; backend de embedding real quando W7-1 o escolher (TD-011) |
| Build | O mesmo artefato/imagem validado é o que é implantado — nunca rebuild (§11) |
| Deployment | Via `docker-compose`/equivalente, seguindo o Deployment Contract (§9), reaproveitando `PRI-009` |
| Migrations | `alembic upgrade head` como etapa explícita e confirmável antes do app subir (§10) |
| Dados | Conjunto de validação real, não trivial, nunca dado de cliente de produção |
| Logging | Estruturado; pronto para receber `correlation_id` quando W7-2 entregar o threading (não bloqueante para W7-5) |
| Health/Readiness | Endpoints distintos: liveness (já existe) + readiness (gap a fechar, §12) |
| Acesso | Controlado, interno — nunca público |
| Promoção | O artefato validado em staging é o promovido para produção (§11) |
| Rollback | Procedimento exercitado (não apenas documentado) — pré-condição de W7-1 |

### PRODUCTION (definido nesta missão, não implementado)
| Aspecto | Definição proposta |
|---|---|
| Propósito | Operação real |
| Configuração | Fonte própria, regras de fail-fast mais restritivas de todas |
| Isolamento | Totalmente separado de staging/dev |
| Banco | Instância dedicada, dado real de cliente, coberta pelo plano de DR (W7-3, fora de escopo aqui) |
| Secrets | Reais, mecanismo de rotação a decidir quando a necessidade for demonstrada (nenhum vault introduzido sem evidência, §17) |
| Providers externos | Chave real de produção; embedding real |
| Build | Idêntico ao artefato validado em staging — nunca rebuild |
| Deployment | Mesmo Deployment Contract, executado contra o alvo de produção |
| Migrations | Mesma disciplina, sempre precedida por backup real (coordenado com W7-3/`PRI-008`) |
| Dados | Dado real de cliente |
| Logging | Mesmo alvo estruturado + `correlation_id` |
| Health/Readiness | Mesmos endpoints, monitorados operacionalmente (alertas são escopo de W7-2) |
| Acesso | Depende da decisão de hospedagem de frontend (§17, item 4) |
| Promoção | Condicionada aos critérios de encerramento de W7-1 estarem satisfeitos |
| Rollback | Mesmo procedimento de staging, agora sob risco real — coordenado com responsabilidades operacionais de DR (W7-3) |

**Distinção obrigatória confirmada:** hoje, DEV/Demo e "ambiente Postgres local RC-2" **são literalmente o mesmo script** (`demo/start-demo.sh`), diferenciados apenas por uma variável de ambiente — nenhum dos dois é STAGING, e nenhum pode ser tratado como substituto conceitual dele em nenhuma condição de encerramento (reafirmando AR-18 §7).

---

## 5. Configuration Contract

Toda variável real hoje existente, classificada:

| Variável | Categoria | Obrigatória | Ambiente | Comportamento hoje se ausente | Default seguro? | Default proibido em staging/prod? | Segredo? | Validação proposta no startup |
|---|---|---|---|---|---|---|---|---|
| `DATABASE_URL` | database | Sim (staging/prod) | Todos | Cai silenciosamente para SQLite | Sim, apenas em DEV | **Sim** | Não (mas a connection string pode carregar credencial) | Falhar boot se ausente e `ENVIRONMENT != dev` |
| `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`/`DB_POOL_TIMEOUT_SECONDS`/`DB_POOL_RECYCLE_SECONDS`/`DB_POOL_PRE_PING` | database | Não | Todos (Postgres only) | Usa default numérico já sensato | Sim | Não | Não | Nenhuma — defaults já adequados |
| `API_KEY` | authentication/security | Sim | Todos | 503 lazy, apenas na primeira requisição | Não | **Sim** | **Sim** | Falhar boot se ausente e `ENVIRONMENT != dev` |
| `SESSION_SECRET` (frontend) | authentication/security | Sim | Todos | Falha fechado no BFF, lazy | Não em staging/prod; auto-gerado apenas em Demo Mode | **Sim** | **Sim** | Falhar boot do BFF se ausente e `ENVIRONMENT != dev` |
| `WORKSPACE_PASSWORD` (frontend) | authentication/security | Sim | Todos | 503 lazy | Não em staging/prod | **Sim** | **Sim** | Mesma regra acima |
| `STRATECH_ADMIN_EMAIL`/`STRATECH_ADMIN_PASSWORD` | authentication/security | Opcional | Todos | Bootstrap de admin simplesmente não ocorre | Sim (ausência é um estado válido) | Não | **Sim** (senha) | Nenhuma obrigatória |
| `LLM_PROVIDER` | LLM | Sim (staging/prod) | Todos | Default `anthropic` — correto por si, mas... | Não (default é "correto" mas não valida a chave) | **Sim**, se resolver para `mock` | Não | Falhar boot se `ENVIRONMENT != dev` e resolver para `mock`, ou se `anthropic` sem `ANTHROPIC_API_KEY` |
| `ANTHROPIC_API_KEY` | LLM | Sim, se `LLM_PROVIDER=anthropic` | Todos | `ProviderConfigError` lazy, só na 1ª chamada real | Não | **Sim** | **Sim** | Falhar boot (não apenas 1ª chamada) se `ENVIRONMENT != dev` e `LLM_PROVIDER=anthropic` |
| `MODEL_NAME` | LLM | Não | Todos | Usa o modelo hardcoded padrão | Sim | Não | Não | Nenhuma |
| `EMBEDDING_PROVIDER` | embeddings | Sim (staging/prod, quando TD-011 fechar) | Todos | Default `mock` | Não em staging/prod | **Sim**, se resolver para `mock` | Não | Mesma regra de `LLM_PROVIDER` — aplicável quando W7-1 escolher o backend real |
| `CORS_ALLOWED_ORIGINS` | application | Sim (staging/prod) | Todos | Vazio — nenhuma origem permitida (fail-closed por efeito colateral, não por design explícito) | Não em staging/prod (frontend real não funciona) | Sim (vazio funcionalmente bloqueia o produto) | Não | Alertar/falhar se vazio e `ENVIRONMENT != dev` |
| `RATE_LIMIT_MAX_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS` | application | Não | Todos | Default 60/60 | Sim | Não | Não | Nenhuma |
| `MOCK_LLM_RESPONSE_FILE` | application | Não | DEV apenas | Ignorado se ausente | Sim | **Sim** — não deve existir fora de DEV | Não | Alertar se presente e `ENVIRONMENT != dev` |
| `BACKEND_URL` (frontend) | frontend/BFF | Sim | Todos | BFF não alcança a API real | Não | Sim | Não | Falhar boot do BFF se ausente e `ENVIRONMENT != dev` |
| `API_KEY` (frontend → backend) | frontend/BFF | Sim | Todos | Toda chamada do BFF falha (503/401) | Não | Sim | **Sim** | Mesma regra do `API_KEY` backend |

Nenhuma categoria nova além das já mandatadas pelo Founder (`application`/`database`/`authentication-security`/`LLM`/`embeddings`/`Knowledge Platform`/`frontend-BFF`/`observability`/`deployment`) foi necessária — **Knowledge Platform** não tem variável própria hoje (embeddings vivem na mesma `DATABASE_URL`, per AR-18 §9); **observability** e **deployment** não têm nenhuma variável hoje — gaps reais, mas pertencem a W7-2 e à Etapa de release deste próprio Epic (§11), respectivamente.

---

## 6. Secrets Boundaries

- **Nenhum valor real de secret é registrado por este documento** — apenas nomes de variáveis e seu comportamento.
- **Nenhuma infraestrutura de secret management é proposta** sem necessidade demonstrada (§17 anti-overengineering) — a necessidade real hoje é apenas: (a) parar de reaproveitar `.env`/Demo Mode para staging/produção; (b) garantir que secrets de staging/produção nunca sejam auto-gerados como `demo/start-demo.sh` faz para Demo Mode.
- **Fronteira proposta:** cada ambiente (staging, produção) tem sua própria fonte de configuração — mecanismo concreto (arquivo protegido, variável de CI/CD, ou serviço de secrets) é uma decisão de implementação de W7-1 (que efetivamente provisiona o ambiente), não deste Technical Design, que apenas define que a fonte deve existir e ser distinta por ambiente.
- **Secrets identificados nesta inspeção:** `API_KEY` (backend e frontend→backend), `SESSION_SECRET`, `WORKSPACE_PASSWORD`, `ANTHROPIC_API_KEY`, `STRATECH_ADMIN_PASSWORD`. Nenhum outro encontrado.
- **Comportamento proibido, explícito:** o padrão de `demo/start-demo.sh` (gerar `SESSION_SECRET` automaticamente quando ausente) é correto e deve **permanecer exclusivo de Demo Mode** — nunca replicado para staging/produção, onde a ausência de um secret deve falhar o boot (§7), nunca gerar um substituto.

---

## 7. Fail-Fast Rules

**Achado central (§2):** nenhuma configuração crítica falha no boot hoje — todas falham lazy, no primeiro uso.

**Regra proposta, aplicável a STAGING e PRODUCTION (nunca a DEV, onde o comportamento permissivo atual já é o produto documentado):**

Na inicialização do processo (antes de aceitar a primeira requisição), validar:
1. `DATABASE_URL` presente e não resolvendo ao fallback SQLite.
2. `API_KEY` presente.
3. `LLM_PROVIDER` presente e, se `anthropic`, `ANTHROPIC_API_KEY` presente — nunca permitir resolução para `mock`.
4. `EMBEDDING_PROVIDER` presente e, quando W7-1 definir o backend real, nunca permitir resolução para `mock`.
5. `SESSION_SECRET`/`WORKSPACE_PASSWORD`/`BACKEND_URL`/`API_KEY` (frontend) presentes no boot do BFF.
6. `CORS_ALLOWED_ORIGINS` não vazio.

Qualquer uma ausente ou inválida → o processo **não deve subir**, com uma mensagem de erro clara identificando exatamente qual variável falta — em vez do comportamento atual (subir normalmente, falhar 503/401 na primeira requisição real que a exercitar).

**Mecanismo de distinção dev vs. staging/produção:** hoje não existe nenhuma variável que declare "em qual ambiente este processo está rodando" — esta é a peça que falta para a regra acima ser aplicável seletivamente. Proposta: uma variável única (`ENVIRONMENT` ou equivalente, valor `dev`/`staging`/`production`) que governa exclusivamente **se** as regras de fail-fast acima se aplicam — não introduz nova arquitetura, apenas nomeia o que hoje é implícito.

**Garantia explícita:** o comportamento permissivo de Demo Mode (SQLite default, `SESSION_SECRET` auto-gerado) nunca pode ser promovido silenciosamente — a própria ausência de `ENVIRONMENT=staging`/`production` já é, por construção desta regra, o que hoje mantém esse comportamento restrito a DEV.

---

## 8. Build Model

- **Backend:** `Dockerfile` já real e funcional (`python:3.12-slim`, `pip install -r requirements.txt`, copia `src/`+`alembic/`) — build reproduzível hoje, apenas nunca publicado a um registry nem taggeado por versão (§11).
- **Frontend:** `next build` já roda em CI, mas **não existe artefato de build empacotado para deployment** — nem `Dockerfile`, nem exportação estática, nem alvo de hospedagem (bloqueado pela decisão pendente, §17 item 4).
- **Nenhuma ferramenta nova de build é proposta** — o gap não é de ferramenta, é de: (a) publicar o artefato já construído; (b) decidir o alvo de hospedagem do frontend.

---

## 9. Deployment Contract

Ciclo conceitual proposto, mapeado ao que já existe versus o que é gap real:

```
Build → Validate → Migrate → Deploy → Health/Readiness Check → Smoke Test → Promote | Rollback
```

| Etapa | Já existe? | Evidência | Gap |
|---|---|---|---|
| Build | Parcial | `Dockerfile` (backend); `next build` (frontend, sem artefato empacotado) | Frontend sem alvo de empacotamento |
| Validate | Sim | CI real (`ci.yml`) — lint/test/coverage/tsc/eslint/build/E2E | Nenhum |
| Migrate | Sim, mas acoplado | `alembic upgrade head` já roda como parte do comando único do serviço `api` | Falta separação explícita como etapa confirmável (hoje `PRI-009` já trata isso como "etapa que só confirma o resultado", não como controle de falha isolado) |
| Deploy | Documentado, não exercitado | `PRI-009` §2 (`docker compose up -d --build api database`) | Nunca executado contra ambiente real (AR-18) |
| Health/Readiness Check | Parcial | `/health` existe (liveness) | Readiness (dependência real) não existe (§12) |
| Smoke Test | Documentado, não automatizado | `PRI-009` §5 — 5 passos manuais reais | `playwright.config.ts` fixo em `localhost:3100`, sem suporte a `PLAYWRIGHT_BASE_URL` |
| Promote | Não existe | — | Nenhum mecanismo de promoção de artefato validado (§11) |
| Rollback | Documentado, não exercitado | `PRI-009` §3 | Nunca exercitado (AR-18) |

**Nenhuma ferramenta de deployment é escolhida por preferência tecnológica** — o modelo proposto reaproveita `docker-compose` (já real, já funcional em CI/dev), sem introduzir Kubernetes, service mesh ou qualquer outra plataforma sem gap real que a justifique (§17).

---

## 10. Migration Discipline

- **Execução:** `alembic upgrade head`, já real e idempotente, reusa `resolve_database_url()` — nunca diverge do alvo do app.
- **Ordem:** linear, 21 migrations sequenciais, sem branching — Alembic já garante isso estruturalmente.
- **Compatibilidade:** cada migration histórica já foi aplicada com sucesso em CI/dev repetidamente; nunca contra um ambiente staging/produção real do zero (AR-18 dimensão #16).
- **Failure handling:** hoje, se a migração falhar, o comando único do serviço `api` (`alembic upgrade head && uvicorn ...`) falha por completo — o container não sobe, comportamento correto por acidente de composição do comando, não por design explícito de failure handling.
- **Rollback de migração:** `PRI-009` já é explícito — nunca `alembic downgrade` manual em produção; reverter via restauração de backup pré-deploy. Este Technical Design **não resolve backup/restore** (pertence a W7-3/`PRI-008`), apenas confirma esta dependência real: **W7-5 exige que W7-3 ou uma decisão equivalente de backup pré-deploy exista antes que produção real seja implantada**, embora staging possa proceder com um backup mais simples (dump antes de cada migration de validação).
- **Migrations irreversíveis:** nenhuma das 21 atuais foi marcada como tal; a disciplina proposta é: qualquer migration futura que remova coluna/tabela (como a já ocorrida `0015`, documentada em TD-008) deve ser precedida por backup, consistente com o padrão já seguido historicamente.
- **Relação com deploy:** proposta de **separar** a execução da migration do start do processo de aplicação (hoje bundlados no mesmo comando) — permite falha isolada e visível antes de qualquer tráfego real, sem exigir nova ferramenta.

---

## 11. Release / Promotion Model

- **Identidade de release proposta:** commit SHA do Git como identidade primária de build (já disponível, sem ferramenta nova) — tags semânticas (`v2.x.x`, seguindo o precedente real de `v1.0.0-rc.*`) podem ser aplicadas sobre commits que passam pelos critérios de encerramento de W7-1, não antes.
- **Build identity:** a imagem Docker do backend deve ser taggeada com o commit SHA que a originou — hoje nenhuma tag é aplicada.
- **Staging validation → Production promotion:** a mesma imagem/artefato validado em staging deve ser o promovido para produção, **nunca reconstruído** — elimina o risco de "funcionou em staging, mas o rebuild para produção introduziu uma diferença silenciosa".
- **Rollback target:** a tag/imagem anterior, já demonstrada funcional (mesmo princípio já documentado em `PRI-009` §3).
- **Evidências de release:** qual commit SHA está rodando em cada ambiente deve ser verificável (ex.: endpoint ou log expondo a revisão), gap real hoje — `/health` não expõe versão/commit.
- **Nenhum registry de imagens é escolhido nesta missão** — decisão de implementação de W7-1 quando staging for de fato provisionado, não deste Technical Design.

---

## 12. Health / Readiness Model

Separação conceitual proposta, hoje inexistente:

| Conceito | Definição | Estado hoje |
|---|---|---|
| Process alive | O processo responde a qualquer requisição | Implícito — se `/health` responde, o processo está vivo |
| Application healthy | `/health` responde 200 | **Já existe**, mas não verifica nada além de si mesma |
| Application ready | Dependências críticas (banco, config obrigatória) estão OK | **Não existe** — gap real |
| Dependencies ready | Banco alcançável, migração aplicada, config de LLM/embedding presente | **Não existe** — gap real |
| Functional smoke test | Um fluxo real de ponta a ponta funciona | Documentado manualmente em `PRI-009` §5, nunca automatizado |

**Mínimo necessário para W7-1 provar que staging está operacional:** um endpoint de readiness (`/ready` ou equivalente) que verifique, no mínimo, conectividade real com o banco e presença das variáveis críticas do Configuration Contract (§5) — reaproveitando o mesmo mecanismo de fail-fast (§7), não uma verificação nova e paralela.

---

## 13. Smoke-Test Model

- **Já existe, documentado, manual:** `PRI-009` §5 — 5 passos reais (login, dashboard carrega, workspace de projeto carrega, submissão de análise reflete em até 30s, todas as 6 rotas do menu sem erro 500).
- **Gap real:** `web/playwright.config.ts` aponta fixamente para `localhost:3100`, sem suporte a uma variável como `PLAYWRIGHT_BASE_URL` — impede reaproveitar a suíte E2E real (já existente e passando) como smoke test automatizado contra staging/produção.
- **Proposta:** não criar uma nova suíte funcional completa (instrução explícita do Founder) — apenas parametrizar o `baseURL` já usado pelo Playwright, permitindo que um subconjunto pequeno e já existente de specs E2E sirva como smoke test pós-deploy, em vez de reescrever os 5 passos manuais como uma ferramenta nova.
- **Os 5 passos de `PRI-009` §5 permanecem a referência de conteúdo** — nenhum passo novo proposto, apenas o mecanismo de execução (manual → parametrizável).

---

## 14. Rollback Model

- **O que significa rollback da aplicação:** reverter para a imagem/tag anterior já demonstrada funcional (§11) — nunca apenas "reverter um commit no Git", que não move nenhum processo real em execução.
- **Relação com banco/migrations:** se a versão com problema alterou o schema, o rollback da aplicação por si só não é suficiente — exige restaurar o backup pré-deploy (pertence a W7-3/`PRI-008`, dependência já identificada em §10), nunca um `alembic downgrade` manual.
- **Versão anterior:** identificada pela tag/commit SHA anterior (§11) — hoje inexistente por falta de identidade de release.
- **Configuração:** o rollback de configuração (não apenas de código) é uma dimensão própria — reverter para o conjunto de variáveis anterior, coordenado com a fonte de configuração por ambiente (§5/§6).
- **Critérios para acionar:** os mesmos critérios de sucesso já documentados em `PRI-009` §6 (health check, `alembic current`, 5 smoke tests, ausência de erro novo nos primeiros 10 minutos, backup pré-deploy validado) — se qualquer um falhar, rollback imediato, sem investigar em produção com o deploy problemático no ar (já a disciplina documentada, reafirmada aqui).
- **Evidência de sucesso:** os mesmos critérios revalidados após o rollback.
- **Nunca alegar rollback readiness apenas porque o Git permite reverter um commit** — rollback readiness real exige: artefato anterior disponível e taggeado (§11), backup pré-deploy existente (W7-3), e o próprio procedimento **exercitado**, não apenas escrito — condição de encerramento explícita (§20).

---

## 15. Relationship with W7-1

W7-5 é pré-condição direta e explícita para W7-1. Entregáveis de W7-5 que W7-1 depende:

1. Modelo de ambientes (§4) definido — W7-1 precisa saber o que "staging" significa antes de provisioná-lo.
2. Configuration Contract (§5) — W7-1 usa esta classificação para saber exatamente quais variáveis staging precisa e como validá-las.
3. Fail-Fast Rules (§7) — W7-1 implementa o mecanismo de validação no boot para o ambiente real que provisionar.
4. Deployment Contract (§9) — W7-1 executa o ciclo real pela primeira vez contra staging.
5. Migration Discipline (§10) — W7-1 executa as 21 migrations do zero contra staging real, seguindo a disciplina aqui definida.
6. Release/Promotion Model (§11) — W7-1 precisa de uma identidade de release para o primeiro build que valida em staging.
7. Health/Readiness Model (§12) — W7-1 usa o endpoint de readiness (uma vez implementado) como parte da prova de que staging está operacional.
8. Smoke-Test Model (§13) — W7-1 executa os smoke tests reais pós-implantação em staging.

**Resultado esperado:** que W7-1, no próximo ciclo, valide uma instalação que seja representativa de staging real — nunca "mais um ambiente local".

---

## 16. Architectural Preservation

W7-5 não reestrutura o produto para facilitar deployment. Nenhum componente abaixo é alterado, aberto para alteração, ou tem impacto arquitetural proposto:

Enterprise Domain, Knowledge Platform, `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline, os 8 Enterprise Advisors, Executive Orchestrator, Decision Support, Executive Narrative, tenant isolation, RBAC, auditability.

Nenhuma necessidade de alteração estrutural nesses componentes foi identificada por esta inspeção. Caso surja durante a implementação incremental (§18), deve ser elevada como Founder Decision antes de qualquer mudança, per a mesma restrição já herdada de AR-18 §2/§16.

---

## 17. Founder Decisions / Dependencies

Das 6 questões listadas pela AR-18 (RTO/RPO; backend de embedding de produção; delete policy; hospedagem de frontend; DR operational ownership; papel futuro do `EnterpriseMemoryService`), avaliação de impacto direto sobre W7-5:

1. **RTO/RPO** — não impacta W7-5. Pertence a W7-3. Permanece aberta.
2. **Backend de embedding de produção (TD-011)** — não impacta W7-5 diretamente; o Configuration Contract (§5) já define a *forma* de `EMBEDDING_PROVIDER` genericamente, independente de qual backend W7-1 escolher depois. Permanece aberta.
3. **Delete policy (TD-002)** — não impacta W7-5. Pertence a W7-3. Permanece aberta.
4. **Hospedagem de frontend** — **impacta W7-5 diretamente.** Bloqueia a conclusão do Build Model (§8) e do Deployment Contract (§9) para o frontend especificamente — sem essa decisão, W7-5 não pode declarar o ciclo `Build → Deploy` do frontend fechado. **Elevada nesta missão.**
5. **DR operational ownership** — não impacta W7-5. Pertence a W7-3. Permanece aberta.
6. **Papel futuro do `EnterpriseMemoryService`** — não impacta W7-5. Permanece aberta, sem consumidor artificial criado.

**Questão elevada, com opções concretas (nenhuma escolhida por preferência tecnológica, §9):**

> **Hospedagem do frontend em staging/produção — duas opções reais, com base no que já existe no repositório:**
> - **Opção A — Containerizado, consistente com o backend:** adicionar um serviço `web` ao `docker-compose.yml` (Next.js via `next start`, mesmo padrão de single-host já usado pelo backend). Menor introdução de tecnologia nova; mesmo modelo operacional do backend; mesmo mecanismo de deploy/rollback (§9/§14) se estende naturalmente.
> - **Opção B — Hospedagem especializada (plataforma de edge/estática para Next.js):** exigiria decidir um provedor específico, introduzindo um segundo modelo de deployment paralelo ao do backend (dois pipelines, duas fontes de rollback).
>
> **Não decidida por esta revisão** — apenas nomeada, com a Opção A identificada como a que introduz menos tecnologia nova e reaproveita mais do que já existe, sem prescrever a resposta.

**Não obrigar o Founder a decidir antecipadamente** RTO/RPO, backend de embedding, delete policy, DR ownership ou papel do `EnterpriseMemoryService` — nenhuma delas bloqueia este Technical Design ou a implementação de W7-5.

---

## 18. Incremental Implementation Plan

Proposto para quando a implementação de W7-5 for autorizada — **nenhuma etapa executada nesta missão**.

**Etapa 1 — `ENVIRONMENT` + Fail-Fast no boot (backend)**
- Objetivo: introduzir a variável `ENVIRONMENT` e a validação de startup (§7) para `DATABASE_URL`/`API_KEY`/`LLM_PROVIDER`/`ANTHROPIC_API_KEY`/`CORS_ALLOWED_ORIGINS`.
- Arquivos impactados: `src/main.py` (lifespan), possivelmente um novo módulo pequeno de validação de config (não um framework de settings).
- Evidência de sucesso: processo recusa subir com config crítica ausente quando `ENVIRONMENT != dev`; sobe normalmente em DEV como hoje.
- Testes: unitário para cada variável ausente/inválida; teste de que DEV permanece permissivo.
- Risco: baixo — mudança aditiva, comportamento DEV inalterado.
- Rollback da própria mudança: reverter o commit; nenhuma migração de dado envolvida.

**Etapa 2 — Endpoint de Readiness**
- Objetivo: `/ready` (ou equivalente) verificando conectividade real de banco + presença de config crítica.
- Arquivos: `src/main.py`.
- Evidência: `/ready` retorna 200 apenas com banco alcançável e config presente; 503 caso contrário.
- Testes: unitário com banco simulado indisponível.
- Risco: baixo.
- Rollback: reverter commit.

**Etapa 3 — Identidade de release (commit SHA em build/health)**
- Objetivo: expor o commit SHA que originou o build (ex.: em `/health` ou endpoint próprio); taggear a imagem Docker com o SHA no processo de build.
- Arquivos: `Dockerfile`, `src/main.py`, possivelmente CI.
- Evidência: `/health` (ou endpoint novo) expõe o SHA; imagem local taggeada corresponde.
- Testes: verificação manual/CI de que a tag corresponde ao SHA do build.
- Risco: baixo.
- Rollback: reverter commit.

**Etapa 4 — Frontend: Build + Deployment Contract** *(depende da Founder Decision de hospedagem, §17)*
- Objetivo: empacotar o frontend conforme a opção decidida (containerização ou plataforma especializada).
- Arquivos: `web/Dockerfile` (se Opção A) ou configuração equivalente da plataforma escolhida; `docker-compose.yml` se Opção A.
- Evidência: build reproduzível do frontend, artefato implantável.
- Testes: build local bem-sucedido; smoke test manual do artefato.
- Risco: médio — primeira vez que o frontend ganha um alvo de deployment real.
- Rollback: reverter commit/configuração.

**Etapa 5 — Migration como etapa explícita separada do boot**
- Objetivo: separar `alembic upgrade head` do comando de start do `api` no `docker-compose.yml`/deployment real, tornando-a uma etapa confirmável isoladamente (§10).
- Arquivos: `docker-compose.yml`, possivelmente scripts de deploy.
- Evidência: falha de migração é distinguível de falha de start da aplicação nos logs/exit code.
- Testes: simular falha de migração, confirmar que app não sobe e o erro é claro.
- Risco: baixo — reordenação de etapas já existentes.
- Rollback: reverter commit.

**Etapa 6 — Smoke test parametrizável (`PLAYWRIGHT_BASE_URL`)**
- Objetivo: permitir que `playwright.config.ts` aponte para um `baseURL` configurável, não fixo em `localhost:3100`.
- Arquivos: `web/playwright.config.ts`.
- Evidência: suíte E2E reduzida executável contra uma URL arbitrária.
- Testes: rodar a suíte localmente com a variável setada para `localhost:3100` (comportamento inalterado por padrão).
- Risco: baixo.
- Rollback: reverter commit.

Cada etapa é pequena, independente e verificável — nenhuma exige que as demais estejam prontas primeiro, exceto Etapa 4 (depende da Founder Decision) e Etapa 6 (mais útil após Etapas 1-2 existirem, mas não bloqueada por elas).

---

## 19. Test Strategy

- **Backend:** testes unitários para cada regra de fail-fast (Etapa 1) e para o endpoint de readiness (Etapa 2) — seguindo o padrão já estabelecido de 862+ testes reais em `tests/`, reusando `pytest`, nenhuma ferramenta nova.
- **Frontend:** nenhuma alteração de comportamento de produto — testes existentes (`vitest`, 546 passando) permanecem a referência; qualquer novo componente de configuração (Etapa 4) ganha teste próprio seguindo o mesmo padrão.
- **E2E:** reaproveitamento da suíte Playwright já existente como smoke test parametrizável (Etapa 6), não uma suíte nova.
- **CI:** nenhuma alteração estrutural ao `ci.yml` proposta por este Technical Design — a validação de fail-fast/readiness entra como testes unitários dentro do job `validate` já existente.

---

## 20. Closure Criteria

Verificáveis por execução real, não apenas declaração documental — nenhum destes é declarado cumprido por esta missão:

1. `ENVIRONMENT=staging`/`production` recusa subir com qualquer variável crítica do Configuration Contract (§5) ausente ou inválida — comprovado por teste real, não apenas lido no código.
2. `ENVIRONMENT=dev` (ou ausente) mantém o comportamento permissivo atual, sem regressão.
3. Endpoint de readiness distingue corretamente "vivo" de "pronto" contra um banco real indisponível.
4. Build reproduzível — mesma imagem gerada a partir do mesmo commit, verificável pelo SHA exposto.
5. Deployment executado ao menos uma vez contra um ambiente real (mesmo que ainda não staging completo — a etapa de W7-1), seguindo o Deployment Contract (§9).
6. Migration disciplinada — falha de migração distinguível de falha de app, comprovada por simulação real.
7. Health/readiness comprovados contra um ambiente real, não apenas localhost de desenvolvimento.
8. Smoke test parametrizável executado com sucesso contra um `baseURL` não-default.
9. Release identificável — commit SHA rastreável do build até o ambiente rodando.
10. Promoção controlada — o mesmo artefato validado é o promovido, sem rebuild, comprovado por comparação de hash/tag.
11. Rollback exercitável — um ciclo real de rollback executado (mesmo que em staging, não necessariamente produção nesta Wave), com os critérios de `PRI-009` §6 revalidados após.
12. Separação DEV/STAGING/PRODUCTION demonstrável — nenhuma config de um ambiente vaza para outro.
13. Ausência de fallback Demo/local em staging/produção — comprovado pela regra de fail-fast (item 1) nunca permitir `DATABASE_URL` resolvendo a SQLite ou `LLM_PROVIDER`/`EMBEDDING_PROVIDER` resolvendo a `mock` fora de DEV.

---

## 21. Risks

- **Introduzir `ENVIRONMENT` e fail-fast pode expor, pela primeira vez, lacunas de configuração hoje mascaradas pelo comportamento lazy** — risco esperado e desejável (é o próprio objetivo), mas pode atrasar a Etapa 1 se múltiplas variáveis estiverem de fato ausentes em ambientes de teste já em uso.
- **Decisão de hospedagem de frontend não tomada a tempo** bloqueia especificamente a Etapa 4, mas não as demais Etapas — risco de sequenciamento, não de escopo.
- **`PRI-008`/`PRI-009` desatualizados para o schema V2 real (21 migrations)** — qualquer execução real de deployment/migration deve revisar esses runbooks primeiro, não assumir que descrevem o estado atual com precisão total.
- **Migration como etapa separada (Etapa 5) pode revelar comportamento diferente do bundlado atual** sob falha — deve ser testado deliberadamente antes de ser considerado equivalente ou superior ao comportamento hoje.
- **Nenhuma infraestrutura de secrets é introduzida** — se, durante a implementação, a necessidade de um mecanismo real (além de "fonte de configuração distinta por ambiente") se demonstrar concretamente, isso deve ser elevado como nova questão, não decidido silenciosamente dentro de W7-5.

---

## 22. GO/NO-GO Recommendation

**GO** para a implementação incremental de W7-5, seguindo as 6 etapas de §18, **condicionado**:

- à confirmação do Founder sobre hospedagem de frontend (§17) antes da Etapa 4 especificamente — as Etapas 1, 2, 3, 5 e 6 não dependem dela e podem proceder;
- à autorização explícita e separada do Founder para iniciar a implementação (esta missão produziu exclusivamente o Technical Design, nenhuma etapa foi executada).

Nenhum código foi escrito. Nenhum ambiente foi provisionado. Nenhuma implementação de W7-5 foi iniciada. W7-1, W7-3, W7-4 e W7-7 permanecem não autorizados para execução. Retornando obrigatoriamente para Executive Review do Founder.

---

## Referências

- `docs/architecture/AR-18-WAVE-7-ENTERPRISE-READINESS-ARCHITECTURE-REVIEW.md` (D-170).
- `docs/operations/PRI-008-production-backup-restore-runbook.md`, `docs/operations/PRI-009-production-deployment-runbook.md`.
- `docker-compose.yml`, `Dockerfile`, `Makefile`, `scripts/*`, `demo/start-demo.sh`, `demo/stop-demo.sh`.
- `.env.example`, `src/database/engine.py`, `src/llm/providers/factory.py`, `src/llm/providers/production_provider.py`, `src/services/knowledge_platform/embedding_provider.py`, `src/api/security.py`, `src/api/rate_limiter.py`, `src/main.py`.
- `.github/workflows/ci.yml`.
- `alembic/env.py`, `alembic/versions/`.
