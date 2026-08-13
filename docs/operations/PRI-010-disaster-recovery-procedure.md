# PRI-010 — Disaster Recovery Procedure

Runbook operacional que transforma o Disaster Recovery Protocol já aprovado
(`docs/architecture/TECHNICAL-DESIGN-W7-3-RESILIENCE-DISASTER-RECOVERY.md` Seção 10, D-181)
em um procedimento executável, fase a fase, reutilizando exclusivamente mecanismos já
implementados: `src/database/backup.py` (Backup Contract, D-182), `src/database/restore_validation.py`
(Restore Contract, D-183), o Deployment Contract do W7-5 (`docker-compose.yml`/`PRI-009`), e a
política de delete já vigente e testada (TD-002, D-184). Nenhum mecanismo novo é introduzido
por este documento.

**RTO/RPO oficiais (Founder Decision, W7-3):** RTO ≤ 8 horas, RPO ≤ 24 horas — baseline de
Enterprise Readiness da V1. Este procedimento deve permitir medir ambos em uma execução real
(Etapa 5, DR Drill — **não executada por esta missão**, per restrição explícita do Founder).

**Estado desta correção:** `DOCUMENTED` — cada fase abaixo mapeia a um mecanismo já
`IMPLEMENTED`/`TESTED LOCALLY` (D-182/D-183/D-184). **`NOT YET EXERCISED IN REAL DR DRILL`** —
nenhuma fase abaixo foi executada contra um ambiente real por este documento; a única prova de
que o procedimento funciona ponta a ponta é um DR Drill real (Etapa 5), ainda não autorizado.

---

## Pré-requisitos

- Um backup válido e verificado, produzido por `python -m src.database.backup` (Seção 8 do
  Technical Design, D-182) — sem um backup válido, este procedimento não pode prosseguir além
  da fase "Restore Database".
- Acesso ao host onde `docker compose -f docker-compose.yml` roda o ambiente afetado (ou onde
  um ambiente de substituição será provisionado — Gate A de W7-1, ainda `PENDING`).
- O papel de **Disaster Declaration Authority** já identificado (Technical Design Seção 14) —
  este procedimento não define quem exerce cada papel, apenas onde cada papel atua.

---

## Fases

### 1. Incident

| Campo | Definição |
|---|---|
| Entrada | Sinal de falha (alerta manual, indisponibilidade observada, erro reportado) |
| Ação | Registrar o horário exato do incidente (`t_incident`) — ponto de partida para o cálculo de RTO/RPO reais |
| Critério de sucesso | Incidente identificado, `t_incident` registrado |
| Critério de falha | N/A (fase de detecção, não de execução) |
| Evidência produzida | Timestamp `t_incident` + descrição do sinal que motivou a fase |

### 2. Declare Disaster

| Campo | Definição |
|---|---|
| Entrada | Avaliação humana de que o incidente excede recuperação local (ex.: reiniciar o container não resolve — Failure Scenario A/B/E/L do Technical Design Seção 12, nunca C/D/F/K, que são rollback de aplicação, não Disaster Recovery) |
| Ação | **Disaster Declaration Authority** (Technical Design Seção 14) declara formalmente o Disaster, registrando `t_declared` |
| Critério de sucesso | Disaster declarado por quem tem a autoridade; classificação do cenário confirmada contra a Failure Scenario Matrix (Seção 12 do Technical Design) |
| Critério de falha | Declarado sem necessidade (falso positivo) — reavaliar antes de prosseguir; ou cenário classificado como rollback de aplicação (C/D/F/K) — este procedimento não se aplica, usar `PRI-009` §3 |
| Evidência produzida | Timestamp `t_declared`, classificação do cenário (letra A-L da Failure Scenario Matrix), identidade de quem declarou |

### 3. Stop/Isolate

| Campo | Definição |
|---|---|
| Entrada | Disaster declarado, ambiente afetado identificado |
| Ação | `docker compose -f docker-compose.yml stop api web` — evita escritas concorrentes durante a recuperação |
| Critério de sucesso | Serviços `api`/`web` parados, sem escrita concorrente ao banco |
| Critério de falha | Comando falha (host inacessível) — prosseguir direto para "Recover Environment" (o cenário é perda de host, não apenas de dado) |
| Evidência produzida | `docker compose -f docker-compose.yml ps` confirmando `api`/`web` parados |

