# TD-008 Fase 3b — Gate pós-Etapa 4a (pré-Etapa 4b destrutiva)

**Data:** 2026-07-26 · **Item:** 8 do Wave Completion Review retrospectivo ·
**Decisões:** D-056 (Etapa 1) · D-057 (Etapa 2) · D-058 (Etapa 3) · D-059 (Etapa 5) ·
**D-060 (Gate Final aprovado + Etapa 4a)**

Este Gate é exigido pelo Founder após a conclusão da **Etapa 4a — Eliminação
Aditiva dos Consumidores Residuais de `project_name` como chave** (R1-R6), e
precede a **Etapa 4b** (a única etapa **irreversível**), que permanece
**bloqueada** até novo Gate + nova aprovação explícita. Reúne as dez
comprovações mandatadas.

---

## 1. Zero filtros por `analysis_records.project_name`

`list_analyses` é **id-only** — o parâmetro e o filtro por `project_name`
foram removidos; o único escopo de projeto é `project_id`. Callers que recebem
um nome (rota, testes) o resolvem para um id via `AnalysisRepository.resolve_scope_id`
(→ `EnterpriseRepository.resolve_project_reference`) **antes** de consultar.

```
$ grep -rnE "record\.project_name|AnalysisRecord\.project_name" src --include=*.py
  src/database/repository.py:53:  # ...never `record.project_name`.   (apenas COMENTÁRIO)
  -> 0 leituras/filtros comportamentais da coluna
```

Resíduos R1 (fallback em `list_analyses`) e o filtro por nome do `AIContextEngine`
(Risk Advisor) **eliminados** — ambos escopam por `project_id` via `resolve_scope_id`.

---

## 2. Zero agrupamentos ou deduplicações por nome

- `summarize_portfolio`: `by_project: dict[int, ...]` agrupado por
  `record.project_id`; o projeto-sentinela "(sem projeto)" é excluído **por
  identidade** (`analysis_display_name(record) is None`), não por comparação de
  string da coluna.
- `list_latest_risks`: `seen_projects: set[int | None]` — dedup por
  `record.project_id` (R2 eliminado).

---

## 3. Zero joins de frontend por nome

`decision-queue` e `portfolio-view` juntam exclusivamente por `project_id`:

```
$ grep -rnE "\.get\(.*project_name|Map<string" web/lib/decision-center/decision-queue.ts \
    web/lib/portfolio-intelligence/portfolio-view.ts
  -> NENHUM join por nome
```

- `ExecutiveDecision` ganhou `project_id`; `groupLatestRisksByProject` e
  `groupDecisionsByProject` são `Map<number, …>`; o set de risco em
  `portfolio-view` é `Set<number>` de `project_id` (R4/R5 eliminados).
- A navegação `/workspace/:projectName` (rota de UI por nome) é **sancionada**:
  o nome é entrada/exibição resolvida para `project_id` antes de qualquer
  operação de domínio.

---

## 4. Zero escrita na coluna

`save_analysis` **não materializa mais** `analysis_records.project_name`: o
`AnalysisRecord(...)` é construído sem esse campo (fica `NULL` para linhas
novas). A única referência a `project_name` no caminho de escrita é a **entrada
de resolução** `get_or_create_project_for_name(session, organization_id, project_name)`
(nome livre → Project → `project_id`), que é a resolução de identidade exigida
pelo end-state, não uma escrita da coluna.

---

## 5. Todas as responses relevantes contendo `project_id`

| Response (`src/api/routes/intelligence.py`) | `project_id` |
|---|---|
| `AnalysisSummary` (+ `AnalysisDetail`) | ✅ (construído a partir de `record.project_id`) |
| `ActionItemResponse` | ✅ |
| `LatestRiskItemResponse` | ✅ |
| `ProjectSummaryResponse` | ✅ (desde a Fase 3a) |

