# TD-008 Fase 3b — Gate Final de Migração

**Data:** 2026-07-26 · **Item:** 8 do Wave Completion Review retrospectivo ·
**Decisões:** D-056 (Etapa 1) · D-057 (Etapa 2) · D-058 (Etapa 3) · D-059 (Etapa 5)

Este Gate precede a **Etapa 4** (a única etapa **irreversível**: `NOT NULL` em
`analysis_records.project_id`, `DROP COLUMN analysis_records.project_name`,
remoção definitiva de `project_name` como chave). Por decisão do Founder, a
Etapa 5 foi executada antes da Etapa 4 e este Gate reúne as comprovações
exigidas. **Veredito adiantado: NÃO-GO para a Etapa 4 no estado atual** — há
pré-requisitos residuais catalogados abaixo. É esse exatamente o valor do
Gate: reduzir o risco da etapa irreversível expondo o que falta.

---

## 1. Consumidores comportamentais que ainda usam `project_name` como chave

Regra do end-state ratificado: `project_id` é a **única chave de acesso**;
`project_name` só pode persistir como **atributo de exibição/entrada** (a UX
por nome resolve para um `project_id` antes de qualquer operação de domínio).

**Chave primária de acesso:** migrada para `project_id` em toda a superfície de
Intelligence (rotas `/analyses`, `/action-items`, `/risks/latest`,
`/projects/summary`; BFF; hooks; consumidores do Workspace e do Dashboard —
Etapas 1-3 e 5).

**Residuais que ainda dependem de `project_name` como chave (bloqueiam o DROP):**

| # | Local | Uso | Por quê |
|---|---|---|---|
| R1 | `src/database/repository.py:102` (`list_analyses`) | filtro `AnalysisRecord.project_name == project_name` | fallback aditivo (Etapa 1) para nome nunca-analisado; **lê a coluna como chave** |
| R2 | `src/services/project_summary_service.py` (`summarize_portfolio`, l.131/140) | dedup/agrupamento por `record.project_name` (`seen_projects`) | ainda usa o nome como chave de agrupamento no portfólio |
| R3 | `src/api/routes/intelligence.py` — `AnalysisSummary`, `ActionItemResponse`, `LatestRiskItemResponse` | expõem `project_name`, **não** expõem `project_id` | o frontend não tem id para juntar; o `project_name` de exibição vem de `analysis_records.project_name` (a coluna a ser removida) |
| R4 | `web/lib/decision-center/decision-queue.ts:140/159/163` | `Map` de riscos **chaveado por `project_name`** + join summary↔riscos por nome | consequência direta de R3 (LatestRiskItem sem `project_id`) |
| R5 | `web/lib/portfolio-intelligence/portfolio-view.ts:59/63/88` | `Map` de decisões por `project_name` + join por nome | os `ExecutiveDecision` não carregam `project_id` |
| R6 | `src/database/repository.py` (`save_analysis`) + `get_or_create_project_for_name` | grava/lê `analysis_records.project_name` | caminho de escrita ainda materializa o nome na coluna |

**Não são residuais (sancionados):** a rota de UI `/workspace/:projectName` e a
coexistência dual-key no BFF (nome **e** id enviados) — o nome é entrada/exibição
resolvida para `project_id` antes da operação de domínio (Etapas 1-3). O
`entry.project_name === null` em `organizational-learnings.ts` é um *skip* de
nulos, não uma chave.

**Conclusão da §1:** `project_id` já é a chave primária, mas **`project_name`
ainda é usado como chave de agrupamento/join/fallback em R1-R6**. Portanto a
coluna `analysis_records.project_name` **ainda tem consumidores de
comportamento**.

---

## 2. `ProjectSummary` não possui mais consumidores

- **Frontend:** `grep` confirma **zero** consumidores de tipo de `ProjectSummary`
  ou `WorkspaceSummary` — ambos removidos e consolidados em
  `ProjectIntelligenceSummary` (`web/lib/project/intelligence-summary.ts`),
  ancorado em `project_id`. Restam apenas menções históricas em comentários e no
  Decision Log/Mission Control.
