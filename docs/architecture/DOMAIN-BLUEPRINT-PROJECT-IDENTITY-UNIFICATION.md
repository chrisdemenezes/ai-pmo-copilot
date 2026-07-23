# Domain Blueprint — Epic W3-1: Project Identity Unification (TD-008, Fase 3)

**Wave:** 3 (Enterprise Master Execution Program), primeiro Epic liberado pela Architecture Review AR-2.
**Precede:** `TD-008` em `docs/architecture/TECHNICAL_DEBT.md` — "reconciliar `analysis_records.project_name` → `project_id`, aposentando `ProjectSummary`".
**Status:** Blueprint conceitual — não implementa, não produz código. Precede a Technical Design deste Epic.

---

## 0. O que já é real hoje (não proposto)

- `AnalysisRecord` (`src/database/repository.py`) já tem `project_id` (FK para `projects.id`), **populado em toda escrita** desde o Épico 1 — `save_analysis()` chama `EnterpriseRepository.get_or_create_project_for_name()` na mesma transação. Nenhuma migração de dado é necessária: os dados já existem, só não são usados como chave de agrupamento nem expostos na API.
- `get_or_create_project_for_name()` resolve por `normalize_project_name()` (`src/database/project_identity.py`): apenas `strip()` de espaços — capitalização e acentos são preservados de propósito ("Projeto ALFA" e "projeto alfa" são Projects diferentes até um admin reconciliar, ADR-V2-003, não uma decisão que este Blueprint reabre).
- `ProjectSummaryService` (`src/services/project_summary_service.py`) — todos os 4 métodos (`summarize`, `summarize_portfolio`, `list_action_items`, `list_latest_risks`) e `_aggregate()` operam inteiramente sobre `AnalysisRecord.project_name` (string), nunca `project_id`.
- **Superfície real que depende deste dado hoje** (levantamento feito nesta auditoria, não estimado): `src/api/routes/intelligence.py` (rotas de análise + `/projects/summary`), `web/lib/dashboard/{types,aggregate,executive-focus}.ts`, `web/lib/portfolio-intelligence/portfolio-view.ts`, `web/lib/decision-center/decision-queue.ts`, `web/lib/workspace/types.ts`, `web/app/api/bff/dashboard/route.ts` — ou seja, **Dashboard, Portfólio, Decision Center, Executive Focus e Workspace inteiros** dependem do formato atual de `ProjectSummary`. Esta é a razão pela qual TD-008 nomeia isso como "Fase 3" e não como um ajuste pequeno.

## 1. Bug real encontrado durante esta auditoria (motivação concreta, não hipotética)

`ProjectSummaryService.summarize_portfolio()` agrupa registros por `record.project_name` **bruto** (sem normalização), enquanto `get_or_create_project_for_name()` já normaliza (`strip()`) antes de resolver o `Project`. Consequência: duas análises da mesma reunião/risco/status enviadas como `"Projeto Alfa"` e `"Projeto Alfa "` (espaço à direita) **resolvem ao mesmo `project_id`** no banco, mas aparecem hoje como **duas entradas separadas** no portfólio agregado (`summarize_portfolio()`), porque o agrupamento em memória usa a string crua. Isto já é uma divergência real entre o que o banco sabe (via `project_id`) e o que a camada de Intelligence mostra (via `project_name` cru) — não uma hipótese.

## 2. Escopo deste Epic — faseado (mesmo padrão já usado com sucesso em `DOMAIN-BLUEPRINT-PROJECT.md`)

Dado o levantamento da Seção 0, "aposentar `ProjectSummary`" por completo em um único Epic significaria reescrever Dashboard, Portfólio, Decision Center, Executive Focus e Workspace simultaneamente — um raio de impacto muito maior do que o resto da Wave 3 e com risco real de regressão em toda a suíte E2E existente (203+ testes cobrindo exatamente essas páginas). Nenhuma regra desta missão exige fazer isso de uma vez; TD-008 já era tratado em fases desde sua origem (Fase 1/2 concluídas na Wave 2). Este Epic executa apenas a **Fase 3a**, deixando **Fase 3b** documentada e explicitamente não implementada agora.

