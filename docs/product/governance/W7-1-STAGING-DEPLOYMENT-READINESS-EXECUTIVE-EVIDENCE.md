# W7-1 — Staging Deployment Readiness — Executive Evidence

**Autorização:** "Founder Decision — W7-1 Staging Deployment Readiness". O `W7-1 Staging & Production AI Validation Plan` (D-178) está **APPROVED**. Antes do provisionamento real, autorizado exclusivamente o fechamento dos gaps de deployment identificados em D-178: exemplos desatualizados de `/health` em `PRI-008`/`PRI-009`; `.env.example` sem `ENVIRONMENT`/`RELEASE_SHA`; `docker-compose.yml` com porta `5432` exposta e `POSTGRES_PASSWORD` hardcoded. **Nenhum staging provisionado, nenhuma credencial real usada, nenhuma chamada Anthropic/Voyage executada, nenhum outro Epic da Wave 7 iniciado.**

---

## 1. Gaps encontrados (origem: D-178, Seção 2 e Seção 15)

| # | Gap | Onde |
|---|---|---|
| 1 | Exemplo de `/health` desatualizado, sem o campo `"release"` (adicionado em W7-5 Etapa 3) | `PRI-008` §4, `PRI-009` §4 |
| 2 | `.env.example` nunca documenta `ENVIRONMENT` nem `RELEASE_SHA` | `.env.example` |
| 3 | `docker-compose.yml` expõe a porta `5432` do `database` ao host sem necessidade | `docker-compose.yml` |
| 4 | `docker-compose.yml` fixa `POSTGRES_PASSWORD: aipmo` como literal, sem forma de sobrescrever para staging/produção — e `DATABASE_URL` do serviço `api` replicava o mesmo literal `aipmo:aipmo` | `docker-compose.yml` |

---

## 2. Alterações realizadas

### 2.1 `docker-compose.yml`

- `database.environment`: `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` passam a `${VAR:-aipmo}` (mesmo padrão já usado por `ANTHROPIC_API_KEY`/`VOYAGE_API_KEY`) em vez de literais fixos.
- `database`: removido o bloco `ports: ["5432:5432"]`.
- `database.healthcheck`: `pg_isready -U ${POSTGRES_USER:-aipmo} -d ${POSTGRES_DB:-aipmo}`.
- `api.environment.DATABASE_URL`: passa a `postgresql://${POSTGRES_USER:-aipmo}:${POSTGRES_PASSWORD:-aipmo}@database:5432/${POSTGRES_DB:-aipmo}`, construída a partir das mesmas três variáveis do `database`, em vez do literal `postgresql://aipmo:aipmo@database:5432/aipmo`.

### 2.2 `docker-compose.override.yml` (novo)

Reexpõe `ports: ["5432:5432"]` para o serviço `database` — mecanismo nativo do Docker Compose (base + override), mesclado automaticamente por `docker compose up` apenas quando invocado **sem** `-f` explícito. Preserva a experiência local/dev exatamente como era antes desta mudança.

### 2.3 `src/api/startup_config.py`

Novo fail-fast: `collect_startup_config_problems()` rejeita, em `staging`/`production`, qualquer `DATABASE_URL` que ainda contenha a credencial padrão de desenvolvimento (`aipmo:aipmo@`) — mesmo padrão já usado para o caso `sqlite`. Nenhuma outra função/assinatura alterada.

### 2.4 `.env.example`

- `ENVIRONMENT=dev` documentado, com explicação do que staging/produção ativam.
- `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` documentados (comentados, sem valor), explicando que são consumidos exclusivamente por `docker-compose.yml` (não por `src/`) e que staging/produção devem sobrescrever `POSTGRES_PASSWORD`.
- `RELEASE_SHA`/`GIT_SHA` documentados (comentados), explicando o bake em build-time — nunca uma variável de runtime.

### 2.5 `docs/operations/PRI-008-production-backup-restore-runbook.md`

- §4: exemplo de `/health` corrigido para incluir `"release"`.
- Todos os comandos `docker compose` passam a usar `-f docker-compose.yml` explicitamente.
- Comandos `pg_dump`/`pg_restore`/`psql` passam a usar `-U "${POSTGRES_USER:-aipmo}" -d "${POSTGRES_DB:-aipmo}"` em vez do literal `aipmo`.
- Nota explicativa adicionada no topo do documento.

### 2.6 `docs/operations/PRI-009-production-deployment-runbook.md`

- §4: exemplo de `/health` corrigido para incluir `"release"`.
- Todos os comandos `docker compose` passam a usar `-f docker-compose.yml` explicitamente.
- Tabela de variáveis do `api` ganha as linhas `ENVIRONMENT` e `RELEASE_SHA`.
- Nova tabela "Variáveis de ambiente do PostgreSQL" (`POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`).
- Nota explicativa adicionada na Seção 2 sobre o motivo do `-f docker-compose.yml`.

### 2.7 `tests/test_startup_config.py`

