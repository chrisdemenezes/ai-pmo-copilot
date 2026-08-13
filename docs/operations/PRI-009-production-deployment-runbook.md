# PRI-009 — Production Deployment Runbook

Runbook operacional para implantar a STRATECH V1 (backend `src/`, via `docker-compose.yml`
+ `Dockerfile`) em produção. Registrado como `PRI-009` no Platform Readiness Backlog por
decisão do Founder/CTO (Release Blocker `RB-003`), como pré-requisito para a STRATECH V1
RC-1. Nenhuma mudança de infraestrutura, arquitetura ou pipeline foi feita por este
documento — ele descreve, com precisão, o que já existe no repositório
(`docker-compose.yml`, `Dockerfile`, `alembic/`, `.github/workflows/ci.yml`) e sinaliza
explicitamente onde uma decisão de infraestrutura ainda não foi tomada.

## 1. Pré-requisitos

| Item | Status | Observação |
|---|---|---|
| Backend containerizado (`Dockerfile` + `docker-compose.yml`) | Pronto | Serviços `api` (FastAPI/Uvicorn), `web` (frontend, W7-5 Etapa 4) e `database` (`pgvector/pgvector:pg16`) |
| Migração de schema | Pronta | Etapa explícita e separada do start do serviço `api` (W7-5 Etapa 5, Migration Discipline) — ver Seção 2 |
| Variáveis de ambiente de produção | A configurar por deploy | Ver tabela abaixo |
| Hospedagem do frontend (`web/`) | **Decidido (Founder Decision, W7-5, D-171/D-172)** | Containerizado, mesma disciplina de deployment do backend — `web/Dockerfile` + serviço `web` em `docker-compose.yml` (W7-5 Etapa 4). Resolve a pergunta aberta desde `RFC-001-frontend-architecture.html` (linha 1167). |
| Mitigação de força bruta em `/api/bff/session` | **Pendente — condição já registrada** | `docs/development/01-project-structure.md` (seção "Decision: Security Finding") registra risco aceito formalmente apenas para uso interno/piloto, com condição explícita e obrigatória antes de qualquer deploy além desse escopo: rate limiting + throttling por IP na rota de login do BFF, com testes e documentação. Verificado nesta revisão: `web/app/api/bff/session/route.ts` ainda não implementa nenhuma dessas mitigações. **Deploy para clientes externos/produção pública não deve ocorrer antes desta condição ser atendida** — este runbook cobre apenas o cenário já aprovado (uso interno/piloto). |

### Variáveis de ambiente obrigatórias (serviço `api`)

| Variável | Obrigatória | Efeito se ausente |
|---|---|---|
| `DATABASE_URL` | Sim (já fixada no `docker-compose.yml` para o serviço `database`) | — |
| `API_KEY` | Sim | Toda rota `/api/*` responde `503` (`verify_api_key`, fail-closed) |
| `LLM_PROVIDER` | Sim | Deve ser o provider real (nunca `mock`) em produção |
| `ANTHROPIC_API_KEY` (ou equivalente do provider real) | Sim, se `LLM_PROVIDER` != mock | Falha ao processar qualquer análise |
| `EMBEDDING_PROVIDER` | Sim | Deve ser `voyage` (nunca `mock`) em produção — Production Embedding Provider Approval, D-177 |
| `VOYAGE_API_KEY` | Sim, se `EMBEDDING_PROVIDER=voyage` | Falha ao indexar/consultar a Knowledge Platform (`EmbeddingProviderConfigError`) |
| `CORS_ALLOWED_ORIGINS` | Sim | Vazio por padrão (fail-closed) — sem isso, o frontend de produção não consegue chamar a API |
| `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | Não (default 60/60) | Usa o default do `src/api/rate_limiter.py` |

### Variáveis de ambiente obrigatórias (frontend `web/`, serviço `web` do `docker-compose.yml`)

| Variável | Obrigatória | Efeito se ausente |
|---|---|---|
| `SESSION_SECRET` | Sim | `web/lib/session.ts` falha fechado (nenhuma sessão pode ser emitida ou validada) |
| `WORKSPACE_PASSWORD` | Sim | `POST /api/bff/session` responde `503` |
| `BACKEND_URL` | Sim | BFF não consegue alcançar a API real |
| `API_KEY` (BFF → backend) | Sim | Toda chamada do BFF à API real falha com `503`/`401` |

## 2. Implantação

```bash
# 1. Backup pré-deploy (obrigatório -- ver PRI-008-production-backup-restore-runbook.md Secao 2)
#    executar o procedimento de backup completo antes de prosseguir

# 2. Build das imagens novas (backend + frontend), com a identidade de release
#    (W7-5 Etapa 3 -- commit SHA, exposto em GET /health de ambos os servicos)
GIT_SHA=$(git rev-parse HEAD) docker compose build api web

