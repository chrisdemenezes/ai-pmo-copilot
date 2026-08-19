# Technical Design — W7-3: Resilience & Disaster Recovery

**Autorização:** "Founder Decision — Wave 7 — Abertura Institucional do W7-3 — Resilience & Disaster Recovery". W7-5 está concluído; W7-1 permanece OPEN, tecnicamente pronto, estacionado aguardando os Gates Externos A-D (Staging Host, Voyage/Anthropic credentials, Data/DPA) — **nenhum trabalho adicional no W7-1 nesta missão**. A AR-18 identificou Disaster Recovery como um dos dois blockers estruturais da Enterprise Readiness (RTO/RPO indefinidos, nenhum plano formal). Autorizada exclusivamente a abertura institucional do W7-3: análise arquitetural e produção deste Technical Design/Architecture Review. **Nenhum código implementado, nenhuma infraestrutura provisionada, nenhum restore real executado, nenhum banco alterado, nenhuma migration alterada, nenhum pipeline alterado, nenhum outro Epic da Wave 7 iniciado.**

**Princípio fundamental (mandato do Founder):** o objetivo não é alta disponibilidade sofisticada — é o menor conjunto verificável, operacional, recuperável, documentado, testável e proporcional ao estágio atual da V1. Nenhum Kubernetes, multi-region, active-active, service mesh, replicação complexa ou plataforma nova é proposto sem necessidade demonstrada pelo código real.

---

## 1. Executive Summary

A STRATECH V1 tem **um único armazenamento com estado**: PostgreSQL (`pgvector/pgvector:pg16`), incluindo os embeddings do Knowledge Platform na própria tabela `chunks` — confirmado por leitura direta de `docker-compose.yml` e `src/database/models.py`, não um vector store separado. Isso simplifica estruturalmente o escopo de W7-3 a um único componente de dados, exatamente como AR-18 §9 já havia antecipado (revalidado aqui, não assumido).

**Mecanismo de backup/restore existe** (`pg_dump -Fc`/`pg_restore`, documentado em `PRI-008`) mas **nunca foi executado contra um ambiente real**, e **nenhuma automação existe** — nenhum script de backup/restore/DR foi encontrado no repositório além da prosa do runbook. `RTO`/`RPO` permanecem indefinidos, confirmando AR-18 §9 itens 12-13 sem alteração. A validação pós-restauração do `PRI-008` §4 **continua cobrindo apenas `analysis_records`**, a única tabela existente quando o runbook foi escrito — o schema real hoje tem 21 tabelas (confirmado por leitura completa de `src/database/models.py` + `src/database/repository.py`) — esta é a divergência mais concreta encontrada nesta revisão, já elevada por W7-5/AR-18 e **ainda não corrigida** por nenhuma missão até esta.

Este documento entrega: inventário completo de estado persistente com classificação de recuperabilidade (Seção 3-4, incluindo confirmação — não assunção — de que embeddings são reconstruíveis a partir dos documentos originais, mas com custo real e uma dependência de uma dívida técnica já registrada); opções concretas de RTO/RPO para decisão do Founder (Seção 7); um Backup Contract e um Restore Contract mínimos, reaproveitando `pg_dump`/`pg_restore`/Alembic (Seções 8-9); um Disaster Recovery Protocol executável reaproveitando integralmente o Deployment Contract do W7-5 (Seção 10); um modelo de DR Drill que exige execução real, não apenas documentação (Seção 11); uma matriz de 12 cenários de falha (Seção 12); análise da relação com o staging do W7-1 (Seção 13); um modelo mínimo de ownership operacional (Seção 14); mapeamento de Technical Debt (TD-001, TD-002) (Seção 16); e uma estratégia incremental de implementação futura em 6 etapas, nenhuma executada (Seção 17).

**Nenhum valor de RTO/RPO foi decidido por este documento.** Nenhuma implementação foi feita. GO/NO-GO recomendado apenas para a **próxima etapa de implementação incremental** (Seção 20), condicionado a decisões explícitas do Founder (Seção 19).

---

## 2. Current State (grounding mecânico, revalidado nesta missão)

| Item mandatado | Estado confirmado | Evidência |
|---|---|---|
| `docker-compose.yml` | Único serviço com estado: `database` (`pgvector/pgvector:pg16`), volume nomeado `aipmo_postgres_data`. `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` interpoláveis, sem literal fixo (D-179) | `docker-compose.yml` |
| `docker-compose.override.yml` | Existe (D-179) — reexpõe a porta `5432` apenas para dev local, mesclado automaticamente só sem `-f` explícito | `docker-compose.override.yml` |
| PostgreSQL/pgvector | `pgvector/pgvector:pg16`, instância única, sem réplica, sem sharding, sem multi-AZ — confirmado, nenhuma mudança desde AR-18 §9 item 2/9 | `docker-compose.yml` |
| Alembic e migrations | 21 migrations reais (`0001_initial.py` a `0021_production_embedding_provider.py`), todas com corpo de `downgrade()` não-vazio (confirmado programaticamente, nenhuma migration é irreversível ao nível de schema) | `alembic/versions/` |
| `PRI-008` | Existe, atualizado em D-179 (exemplo de `/health`, `-f docker-compose.yml`, `${POSTGRES_USER:-aipmo}`/`${POSTGRES_DB:-aipmo}` nos comandos `pg_dump`/`pg_restore`/`psql`) — **mas o gap de validação pós-restauração (§4, cobre apenas `analysis_records`) permanece aberto**, não tocado por D-179 | `docs/operations/PRI-008-production-backup-restore-runbook.md` §4 |
| `PRI-009` | Existe, atualizado em D-179; §3 Rollback documenta reverter imagem + restaurar backup pré-deploy — nunca exercitado | `docs/operations/PRI-009-production-deployment-runbook.md` §3 |
| Scripts existentes de backup/restore | **Nenhum encontrado.** `scripts/` contém apenas `prepare-env.sh`, `rc1-local-start.sh`, `rc2-db.sh`/`rc2-db.ps1` — nenhum relacionado a backup/restore/DR. Todo o procedimento de `PRI-008` é manual, copiado/colado da prosa do runbook | busca completa no repositório (`find`, sem `.git`/`node_modules`) |
| Health/Readiness | `GET /health` (`release` incluso), `GET /ready` (config + `SELECT 1` real) — inalterados desde W7-5 | `src/main.py` |
| Configuration Contract | `src/api/startup_config.py` — inalterado nesta missão; já inclui (D-179) o fail-fast contra a credencial padrão de dev em `DATABASE_URL` | `src/api/startup_config.py` |
| Deployment Contract | `docker-compose.yml` + `PRI-009` §2 — inalterado | — |
| Release identity | `RELEASE_SHA`/`GIT_SHA`, bake em build-time — inalterado | `Dockerfile`, `web/Dockerfile` |
| Migration discipline | Etapa explícita, separada do `command:` do `api` — inalterado | `docker-compose.yml` |
| Rollback existente | `PRI-009` §3: reverter imagem/tag + restaurar backup pré-deploy; **nunca reverter uma migration Alembic manualmente em produção** — documentado, nunca exercitado sob condição real | `PRI-009` §3 |
| Persistência de documentos/chunks/vetores | `documents`/`document_versions`/`chunks` — conteúdo normalizado armazenado como texto no próprio Postgres (`document_versions.content`), **nenhum blob storage externo** — confirmado por leitura direta de `KnowledgeRepository.ingest()`/`index()`, não apenas por AR-18 §9 item 3 | `src/database/models.py`, `src/services/knowledge_platform/knowledge_repository.py` |
| Dados de domínio | `organizations`, `users`, `roles`/`permissions`/`role_permissions`/`user_roles`, `portfolios`/`programs`/`projects`/`user_project_memberships`, `analysis_records`, `api_keys`, `sessions`, `invitations` — inventário completo na Seção 3 | `src/database/models.py`, `src/database/repository.py` |
| Audit logs | `audit_logs` — presente, inalterado | `src/database/models.py` |
| Knowledge Platform | `documents`/`document_versions`/`chunks`/`memory_records` — inalterado | `src/database/models.py` |
| Configurações de volumes | Único volume nomeado, `aipmo_postgres_data` — nenhum outro volume persistente existe | `docker-compose.yml` |
| Mecanismos atuais de backup/restore/recovery/rollback | `pg_dump -Fc`/`pg_restore` (manual, `PRI-008`); reverter imagem + restaurar backup (`PRI-009` §3) — **nenhuma automação, nenhum script, nenhum job de CI** | busca completa + `.github/workflows/` |

