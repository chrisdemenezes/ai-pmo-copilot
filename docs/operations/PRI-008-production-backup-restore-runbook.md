# PRI-008 — Production Backup & Restore Runbook

Runbook operacional para o único armazenamento com estado da STRATECH V1 em produção: o
banco PostgreSQL (`docker-compose.yml`, serviço `database`, imagem `pgvector/pgvector:pg16`
— o `postgres:16` oficial com a extensão `pgvector` pré-instalada, adotada na Wave 3,
Enterprise Knowledge Platform Fase 1 —, volume nomeado `aipmo_postgres_data`). O SQLite
usado por `AnalysisRepository` é o padrão apenas para desenvolvimento local/Demo Mode
(`DATABASE_URL` não definido) — nunca o alvo deste runbook.

Registrado como `PRI-008` no Platform Readiness Backlog por decisão do Founder/CTO
(Release Blocker `RB-002`), como pré-requisito para a STRATECH V1 RC-1. Nenhuma
automação nova foi criada por este documento — os comandos abaixo usam exclusivamente
ferramentas já presentes na imagem `postgres:16` (`pg_dump`/`pg_restore`/`psql`) e o
Alembic já usado pelo próprio serviço `api` (`alembic upgrade head`, `Dockerfile` linha 12
e comando do serviço `api` em `docker-compose.yml`).

**W7-1 Staging Deployment Readiness (Founder Decision, D-179):** todos os comandos
`docker compose` abaixo passam `-f docker-compose.yml` explicitamente — em staging/
produção isso exclui `docker-compose.override.yml` (mesclado automaticamente apenas
quando `docker compose` é invocado sem `-f`, mecanismo nativo do Compose para
conveniência de desenvolvimento local), garantindo que a porta `5432` do `database`
nunca fique acessível fora da rede do Compose nesses ambientes. `POSTGRES_USER`/
`POSTGRES_DB` nos comandos `pg_dump`/`pg_restore`/`psql` abaixo usam a mesma variável
de ambiente (`${POSTGRES_USER:-aipmo}`/`${POSTGRES_DB:-aipmo}`) que `docker-compose.yml`
já usa para o serviço `database` — funcionam sem alteração tanto com o default de
desenvolvimento quanto com um valor real sobrescrito em staging/produção.

## 1. Estratégia de backup

Backup lógico via `pg_dump` em formato custom (`-Fc`), executado dentro do container
`database` (mesmo host da rede Docker, sem expor a porta 5432 além do necessário). Um
dump lógico foi escolhido em vez de um snapshot do volume porque:

- é portável entre versões de imagem do Postgres (16.x → 16.y);
- permite restauração seletiva (`pg_restore --table`) se um dia necessário;
- não exige parar o container para um backup consistente (`pg_dump` usa uma transação
  `REPEATABLE READ`, sem lock exclusivo sobre nenhuma das tabelas do banco `aipmo` —
  revisão W7-5 Etapa 5: o schema real hoje tem ~20 tabelas, não apenas `analysis_records`,
  ver nota na Seção 4).

```bash
# Executar a partir do host que roda o docker-compose
docker compose -f docker-compose.yml exec -T database \
  pg_dump -U "${POSTGRES_USER:-aipmo}" -d "${POSTGRES_DB:-aipmo}" -Fc -f /tmp/aipmo_backup.dump

docker compose -f docker-compose.yml cp database:/tmp/aipmo_backup.dump \
  "./backups/aipmo_$(date +%Y%m%d_%H%M%S).dump"

docker compose -f docker-compose.yml exec -T database rm /tmp/aipmo_backup.dump
```

Armazenar o arquivo resultante fora do host do container (o diretório `./backups/` acima
é ilustrativo — a política real de onde os backups são persistidos, replicados e
criptografados em repouso depende do provedor de infraestrutura escolhido para produção,
ainda não definido neste repositório; ver Seção 5 do `PRI-009-production-deployment-runbook.md`
sobre esse mesmo ponto em aberto).

## 2. Periodicidade

Linha de base recomendada, a ajustar conforme volume real observado em produção (o
Architecture Gate V1 e o Platform Readiness Assessment já registraram que a V1 não tem
hoje uma projeção de volume real de cliente corporativo — `PRI-005`):

| Tipo | Frequência | Retenção |
|---|---|---|
| Backup completo (`pg_dump -Fc`) | Diário | 7 backups diários |
| Backup completo | Semanal (aos domingos) | 4 backups semanais |
| Backup antes de qualquer deploy | Sob demanda, antes de `alembic upgrade head` | Mantido até o próximo backup diário confirmar sucesso |

A execução automática (cron, GitHub Actions agendado, ou o agendador do provedor de
infraestrutura escolhido) não está implementada neste repositório — este runbook
descreve o procedimento manual/scriptável que qualquer automação futura deve reproduzir
exatamente, para que o comportamento nunca dependa de uma ferramenta específica.

## 3. Restauração

Pré-requisito: um dump gerado pela Seção 1, e o serviço `api` parado (para evitar
escritas durante a restauração).