### 4. Recover Environment

| Campo | Definição |
|---|---|
| Entrada | Serviços parados (ou host indisponível — Failure Scenario E) |
| Ação | Se o host existe: `docker compose -f docker-compose.yml up -d database`. Se o host foi perdido: provisionar um substituto (fora do escopo deste documento — depende do Gate A de W7-1, `PENDING`) e clonar o release atual (`git clone`/`docker compose -f docker-compose.yml build`, mesma identidade de release, `GIT_SHA=$(git rev-parse HEAD)`) |
| Critério de sucesso | `database` `healthy` (`docker compose -f docker-compose.yml ps` reporta `pg_isready` verde) |
| Critério de falha | Timeout de `healthcheck`, ou nenhum host disponível (bloqueado no Gate A) |
| Evidência produzida | `docker compose -f docker-compose.yml ps` do serviço `database`; `RELEASE_SHA` do ambiente recuperado |

### 5. Restore Database

| Campo | Definição |
|---|---|
| Entrada | `database` saudável, um backup válido disponível (metadata sidecar `.json` do `src/database/backup.py`, D-182, confirmando `environment`/`release_sha`/`alembic_revision` do backup a usar) |
| Ação | `pg_restore --clean --if-exists --dbname <DATABASE_URL> <backup>.dump` (`PRI-008` §3) |
| Critério de sucesso | `pg_restore` conclui sem erro `FATAL` |
| Critério de falha | Dump corrompido/ilegível — usar o backup anterior na retenção (`PRI-008` §5); registrar o horário do backup efetivamente usado como `t_backup` — a diferença `t_incident - t_backup` é o **RPO real** desta execução |
| Evidência produzida | Log de `pg_restore`; `t_backup` (timestamp do backup usado, do seu metadata sidecar); RPO real calculado |

### 6. Validate Schema

| Campo | Definição |
|---|---|
| Entrada | Restore concluído |
| Ação | `alembic current` seguido de `alembic upgrade head` (idempotente — `PRI-008` §3) |
| Critério de sucesso | Revisão aplicada é o head real do repositório |
| Critério de falha | Migration falha — **nunca** tentar `alembic downgrade` manual (`PRI-009` §3); investigar a causa antes de prosseguir |
| Evidência produzida | Saída de `alembic current` pós-migração |

### 7. Start Services

| Campo | Definição |
|---|---|
| Entrada | Schema validado |
| Ação | `docker compose -f docker-compose.yml up -d api web` |
| Critério de sucesso | Containers `api`/`web` em estado `running` |
| Critério de falha | Crash loop — investigar logs (`docker compose -f docker-compose.yml logs api`), corrigir configuração (Configuration Contract, `src/api/startup_config.py`), repetir esta fase |
| Evidência produzida | `docker compose -f docker-compose.yml ps` |

### 8. Readiness

| Campo | Definição |
|---|---|
| Entrada | Serviços `running` |
| Ação | `curl -sf <host>/health` e `curl -sf <host>/ready` |
| Critério de sucesso | `/health` → `200` com `release` esperado; `/ready` → `200 {"status":"ready"}` |
| Critério de falha | `/ready` → `503` com `problems` — corrigir o item listado (Configuration Contract), repetir esta fase |
| Evidência produzida | Corpo de `/health` e `/ready` |

### 9. Structural Validation

| Campo | Definição |
|---|---|
| Entrada | Readiness verde |
| Ação | `validate_restore(engine, expect_populated=True)` (`src/database/restore_validation.py`, D-183) — nesta fase, interpretar exclusivamente os dois primeiros grupos de achados que o mesmo módulo já produz: (1) revisão Alembic aplicada == head real; (2) todas as tabelas esperadas (derivadas de `Base.metadata`, nunca hardcoded) presentes |
| Critério de sucesso | Nenhum achado de schema/tabela ausente |
| Critério de falha | Restore estruturalmente incompleto (Failure Scenario L) — repetir a partir de um backup anterior (Seção 5) |
| Evidência produzida | Saída completa de `validate_restore()` (`RestoreValidationResult`) |

### 10. Functional Validation