Espelhos de frontend correspondentes (`AnalysisListItem`, `ActionItemView`,
`LatestRiskItem`, `ProjectIntelligenceSummary`) também carregam `project_id`.
O `project_name` das responses é **exibição derivada de `Project.name`** via o
relacionamento `AnalysisRecord.project` (`analysis_display_name`), nunca da
coluna legada.

---

## 6. Busca global comprobatória

```
# Backend: leitura/filtro da coluna como chave      -> 0 (só 1 comentário)
# Backend: dedup/group por project_name             -> 0 (por project_id)
# Backend: escrita da coluna em save_analysis        -> 0 (só resolução nome->id)
# Frontend: joins por project_name (decision/portfolio) -> 0 (Map<number> por id)
# Backend produtor da projeção (mantido, classificado): ProjectSummaryResponse (3), ProjectSummaryService (9)
```

---

## 7. Suíte completa verde

| Suíte | Resultado |
|---|---|
| `ruff check src tests` | ✅ limpo |
| `pytest` (backend) | ✅ **449 passando** + `test_migration_0015_drop_project_name` |
| `tsc --noEmit` | ✅ limpo |
| `eslint` | ✅ limpo |
| `vitest` (frontend) | ✅ **491 passando** |
| Playwright E2E (lg/md/mobile) | ✅ **292 passando** (2 skipped), contra build de produção, servidor limpo |

**Novos testes de join por identidade:** mesmo `project_id` com nomes de
exibição diferentes → **juntam**; nomes de exibição iguais com `project_id`
diferentes → **não juntam** (`decision-queue.test.ts`, `portfolio-view.test.ts`).

---

## 8. Definição da migração 0015

`alembic/versions_pending/0015_drop_analysis_records_project_name.py` (staged):

- **upgrade:** `SET NOT NULL` em `analysis_records.project_id` → `DROP INDEX
  ix_analysis_records_project_name` → `DROP COLUMN project_name`.
- **downgrade:** `ADD COLUMN project_name` (nullable) → recria o índice → `DROP
  NOT NULL` em `project_id`.

**Encenada, NÃO ativada:** vive fora do `version_locations` ativo, então
`alembic heads` (app + suíte) permanece **`0014`** — a coluna é preservada,
exatamente como a Etapa 4a exige. Ativar a 0015 (movê-la para
`alembic/versions/`) é o ato da Etapa 4b.

```
$ python -m alembic heads
  0014 (head)      # 0015 encenada, não ativa
```

---

## 9. Teste real de upgrade e downgrade

`tests/test_migration_0015_drop_project_name.py` — contra **PostgreSQL real**
(banco descartável), a nível de conexão bruta (a coluna ainda mapeada no ORM
nunca conflita):

1. `upgrade 0014` → coluna presente, `project_id` nullable ✅
2. `upgrade 0015` → coluna **removida**, `project_id` **NOT NULL** ✅
3. `downgrade 0014` → coluna e `project_id` nullable **restaurados** ✅

Resultado: **1 passed**. Reversibilidade da única etapa irreversível provada
antes de qualquer aprovação da 4b.

---

## 10. Procedimento de backup validado

- **Runbook em vigor:** `RB-002 — Production Backup & Restore Runbook`.
- Antes de ativar a 0015 em produção (Etapa 4b): backup completo conforme
  RB-002 + verificação do downgrade da 0015 (já testado, §9) como plano de
  rollback imediato.

---

## Veredito e próximo passo

**Etapa 4a concluída, aditiva e reversível.** Os dez itens do Gate estão
comprovados. A coluna `analysis_records.project_name` **não tem mais nenhum
consumidor de comportamento** (leitura, filtro, agrupamento, join ou escrita),
mas **permanece na tabela** — nada foi removido.

A **Etapa 4b permanece bloqueada.** Nenhuma operação irreversível foi executada:
o `NOT NULL` definitivo, o `DROP COLUMN` e a remoção dos contratos temporários
(coluna `project_name` no ORM, campo `project_name` nas responses) só ocorrem
após **nova aprovação explícita do Founder** sobre este Gate.