### Fase 3a — nesta implementação (aditiva, baixo risco)

1. `ProjectSummaryService._aggregate`/`summarize_portfolio`/`list_action_items`/`list_latest_risks` passam a agrupar por `project_id` (com `project_name` do primeiro registro do grupo mantido apenas como rótulo de exibição) — corrige o bug da Seção 1, sem mudar nenhum contrato de API existente.
2. `ProjectSummaryResponse` (`src/api/routes/intelligence.py`) e o tipo `ProjectSummary` (`web/lib/dashboard/types.ts`) ganham um campo **novo e aditivo** `project_id: int` — nenhum campo existente é removido ou renomeado, nenhum consumidor existente quebra (TypeScript estrutural: um campo a mais não invalida nenhum uso atual).
3. Nenhuma rota, URL, parâmetro de API ou tipo de frontend existente é removido nesta fase. `project_name` continua sendo o parâmetro de entrada de todas as rotas (`/analyze/*`, `/analyses`, `/action-items`, `/latest-risks`, `/projects/summary`) — mudar isso é exatamente o que a Fase 3b faz, deliberadamente adiada.

### Fase 3b — documentada aqui, não implementada neste Epic

Migrar as rotas de `src/api/routes/intelligence.py`, o BFF (`web/app/api/bff/dashboard/route.ts`) e todo o consumo em `web/lib/dashboard/`, `web/lib/portfolio-intelligence/`, `web/lib/decision-center/`, `web/lib/workspace/` de `project_name` para `project_id` como chave primária de fato, incluindo a rota `/workspace/{projectName}` (hoje com lógica própria de encode/decode de `/` no nome). **Não incluída neste Epic** — motivo: raio de impacto abrange praticamente toda a experiência executiva do produto e a suíte E2E completa; candidata a um Epic dedicado subsequente da Wave 3, com sua própria Architecture Review de escopo (mesma disciplina já usada para W3-3/Risk Advisor). Registrada como trabalho futuro, não como uma lacuna silenciosa desta entrega.

## 3. Por que isto não é "ampliação de escopo" nem "alteração arquitetural significativa"

- Nenhum Bounded Context novo: `Project` já existe como entidade real desde a Wave 2.
- Nenhum contrato de API quebrado: `project_id` é aditivo; `project_name` continua funcionando exatamente como hoje.
- Nenhuma decisão de negócio ou infraestrutura nova: é a correção de um bug real já nomeado como dívida técnica aberta (TD-008), com o gatilho de resolução ("a Wave 3 começar") já cumprido pela AR-2.
- A Fase 3b (a parte realmente grande) é explicitamente **não** executada agora — evita o próprio risco que motivaria um Decision Proposal.

## 4. Testes obrigatórios para a Technical Design que segue este Blueprint

- `ProjectSummaryService.summarize_portfolio()` agrupa corretamente por `project_id`, incluindo o caso do bug da Seção 1 (nomes com variação de espaço resolvendo ao mesmo projeto).
- `ProjectSummaryResponse`/`ProjectSummary` incluem `project_id` sem quebrar nenhum teste existente que já asserte a forma da resposta.
- Regressão completa: suíte backend (281 testes) e suíte E2E completa (`lg`/`md`/`mobile`) permanecem verdes sem nenhuma alteração de expectativa — evidência de que a Fase 3a é puramente aditiva.

## 5. O que este Blueprint NÃO decide

- Quando a Fase 3b será agendada (fica para uma futura organização de Epics da própria Wave 3, não decidida aqui).
- Nenhuma mudança ao modelo `Project`, `Portfolio` ou `Program` já aprovado (Wave 2).
