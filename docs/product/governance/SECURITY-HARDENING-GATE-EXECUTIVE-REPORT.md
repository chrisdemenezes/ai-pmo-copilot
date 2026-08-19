# SECURITY HARDENING GATE — EXECUTIVE REPORT

**Wave 3 — Gate de segurança (C-1 + C-2)**
**Data:** 2026-07-23
**Autor:** Claude / Tech Lead
**Base:** `TECHNICAL-DESIGN-SECURITY-HARDENING-GATE.md`, `REPOSITORY-AUDIT-WAVE-3.md` (achados C-1/C-2 originais), autorização direta do Founder ("AUTORIZAÇÃO — MERGE DA PR #45 E SECURITY HARDENING GATE").

---

## Escopo entregue

Fecha os 2 achados críticos que o Repository Audit Wave 3 (Decision Log D-042) havia registrado como Decision Proposal, sem correção de código naquele momento, por instrução explícita do Founder de não decidir correções de impacto arquitetural silenciosamente:

- **C-1 — RBAC em `intelligence.py`:** as 8 rotas (`/api/projects/analyze`, `/api/risks/analyze`, `/api/meetings/analyze`, `/api/analyses`, `/api/analyses/{id}`, e as rotas por trás de `/api/action-items`, `/api/risks/latest`, `/api/projects/summary`) não aplicavam nenhum controle de acesso nem escopo organizacional, ao contrário de todo outro módulo de rota da plataforma.
- **C-2 — Tenant Isolation em `AnalysisRecord`:** a tabela não tinha `organization_id`, causando vazamento real de dados entre as duas organizações que já coexistem na base de produção.

O Technical Design consolidado (`TECHNICAL-DESIGN-SECURITY-HARDENING-GATE.md`) confirmou, antes de qualquer código ser escrito, que nenhuma das duas correções teria impacto arquitetural fora do escopo aprovado — por isso a implementação prosseguiu diretamente para código, testes e este Relatório, sem uma segunda rodada de autorização, conforme instruído.

## Arquivos alterados

**Novos:**
- `docs/architecture/TECHNICAL-DESIGN-SECURITY-HARDENING-GATE.md`
- `alembic/versions/0010_security_hardening.py`
- `src/api/dependencies.py` (extração de `build_repository`, quebra de import circular)
- `web/lib/bff/test-support.ts` (helper de teste compartilhado para as 9 rotas BFF que passaram a exigir sessão)

**Backend:**
- `src/api/routes/intelligence.py` — RBAC + escopo organizacional nas 8 rotas; auditoria nas 3 rotas de análise.
- `src/api/authorization.py`, `src/api/routes/portfolio.py`, `src/api/routes/administration.py` — import de `build_repository` redirecionado para `src/api/dependencies.py`.
- `src/database/repository.py` — `AnalysisRecord.organization_id`; `save_analysis`/`list_analyses`/`get_analysis` passam a exigir/filtrar por `organization_id`.
- `src/database/enterprise_repository.py` — `get_or_create_project_for_name` corrigido na causa raiz (usava sempre a "Default Organization" hardcoded).
- `src/services/project_summary_service.py` — `organization_id` roteado por toda a cadeia de agregação.

**Backend, testes:** `tests/test_action_items_api.py`, `tests/test_administration_api.py`, `tests/test_administration_repository.py`, `tests/test_alembic_migration.py`, `tests/test_api_security.py`, `tests/test_enterprise_repository.py`, `tests/test_intelligence_api.py` (reescrito na convenção Postgres+RBAC real), `tests/test_latest_risks_api.py`, `tests/test_project_summary_api.py`, `tests/test_project_summary_service.py`, `tests/test_rate_limit_api.py`, `tests/test_repository.py`.

**BFF (Next.js), 9 rotas + `domain-proxy.ts`:** `web/lib/bff/domain-proxy.ts` (exporta `readSessionIdentity`/`institutionalHeaders`), `web/app/api/bff/dashboard/route.ts`, `web/app/api/bff/action-items/route.ts`, `web/app/api/bff/risks/latest/route.ts`, e as 6 rotas de `web/app/api/bff/workspace/[projectName]/{summary,analyses,analyses/[analysisId],analyze/risk,analyze/meeting,analyze/status}/route.ts`, todas com seus `.test.ts` correspondentes.

**Governança:** `docs/product/stratech-v2/DECISION-LOG.md` (D-045), `CHANGELOG.md`, `web/lib/mock/mission-control-data.ts` (Mission Control).

## Migrações

`alembic/versions/0010_security_hardening.py` (`down_revision="0009"`):
- **Upgrade:** seed de `intelligence.read`/`intelligence.write` em `permissions` + `role_permissions` (mesmo padrão da migração `0006`); `analysis_records.organization_id` adicionada nullable → backfill via `UPDATE ... SET organization_id = (SELECT organization_id FROM projects WHERE projects.id = analysis_records.project_id)` → `RuntimeError` explícito se qualquer linha permanecer sem backfill → `NOT NULL` → FK `fk_analysis_records_organization_id` → índice `ix_analysis_records_organization_id`.
- **Downgrade:** reversão completa na ordem inversa.
- **Validado por round-trip manual completo** em banco Postgres descartável: upgrade limpo; downgrade para `0009` + inserção manual de uma linha no formato legado (sem `organization_id`, `project_id` apontando para um projeto real semeado) + re-upgrade confirmou o backfill correto (`organization_id` populado a partir do `project_id`); downgrade final confirmou remoção limpa de colunas/permissões.

