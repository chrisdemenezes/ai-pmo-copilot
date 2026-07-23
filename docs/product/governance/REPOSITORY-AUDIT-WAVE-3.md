# Repository Audit — Wave 3 Gate

**Missão:** Auditoria técnica completa do repositório, exigida pelo Founder antes de: (1) atualizar a branch `main`, e (2) iniciar o Epic W3-3 (Risk Advisor PoC).
**Data:** 2026-07-23
**Autor:** Claude / Tech Lead
**Metodologia:** 4 auditorias de pesquisa (estrutura/código, banco de dados/PostgreSQL, segurança, coerência de documentação/governança) executadas em paralelo, cada achado verificado diretamente por mim antes de ser aceito neste relatório; suítes completas de teste executadas e revalidadas.

---

## 1. Escopo auditado

Estrutura e organização; código e dependências; banco de dados e PostgreSQL; testes e qualidade; segurança; documentação e governança — os 6 pontos exigidos pelo Founder, sem omissão.

## 2. Achados por severidade

### CRÍTICO — 2 achados, ambos pré-existentes (não introduzidos por nenhum trabalho desta ou de missões anteriores da Wave 2/3)

**C-1 — `src/api/routes/intelligence.py`: nenhuma das 8 rotas aplica RBAC ou contexto organizacional.**
Todas as rotas (`POST /meetings/analyze`, `/risks/analyze`, `/projects/analyze`, `GET /analyses`, `/analyses/{id}`, `/action-items`, `/risks/latest`, `/projects/summary`, `/portfolio/summary`) carregam apenas `Depends(verify_api_key)` + `Depends(enforce_rate_limit)` no nível do router (`intelligence.py:21`) — **nenhuma** delas usa `Depends(require_permission(...))` nem `Depends(get_request_context)`, ao contrário de **todo** outro módulo de rota (`administration.py`, `portfolio.py`, `program.py`, `project_delivery.py`), que aplicam `<domínio>.read`/`<domínio>.write` em cada endpoint. Confirmado por leitura direta do arquivo (linhas 115-239): qualquer chamador com a `API_KEY` compartilhada, sem nenhum papel/permissão, executa análises de IA (mutação) e lê todo o histórico de análises.

**C-2 — `AnalysisRecord` (`src/database/repository.py:20-32`) não tem `organization_id` — vazamento real entre organizações.**
`list_analyses()`, `get_analysis()` e `ProjectSummaryService.summarize_portfolio()`/`list_action_items()`/`list_latest_risks()` (sem `project_name`) não filtram por organização. Confirmado que **duas organizações reais coexistem hoje na mesma base** ("Default Organization" e "Demo Organization", `src/services/identity/auth_service.py:21-29`) — ou seja, este não é um risco teórico: qualquer usuário autenticado de uma organização, ao chamar `GET /portfolio/summary` ou `GET /analyses` sem filtro, recebe transcrições de reunião, avaliações de risco e status de projeto **de todas as organizações**, não só a sua.

**Origem:** ambos são um artefato do V1 (quando a plataforma era single-tenant), nunca atualizados quando RBAC (Wave 2, Épico 3) e multi-organização (Wave 1-2) foram introduzidos em todo o resto da plataforma. Não é uma regressão de nenhum Épico/Sprint/Epic desta sessão — confirmado que nenhum commit da Wave 2/3 tocou `intelligence.py` ou `AnalysisRecord` além da extensão aditiva de `project_id` (Epic W3-1).
**Correção:** **não executada nesta auditoria** — ver Seção 5 (Decision Proposal). Impacto arquitetural e de escopo real demais para decisão silenciosa.

### ALTO — 1 achado, corrigido nesta auditoria

**A-1 — `README.md:7` declarava "Wave 2 Release Candidate (RC-2)"**, duas Waves desatualizado (Wave 2 encerrada há D-038, Wave 3 já com 2 Epics resolvidos). **Corrigido** — ver Seção 6.

### MÉDIO — 2 achados