### Divergência encontrada e elevada explicitamente

**`PRI-008` §4 (Validação pós-restauração) continua desatualizado para o schema real.** O próprio runbook já registra este gap explicitamente desde a revisão W7-5 Etapa 5 ("Gap elevado... os 3 checks acima validam apenas `analysis_records`"), e D-179 (a missão imediatamente anterior) **não o corrigiu** — D-179 tocou apenas o exemplo de `/health`, o flag `-f docker-compose.yml` e os placeholders `POSTGRES_USER`/`POSTGRES_DB` nos comandos `pg_dump`/`pg_restore`/`psql`, deixando a lacuna de cobertura de validação intocada por decisão de escopo (fora do que D-178 havia identificado como gap de *deployment*). Este é precisamente o gap que a Seção 9 (Restore Contract) deste documento endereça — determinando o que deve substituí-lo, sem implementá-lo nesta missão.

Nenhuma outra divergência entre documentação e código real foi encontrada nesta revisão.

---

## 3. Persistent State Inventory

Todas as 21 tabelas do schema real (`src/database/models.py` + `AnalysisRecord` em `src/database/repository.py`), nenhuma omitida:

| Tabela | Domínio | Descrição |
|---|---|---|
| `organizations` | Identity/Tenant | Raiz do isolamento multi-tenant |
| `users` | Identity | Contas reais, unicidade case-insensitive por org |
| `roles` | RBAC | Catálogo de papéis |
| `permissions` | RBAC | Catálogo de permissões |
| `role_permissions` | RBAC | Mapeamento papel→permissão |
| `user_roles` | RBAC | Atribuição real usuário→papel |
| `portfolios` | Enterprise Domain | Raiz Portfolio→Program→Project |
| `programs` | Enterprise Domain | Pertence a exatamente um Portfolio |
| `projects` | Enterprise Domain | Unificado (Épico 1 + campos de domínio) |
| `user_project_memberships` | Enterprise Domain | Atribuição real usuário→projeto |
| `analysis_records` | Executive Intelligence (legado) | Histórico real de análises (Status/Risco) |
| `api_keys` | Identity | Credencial de acesso programático, hash Argon2 |
| `sessions` | Identity | Sessão de login server-side, TTL 12h |
| `invitations` | Identity | Credencial de onboarding, single-use, com expiração |
| `audit_logs` | Enterprise Administration | Trilha de auditoria de mutações |
| `documents` | Knowledge Platform | Ponteiro de metadado de uma fonte ingerida |
| `document_versions` | Knowledge Platform | Conteúdo normalizado, nunca sobrescrito — **única cópia do texto ingerido** |
| `chunks` | Knowledge Platform | Unidade recuperável: texto + vetor `pgvector(1024)` + proveniência |
| `memory_records` | Enterprise Memory Model | Classificação de um Document já ingerido (5 categorias) |
| `events` | Wave 4, Event Audit | Envelope durável de todo evento publicado |
| `dead_letter_events` | Wave 4, Event Audit | Evento cujo dispatch falhou `MAX_ATTEMPTS` vezes |
| `workflow_executions` | Wave 4, Workflow Runtime | Rastreamento de execução (idempotência via `UNIQUE(event_id, workflow_name)`) |

Nenhum armazenamento com estado fora do Postgres foi encontrado — nenhum arquivo em disco do container, nenhum bucket externo, nenhuma fila persistente, nenhum cache com estado de negócio (confirmado por `requirements.txt`: nenhuma dependência de Redis/S3/MinIO/Celery/Kafka/RabbitMQ).

---

## 4. Criticality Classification

Critério: **CRITICAL** = perda inaceitável, sem caminho de reconstrução automático (trabalho real, decisão humana, ou histórico não recriável). **RECONSTRUCTABLE** = pode ser regenerado a partir de outra fonte durável (seed de código, ou outra tabela ainda intacta), com ou sem custo/atrito operacional. **EPHEMERAL** = de vida curta por design, perda sem consequência funcional além de fricção menor. **N/A** = não aplicável/não persistido.