## Arquitetura impactada

Nenhuma fora do escopo aprovado pelo Technical Design. Nenhuma arquitetura paralela, nenhum novo provider, nenhum novo registry — reaproveitamento total do padrão RBAC (`require_permission`/`get_request_context`) e do mecanismo de auditoria (`AdministrationRepository.record_audit`) já existentes na plataforma. A única refatoração incidental foi a extração de `build_repository` para `src/api/dependencies.py`, motivada exclusivamente por uma dependência circular que surgiria assim que `intelligence.py` passasse a importar `require_permission` de `authorization.py` (que já importava de `intelligence.py`) — mecânica, de baixo risco, sem mudança de comportamento.

Um achado adicional, descoberto por inspeção durante a implementação (não relatado pela auditoria original): a camada BFF nunca encaminhava os headers institucionais para nenhuma rota apoiada em `intelligence.py`, porque essas rotas de backend também nunca os exigiam antes. Corrigido nas 9 rotas BFF afetadas como consequência necessária deste mesmo Gate — sem essa correção, C-1 quebraria silenciosamente todo o Dashboard/Workspace/Decision Center em produção.

## Testes executados e resultados

| Suíte | Resultado |
|---|---|
| `pytest` (backend, PostgreSQL real) | **305 passed** (282 pré-existentes + 23 novos/reescritos) |
| `ruff check src tests` | Limpo |
| Migração `0010` (upgrade → downgrade → re-upgrade) | Validada manualmente em banco descartável, incluindo linha em formato legado |
| `tsc --noEmit` (frontend) | Limpo |
| `eslint .` (frontend) | Limpo |
| `vitest run` (frontend) | **452 passed** (437 pré-existentes + 15 novos, incluindo os casos de 401 sem sessão) |
| Playwright E2E (3 projetos: `lg`/`md`/`mobile`) | Executado 2 vezes completas; 6 falhas observadas em ambas — todas isoladas individualmente e comparadas via `git stash` contra a baseline anterior a este Gate: **todas as 6 reproduzem de forma idêntica na baseline**, confirmando que nenhuma é uma regressão introduzida por este Gate (flakiness pré-existente de ambiente: `executive-memory.spec.ts` "Mudou", `workspace.spec.ts` TIP-006/TIP-007, `users-admin.spec.ts` atribuição de papel, timeouts de navegação em `mobile`) |

## Critérios de aceite do Founder — confirmação item a item

| Critério | Status |
|---|---|
| Nenhuma rota de `intelligence.py` acessível sem autorização | ✅ `TestRbacEnforcement` — 403 parametrizado nas 8 rotas sem permissão |
| Nenhum `AnalysisRecord` acessível entre organizações | ✅ `test_meeting_analyzed_by_org_a_is_invisible_to_org_b` (`TestOrganizationScoping`) — prova ponta-a-ponta |
| PostgreSQL como banco de dados oficial | ✅ Toda a suíte de integração roda sobre Postgres real (`tests/db.py::temp_database_url`) |
| Migração validada (upgrade/downgrade/re-upgrade) | ✅ Round-trip manual completo, incluindo backfill de linha legada |
| Regressão completa aprovada | ✅ 305 backend + 452 frontend + E2E (6 falhas, todas pré-existentes confirmadas) |
| Testes específicos de isolamento multi-tenant | ✅ `TestOrganizationScoping` (3 testes) + 2 testes equivalentes em `test_repository.py`/`test_project_summary_service.py` |
| Trilha de auditoria atualizada | ✅ `TestAuditTrail` — 3 ações (`analysis.meeting_created`/`analysis.risk_created`/`analysis.status_created`) com `actor_user_id`/`organization_id`/`entity_id` corretos |
| Nenhuma exposição de dado histórico durante o backfill | ✅ Coluna permanece nullable até o backfill ser confirmado 100% completo (`RuntimeError` interrompe a migração se qualquer linha ficar sem `organization_id`); `NOT NULL` só é aplicado depois |

## Riscos e pendências

Nenhum risco novo identificado. As 6 falhas E2E observadas são flakiness de ambiente pré-existente (confirmada por comparação A/B contra a baseline, não introduzida por este Gate) e permanecem fora do escopo desta missão — candidatas a um item de Technical Debt separado, se o Founder desejar investigá-las formalmente. Nenhuma pendência de arquitetura, Blueprint ou ADR aberta por este Gate.

## Confirmação de encerramento

**C-1 e C-2 fechados.** Todos os critérios de aceite do Founder confirmados item a item. Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado. Per a sequência explicitamente autorizada, a Wave 3 retoma o **Epic W3-3 (Risk Advisor PoC)** com o Blueprint já aprovado (`DOMAIN-BLUEPRINT-RISK-ADVISOR.md`) — a dependência que bloqueava sua Implementação (Decision Log D-043) está resolvida.
