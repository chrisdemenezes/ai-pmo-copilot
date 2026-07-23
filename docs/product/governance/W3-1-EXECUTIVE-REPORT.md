# W3-1 EXECUTIVE REPORT — Project Identity Unification (TD-008, Fase 3a)

**Wave 3, Epic W3-1**
**Data:** 2026-07-23
**Autor:** Claude / Tech Lead
**Base:** `DOMAIN-BLUEPRINT-PROJECT-IDENTITY-UNIFICATION.md`, `TECHNICAL-DESIGN-PROJECT-IDENTITY-UNIFICATION.md`, liberados pela Architecture Review AR-2.

---

## Escopo entregue

Fase 3a de TD-008: `ProjectSummaryService.summarize_portfolio()` passa a agrupar por `project_id` em vez de `project_name` bruto, corrigindo um bug real (duas análises com nomes que diferem apenas por espaço em branco resolviam ao mesmo `project_id` no banco, mas apareciam como duas entradas separadas no portfólio agregado). `ProjectSummaryResponse` (API) e `ProjectSummary` (frontend) ganham o campo aditivo `project_id`. Nenhuma rota, parâmetro de URL ou contrato existente foi alterado — `project_name` continua sendo a chave de entrada de toda a superfície de API/BFF/frontend, exatamente como documentado no Blueprint como escopo desta Fase (a Fase 3b, muito maior, permanece explicitamente não implementada).

## Arquivos alterados

- `src/services/project_summary_service.py`: `summarize()`/`summarize_portfolio()`/`_aggregate()` — agrupamento por `project_id`, campo `project_id` na saída.
- `src/api/routes/intelligence.py`: `ProjectSummaryResponse.project_id: int | None = None`.
- `web/lib/dashboard/types.ts`: `ProjectSummary.project_id?: number` (opcional).
- `tests/test_project_summary_service.py`: 2 asserções existentes atualizadas, 1 teste novo (bug de agrupamento por espaço em branco).
- `tests/test_project_summary_api.py`: 2 fixtures de teste atualizadas com `project_id`.
- `docs/architecture/TECHNICAL_DEBT.md`: TD-008 atualizado (Fase 3a concluída, Fase 3b escopada e documentada, premissa de `projects_delivery` corrigida).

## Migrações

Nenhuma. `project_id` já existia na coluna `analysis_records.project_id` desde o Épico 1 — este Epic apenas passou a lê-la/agrupá-la, sem nenhuma alteração de schema.

## Arquitetura impactada

Nenhuma. Mudança inteiramente aditiva na camada de serviço e no contrato de resposta; nenhum Bounded Context novo, nenhum Blueprint/Domain Model aprovado alterado.

## Testes executados e resultados

| Suíte | Resultado |
|---|---|
| `pytest` (backend, PostgreSQL) | 282 passed (281 pré-existentes + 1 novo) |
| `ruff check src tests` | Limpo |
| `tsc --noEmit` | Limpo |
| `eslint .` | Limpo |
| `vitest run` | 437 passed (sem alteração — campo opcional não exigiu nenhuma fixture nova) |
| Playwright E2E (`dashboard.spec.ts` + `portfolio.spec.ts`, `lg`) | 20 passed — spot-check justificado: mudança não toca nenhum comportamento de frontend nem o mock E2E (`mock-backend.mjs`, independente do backend Python), apenas um campo opcional aditivo |

## Riscos e pendências

Nenhum risco novo. Fase 3b (migração completa de `project_name` para `project_id` em toda a superfície Dashboard/Portfólio/Decision Center/Executive Focus/Workspace, aposentando `ProjectSummary`) permanece documentada como trabalho futuro de escopo muito maior — não teve gatilho definido, não é urgente (nenhum bug ativo pendente após esta Fase 3a).

## Confirmação de encerramento

**Epic W3-1 concluído** para o escopo aprovado (Fase 3a). TD-008 permanece "Em progresso" (não "Resolvido") — refletindo honestamente que a Fase 3b continua em aberto, sem prazo definido. Wave 3 segue para o próximo Epic do Ledger (W3-2, AI Platform Foundation), sem necessidade de nova autorização do Founder.