| Tabela | Classificação | Justificativa técnica |
|---|---|---|
| `organizations` | **CRITICAL** | Raiz do tenant — nenhuma fonte de reconstrução |
| `users` | **CRITICAL** | Contas reais, credenciais (hash), sem fonte alternativa |
| `roles` | RECONSTRUCTABLE | Catálogo estático, semeado pela migration `0006` (`op.bulk_insert`) — conteúdo definido em código, não pelo usuário |
| `permissions` | RECONSTRUCTABLE | Idem — catálogo estático semeado por `0006` |
| `role_permissions` | RECONSTRUCTABLE | Idem — mapeamento estático semeado por `0006` |
| `user_roles` | **CRITICAL** | Atribuição real (decisão de admin) — nenhum reseed reconstrói quem tem qual papel |
| `portfolios` / `programs` / `projects` | **CRITICAL** | Dado de domínio real, sem fonte alternativa |
| `user_project_memberships` | **CRITICAL** | Atribuição real |
| `analysis_records` | **CRITICAL** | Histórico real de análises — reexecutar a análise produziria conteúdo diferente (LLM não determinístico), não uma restauração do registro original |
| `api_keys` | **CRITICAL** | Hash do segredo, sem forma de recriar a chave física já entregue a uma integração; perda exige reemissão de todas as chaves e quebra de integrações em produção |
| `sessions` | EPHEMERAL | TTL de 12h por design; ausência de linha é tratada como sessão ainda ativa (`UserSession` docstring) — perda apenas reabre uma janela de revogação, sem quebrar autenticação |
| `invitations` | RECONSTRUCTABLE | Convite pendente perdido pode ser reenviado pelo admin sem perda de estado permanente — aceitação já promove a um `User`, que é separadamente Critical |
| `audit_logs` | **CRITICAL** | Trilha de auditoria — requisito de integridade de auditoria (Enterprise Administration, Nível 1), sem reconstrução possível |
| `documents` | **CRITICAL** | Ponteiro de metadado real (fonte, organização, projeto) |
| `document_versions` | **CRITICAL** | **Única cópia do conteúdo ingerido** — confirmado: nenhum blob storage externo existe, `content` é a fonte de verdade |
| `chunks.text` | RECONSTRUCTABLE (condicional) | Derivado deterministicamente de `document_versions.content` via `_chunk_text()` (`knowledge_repository.py`, função pura, `CHUNK_SIZE_CHARS=500`/`CHUNK_OVERLAP_CHARS=50`) — reconstruível **somente se** `document_versions.content` (Critical) estiver intacto |
| `chunks.embedding` | RECONSTRUCTABLE (condicional, com custo real) | **Confirmado pelo pipeline real, não assumido:** `KnowledgeRepository.index()` computa cada embedding chamando `self._embedding_provider.embed(chunk_text)` — reconstruível reindexando o `DocumentVersion`, mas exige (a) `document_versions.content` intacto, (b) o mesmo provider/modelo de produção disponível (Voyage `voyage-4`) e uma chamada real, paga, à API (não gratuita, não instantânea), (c) atenção a uma dívida já registrada (D-175/D-177): `KnowledgeRepository.index()` **não deleta** chunks existentes do `document_version_id` antes de inserir novos — reindexar sem antes limpar as linhas antigas duplicaria os chunks. **Conclusão:** reconstrução é tecnicamente possível como *caminho secundário*, nunca como substituto do restore primário (Seção 8-9) |
| `memory_records` | RECONSTRUCTABLE (condicional) | Classificação derivada de um `Document` já ingerido — reconstruível se o `Document`/`DocumentVersion` de origem estiver intacto, mediante reclassificação real (não um valor determinístico puro, mas derivável do mesmo processo de classificação) |
| `events` | **CRITICAL** | Envelope durável do fato publicado — sem fonte alternativa; perda quebra a auditoria "o que foi publicado" |
| `dead_letter_events` | RECONSTRUCTABLE | Registro de falha de dispatch — sua perda não perde o evento original (`events` é a fonte de verdade); apenas perde o histórico de tentativas falhas, que não bloqueia nenhuma função |
| `workflow_executions` | RECONSTRUCTABLE | Rastreamento de execução — sua perda não impede reprocessamento (a idempotência é a garantia operacional, não o histórico); perde-se apenas a visibilidade histórica de "o que rodou e como" |

**Achado explícito sobre embeddings (mandato do Founder, não assumido):** embeddings **não são "gratuitamente" reconstruíveis** — dependem de uma chamada real e paga ao provider de produção, e a reconstrução via reindexação está condicionada a uma dívida técnica já registrada (duplicação de chunks se o `document_version` não for limpo antes). Por isso, o Backup/Restore Contract (Seções 8-9) trata `chunks` (texto + vetor + proveniência) como parte integral do backup lógico do Postgres — a mesma unidade de recuperação de qualquer outra tabela — e não como algo dispensável do backup só porque, em teoria, é reconstruível.

---

## 5. Existing Backup/Restore Capabilities

| Capacidade | Existe? | Comprovada em produção? |
|---|---|---|
| Backup lógico (`pg_dump -Fc`) | Sim, documentado em `PRI-008` §1, usa exclusivamente ferramentas já presentes na imagem `postgres:16` | Não — nunca executado contra ambiente real |
| Restore (`pg_restore --clean --if-exists`) | Sim, documentado em `PRI-008` §3 | Não — nunca exercitado |
| Verificação pós-restauração | Parcial — 3 checks (`/health`, contagem de `analysis_records`, registro mais recente) | Cobre apenas 1 das 21 tabelas — gap já registrado, ainda aberto |
| Automação de periodicidade (cron/scheduler) | **Não implementada** — `PRI-008` §2 documenta a linha de base recomendada (diário/semanal/pré-deploy) mas nenhum agendador real existe no repositório | N/A |
| Rollback de aplicação (imagem/tag) | Sim, `PRI-009` §3 | Não — nunca exercitado |
| Rollback de migration | **Explicitamente desaconselhado em produção** — `PRI-009` §3 determina sempre restaurar backup pré-deploy em vez de `alembic downgrade` manual | N/A por design |
| Criptografia em repouso do backup | **Não definida** — `PRI-008` §1 registra que a política real de armazenamento/replicação/criptografia depende do provedor de infraestrutura, ainda não escolhido (Gate A de W7-1) | Não |
| Isolamento do backup do ambiente principal | **Não definido** — mesmo ponto em aberto acima | Não |
| Identificação de release/schema no backup | Parcial — `alembic current` documentado como passo de confirmação pós-restore, mas o backup em si (`pg_dump`) não carimba a revisão Alembic no nome do arquivo | Não |

---

## 6. Gaps