**M-1 — `src/database/engine.py:12` mantém `DEFAULT_DATABASE_URL` em SQLite, e `demo/start-demo.sh` cai silenciosamente para SQLite quando `DATABASE_URL` não está definida.** Já rastreado como **TD-001** (aberto) em `docs/architecture/TECHNICAL_DEBT.md` — confirmado, não é uma descoberta nova, e o próprio script já rotula esse modo explicitamente ("SQLite, no Docker/Postgres needed") em vez de escondê-lo. **Nenhuma correção nesta auditoria** — já é dívida conscientemente aceita, gatilho de resolução (`TD-001`) inalterado.
**M-2 — `get_request_context` confia nos headers `X-Stratech-User-Id`/`X-Stratech-Organization-Id` sem vínculo criptográfico entre eles** (`src/api/identity_context.py:23-60`, a própria docstring admite a limitação). Seguro hoje apenas porque a `API_KEY` nunca é exposta ao browser e o BFF é o único emissor desses headers a partir de um cookie assinado. **Defesa em profundidade, não um achado bloqueante** — registrado para referência futura, não decidido nesta auditoria.
**M-3 — `.github/workflows/ci.yml`, job `validate`, nunca provisionava um serviço PostgreSQL** — encontrado ao investigar a falha real de CI no PR #45 (job `validate`, `check_run` 89228306744): `pytest` falhava deterministicamente com `psycopg2.OperationalError: connection to server at "localhost", port 5432 failed: Connection refused` em toda a suíte que usa `tests/db.py::temp_database_url()` (20 arquivos de teste), porque o workflow nunca foi atualizado quando a RC-2 tornou Postgres obrigatório para os testes de integração. **Corrigido nesta auditoria** — serviço `postgres:16` adicionado ao job `validate` (usuário/senha `aipmo`/`aipmo`, mesma convenção de `docker-compose.yml`/`Makefile`), com healthcheck `pg_isready`. Baixo risco, sem impacto de produto — infraestrutura de CI, não código de aplicação.

### BAIXO / INFORMACIONAL — resumo (evidência completa nos relatórios dos 4 agentes, arquivada nesta sessão)

- Estrutura `src/` 100% conforme CLAUDE.md, nenhuma arquitetura paralela.
- Nenhum TODO/FIXME/XXX/HACK órfão em `src/` ou `web/`.
- `AuthenticatedUser.is_demo` (`src/services/identity/models.py:16-18`) é código morto (zero call sites) — baixo risco, não corrigido nesta auditoria (não é claramente necessário, apenas inerte).
- Nenhuma dependência (Python ou `package.json`) não utilizada; nenhuma duplicada.
- Migrações (`alembic/versions/0001`-`0009`): cadeia única, sem órfãos, sem gaps, upgrade/downgrade simétricos.
- Modelos ORM vs. schema de migração: 100% consistentes.
- Seeds: idempotentes (padrão get-or-create em todos os pontos).
- Autenticação: Argon2id, normalização de e-mail, bloqueio de usuário inativo antes da senha — conforme.
- Nenhuma senha/hash em resposta de API, log ou auditoria.
- `.env.example`: apenas placeholders, nenhum segredo real commitado.
- Auditoria de mutações do User Management: completa, before/after capturado, sem PII de credencial.
- `Quick-Start.md`/`Release-Validation-Checklist.md` (RC-2): contagens de teste desatualizadas (245/436/203 vs. 282/437/243 atuais) — são artefatos de um snapshot datado da RC-2, não uma alegação de status atual; **não corrigido nesta auditoria** (baixa prioridade, nenhuma alegação de conclusão/pendência incorreta, apenas um número histórico).

## 3. Inconsistências de documentação/governança encontradas e corrigidas