- `_set_valid_env()` (ambas as classes) passa a usar uma credencial não-default (`stratech_staging:real-db-secret`) em vez do literal `aipmo:aipmo`, que agora seria rejeitado pelo próprio fail-fast que ele deveria estar testando como "válido".
- Novo teste `test_database_url_uses_default_dev_credentials` (staging e produção), confirmando o novo fail-fast.

### Diff completo

```
 .env.example                                       | 29 +++++++++++++
 docker-compose.yml                                 | 34 +++++++++++----
 .../PRI-008-production-backup-restore-runbook.md   | 49 ++++++++++++++--------
 .../PRI-009-production-deployment-runbook.md       | 40 ++++++++++++++----
 src/api/startup_config.py                          | 12 ++++++
 tests/test_startup_config.py                       | 18 +++++++-
 6 files changed, 147 insertions(+), 35 deletions(-)
 docker-compose.override.yml (novo, 17 linhas)
```

Nenhum arquivo em `src/services/`, `src/agents/`, `src/workflows/`, `src/database/models.py`, `alembic/`, ou `web/` foi alterado.

---

## 3. Testes executados

| Comando | Resultado |
|---|---|
| `ruff check src/api/startup_config.py tests/test_startup_config.py` | Limpo |
| `ruff check src tests` (baseline completo) | 280 achados pré-existentes, idênticos antes e depois desta missão (não são desta missão — nenhum arquivo tocado por ela contribui a essa contagem) |
| `pytest tests/test_startup_config.py -q` | 31 passed (29 pré-existentes + 2 novos) |
| `pytest tests/ -q` (suíte completa, Postgres real) | **914 passed**, 0 failed (912 pré-D-179 + 2 novos testes) |
| `npx tsc --noEmit` (`web/`) | Limpo (nenhum arquivo `web/` alterado) |
| `docker compose config` (sem `-f`, simulando `docker compose up` local) | Válido — `database.ports = ["5432:5432"]`, `DATABASE_URL=postgresql://aipmo:aipmo@database:5432/aipmo` (idêntico ao comportamento anterior) |
| `docker compose -f docker-compose.yml config` com `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` reais (valores sintéticos de teste, não credenciais reais) | Válido — `database.ports = None` (porta não exposta), `DATABASE_URL` reflete a credencial sobrescrita, consistente entre `api` e `database` |

---

## 4. Configuração DEV (comportamento local, confirmado inalterado)

`docker compose up` (sem `-f`, comportamento padrão local) mescla `docker-compose.override.yml` automaticamente:

- `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` resolvem para `aipmo`/`aipmo`/`aipmo` (defaults, nenhuma variável precisa ser exportada).
- `DATABASE_URL` do `api` = `postgresql://aipmo:aipmo@database:5432/aipmo` — **string idêntica** à existente antes desta mudança.
- Porta `5432` do `database` continua exposta ao host (`localhost:5432`), para `psql`/DBeaver/etc.
- `ENVIRONMENT` continua sem exigência de configuração (default `production` no `docker-compose.yml`; `dev` no `.env.example`/execução direta fora de container) — nenhum comportamento de fail-fast novo se aplica em `dev`.

Confirmado por `docker compose config` (Seção 3) e pela suíte de testes completa (Seção 3), que roda majoritariamente contra bancos Postgres reais criados por `tests/db.py` sem qualquer alteração de comportamento.

---

## 5. Configuração STAGING (protocolo, não executado)

Ao rodar com `-f docker-compose.yml` explícito (per `PRI-009` §2, atualizado nesta missão) e `POSTGRES_PASSWORD` (mínimo) sobrescrita via variável real de ambiente do host (nunca commitada):

- `database.ports` deixa de existir — Postgres não fica acessível fora da rede do Compose.
- `DATABASE_URL` do `api` reflete a mesma credencial real, automaticamente, sem edição manual em dois lugares.
- Se o operador esquecer de sobrescrever `POSTGRES_PASSWORD`, `DATABASE_URL` ainda resolve para a credencial padrão de dev (`aipmo:aipmo@`) — e o Configuration Contract (`src/api/startup_config.py`) falha o boot explicitamente com uma mensagem que nomeia a causa e a correção (`test_database_url_uses_default_dev_credentials`, Seção 3).
- `ENVIRONMENT=staging`/`production` continua ativando todo o restante do Configuration Contract já existente (inalterado por esta missão): `API_KEY`, `LLM_PROVIDER`/`ANTHROPIC_API_KEY`, `EMBEDDING_PROVIDER`/`VOYAGE_API_KEY`, `CORS_ALLOWED_ORIGINS`.

Validado nesta missão exclusivamente por `docker compose config` (renderização/interpolação, sem subir containers) e pelo teste automatizado citado — **nenhum container de staging foi de fato iniciado**.

---

## 6. Tratamento de PostgreSQL