| # | Gap | Severidade | Origem |
|---|---|---|---|
| 1 | Validação pós-restauração cobre apenas `analysis_records`, não as outras 20 tabelas | Alta — um restore "bem-sucedido" pode ocultar perda silenciosa em Identity/RBAC/Knowledge Platform | `PRI-008` §4, reconfirmado nesta missão |
| 2 | RTO/RPO indefinidos | Alta — blocker nomeado pelo Founder (AR-18 §8) | AR-18 §9 itens 12-13 |
| 3 | Nenhuma automação de backup (cron/scheduler) | Média — procedimento manual é o único existente | `PRI-008` §2 |
| 4 | Nenhum backup/restore jamais executado contra dado real | Alta — mecanismo nunca comprovado sob condição real | AR-18 §12 |
| 5 | Nenhum DR drill jamais ocorreu | Alta — blocker nomeado (AR-18 §8/§9 item 11) | AR-18 §9 item 11 |
| 6 | Política de delete (RESTRICT/CASCADE) indefinida (TD-002) | Média-Alta — um `DELETE` real hoje produz órfãos silenciosos, não um erro | AR-18 §12, TD-002 |
| 7 | Ownership operacional de DR não atribuído | Média — nenhum papel de Disaster Declaration/Recovery Operator/Validation decidido | AR-18 §9 item 10 |
| 8 | Localização/criptografia/isolamento do armazenamento de backup indefinidos | Média — depende do Gate A (Staging Host) de W7-1, ainda `PENDING` | `PRI-008` §1 |
| 9 | Identificação de release/schema não carimbada no artefato de backup | Baixa — `alembic current` cobre parcialmente, mas não no próprio arquivo de backup | `PRI-008` §1/§3 |
| 10 | Reconstrução de `chunks.embedding` depende de uma dívida não corrigida (reindex não deleta chunks antigos) | Baixa (só relevante se reconstrução for usada como caminho *secundário*, não é o restore primário) | D-175/D-177, confirmado nesta missão |

Nenhum gap novo além destes 10 foi encontrado. Nenhum é resolvido por este documento — todos ficam registrados para a Seção 17 (Estratégia de Implementação).

---

## 7. RTO/RPO Decision Analysis

**Nenhum valor é decidido aqui.** Apresentadas como alternativas concretas, com trade-offs reais baseados na arquitetura atual (Postgres único, `pg_dump`/`pg_restore` lógico, sem réplica).

### RPO (Recovery Point Objective — quanto dado pode se perder)

| Alternativa | Mecanismo necessário | Complexidade | Custo | Adequação à V1 |
|---|---|---|---|---|
| **24h** | Backup diário via `pg_dump` (já documentado) + agendador simples (cron) | Baixa — nenhuma mudança de arquitetura | Baixo | Alta — proporcional ao estágio atual, sem cliente corporativo real ainda operando 24/7 (confirmado ausência de projeção de volume real, `PRI-005`) |
| **4h** | Backup a cada 4h via `pg_dump` + agendador; ou WAL archiving (`pg_basebackup`/`archive_command`) para PITR (Point-in-Time Recovery) | Média — `pg_dump` a cada 4h é trivial de agendar, mas cada execução compete por I/O com a carga real; PITR via WAL exige configuração adicional de storage e retenção de arquivos WAL | Médio | Adequado somente se houver justificativa real de negócio para menos de 24h de perda tolerável — não demonstrada nesta revisão |
| **1h** | PITR via WAL archiving (`archive_command`/`restore_command`) é o único mecanismo realista para RPO de 1h com backup lógico periódico — `pg_dump` de hora em hora é tecnicamente possível mas operacionalmente pesado em bancos maiores | Alta — introduz um mecanismo novo (WAL archiving), armazenamento contínuo de WALs, retenção, e testes de restore por PITR | Alto | **Overengineering para o estágio atual** — nenhuma evidência de necessidade real; volume de dados e criticidade de negócio não demonstram esse requisito hoje |

### RTO (Recovery Time Objective — quanto tempo até religar)

| Alternativa | Mecanismo necessário | Complexidade | Custo | Adequação à V1 |
|---|---|---|---|---|
| **8h** | Protocolo manual (Seção 10): provisionar/reutilizar VM, restaurar backup, migrar, subir serviços, validar — tudo manual, seguindo o Deployment Contract do W7-5 | Baixa | Baixo | Alta — realista para um time pequeno executando um runbook manual, sem automação de orquestração |
| **4h** | Reduz o tempo manual via automação parcial (scripts que encapsulam os passos do protocolo, hot-standby de VM pré-provisionada) | Média | Médio | Possível, mas exige pelo menos um "ambiente de reserva" já provisionado e pronto para receber o restore — não existe hoje (depende do Gate A de W7-1) |
| **1h** | Exige infraestrutura ativa/passiva (standby quente, réplica pronta para promoção) — muda fundamentalmente a arquitetura de instância única | Alta | Alto | **Overengineering para o estágio atual** — introduziria réplica/failover sem necessidade demonstrada, contra o princípio fundamental desta missão |

### RECOMMENDED RTO

**8h**, com o protocolo manual da Seção 10, sem automação de orquestração nova. Justificativa: proporcional ao estágio atual (nenhum SLA de cliente corporativo real ainda contratado, confirmado por `PRI-005`), reutiliza integralmente o Deployment Contract já existente, e é o único que não exige nenhuma capacidade nova de infraestrutura.

### RECOMMENDED RPO

**24h**, com backup diário via `pg_dump` + agendador simples (a definir na implementação — cron do host, ou o agendador do provedor de infraestrutura escolhido no Gate A). Justificativa: mesma proporcionalidade — nenhuma evidência de necessidade de PITR/WAL archiving hoje; `PRI-008` §2 já recomenda esta cadência como linha de base.

### ALTERNATIVES

RPO de 4h/1h e RTO de 4h/1h permanecem tecnicamente descritos acima, disponíveis caso o Founder identifique um requisito de negócio real (ex.: SLA contratual futuro) que justifique o investimento adicional.

### DECISION REQUIRED

O Founder deve decidir formalmente RTO e RPO antes do fechamento do W7-3 (Seção 14 do mandato: critério de encerramento explícito). Esta análise não decide por ele.

---

## 8. Backup Contract

Contrato mínimo, reaproveitando exclusivamente o mecanismo já documentado (`pg_dump -Fc`, `PRI-008` §1) — nenhuma infraestrutura nova.