| Campo | Definição |
|---|---|
| Entrada | Validação estrutural verde |
| Ação | Mesma chamada de `validate_restore(engine, expect_populated=True)` (uma única execução já cobre Estrutural + Funcional — Seção 9 acima) — nesta fase, interpretar o restante dos achados: integridade referencial (nenhuma linha órfã em `programs`/`document_versions`/`chunks`), contrato de embedding (`vector_dims(embedding) = 1024` em todo `chunks`), tabelas CRITICAL não vazias (`organizations`/`users`/`audit_logs`/`events`) |
| Critério de sucesso | `RestoreValidationResult.ok is True`, `problems == ()` |
| Critério de falha | Qualquer achado funcional — restauração não é aceita; repetir a partir de um backup anterior |
| Evidência produzida | Mesma saída de `validate_restore()` da fase anterior |

### 11. Knowledge/AI Validation (quando aplicável)

| Campo | Definição |
|---|---|
| Entrada | Validação funcional verde |
| Ação | Retrieval real via `KnowledgeRepository.search()` (ou a rota `document-advisor/ask`) contra um documento conhecido do dataset restaurado — "quando aplicável" porque só se aplica a um ambiente que já tinha Knowledge Platform populada antes do incidente |
| Critério de sucesso | Retorna o(s) chunk(s) esperado(s), citando o documento correto |
| Critério de falha | Retrieval vazio/incorreto apesar da Seção 10 já ter confirmado `vector_dims`/integridade — investigar como achado novo, não presumir que é o mesmo problema já coberto |
| Evidência produzida | Resposta da busca/rota, com os `chunk_id`/`document_id` retornados |

### 12. Smoke Test

| Campo | Definição |
|---|---|
| Entrada | Validações anteriores verdes (Knowledge/AI Validation, se aplicável) |
| Ação | `PLAYWRIGHT_BASE_URL=<ambiente> SMOKE_BACKEND_URL=<ambiente-api> npx playwright test e2e/smoke.spec.ts` (`web/e2e/smoke.spec.ts`, já parametrizável desde W7-5 Etapa 6, nenhuma mudança necessária) |
| Critério de sucesso | Os 4 checks do smoke test passam |
| Critério de falha | Qualquer check falho — investigar pela camada correspondente (mapeia às fases 7-11 acima) |
| Evidência produzida | Relatório do Playwright |

### 13. Recovery Acceptance

| Campo | Definição |
|---|---|
| Entrada | Smoke test verde |
| Ação | **Validation Authority** confirma tecnicamente que todas as fases passaram; **Business Acceptance Authority** confirma que o RPO real (Seção 5) é aceitável do ponto de vista de negócio (Technical Design Seção 14) |
| Critério de sucesso | Ambiente aceito como recuperado; registrar `t_accepted` |
| Critério de falha | Não aceito — continuar investigando antes de declarar a recuperação concluída, nunca aceitar com ressalvas silenciosas |
| Evidência produzida | `t_accepted`; **RTO real = `t_accepted - t_incident`**, comparado contra o objetivo aprovado (≤ 8h); **RPO real** já calculado na fase 5, comparado contra o objetivo aprovado (≤ 24h); consolidação de toda a evidência das 13 fases em um documento de Executive Evidence do drill (produzido apenas na execução real, Etapa 5/6 — não nesta missão) |

---

## Medição de RTO/RPO

| Métrica | Fórmula | Objetivo aprovado (Founder, W7-3) |
|---|---|---|
| RPO real | `t_incident - t_backup` (fase 5) | ≤ 24 horas |
| RTO real | `t_accepted - t_incident` (fase 13) | ≤ 8 horas |

Se qualquer métrica exceder o objetivo aprovado, a execução não é automaticamente um `NO-GO`
silencioso — é registrada como achado real do drill (Technical Design Seção 11, critérios
GO/NO-GO), elevada ao Founder junto da Executive Evidence.

---

## Relação com os demais runbooks

Este procedimento **não substitui** `PRI-008` (Backup & Restore) nem `PRI-009` (Deployment) —
ele os sequencia, junto dos mecanismos das Etapas 1-3 do W7-3, em um protocolo único e
executável para o cenário específico de Disaster Recovery (Failure Scenarios A/B/E/L do
Technical Design Seção 12). Rollback de aplicação/deployment comum (Failure Scenarios C/D/F/K
— migration falha, release defeituosa, container perdido, config incorreta) continua coberto
integralmente por `PRI-009` §3, nunca por este documento.