```bash
# 1. Parar a API para evitar escritas durante a restauração
docker compose -f docker-compose.yml stop api

# 2. Copiar o dump para dentro do container do banco
docker compose -f docker-compose.yml cp "./backups/aipmo_20260716_030000.dump" \
  database:/tmp/restore.dump

# 3. Restaurar em um banco limpo (--clean remove objetos existentes antes de recriar)
docker compose -f docker-compose.yml exec -T database \
  pg_restore -U "${POSTGRES_USER:-aipmo}" -d "${POSTGRES_DB:-aipmo}" --clean --if-exists /tmp/restore.dump

# 4. Confirmar que o schema está na revisão esperada pelo código atual
docker compose -f docker-compose.yml run --rm api alembic current
docker compose -f docker-compose.yml run --rm api alembic upgrade head

# 5. Reiniciar a API
docker compose -f docker-compose.yml up -d api

# 6. Limpar o dump temporário do container
docker compose -f docker-compose.yml exec -T database rm /tmp/restore.dump
```

`alembic upgrade head` no passo 4 é idempotente (não-op se o schema restaurado já estiver
na revisão mais recente) — executá-lo sempre após qualquer restauração garante que um
dump mais antigo que uma migração nova seja corretamente atualizado antes da API voltar
ao ar.

## 4. Validação pós-restauração

**Gap histórico corrigido (W7-3 Etapa 2, Founder Decision):** os 3 checks que este runbook
documentava até então validavam apenas `analysis_records`, a única tabela que existia
quando o runbook foi escrito — o schema real tem hoje 21 tabelas. `src/database/restore_validation.py`
(`validate_restore()`) substitui definitivamente essa cobertura parcial: deriva as tabelas
esperadas de `Base.metadata` (nunca uma contagem hardcoded, per Founder), confirma a
revisão Alembic aplicada contra o head real do repositório, confirma integridade
referencial (nenhuma linha órfã em `programs`→`portfolios`, `document_versions`→`documents`,
`chunks`→`document_versions`), confirma que todo `chunks.embedding` restaurado tem a
dimensão de produção (`vector_dims(embedding) = 1024`), e, quando o backup usado é
conhecidamente de uma fonte populada (`expect_populated=True`), confirma que as tabelas
CRITICAL (`organizations`, `users`, `audit_logs`, `events`) não ficaram vazias — nunca
exige isso de tabelas RECONSTRUCTABLE (`roles`/`permissions`/`invitations`), que podem
legitimamente estar vazias sem indicar uma restauração incompleta. Nenhuma restauração é
considerada concluída sem os 4 checks abaixo:

```bash
# 1. Health check da API
curl -sf http://localhost:8000/health
# esperado (W7-5 Etapa 3, Release Identity):
# {"status":"healthy","service":"AI PMO Copilot","release":"<git-sha-do-deploy>"}

# 2. Readiness (Configuration Contract + conectividade real ao banco)
curl -sf http://localhost:8000/ready
# esperado: {"status":"ready"}

# 3. Validação estrutural + funcional completa das 21 tabelas (W7-3 Etapa 2)
docker compose -f docker-compose.yml run --rm api python -c \
  "from sqlalchemy import create_engine; import os; \
   from src.database.restore_validation import validate_restore; \
   result = validate_restore(create_engine(os.environ['DATABASE_URL']), expect_populated=True); \
   print(result); \
   raise SystemExit(0 if result.ok else 1)"

# 4. Smoke test (Seção 5 abaixo) contra o ambiente restaurado
```

Se qualquer um dos 4 falhar, não promover a restauração como concluída — repetir a partir
de um backup anterior (Seção 2, retenção de 7 diários + 4 semanais existe exatamente para
esse cenário).

**Estado desta correção:** `IMPLEMENTED`/`TESTED LOCALLY` (`tests/test_restore_validation.py`,
ciclo real backup→restore→validação contra Postgres real, incluindo detecção de restore
incompleto e de schema incompatível) — `NOT YET EXERCISED IN REAL DR DRILL`. O DR Drill
real (Technical Design Seção 11, Etapa 5 — não autorizada nesta missão) é o único evento
que pode declarar este mecanismo comprovado em produção.

## 5. Recuperação após falha

| Cenário | Procedimento |
|---|---|
| Volume do Postgres corrompido/perdido | Provisionar um volume novo (`docker compose -f docker-compose.yml down -v database && docker compose -f docker-compose.yml up -d database`), seguir a Seção 3 (Restauração) a partir do backup diário mais recente |
| Migração (`alembic upgrade head`) falha após deploy | Restaurar o backup pré-deploy (Seção 2, linha "antes de qualquer deploy") — nunca tentar reverter uma migração parcialmente aplicada manualmente no banco |
| Dump mais recente está corrompido/ilegível pelo `pg_restore` | Usar o dump anterior na retenção (diário N-1, depois semanal); documentar o dump corrompido como incidente para investigar a causa antes do próximo ciclo |
| Perda total do host (sem backups locais acessíveis) | Depende inteiramente de onde os arquivos de `./backups/` foram replicados (Seção 1) — este runbook não pode garantir recuperação nesse cenário até que a estratégia de armazenamento externo de backup seja decidida (mesmo ponto em aberto citado na Seção 1) |

## 6. Limitação registrada

Este runbook cobre o procedimento técnico completo (estratégia, periodicidade,
restauração, validação, recuperação). Ele **não** resolve, por si só, dois pontos que
permanecem em aberto e são pré-requisitos de qualquer execução real em produção: (a)
onde os arquivos de backup são armazenados fora do host (Seção 1); (b) a automação que
dispara este procedimento na periodicidade da Seção 2. Ambos dependem da escolha do
provedor de infraestrutura de produção, ainda não definida neste repositório (mesmo
ponto em aberto registrado no `PRI-009-production-deployment-runbook.md`, Seção 1).