| Aspecto | Definição proposta |
|---|---|
| O que precisa ser salvo | Backup lógico completo do banco `aipmo` (`pg_dump -Fc`, sem `--table`) — cobre as 21 tabelas em uma única operação, incluindo `chunks` (texto + vetor `pgvector` + proveniência) |
| Frequência | Conforme RPO decidido (Seção 7) — recomendado: diário + semanal (já a linha de base de `PRI-008` §2) + obrigatório antes de qualquer deploy (`PRI-009` §2 passo 1) |
| Retenção | 7 diários + 4 semanais (já proposto em `PRI-008` §2) — ponto de partida, ajustável quando houver projeção real de volume de cliente corporativo (`PRI-005`) |
| Consistência | Já garantida — `pg_dump` usa uma transação `REPEATABLE READ` sem lock exclusivo (confirmado, `PRI-008` §1) |
| Criptografia | **Não definida** — depende do provedor de infraestrutura de staging/produção (Gate A de W7-1, `PENDING`). Não introduzir mecanismo de criptografia próprio sem necessidade demonstrada — usar o que o provedor escolhido oferecer nativamente (a maioria oferece criptografia em repouso por padrão para armazenamento de objeto) |
| Localização | Fora do host do container (já recomendado em `PRI-008` §1) — destino real depende do Gate A |
| Isolamento do ambiente principal | O backup deve residir em um armazenamento logicamente distinto da instância `database` (mesmo requisito já registrado, não resolvido) |
| Identificação de release/schema | **Gap a fechar (não implementado aqui):** o nome do arquivo de backup deve carimbar, no mínimo, a revisão Alembic corrente no momento do backup (ex.: `aipmo_<timestamp>_<alembic-revision>.dump`) — hoje `PRI-008` só usa timestamp |
| Relação com Alembic | Backup pré-deploy já obrigatório antes de `alembic upgrade head` (`PRI-009` §2 passo 1) — mantido sem alteração |
| Verificação automática | **Gap a fechar:** hoje nenhuma verificação automática existe — mínimo proposto: confirmar que o arquivo de backup gerado é não-vazio e que `pg_restore --list` (que apenas lista o conteúdo do dump, sem restaurar) roda sem erro contra o arquivo recém-criado, como smoke check do próprio backup |
| Tratamento de falha do backup | **Gap a fechar:** hoje nenhum alerta/retry existe — mínimo proposto: se o comando `pg_dump` sair com código de erro, o backup do dia é marcado como falho e o backup anterior na retenção continua sendo o mais recente válido (nunca substituir um backup bom por um resultado de falha) |
| Backup lógico é suficiente para a V1? | **Sim — nenhuma evidência concreta exige mecanismo adicional.** Confirmado: volume de dados real desconhecido (sem cliente corporativo operando, `PRI-005`), instância única sem réplica, RPO recomendado de 24h (Seção 7) plenamente atendido por `pg_dump` periódico. Snapshot de volume (alternativa a `pg_dump`) permanece descartado pelas mesmas razões já registradas em `PRI-008` §1 (portabilidade entre versões de imagem, restauração seletiva, sem necessidade de parar o container) |

---

## 9. Restore Contract

### Processo mínimo (reaproveitando `PRI-008` §3, sem alteração de comandos)

1. Parar a API (`docker compose -f docker-compose.yml stop api`).
2. Copiar o dump para o container do banco.
3. `pg_restore --clean --if-exists` em um banco limpo.
4. Confirmar a revisão Alembic (`alembic current`) e aplicar `alembic upgrade head` se o dump for de uma revisão anterior à mais recente (idempotente).
5. Reiniciar a API.

### Por que "pg_restore terminou sem erro" não é suficiente (mandato do Founder)

`pg_restore` sem erro confirma apenas que o dump foi sintaticamente aplicado — não que os dados restaurados são funcionalmente corretos, completos, ou compatíveis com o release/schema que vai rodar sobre eles. O que precisa substituir a validação atual (que cobre 1 de 21 tabelas):

| Camada | O que validar | Como (reaproveitando mecanismos existentes) |
|---|---|---|
| Schema/migrations | Revisão Alembic aplicada é a esperada | `alembic current` (já documentado) |
| Organizations | Existe ao menos 1 organização, contagem plausível (não zero se o backup não era de uma instalação vazia) | `SELECT COUNT(*) FROM organizations;` |
| Users | Contagem plausível, ao menos 1 usuário ativo por organização crítica | `SELECT COUNT(*) FROM users WHERE is_active;` |
| Domain entities | Portfolios/Programs/Projects presentes e com FK íntegra (nenhum `program.portfolio_id` órfão) | `SELECT COUNT(*) FROM programs p LEFT JOIN portfolios pf ON p.portfolio_id = pf.id WHERE pf.id IS NULL;` deve retornar `0` |
| `AnalysisRecords` | Já coberto — contagem + registro mais recente (mantido de `PRI-008` §4 atual) |
| Auditability | `audit_logs` não está vazio se a instalação restaurada tinha atividade real | `SELECT COUNT(*) FROM audit_logs;` |
| Knowledge Documents | `documents`/`document_versions` presentes, sem `document_versions` órfão de `documents` | `SELECT COUNT(*) FROM document_versions dv LEFT JOIN documents d ON dv.document_id = d.id WHERE d.id IS NULL;` deve retornar `0` |
| Chunks | Contagem de `chunks` plausível frente à contagem de `document_versions`; nenhum `chunk` órfão | Mesma checagem de FK acima, aplicada a `chunks`→`document_versions` |
| Embeddings/pgvector | `vector_dims(embedding) = 1024` para toda linha (confirma que o dump não veio de um schema com dimensão antiga, ex. o `vector(16)` pré-D-177) | `SELECT COUNT(*) FROM chunks WHERE vector_dims(embedding) != 1024;` deve retornar `0` |
| Health | `/health` responde `200` com o `release` esperado | `curl -sf .../health` (já documentado) |
| Readiness | `/ready` responde `200` | `curl -sf .../ready` (já documentado) |
| Smoke test | Suite parametrizável já existente roda contra o ambiente restaurado | `web/e2e/smoke.spec.ts` (W7-5 Etapa 6, já parametrizável — nenhuma mudança necessária) |

### O que deve substituir o gap do `PRI-008` §4

Um restore só é considerado válido com evidência real de **todas** as checagens acima (não apenas as 3 atuais) — a tabela acima é a especificação do que a Seção 17 (Etapa 2 — Restore Validation) deve implementar como um script único e reutilizável (não implementado nesta missão), substituindo os 3 checks atuais do `PRI-008` §4 por esta cobertura completa das 21 tabelas.

---

## 10. Disaster Recovery Protocol

A sequência proposta pelo Founder foi validada contra o produto real e **confirmada sem alteração estrutural** — cada etapa já tem um mecanismo real correspondente (nenhuma etapa inventada):