- **Backend:** `ProjectSummaryResponse` (3 ocorrências) e `ProjectSummaryService`
  (9) **permanecem** — são o *produtor* legítimo da projeção (agrupam por
  `project_id` desde a Fase 3a), não um conceito paralelo. Renomeá-los mexeria no
  contrato OpenAPI sem ganho arquitetural. **Decisão pendente do Founder:** manter
  esses nomes no backend (recomendado) ou renomeá-los também.

**Conclusão da §2:** ✅ `ProjectSummary` eliminado como conceito de frontend.

---

## 3. Resultado da busca global no repositório

```
# Consumidores de tipo ProjectSummary/WorkspaceSummary no frontend:
$ grep -rn "\bProjectSummary\b|\bWorkspaceSummary\b" web/lib web/components web/app \
    --include=*.ts --include=*.tsx | grep -vE "ProjectSummaryResponse|ProjectSummaryService"
  -> apenas comentários e texto histórico do Mission Control/Decision Log (0 usos de tipo)

# project_name como chave (grouping/join/filter):
  -> R1-R6 acima (2 backend, 3 frontend read-models, 1 write-path)

# Backend ProjectSummary* (produtor, mantido):
  -> ProjectSummaryResponse (3), ProjectSummaryService (9)
```

---

## 4. Resultado completo da suíte de testes

| Suíte | Resultado | Observação |
|---|---|---|
| `ruff check src tests` | **limpo** | backend inalterado desde a Etapa 1 |
| `pytest` (backend) | **449 passando** | backend não muda desde `31ac445` (Etapa 1); `git diff --name-only 31ac445 HEAD -- src tests *.py` = vazio |
| `tsc --noEmit` | **limpo** | — |
| `eslint` | **limpo** | — |
| `vitest` (frontend) | **486 passando** | inclui os fixtures atualizados com `project_id` |
| Playwright E2E (lg/md/mobile) | **292 passando** | contra build de produção, servidor limpo |

*(O ambiente do container é propenso a OOM sob carga acumulada; a suíte E2E foi
validada isolada — `workspace.spec.ts` 19/19 — e completa em servidor limpo,
com `--retries=2` para absorver flakiness de infraestrutura, não de código.)*

---

## 5. Backup e downgrade testados

- **Runbook de backup/restore de produção:** `RB-002 Production Backup & Restore
  Runbook` existe e está em vigor.
- **Downgrade das migrações atuais:** a migração `0014` (Etapa 1, backfill
  defensivo) tem downgrade testado (`tests/test_migration_0014_backfill.py` —
  `downgrade 0013 → upgrade head`, no-op reversível).
- **Migração destrutiva da Etapa 4:** **ainda não existe** (será a `0015`).
  Backup completo + downgrade dessa migração serão **escritos e testados como o
  primeiro sub-passo da Etapa 4**, antes de qualquer execução, conforme o gate
  destrutivo — não é possível "confirmar testado" uma migração ainda não
  escrita.

---

## Veredito e pré-requisitos para liberar a Etapa 4

**NÃO-GO no estado atual.** A coluna `analysis_records.project_name` ainda tem
consumidores de comportamento (R1-R6). Um `DROP COLUMN` hoje quebraria o
fallback de nome, os campos de exibição das respostas e os joins de frontend.

**Pré-requisitos (uma Etapa 4 aditiva-primeiro, destrutiva-por-último):**
1. Adicionar `project_id` a `LatestRiskItemResponse`, `ActionItemResponse` e
   `AnalysisSummary` (resolve R3) — aditivo.
2. Migrar os joins de frontend `decision-queue` e `portfolio-view` para
   `project_id` (resolve R4/R5).
3. Re-derivar o `project_name` de exibição das respostas a partir de
   `projects.name` (join por `project_id`) em vez de `analysis_records.project_name`
   (resolve R3 no backend).
4. Substituir/aposentar o fallback por nome em `list_analyses` e a dedup por nome
   em `summarize_portfolio` (resolve R1/R2).
5. Ajustar `save_analysis` para não depender da coluna (resolve R6).
6. Só então: `NOT NULL` em `project_id`, migração `0015` com backup+downgrade
   testados, e `DROP COLUMN analysis_records.project_name`.

Cada sub-passo aditivo (1-5) mantém a suíte verde; o passo 6 (destrutivo) exige
**nova aprovação explícita do Founder** conforme o gate destrutivo.
