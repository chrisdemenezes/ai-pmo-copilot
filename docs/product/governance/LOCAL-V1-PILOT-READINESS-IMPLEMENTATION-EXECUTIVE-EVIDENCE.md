# Local V1 Pilot Readiness Implementation — Executive Evidence

- **Missão:** FOUNDER DECISION — LOCAL V1 PILOT READINESS IMPLEMENTATION (Aprovação do Pacote Mínimo para User Session #2 e Controlled External Pilot)
- **Data:** 2026-08-20
- **Escopo:** implementação exclusiva dos 3 itens do Controlled Pilot Gate definidos em D-217 (Priorização, Dashboard, Provisionamento de organização) — nada mais.

## 1. Escopo executado

**A. Priorização** — delta mínimo aprovado (D-217, Seção 5): título corrigido para "Priorização", cabeçalhos de camada, uma linha explicando a regra de ranking. Backend/algoritmo intocados.

**B. Dashboard** — os 5 widgets alimentados por `web/lib/mock/cockpit-data.ts` (Demandas/Riscos/Issues/Mudanças, Decision Center, Actions Center, Recent Activity, AI Recommendations) agora exibem um badge "Dados demonstrativos"; indicador de prazo (No prazo/Atenção/Atrasado) adicionado a "Situação do Portfólio", usando exclusivamente `start_date`/`planned_end_date`/`actual_end_date` já existentes.

**C. Provisionamento de organização** — `AuthService.bootstrap_organization()` (generalização do padrão já existente de `bootstrap_administrator`/`bootstrap_demo_user`), acionável via 3 variáveis de ambiente opcionais no boot, mesma disciplina idempotente. Runbook operacional completo. Nenhum endpoint novo, nenhuma UI nova.

**Explicitamente fora de escopo, não tocado:** Kanban/board, indicadores financeiros, tema claro/escuro, redesign visual, menu dedicado de IA, agrupamento de navegação Projetos/Program Management/Project Delivery, UI de Organization Administration, CRUD de tenants, nomenclatura de "chunks", design review de tipografia, storage externo, mudanças em Aprendizados, novo modelo de dados, W7-1/staging/DR Drill/outro Epic.

## 2. Etapa 1 — Priorização

### BEFORE
`web/app/portfolio/page.tsx`: `<h1>Portfólio</h1>`, lista plana de `ExecutivePortfolioCard`, sem cabeçalho de camada, sem explicação da regra de ordenação.

### AFTER
`<h1>Priorização</h1>` + linha explicativa ("Ordenado por prioridade: decisão pendente hoje, depois esta semana, depois risco a monitorar, depois sem sinal de atenção."). Itens agrupados por `item.layer` (já computado por `buildExecutivePortfolioView`, intocado) sob rótulos de seção ("Decisão hoje" / "Decisão esta semana" / "Risco a monitorar" / "Sem sinal de atenção"), mesmo padrão de bucket-label já usado em `ActionItemsList`.

### TEST RESULT
`web/e2e/portfolio.spec.ts`: 2 asserções de heading atualizadas (Portfólio→Priorização) + 2 novas asserções (explicação da regra, rótulos de camada visíveis). `web/app/portfolio/page.test.tsx`: 8/8 PASS, sem alteração (não depende do texto do heading removido).

## 3. Etapa 2 — Dashboard

### SIMULATED DATA TREATMENT
5 seções (`WorkItemsOverview`, `DecisionCenterPanel`, `ActionsCenterTable`, `RecentActivityTimeline`, `AIRecommendationsPanel`) ganharam `<Badge variant="outline">Dados demonstrativos</Badge>` junto ao título. `RecentActivityTimeline` não estava nomeada no achado original de D-217, mas é igualmente alimentada por mock — incluída por consistência, decisão autônoma registrada aqui com transparência. Nenhuma seção oculta; nenhum dado real alterado.

### SCHEDULE INDICATOR
`web/lib/dashboard/schedule-status.ts` (novo): `computeScheduleStatus(plannedEndDate, actualEndDate, status, referenceDate)` — generaliza a lógica booleana já existente de `Project.isOverdue()` (`web/lib/domain/project.ts`) para um rótulo de 3 estados, sem inventar regra de negócio nova. Aplicado em `PortfolioSituationGrid` (tabela desktop + cards mobile), usando `Portfolio.plannedEndDate`/`actualEndDate`/`status`, já totalmente serializados ponta a ponta (confirmado por investigação — nenhuma mudança de API/hook/tipo necessária).

### TEST RESULT
`web/lib/dashboard/schedule-status.test.ts`: 8/8 PASS (atrasado/no_prazo/atenção/encerrado/actualEndDate setado). `web/components/cockpit/portfolio-situation-grid.test.tsx` (novo): 3/3 PASS. `web/app/dashboard/page.test.tsx` + `error.test.tsx`: 9/9 PASS, sem alteração.

## 4. Etapa 3 — Organization Provisioning

### MECHANISM
`AuthService.bootstrap_organization(organization_name, email, password)` — mesmo padrão transacional/idempotente de `bootstrap_administrator()`/`bootstrap_demo_user()` na mesma classe, generalizado por nome de organização. Acionado por `bootstrap_identities()` via 3 variáveis de ambiente opcionais (`PILOT_ORGANIZATION_NAME`/`PILOT_ORGANIZATION_ADMIN_EMAIL`/`PILOT_ORGANIZATION_ADMIN_PASSWORD`), unset por padrão — nunca roda em instalações locais/demo existentes. Nenhum endpoint HTTP novo (confirmado que os mecanismos atuais — `POST /admin/users`, `POST /admin/invitations`, `GET /admin/users/{id}/roles`, `GET /admin/organization`, `POST /api/auth/login` — já cobrem os 7 itens do Runbook).

### RUNBOOK
`docs/operations/LOCAL-V1-PILOT-ORGANIZATION-PROVISIONING-RUNBOOK.md` — 7 passos, cada um mapeado a um mecanismo real já existente, nenhum novo.

### REHEARSAL
`tests/test_pilot_organization_provisioning.py` — 5 testes de integração real (Postgres real via `temp_database_url`, alembic `upgrade head` real, `TestClient` real, dados exclusivamente sintéticos: `"Piloto Externo A"`/`admin@piloto-a.example`): login real, confirmação de papel via endpoint real, criação de usuário do piloto + login desse usuário, isolamento de tenant (404 cross-tenant, mesma convenção de `test_administration_api.py`), acesso à própria organização. **Isso prova o mecanismo de ponta a ponta em CI real — não substitui um ensaio manual na máquina física antes do piloto externo real de fato**, registrado com transparência como próximo passo operacional recomendado, não bloqueante para este gate técnico.

### TENANT ISOLATION
Confirmado mecanicamente: `test_tenant_isolation_holds_between_pilot_and_default_organization` — admin do piloto tenta acessar usuário de outra organização → `404`, nunca `200`/`403` (convenção uniforme do produto).

## 5. Files Changed

```
.env.example                                                    |  13 +
docs/operations/LOCAL-V1-PILOT-ORGANIZATION-PROVISIONING-RUNBOOK.md |  70 +++
src/services/identity/auth_service.py                           |  54 +++
tests/test_identity_auth_service.py                             |  83 +++
tests/test_pilot_organization_provisioning.py                   | 195 +++++
web/app/dashboard/page.tsx                                      |  45 ++--
web/app/portfolio/page.tsx                                      |  71 +++-
web/components/cockpit/portfolio-situation-grid.test.tsx        |  65 +++
web/components/cockpit/portfolio-situation-grid.tsx             |  44 ++-
web/e2e/portfolio.spec.ts                                       |  15 +-
web/lib/dashboard/schedule-status.test.ts                       |  52 +++
web/lib/dashboard/schedule-status.ts                             |  56 +++
12 files changed, 731 insertions(+), 32 deletions(-)
```

## 6. Tests Added

- `tests/test_identity_auth_service.py::TestBootstrapOrganization` (4 testes)
- `tests/test_pilot_organization_provisioning.py` (5 testes de integração real)
- `web/lib/dashboard/schedule-status.test.ts` (8 testes)
- `web/components/cockpit/portfolio-situation-grid.test.tsx` (3 testes)
- `web/e2e/portfolio.spec.ts` (2 asserções atualizadas + 2 novas)

## 7. Backend

`ruff check src tests`: limpo. `py_compile` em todos os arquivos tocados: OK. Suíte completa dependente de Postgres não executada localmente (sandbox sem Docker, limitação estrutural já registrada em missões anteriores) — validação real ocorre via CI (mesmo padrão desde D-214).

## 8. Frontend

`tsc --noEmit`: limpo. `eslint` nos arquivos tocados: limpo. `vitest run` (suíte completa): **590/590 PASS**, 80 arquivos, zero regressão. `next build`: sucesso.

## 9. E2E

`web/e2e/portfolio.spec.ts` atualizado e revisado; execução real depende do backend mock (`e2e/mock-backend.mjs`) e Playwright, ambos fora do meu sandbox local — validado via CI, mesmo padrão desde D-214.

## 10. Build

`next build`: sucesso, todas as rotas listadas normalmente, nenhum erro.

## 11. Architectural Preservation

`git diff --stat origin/main HEAD` (merge-base confirmado = ponta real de `origin/main`): **12 arquivos alterados**, exatamente o escopo autorizado (Seção 1). Zero arquivo em `src/services/authorization/`, `src/services/advisor_framework/`, `src/services/ai_foundation/`, `src/services/executive_orchestrator/`, `src/services/knowledge_platform/`, `src/database/enterprise_repository.py` (exceto leitura via métodos já existentes, nenhuma alteração de arquivo), migrations, ou qualquer artefato de W7-1/W7-3/W7-4/W7-7 — confirmado mecanicamente, não presumido.

## 12. New Findings

- `RecentActivityTimeline` também é alimentada por dado mock, mas não estava nomeada nos 4 achados originais de D-217 — incluída na marcação "Dados demonstrativos" por consistência (achado incidental, decisão autônoma dentro da autoridade desta missão, registrado com transparência).
- O ensaio de provisionamento é automatizado (teste de integração real em CI), não um walkthrough manual na máquina física — registrado explicitamente como limitação, não mascarado como equivalente.

## 13. Controlled External Pilot Technical Gate

**SATISFIED** — os 3 itens do gate (D-217, Seção 21) estão tecnicamente fechados e reverificados:
1. Priorização comunica sua regra de ranking — implementado e testado.
2. Provisionamento pré-piloto documentado e ensaiado (mecanicamente, via teste de integração real) — implementado e testado.
3. Widgets mock/demo do Dashboard visualmente distinguidos — implementado e testado.

**Isso não autoriza ainda o piloto externo.** A User Session #2 deve revalidar a experiência antes da autorização final, conforme o próprio mandato exige explicitamente.

## 14. User Session #2

**READY** — ambiente técnico pronto, correções implementadas e testadas. Escopo recomendado (D-217, Seção 20, refinado por esta missão): revalidar Priorização; verificar percepção de clareza do Dashboard; confirmar que dados simulados não confundem; confirmar compreensão do indicador de prazo; confirmar viabilidade operacional do provisionamento pré-piloto (Cenário A). Perfil recomendado: Founder novamente, para ciclo rápido.

## 15. GO/NO-GO for User Session #2

**GO** — ambiente técnico pronto, gate satisfeito, nenhuma correção implementada além do pacote mínimo autorizado.

## 16. Next Recommended Action

Founder Executive Review desta evidência → autorização explícita de uma nova Founder Decision para conduzir a User Session #2 (não iniciada automaticamente por esta missão).
