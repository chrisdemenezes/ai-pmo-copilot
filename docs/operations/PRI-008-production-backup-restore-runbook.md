# PRI-008 — Production Backup & Restore Runbook

Runbook operacional para o único armazenamento com estado da STRATECH V1 em produção: o
banco PostgreSQL (`docker-compose.yml`, serviço `database`, imagem `postgres:16`, volume
nomeado `aipmo_postgres_data`). O SQLite usado por `AnalysisRepository` é o padrão apenas
para desenvolvimento local/Demo Mode (`DATABASE_URL` não definido) — nunca o alvo deste
runbook.

Registrado como `PRI-008` no Platform Readiness Backlog por decisão do Founder/CTO
(Release Blocker `RB-002`), como pré-requisito para a STRATECH V1 RC-1. Nenhuma
automação nova foi criada por este documento — os comandos abaixo usam exclusivamente
ferramentas já presentes na imagem `postgres:16` (`pg_dump`/`pg_restore`/`psql`) e o
Alembic já usado pelo próprio serviço `api` (`alembic upgrade head`, `Dockerfile` linha 12
e comando do serviço `api` em `docker-compose.yml`).

## 1. Estratégia de backup

Backup lógico via `pg_dump` em formato custom (`-Fc`), executado dentro do container
`database` (mesmo host da rede Docker, sem expor a porta 5432 além do necessário). Um
dump lógico foi escolhido em vez de um snapshot do volume porque:

- é portável entre versões de imagem do Postgres (16.x → 16.y);
- permite restauração seletiva (`pg_restore --table`) se um dia necessário;
- não exige parar o container para um backup consistente (`pg_dump` usa uma transação
  `REPEATABLE READ`, sem lock exclusivo sobre a tabela `analysis_records`).

```bash
# Executar a partir do host que roda o docker-compose
docker compose exec -T database \
  pg_dump -U aipmo -d aipmo -Fc -f /tmp/aipmo_backup.dump

docker compose cp database:/tmp/aipmo_backup.dump \
  "./backups/aipmo_$(date +%Y%m%d_%H%M%S).dump"

docker compose exec -T database rm /tmp/aipmo_backup.dump
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
docker compose stop api

# 2. Copiar o dump para dentro do container do banco
docker compose cp "./backups/aipmo_20260716_030000.dump" \
  database:/tmp/restore.dump

# 3. Restaurar em um banco limpo (--clean remove objetos existentes antes de recriar)
docker compose exec -T database \
  pg_restore -U aipmo -d aipmo --clean --if-exists /tmp/restore.dump

# 4. Confirmar que o schema está na revisão esperada pelo código atual
docker compose run --rm api alembic current
docker compose run --rm api alembic upgrade head

# 5. Reiniciar a API
docker compose up -d api

# 6. Limpar o dump temporário do container
docker compose exec -T database rm /tmp/restore.dump
```

`alembic upgrade head` no passo 4 é idempotente (não-op se o schema restaurado já estiver
na revisão mais recente) — executá-lo sempre após qualquer restauração garante que um
dump mais antigo que uma migração nova seja corretamente atualizado antes da API voltar
ao ar.

## 4. Validação pós-restauração

Nenhuma restauração é considerada concluída sem os 3 checks abaixo:

```bash
# 1. Health check da API
curl -sf http://localhost:8000/health
# esperado: {"status":"healthy","service":"AI PMO Copilot"}

# 2. Contagem de registros restaurados é maior que zero e plausível
docker compose exec -T database \
  psql -U aipmo -d aipmo -c "SELECT COUNT(*) FROM analysis_records;"

# 3. O registro mais recente restaurado corresponde ao esperado (mesma
#    data/hora do momento em que o backup usado foi gerado, nunca mais recente)
docker compose exec -T database \
  psql -U aipmo -d aipmo -c \
  "SELECT project_name, kind, created_at FROM analysis_records ORDER BY created_at DESC, id DESC LIMIT 5;"
```

Se qualquer um dos 3 falhar, não promover a restauração como concluída — repetir a partir
de um backup anterior (Seção 2, retenção de 7 diários + 4 semanais existe exatamente para
esse cenário).

## 5. Recuperação após falha

| Cenário | Procedimento |
|---|---|
| Volume do Postgres corrompido/perdido | Provisionar um volume novo (`docker compose down -v database && docker compose up -d database`), seguir a Seção 3 (Restauração) a partir do backup diário mais recente |
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