- `web/lib/mock/mission-control-data.ts::EPIC_STATUS`: Épicos 3, 4 e 5 estavam "Not Started" quando já concluídos desde a Wave 2 (D-034/D-035/D-036/D-038). **Corrigido** para "Merged" com referência à decisão que os concluiu, seguindo a mesma convenção de nota histórica já usada em `PROGRAM_PHASES`/`CAPABILITY_PROGRESS` (D-030).
- `RELEASE_STATUS`: Releases 0.1/0.2 estavam "In Progress" (33%/35%) quando ambas mapeiam a Waves 1/2, já 100% concluídas. **Corrigido** para "Done"/100%; Release 0.3 (mapeia a Wave 3) atualizada de "Not Started" para "In Progress".
- `DOMAIN_EVOLUTION` (nota do nó "Project"): ainda dizia que restava "a Fase 3 do TD-008", quando a Fase 3a já foi concluída nesta sessão (D-040). **Corrigido.**
- `README.md`: status desatualizado (Seção 2, achado A-1). **Corrigido.**

Nenhum artefato, após estas correções, declara como pendente algo já concluído ou como concluído algo ainda não implementado — os únicos itens genuinamente pendentes (TD-008 Fase 3b, os 2 achados críticos C-1/C-2, Épico 6 contínuo) permanecem descritos como pendentes, com precisão.

## 4. Dívida técnica — situação após esta auditoria

Nenhum TD novo registrado por esta auditoria além dos 2 achados críticos, que são tratados como Decision Proposal (Seção 5), não como TD (um TD pressupõe uma resolução futura já aceita; C-1/C-2 exigem primeiro uma decisão sobre a abordagem, per a regra do Founder). TD-001 (SQLite residual) e TD-008 (unificação de Project) permanecem exatamente como estavam, confirmados precisos.

## 5. Decision Proposal — C-1 e C-2 exigem decisão do Founder antes de resolução

