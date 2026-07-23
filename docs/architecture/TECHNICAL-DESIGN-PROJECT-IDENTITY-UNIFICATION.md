# Technical Design — Epic W3-1: Project Identity Unification (Fase 3a)

**Base:** `DOMAIN-BLUEPRINT-PROJECT-IDENTITY-UNIFICATION.md`.
**Escopo:** exatamente a Fase 3a descrita no Blueprint — aditivo, sem quebrar nenhum contrato existente. Fase 3b permanece fora deste Technical Design.

## 1. `ProjectSummaryService` (`src/services/project_summary_service.py`)

- `summarize_portfolio()`: passa a agrupar por `record.project_id` em vez de `record.project_name` bruto — corrige o bug descrito no Blueprint §1 (variação de espaço em branco resolvendo ao mesmo `project_id` mas hoje aparecendo como 2 entradas). A exclusão de registros com `project_name is None` é preservada (mesmo comportamento hoje testado); o nome de exibição de cada grupo usa o `project_name` do registro mais recente do grupo (a lista já vem ordenada mais-novo-primeiro do repositório, preservada dentro de cada grupo).
- `summarize(project_name)`: sem mudança de comportamento — já filtra por nome exato, não agrupa. Ganha apenas `project_id` na saída, resolvido do primeiro registro (`records[0].project_id`) ou `None` se não houver nenhuma análise para o nome pedido.
- `_aggregate(project_name, records)` → `_aggregate(project_name, project_id, records)`: assinatura ganha o parâmetro `project_id: int | None`, incluído na saída.
- `list_action_items`/`list_latest_risks`: **sem mudança** — não fazem agrupamento (cada item carrega o `project_name` do seu próprio registro), portanto não têm o bug do Blueprint §1. Fora de escopo desta Fase, per a correção de escopo desta Technical Design (o Blueprint os mencionava por engano na Seção 2.1; `ProjectSummaryResponse` é a única resposta que muda).

## 2. API (`src/api/routes/intelligence.py`)

- `ProjectSummaryResponse` ganha `project_id: int | None` — campo aditivo, nenhum campo existente removido/renomeado.

## 3. Frontend (`web/lib/dashboard/types.ts`)

- `ProjectSummary` ganha `project_id?: number` — **opcional**, não obrigatório, para não exigir atualização de nenhuma fixture de teste existente (83 ocorrências de literais `ProjectSummary` em 6 arquivos de teste, nenhum deles precisa mudar). O BFF (`web/app/api/bff/dashboard/route.ts`) já faz passthrough puro do JSON do backend — nenhuma mudança necessária ali.

## 4. Testes

- `tests/test_project_summary_service.py`: atualizar as 2 asserções de igualdade estrita de dict (`test_summarize_counts_risks_and_action_items_from_structured_payloads`, `test_summarize_returns_zeros_for_project_with_no_analyses`) para incluir `project_id`; adicionar 1 teste novo cobrindo o bug do Blueprint §1 (duas análises com nomes que diferem só por espaço em branco devem aparecer como uma única entrada no portfólio).
- `tests/test_project_summary_api.py`/`tests/test_intelligence_api.py`: revisar se alguma resposta serializada de `/projects/summary` faz asserção estrita de corpo completo; se sim, incluir `project_id`.
- Nenhuma mudança em testes de frontend — campo opcional não quebra fixtures existentes.
- Regressão completa (backend + frontend + E2E 3 projetos) deve permanecer verde sem nenhuma mudança de expectativa fora do listado acima.

## 5. Fora de escopo (Fase 3b, não implementado agora)

Qualquer mudança a rotas, parâmetros de URL, ou ao consumo em `web/lib/dashboard/aggregate.ts`, `executive-focus.ts`, `web/lib/portfolio-intelligence/`, `web/lib/decision-center/`, `web/lib/workspace/` — permanecem inalterados, consumindo `project_name` exatamente como hoje.