| Etapa | Input | Mecanismo/comando existente | Critério de sucesso | Critério de falha | Rollback aplicável |
|---|---|---|---|---|---|
| Incident | Sinal de falha (alerta manual, monitoramento externo — nenhum mecanismo de alerta automatizado existe hoje) | N/A (humano) | Incidente identificado e registrado | N/A | N/A |
| Declare Disaster | Avaliação humana de que o incidente excede recuperação local (ex.: reiniciar container não resolve) | N/A (humano, ownership Seção 14) | Disaster declarado formalmente por quem tem a autoridade (Seção 14) | Declarado sem necessidade (falso positivo) — reavaliar | N/A |
| Stop/Isolate | Ambiente afetado identificado | `docker compose -f docker-compose.yml stop api web` (evita escritas durante a recuperação) | Serviços parados, sem escrita concorrente | Comando falha (host inacessível) → ir direto a Provision/Recover | N/A |
| Provision/Recover Environment | Host disponível (existente ou novo, conforme o cenário — Seção 12) | `docker compose -f docker-compose.yml up -d database` (host existente) ou provisionamento de host novo (fora do escopo desta missão) | `database` `healthy` (`pg_isready`) | Timeout de `healthcheck` | N/A |
| Restore Database | Backup mais recente válido (Seção 8) | `PRI-008` §3 (Seção 9 acima) | `pg_restore` sem erro | Dump corrompido → usar backup anterior na retenção (`PRI-008` §5) | Repetir com backup N-1 |
| Apply/Validate Schema | Restore concluído | `alembic current` + `alembic upgrade head` (idempotente) | Revisão esperada confirmada | Migration falha | Investigar; nunca `downgrade` manual (`PRI-009` §3) |
| Start Services | Schema validado | `docker compose -f docker-compose.yml up -d api web` | Containers `running` | Crash loop | Investigar logs |
| Readiness | Serviços up | `GET /ready` | `200` | `503` com `problems` | Corrigir o problema listado (Configuration Contract) |
| Functional Validation | Readiness verde | Consultas SQL da Seção 9 (tabela completa) | Todas as checagens passam | Qualquer checagem falha | Reavaliar qual backup foi usado; repetir com backup anterior se dado estiver incompleto |
| AI/Knowledge Validation | Functional Validation verde | Retrieval real via `KnowledgeRepository.search()` (ou rota `document-advisor/ask`) contra um documento conhecido do dataset restaurado | Retorna resultado esperado | Retrieval vazio/incorreto | Investigar — não é um cenário de restore incompleto se `chunks`/`vector_dims` já passaram na Seção 9 |
| Smoke Test | Validações anteriores verdes | `web/e2e/smoke.spec.ts` (já parametrizável, W7-5) | Todos os checks verdes | Qualquer check falho | Investigar por camada |
| Recovery Acceptance | Smoke verde | Decisão humana (Validation Authority, Seção 14) | Ambiente aceito como recuperado | Não aceito → continuar investigando antes de declarar recuperação concluída | N/A |

Nenhuma etapa foi adicionada ou removida da hipótese do Founder — todas mapeiam 1:1 a mecanismos já existentes, confirmando que o protocolo é executável **sem** nenhuma capacidade nova de infraestrutura.

---

## 11. DR Drill Model

**Documentação não é prova.** O Completion Gate futuro do W7-3 exige execução real. Modelo proposto (não executado nesta missão):

| Aspecto | Definição |
|---|---|
| Ambiente | O ambiente de staging do W7-1, uma vez provisionado (Gate A) — ver análise de conflito de finalidade na Seção 13. Nunca produção real |
| Dataset | Sintético/controlado — mesmo princípio já aplicado em W7-1 (D-178 Seção 6/8: nenhum dado corporativo real antes do Gate D de Data/DPA) — um conjunto de organizações/usuários/documentos de teste, com volume suficiente para exercitar todas as 21 tabelas |
| Backup utilizado | Um backup real gerado pelo Backup Contract (Seção 8) contra esse dataset sintético, não um backup fabricado à mão |
| Procedimento | O Disaster Recovery Protocol completo (Seção 10), do Incident simulado até a Recovery Acceptance |
| Métricas | Tempo decorrido de cada etapa da Seção 10, agregado no RTO medido; timestamp do backup usado vs. timestamp do "incidente simulado", agregado no RPO comprovado |
| RTO medido | Tempo real do drill, comparado ao RTO decidido pelo Founder (Seção 7) |
| RPO comprovado | Diferença real entre o estado restaurado e o estado no momento do "incidente", comparada ao RPO decidido |
| Validações | Todas as checagens da Seção 9 (Restore Contract), executadas de fato, não apenas descritas |
| Evidências produzidas | Log de cada etapa, saída de cada query de validação, resultado do smoke test, tempo decorrido por etapa — reunidos em um documento de Executive Evidence do drill (futuro, não produzido aqui) |
| Critérios GO/NO-GO | GO: todas as validações da Seção 9 passam, RTO medido ≤ RTO decidido, RPO comprovado ≤ RPO decidido. NO-GO: qualquer validação falha, ou RTO/RPO medidos excedem o decidido — nesse caso, o drill é repetido após correção, nunca aceito com ressalvas silenciosas |

**Não executado nesta missão** — depende do Gate A de W7-1 (Staging Host) e da decisão de RTO/RPO (Seção 7), ambos pendentes do Founder.

---

## 12. Failure Scenario Matrix