| Requisito do Founder | Como foi atendido |
|---|---|
| Não expor `5432` publicamente sem necessidade | Removido do `docker-compose.yml` base; reexposto apenas via `docker-compose.override.yml`, mesclado apenas quando não há `-f` explícito (nunca o caso em staging/produção, per `PRI-009` §2 atualizado) |
| Remover dependência de senha hardcoded para staging/produção | `POSTGRES_PASSWORD` passa a `${POSTGRES_PASSWORD:-aipmo}` — staging/produção sobrescrevem com um segredo real; se não sobrescreverem, o boot falha explicitamente (Seção 5) em vez de silenciosamente aceitar a senha fraca |
| Preservar a experiência local/dev existente | Confirmado idêntico por `docker compose config` (Seção 3) — mesma `DATABASE_URL`, mesma porta exposta, nenhuma variável nova exigida localmente |
| Usar somente mecanismos compatíveis com o Configuration Contract e docker-compose atuais | Interpolação `${VAR:-default}` (já usada por `ANTHROPIC_API_KEY`/`VOYAGE_API_KEY`) + base/override nativo do Compose — nenhum mecanismo novo |
| Não introduzir secrets manager ou nova infraestrutura | Nenhum introduzido — nenhuma dependência nova em `requirements.txt`/`package.json`, nenhum serviço novo no `docker-compose.yml` |

---

## 7. Tratamento de secrets

- Nenhum valor real de `POSTGRES_PASSWORD`/`ANTHROPIC_API_KEY`/`VOYAGE_API_KEY`/`API_KEY` foi definido, usado ou registrado em nenhum arquivo desta missão.
- `docker-compose.yml`/`docker-compose.override.yml`/`.env.example` contêm exclusivamente defaults de desenvolvimento (`aipmo`) ou placeholders vazios/comentados — nenhum segredo versionado.
- O valor usado para validar `docker compose config` em staging (Seção 3) foi uma string sintética de teste (`not-a-real-secret-example`), nunca persistida em nenhum arquivo do repositório.
- `git diff`/`git status` confirmam que nenhum arquivo de segredo (`.env`, chaves, tokens) foi criado ou alterado por esta missão.

---

## 8. Riscos residuais

| Risco | Registro |
|---|---|
| A checagem de credencial padrão em `startup_config.py` é uma correspondência de string literal (`aipmo:aipmo@`) — detecta especificamente o default deste repositório, não qualquer senha fraca em geral | Aceitável: o objetivo mandatado era eliminar a dependência do default hardcoded conhecido, não construir um validador de força de senha genérico (fora de escopo, não demandado) |
| `docker-compose.override.yml` precisa continuar existindo e ser corretamente excluído (`-f docker-compose.yml`) em todo comando de staging/produção — depende de disciplina operacional, não de um mecanismo que impeça o erro estruturalmente | Mitigado por documentação consistente em `PRI-008`/`PRI-009` (todos os comandos já usam `-f` explicitamente) e pelo próprio fail-fast do Configuration Contract, que barra o boot se a porta continuar exposta *e* a senha permanecer no default simultaneamente — mas não impede uma senha real com a porta ainda exposta por engano de operação; validação real desse cenário fica para a execução real do W7-1 |
| `TD-... `docs/product/governance/W7-1-STAGING-PRODUCTION-AI-VALIDATION-PLAN.md` (D-178) não foi retroativamente editado para refletir esta correção | Decisão deliberada, consistente com a disciplina já estabelecida nesta missão (`DECISION-LOG.md`: "Não editado retroativamente — uma correção é uma nova entrada") — este documento (D-179) é o registro da resolução, não uma revisão silenciosa do plano já aprovado |

Nenhum risco novo introduzido por esta missão além dos listados.

---

## 9. Confirmação: nenhum staging foi provisionado

- Nenhum host real foi criado, acessado ou configurado.
- `docker compose config` foi usado exclusivamente para validar a renderização/interpolação do YAML — nenhum `docker compose up`/`run` foi executado contra qualquer ambiente além do já existente ambiente de teste local (Postgres local, mesmo usado por toda a suíte `pytest` desta missão).
- Nenhuma credencial real (`ANTHROPIC_API_KEY`/`VOYAGE_API_KEY`/`POSTGRES_PASSWORD` real) foi usada em nenhum passo.
- Nenhuma chamada real a Anthropic/Voyage AI foi executada.
- Nenhum outro Epic da Wave 7 foi iniciado.

---

## 10. GO/NO-GO para Provision Staging

**GO tecnicamente para `Provision Staging`** — os quatro gaps de deployment identificados em D-178 estão fechados, comprovados por `docker compose config` (dev e staging simulados) e pela suíte de testes completa (914 passed, incluindo os 2 novos testes do fail-fast de credencial padrão). Nenhuma regressão introduzida. `docker-compose.yml`, `docker-compose.override.yml`, `.env.example`, `PRI-008`, `PRI-009` e o Configuration Contract estão agora mutuamente consistentes.

**O provisionamento real permanece condicionado aos Gates Externos já registrados em D-178** (Staging Host, Voyage API Credential, Anthropic API Credential, Data/DPA Approval) — nenhum deles foi resolvido por esta missão. Nenhum trabalho subsequente inicia automaticamente. Retornando obrigatoriamente para Executive Review do Founder.