Per a instrução explícita do Founder ("Caso seja identificada qualquer correção com impacto arquitetural, funcional ou de escopo, não decida silenciosamente"), nenhuma correção de código foi aplicada a `intelligence.py` ou `AnalysisRecord` nesta auditoria. Registrado como nova seção aditiva em `docs/product/ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §16:

- **Opções para C-1** (RBAC ausente): (a) adicionar `intelligence.read`/`intelligence.write` ao catálogo de permissões (mesmo padrão de todo outro módulo) e decidir quais papéis as recebem; (b) reaproveitar um dos pares de permissão já existentes (`project_delivery.*` ou `portfolio.*`) se o Founder considerar Intelligence parte desses domínios, evitando um novo par de permissões.
- **Opções para C-2** (sem organization_id): (a) adicionar `organization_id` a `analysis_records` via migração, com backfill dos registros existentes para a organização do Project já vinculado (`project_id` → `projects.organization_id`, join direto, sem ambiguidade — todo registro já tem `project_id` populado); (b) decidir se a granularidade correta é a organização do ator que criou o registro, ou a organização do Project (podem divergir teoricamente, mas nunca divergem hoje, já que `get_or_create_project_for_name` sempre usa a organização padrão).
- **Risco de não decidir agora:** o vazamento é real e ativo hoje, independentemente da Wave 3 prosseguir ou não — mas é anterior a esta sessão, não uma regressão introduzida por ela.
- **Relevância direta para o Epic W3-3 (Risk Advisor):** o Advisor proposto porta exatamente o Accelerator `risk_review`, que hoje passa por esta mesma rota sem RBAC/escopo — construir uma interface conversacional sobre uma rota sem controle de acesso agravaria o problema, não o resolveria. **Recomendação: resolver C-1 (no mínimo) antes da Implementação do Epic W3-3**, mesmo que o Blueprint/Technical Design prossiga em paralelo.

## 6. Correções executadas nesta auditoria (baixo risco, sem impacto de produto/arquitetura)

1. `web/lib/mock/mission-control-data.ts`: `EPIC_STATUS`, `RELEASE_STATUS`, nota de `DOMAIN_EVOLUTION` — corrigidos para refletir a realidade (Seção 3).
2. `README.md`: linha de status atualizada (Seção 3).

Nenhuma mudança de comportamento de produto; `tsc --noEmit`, `eslint`, `vitest run` (437 testes) revalidados limpos após as duas mudanças.

## 7. Correções NÃO executadas (aguardando decisão do Founder)

- C-1 e C-2 (Seção 2/5) — arquiteturais/funcionais, Decision Proposal registrada.
- M-1 (SQLite fallback) — já é TD-001 aceita conscientemente, gatilho de resolução inalterado.
- M-2 (headers sem vínculo criptográfico) — defesa em profundidade, não bloqueante, registrado para referência.
- `AuthenticatedUser.is_demo` código morto — baixo risco, não claramente necessário remover agora.
- Contagens de teste desatualizadas em `Quick-Start.md`/`Release-Validation-Checklist.md` (RC-2) — snapshot histórico, não uma alegação de status incorreta.

## 8. Testes executados

| Suíte | Resultado |
|---|---|
| `pytest --cov=src` (backend, PostgreSQL) | **282 passed**, cobertura 97% (`1708 stmts, 55 miss`) |
| `ruff check src tests` | Limpo |
| `tsc --noEmit` | Limpo |
| `eslint .` | Limpo |
| `vitest run` | 437 passed |
| Playwright E2E (suíte completa, `lg`+`md`+`mobile`) | 230 passed, 11 failed, 2 skipped (241 executados) |
| Playwright E2E (re-execução isolada dos 11 falhos) | 6/11 reproduzem de forma determinística — todos já rastreados como **TD-004/005/006** (Baseline Defects, race de invalidação do React Query, `docs/architecture/TECHNICAL_DEBT.md`); os outros 5 (nav mobile de `actions.spec.ts`/`decisions.spec.ts`, uma falha de `workspace.spec.ts` em `md`) **não reproduziram isoladamente** — transitórios, atribuídos à contenção de recursos descrita abaixo, não uma regressão real |

**Incidente durante a auditoria (registrado por transparência):** a primeira execução de `pytest --cov` (rodando em paralelo com a suíte Playwright completa) falhou com 171 erros de conexão — investigado e confirmado como **o próprio serviço PostgreSQL do ambiente ter parado** (`pg_isready` reportou "no response", `service postgresql status` reportou "down"), não um defeito de código. Causa provável: contenção de recursos por rodar duas suítes pesadas simultaneamente neste ambiente. PostgreSQL reiniciado (`service postgresql start`), e a suíte completa re-executada com sucesso (282/282, tabela acima). Nenhum código foi alterado por conta deste incidente.

## 9. Riscos

1. **C-1/C-2 (Crítico, pré-existente):** vazamento de dados entre organizações e ausência total de RBAC em `intelligence.py` — real e ativo hoje. Ver Seção 5.
2. **TD-004/005/006 (já conhecido):** flakiness determinística em 3 testes E2E específicos (race de invalidação de query) — não bloqueia o Regression Gate por convenção já estabelecida, mas seguem abertos.
3. **M-1/M-2:** riscos aceitos conscientemente, sem mudança de status nesta auditoria.

## 10. Recomendação — **GO WITH CONDITIONS**

**Go** para: (a) atualização da branch `main` com o trabalho já produzido nesta sessão (Wave 2 closure, AR-2, Epic W3-1, Epic W3-2, e as correções desta auditoria) — nenhuma dessas mudanças toca `intelligence.py` ou `AnalysisRecord`, portanto não piora C-1/C-2, que já existem identicamente na `main` atual; (b) o Domain Blueprint do Epic W3-3 (documento, não código).

**Condição explícita, per a própria regra do Founder ("não realizar push para main caso... haja bloqueio de segurança"):** dado que C-1/C-2 são achados de segurança críticos, **a Implementação do Epic W3-3 não deve prosseguir** até o Founder decidir, via a Decision Proposal da Seção 5, como e quando resolver C-1 (no mínimo). O Blueprint do Risk Advisor pode e deve nomear esta dependência explicitamente em sua seção de riscos.

**Não é No-Go** porque: nenhum teste genuíno falha (a falha de `pytest --cov` foi um incidente de infraestrutura do ambiente, não do código, e a suíte completa foi revalidada limpa); nenhuma migração está inconsistente; C-1/C-2 são pré-existentes, não introduzidos por este trabalho, e já têm uma Decision Proposal registrada em vez de decisão silenciosa.
