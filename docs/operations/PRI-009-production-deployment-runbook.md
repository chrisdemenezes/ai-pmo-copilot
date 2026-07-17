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
| Backend containerizado (`Dockerfile` + `docker-compose.yml`) | Pronto | Serviços `api` (FastAPI/Uvicorn) e `database` (`postgres:16`) |
| Migração de schema | Pronta | `alembic upgrade head` já é parte do comando de start do serviço `api` |
| Variáveis de ambiente de produção | A configurar por deploy | Ver tabela abaixo |
| Hospedagem do frontend (`web/`) | **Não decidido** | `RFC-001-frontend-architecture.html` (linha 1167) registra esta pergunta como aberta desde a concepção do frontend ("Deploy: nova entrada no `docker-compose.yml` existente, ou pipeline separado?") — não há `Dockerfile` em `web/`, nem `vercel.json`, nem entrada de frontend no `docker-compose.yml` atual. **Este runbook não pode prescrever passos de deploy do frontend até essa decisão ser tomada pelo Founder/CTO.** |
| Mitigação de força bruta em `/api/bff/session` | **Pendente — condição já registrada** | `docs/development/01-project-structure.md` (seção "Decision: Security Finding") registra risco aceito formalmente apenas para uso interno/piloto, com condição explícita e obrigatória antes de qualquer deploy além desse escopo: rate limiting + throttling por IP na rota de login do BFF, com testes e documentação. Verificado nesta revisão: `web/app/api/bff/session/route.ts` ainda não implementa nenhuma dessas mitigações. **Deploy para clientes externos/produção pública não deve ocorrer antes desta condição ser atendida** — este runbook cobre apenas o cenário já aprovado (uso interno/piloto). |

### Variáveis de ambiente obrigatórias (serviço `api`)

| Variável | Obrigatória | Efeito se ausente |
|---|---|---|
| `DATABASE_URL` | Sim (já fixada no `docker-compose.yml` para o serviço `database`) | — |
| `API_KEY` | Sim | Toda rota `/api/*` responde `503` (`verify_api_key`, fail-closed) |
| `LLM_PROVIDER` | Sim | Deve ser o provider real (nunca `mock`) em produção |
| `ANTHROPIC_API_KEY` (ou equivalente do provider real) | Sim, se `LLM_PROVIDER` != mock | Falha ao processar qualquer análise |
| `CORS_ALLOWED_ORIGINS` | Sim | Vazio por padrão (fail-closed) — sem isso, o frontend de produção não consegue chamar a API |
| `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | Não (default 60/60) | Usa o default do `src/api/rate_limiter.py` |

### Variáveis de ambiente obrigatórias (frontend `web/`, onde quer que seja hospedado)

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

# 2. Build e subida do backend com a imagem nova
docker compose pull        # se usando um registry; ou:
docker compose build api
docker compose up -d --build api database

# 3. Confirmar que a migracao foi aplicada (o comando do servico ja roda
#    "alembic upgrade head" antes do uvicorn subir -- isto so confirma o resultado)
docker compose run --rm api alembic current

# 4. Frontend: depende da decisao de hospedagem da Secao 1 -- nao prescrito aqui
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
repositório tem hoje uma única migração (`alembic/versions/0001_initial.py`), então este
cenário é hipotético até que uma segunda migração exista, mas o procedimento vale a
partir da primeira migração adicional.

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

Executar manualmente (ou via a suíte E2E real, `npx playwright test`, apontada para o
ambiente de produção via `PLAYWRIGHT_BASE_URL`, se essa variável vier a ser suportada
pela config — hoje `playwright.config.ts` aponta para `localhost:3100` fixamente, então
o smoke test pós-deploy real é manual até essa lacuna ser fechada):

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