| # | Cenário | Classificação | Justificativa |
|---|---|---|---|
| A | Perda completa do PostgreSQL | **requires DR** | Único datastore com estado — perda total exige o protocolo completo da Seção 10 |
| B | Corrupção lógica de dados | **requires DR** | Não é revertível por rollback de aplicação (não é um problema de código/deploy) — exige restore de um backup anterior à corrupção |
| C | Migration com falha | **handled by rollback** | `PRI-009` §3: nunca reverter a migration manualmente — restaurar o backup pré-deploy (que já é obrigatório antes de qualquer `alembic upgrade head`, `PRI-009` §2 passo 1) |
| D | Release defeituosa (aplicação, não schema) | **handled by rollback** | `PRI-009` §3: reverter para a imagem/tag anterior — não é um cenário de Disaster Recovery, é rollback de deployment padrão |
| E | Perda do host | **requires DR** | Exige provisionar/recuperar um novo ambiente (Seção 10, etapa "Provision/Recover Environment") — depende do Gate A de W7-1 para ter onde recuperar |
| F | Perda do container (não do host) | **handled by rollback** | `docker compose -f docker-compose.yml up -d <service>` recria o container a partir da mesma imagem — o volume nomeado `aipmo_postgres_data` sobrevive à recriação do container `database` (não é um cenário de perda de dado, apenas de processo) |
| G | Indisponibilidade de Anthropic | **external dependency** | Fora do controle da STRATECH — já tratado pelo `ProductionLLMProvider` com `ProviderUnavailableError` (fail explícito, não DR) |
| H | Indisponibilidade de Voyage | **external dependency** | Idem — já tratado por `EmbeddingProviderUnavailableError` |
| I | Corrupção/perda de embeddings | **handled by backup/restore** (primário) / reprocessing (secundário, condicional) | Restore cobre `chunks.embedding` como qualquer outra coluna (Seção 8); reconstrução via reindexação é um caminho secundário condicional (Seção 4), nunca o primário |
| J | Perda de documentos/chunks | **handled by backup/restore** | Mesma unidade de recuperação de qualquer outra tabela — nenhum mecanismo especial necessário além do restore geral |
| K | Configuração/secrets incorretos | **handled by rollback** (Configuration Contract) | `src/api/startup_config.py` já falha fechado no boot (staging/produção) — não é um cenário de perda de dado, é detectado antes de causar dano |
| L | Restore incompatível com release/schema | **requires DR** (com achado explícito) | Cenário real não coberto por mecanismo existente: um backup de uma revisão Alembic antiga restaurado sob uma release nova exige `alembic upgrade head` pós-restore (Seção 10, etapa "Apply/Validate Schema") — mecanismo existe, mas depende de identificação de release/schema no próprio backup (Gap #9, Seção 6, ainda não implementado) |

**Distinção explícita, per mandato do Founder:** cenários C/D/F/K são **rollback de aplicação/deployment** (já cobertos pelo W7-5), nunca confundidos com Disaster Recovery. Apenas A/B/E/L exigem o protocolo completo da Seção 10. G/H são dependências externas, fora do controle da STRATECH. I/J são cobertos pelo backup/restore geral, sem mecanismo especial.

---

## 13. Staging Relationship

**OPTION A — Staging do W7-1 também serve como ambiente de DR Drill.**
Trade-offs: reaproveita a única infraestrutura de validação já planejada (Gate A de W7-1), sem custo adicional de um terceiro ambiente. Risco de conflito de finalidade: um drill de DR (que envolve parar serviços, restaurar um banco, possivelmente destruir e recriar o volume) pode colidir no tempo com a validação de LLM/Embedding real do W7-1 (que precisa do staging disponível e íntegro). Mitigação: agendar o drill fora das janelas de validação de IA, ou executar o drill **antes** de popular o staging com o dataset de validação de IA do W7-1.

**OPTION B — Ambiente de DR Drill dedicado, separado do staging do W7-1.**
Trade-offs: elimina o conflito de finalidade, mas introduz um terceiro ambiente permanente — contra o princípio de não overengineering desta missão, e sem necessidade demonstrada (o volume de dados e a frequência de drills não justificam, no estágio atual, manter dois ambientes permanentes).

**RECOMMENDATION:** **OPTION A**, com a mitigação de agendamento acima. Justificativa técnica direta de AR-18 (Epic Ledger, §14, W7-3): o drill depende de "um ambiente com dados reais para restaurar (W7-5, não necessariamente o staging completo de W7-1 com LLM validado — dependência mais estreita do que a hipótese do Founder sugere)" — ou seja, o drill **não precisa** esperar o staging estar com Voyage/Anthropic validados; precisa apenas que o ambiente exista e tenha um dataset real (sintético) para restaurar. Isso relaxa a dependência temporal entre W7-1 e o drill de W7-3, mas não elimina o reuso do mesmo host físico.

**TRADE-OFFS resumidos:** Option A = zero custo adicional, risco de conflito de agenda gerenciável por disciplina operacional. Option B = zero conflito de agenda, custo permanente de infraestrutura duplicada sem necessidade demonstrada. Nenhuma das duas é decidida por este documento — apresentada para confirmação do Founder (Seção 19).

---

## 14. Operational Ownership

AR-18 §9 item 10 deixou isso como Founder Decision pendente. Papéis mínimos necessários (conceituais, sem atribuição de pessoa):

| Papel | Responsabilidade |
|---|---|
| **Disaster Declaration Authority** | Decide formalmente que um incidente é um Disaster (não um incidente operacional comum) e aciona o protocolo da Seção 10 |
| **Recovery Operator** | Executa tecnicamente o protocolo — restore, migration, subida de serviços |
| **Validation Authority** | Confirma que as checagens da Seção 9 e o smoke test passaram antes de aceitar a recuperação como concluída |
| **Business Acceptance** | Confirma, do ponto de vista de negócio, que o RPO real (dado perdido) é aceitável e que o serviço pode ser reaberto a usuários |

Para a V1, no estágio atual (equipe pequena, sem cliente corporativo real operando 24/7), esses 4 papéis podem ser exercidos pela mesma pessoa/pequeno grupo sem necessidade de uma estrutura de on-call formal — mas devem ser **nomeados explicitamente** antes do encerramento do W7-3, não deixados implícitos. A decisão organizacional final (quem exerce cada papel) permanece com o Founder.

---

## 15. Dependencies

| Dependência | Tipo | Estado |
|---|---|---|
| Decisões de RTO/RPO (Seção 7) | Founder Decision | Não depende de nenhum ambiente — pode ser decidida imediatamente |
| Backup/Restore Contract (Seções 8-9) | Design | Não depende de ambiente — pode ser especificado e até implementado como script contra o ambiente de teste local já existente |
| Ambiente com dado real para o drill | W7-1 (Gate A, Staging Host) | **PENDING** — bloqueia apenas o drill (Seção 11), não as decisões/contratos |
| Ownership operacional (Seção 14) | Founder Decision | Não depende de ambiente |
| TD-002 (política de delete) | Founder/Arquitetura | Acoplado a esta missão (Seção 16) — decisão não depende de ambiente |

**Confirmado, consistente com AR-18 Epic Ledger:** as decisões de W7-3 (RTO/RPO, contratos, ownership, TD-002) podem avançar **em paralelo** a W7-1 — apenas o DR Drill real depende de um ambiente existir.

---

## 16. Technical Debt Mapping

Reavaliados especificamente os itens relacionados a backup/restore/migrations/resilience/database/embeddings/deployment — nenhum item não relacionado foi tocado.

| Item | Categoria | Classificação |
|---|---|---|
| TD-001 (SQLite FK não aplicado) | Database | **RELATED BUT OUT OF SCOPE** — afeta apenas o ambiente de teste (SQLite); produção usa Postgres real, que já aplica FK por padrão. Não é uma questão de backup/restore/DR |
| TD-002 (política de delete RESTRICT/CASCADE indefinida) | Database, acoplado a DR/backup-restore | **ABSORBED BY W7-3** — confirmado por AR-18 como "MUST CLOSE IN WAVE 7", diretamente relacionado a integridade de dados que qualquer restore precisa preservar (Seção 9, checagem de FK órfã). Decisão de política (RESTRICT vs. CASCADE por relação) não foi tomada nesta missão — fica para a Seção 17 (implementação futura), mediante nova autorização do Founder |
| Gap de validação pós-restauração cobrindo só `analysis_records` (não um TD numerado, gap de dimensão AR-18 §7) | Backup/Restore | **ABSORBED BY W7-3** — endereçado tecnicamente pela Seção 9 (Restore Contract), implementação futura na Seção 17 |
| `KnowledgeRepository.index()` não deleta chunks antigos antes de reindexar (D-175/D-177) | Embeddings | **RELATED BUT OUT OF SCOPE** — só se torna operacionalmente relevante se reconstrução (caminho secundário, Seção 4) for usada como alternativa ao restore primário; o Backup/Restore Contract (Seções 8-9) não depende de corrigir isso, já que `chunks` é recuperado pelo mesmo `pg_restore` de qualquer outra tabela. Não expandido, não corrigido — permanece exatamente como já registrado |
| TD-011 (backend de embedding de produção não escolhido) | Embeddings | **RESOLVED BY EXISTING WORK** — Voyage AI/`voyage-4`/dimensão 1024 implementado e aprovado (D-177), fora do escopo desta missão revisitar |
| BFF brute-force mitigation pendente (`PRI-009` §1) | Deployment/Security | **RELATED BUT OUT OF SCOPE** — pertence a W7-4 (Security Hardening), não a Resilience/DR |
| Migration Discipline / Deployment Contract (W7-5) | Deployment | **UNCHANGED** — já resolvido por W7-5, W7-3 apenas consome (Seção 10), não redesenha |
| Localização/criptografia de armazenamento de backup indefinidas | Backup, acoplado a infraestrutura | **RELATED BUT OUT OF SCOPE** — depende diretamente do Gate A (Staging Host) de W7-1, decisão de procurement/infraestrutura fora do escopo arquitetural do W7-3 |

Nenhuma dívida não relacionada foi tocada, revisitada ou proposta para eliminação apenas por ter sido encontrada durante esta revisão.

---

## 17. Incremental Implementation Strategy

**Nenhuma etapa abaixo foi executada nesta missão.** Sequência validada e ajustada contra o código real (a hipótese do Founder é confirmada na ordem, com detalhamento adicional):

| Etapa | Objetivo | Verificável por |
|---|---|---|
| **Etapa 1 — Backup Contract** | Formalizar o Backup Contract da Seção 8: script único que executa `pg_dump -Fc`, carimba a revisão Alembic no nome do arquivo, verifica que o dump não é vazio, roda `pg_restore --list` como smoke check | Execução real contra o ambiente de teste local (Postgres já usado pela suíte de testes), sem staging |
| **Etapa 2 — Restore Validation** | Substituir os 3 checks do `PRI-008` §4 pela cobertura completa das 21 tabelas (Seção 9) — um script único de validação pós-restauração | Execução real de um ciclo backup→restore→validação contra o ambiente de teste local |
| **Etapa 3 — TD-002 (política de delete)** | Decidir e aplicar RESTRICT/CASCADE por relação, mediante Founder Decision explícita — migration nova, testada | Testes automatizados provando o comportamento decidido |
| **Etapa 4 — DR Procedure** | Formalizar o protocolo da Seção 10 como runbook executável (`PRI-008`/novo documento), com os critérios de sucesso/falha por etapa | Revisão documental + dry-run manual contra o ambiente de teste local |
| **Etapa 5 — DR Drill** | Executar o drill real (Seção 11) contra o staging do W7-1 (Option A, Seção 13), com dataset sintético | RTO/RPO medidos, evidências reais coletadas — depende do Gate A de W7-1 |
| **Etapa 6 — Executive Evidence** | Consolidar evidência de todas as etapas anteriores em um documento de Executive Evidence do W7-3, com GO/NO-GO para encerramento | Documento produzido, mapeando cada prova a uma etapa real executada |

Etapas 1-4 **não dependem de staging** — podem avançar contra o ambiente de teste local já existente, em paralelo a W7-1 (Seção 15). Apenas a Etapa 5 depende do Gate A de W7-1.

**Esta sequência não está aprovada para execução** — nenhuma etapa inicia sem nova autorização explícita do Founder.

---

## 18. Risks

| Risco | Registro |
|---|---|
| RTO/RPO permanecerem indefinidos por mais tempo, atrasando o encerramento de W7-3 | Já antecipado por AR-18 §16 — dependência de decisão, não de implementação |
| `PRI-008` desatualizado ser usado num drill/restore real sem revisão prévia | Já antecipado por AR-18 §16 — mitigado pela Seção 9 deste documento, mas só se a Etapa 2 (Seção 17) for de fato implementada antes de qualquer restore real |
| TD-002 não decidido antes de um restore real | Um restore que reintroduz dados após deletes parciais pode expor órfãos silenciosos se a política de delete permanecer indefinida — risco real, motivo da absorção em W7-3 (Seção 16) |
| Conflito de agenda entre o drill de DR e a validação de IA do W7-1 no mesmo staging (Option A, Seção 13) | Mitigável por disciplina operacional (agendamento), não por mecanismo técnico novo |
| Reconstrução de embeddings ser usada incorretamente como substituto do restore primário | Mitigado por este documento deixar explícito (Seção 4) que reconstrução é caminho secundário, condicional, com custo real — nunca o primário |
| Nenhuma automação de backup existir ainda | Gap #3 (Seção 6) — mitigável apenas por implementação futura (Etapa 1, Seção 17), não por este documento |

Nenhum risco novo além destes foi identificado.

---

## 19. Founder Decisions Required

1. **RTO** — escolher entre as alternativas da Seção 7 (recomendado: 8h) ou apresentar um valor diferente com justificativa de negócio.
2. **RPO** — escolher entre as alternativas da Seção 7 (recomendado: 24h) ou apresentar um valor diferente com justificativa de negócio.
3. **Política de delete (TD-002)** — RESTRICT ou CASCADE, por relação (não decidido nem proposto tecnicamente aqui — decisão de produto/arquitetura, per AR-18).
4. **Relação com staging (Seção 13)** — confirmar Option A (recomendada) ou Option B.
5. **Ownership operacional (Seção 14)** — confirmar o modelo de 4 papéis proposto e, quando aplicável, nomear responsáveis.
6. **Autorização da Etapa 1 (Seção 17)** — se e quando iniciar a implementação incremental, começando pelo Backup Contract (não depende de staging).

Nenhuma dessas decisões foi tomada por este documento.

---

## 20. GO/NO-GO Recommendation

**GO para a Seção 19 (Founder Decisions)** — toda a análise arquitetural necessária para decidir RTO/RPO, política de delete, relação com staging e ownership está completa e fundamentada no código real, sem necessidade de mais investigação técnica antes dessas decisões.

**GO técnico condicional para o início da Etapa 1 (Backup Contract, Seção 17)** — não depende de staging, não depende dos Gates Externos de W7-1, pode avançar em paralelo. **Condicionado a nova autorização explícita do Founder** — não inicia automaticamente por este documento.

**NO-GO para qualquer execução real de backup/restore/drill nesta missão** — nenhuma foi executada, nenhuma está autorizada aqui.

**NO-GO para o encerramento do W7-3** — RTO/RPO não decididos, TD-002 não resolvido, nenhum drill real ocorrido, nenhuma automação implementada. W7-3 permanece na fase de abertura institucional (Technical Design), não avança para implementação sem nova autorização.

Nenhum outro Epic da Wave 7 foi iniciado. W7-1 permanece OPEN, inalterado por esta missão. Retornando obrigatoriamente para Executive Review do Founder.