# 3. Migracao como etapa explicita e separada, ANTES de subir a aplicacao
#    (W7-5 Etapa 5, Migration Discipline -- nao faz mais parte do comando de
#    start do servico api). Uma falha aqui interrompe o deploy: nao
#    prosseguir para o passo 4 se este comando sair com erro.
docker compose run --rm api alembic upgrade head

# 4. Subida da aplicacao (backend + frontend) sobre o schema ja migrado
docker compose up -d api web database

# 5. Confirmar a revisao aplicada (o passo 3 ja a aplicou -- isto so confirma o resultado)
docker compose run --rm api alembic current
```

## 3. Rollback

```bash
# 1. Reverter para a imagem/tag anterior do backend
docker compose up -d --no-build api   # com a tag anterior configurada na imagem/registry

# 2. Se a migracao da versao com problema alterou o schema, restaurar o backup
#    pre-deploy (PRI-008-production-backup-restore-runbook.md Secao 3) --
#    nunca reverter uma migracao Alembic aplicada manualmente no banco em producao

# 3. Confirmar saude apos o rollback (Secao 4 deste documento)
```

Rollback de uma migração de schema (não apenas da imagem da aplicação) sempre passa por
restaurar o backup pré-deploy, nunca por um `alembic downgrade` manual em produção — o
repositório tem hoje 20 migrations reais (`alembic/versions/0001_initial.py` a
`0020_w5_0_document_ingestion.py`), então este cenário deixou de ser hipotético: qualquer
deploy que aplique uma migration nova precisa deste procedimento se o deploy for revertido.

## 4. Validação pós-deploy

```bash
# 1. Health check
curl -sf https://<host-de-producao>/health
# esperado: {"status":"healthy","service":"AI PMO Copilot"}

# 2. Confirmar a revisao do schema
docker compose run --rm api alembic current
# esperado: a revisao mais recente em alembic/versions/

# 3. Confirmar que a chave de API esta ativa (uma chamada real, nao apenas o health check)
curl -sf -H "X-API-Key: <API_KEY-de-producao>" https://<host-de-producao>/api/projects/summary?project_name=<projeto-existente>
```

## 5. Smoke tests

**Smoke test parametrizável (W7-5 Etapa 6):** `web/e2e/smoke.spec.ts`, distinto da suíte
E2E completa, aponta para qualquer ambiente via `PLAYWRIGHT_BASE_URL` (em vez de assumir
`localhost:3100`) e cobre apenas os sinais essenciais pós-instalação: app acessível,
`/api/health` do frontend saudável, `/ready` do backend verde (via `SMOKE_BACKEND_URL`) e
um login básico até um endpoint funcional (via `SMOKE_LOGIN_EMAIL`/`SMOKE_LOGIN_PASSWORD`/
`SMOKE_LOGIN_ORGANIZATION` — nenhuma credencial hardcoded; os checks que dependem dessas
variáveis são pulados, não falham, se elas não forem informadas). Executar:

```bash
PLAYWRIGHT_BASE_URL=https://<host-de-producao> \
SMOKE_BACKEND_URL=https://<host-de-producao-api> \
SMOKE_LOGIN_EMAIL=<email-real> SMOKE_LOGIN_PASSWORD=<senha-real> SMOKE_LOGIN_ORGANIZATION=<org-real> \
  npx playwright test e2e/smoke.spec.ts
```

Este smoke test automatizado cobre apenas o essencial operacional -- ele não substitui os
5 passos manuais abaixo, que continuam sendo a validação funcional completa recomendada
após qualquer deploy real:

1. Login no workspace com a senha real de produção → deve redirecionar para `/dashboard`.
2. `/dashboard` carrega o Portfolio Overview com dado real (não vazio, não erro).
3. Abrir um projeto real em `/workspace/<nome>` → Riscos, Comunicação e Ações carregam.
4. Submeter uma análise real (Status ou Risco) → aparece no Dashboard e no Workspace em
   até 30s (janela de `staleTime` das queries).
5. Navegar por todas as 6 rotas do menu (Dashboard, Priorização, Projetos, Ações,
   Decisões, Aprendizados) → nenhuma retorna erro 500 nem tela em branco.

## 6. Critérios de sucesso

Um deploy é considerado bem-sucedido somente se **todos** os itens abaixo forem
verdadeiros:

- Health check (Seção 4.1) responde `200` com `status: healthy`.
- `alembic current` (Seção 4.2) reporta a revisão mais recente esperada.
- Todos os 5 smoke tests da Seção 5 passam.
- Nenhum erro novo nos logs do container `api` nos primeiros 10 minutos após o deploy.
- O backup pré-deploy (Seção 2, passo 1) existe e foi validado (`PRI-008-production-backup-restore-runbook.md`, Seção 4) **antes** do deploy ser iniciado.

Se qualquer critério falhar, executar o Rollback (Seção 3) imediatamente — não
investigar em produção com o deploy problemático no ar.
