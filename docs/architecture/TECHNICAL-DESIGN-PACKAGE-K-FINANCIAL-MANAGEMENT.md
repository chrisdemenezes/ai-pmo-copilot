# Technical Design — Package K: Financial Management / Executive Financial KPIs

STRATECH V1 Product & Capability Completion (Founder Mandate), Fase 3.

## 1. Contexto real (audit, não hipótese)

- `Project` (`src/database/models.py`) já é a tabela unificada Épico-1 + Enterprise
  Domain (`DOMAIN-BLUEPRINT-PROJECT.md`, Opção A) — nenhuma coluna financeira existe
  hoje em `portfolios`, `programs` ou `projects`.
- `Program`/`Portfolio` já seguem a disciplina "rollup derivado, nunca duplicado"
  (`progress_percentage`/`health` no frontend via `consolidateFromChildren`,
  AR-1, `web/lib/domain/shared.ts`) — este pacote estende a mesma disciplina para o
  dado financeiro, em vez de inventar um segundo mecanismo de agregação.
- Migração `0008_domain_seed.py` já semeia Portfolio→Program→Project reais (7
  Projects, códigos PJ-001..PJ-007) em ambas as organizações fixas do produto
  ("Organização Principal", "Demo Organization") — não é dado "DEMO" rotulado à
  parte, é a mesma baseline ilustrativa que todo o produto já usa hoje. Este
  pacote segue essa mesma convenção (não introduz uma segunda categoria de dado).
- `project_delivery.py` já expõe Create (`POST /api/projects-delivery`) mas não
  tem endpoint de update — fora de escopo deste pacote (não solicitado, YAGNI).

## 2. Modelo mínimo (Founder Mandate, Fase 3)

Apenas em `Project` (nunca duplicado em Program/Portfolio):

- `approved_budget NUMERIC(14,2) NULL`
- `actual_cost NUMERIC(14,2) NULL`
- `forecast_cost NUMERIC(14,2) NULL`

`variance` (`approved_budget - actual_cost`) e `variance_percentage` nunca são
colunas — são sempre calculados no ponto de leitura (mesmo princípio de
"derivado, nunca armazenado" já usado para health/progress). Program/Portfolio
não ganham coluna nenhuma: seu KPI financeiro é a soma dos Projects filhos,
computada em runtime (frontend), exatamente como já ocorre com
`progressPercentage`/`health` via `consolidateFromChildren`.

## 3. Migração

Nova migração (não edita `0008`, nunca reescreve seed anterior): adiciona as 3
colunas nullable a `projects`; preenche valores ilustrativos apenas nas 7
Projects que a própria `0008` semeia (mesmo padrão de busca por
`organization_id + code`, idempotente, nas mesmas 2 organizações). Downgrade
limpa esses valores e remove as colunas. Reversível, Postgres-compatível
(`NUMERIC`), tenant-safe (nenhuma coluna nova em tabela sem `organization_id`
próprio ou derivado).

## 4. API

`ProjectDeliveryResponse`/`ProjectDeliveryCreateRequest` (`project_delivery.py`)
ganham os 3 campos brutos (nullable). Nenhuma rota nova — reaproveita
create/list/get já existentes; `DomainRepository`/`DomainService` já fazem
passthrough genérico de `**fields`, nenhuma mudança necessária ali.

## 5. Frontend

- `web/lib/domain/project.ts`: `ProjectProps`/`Project`/`ProjectApiRow`/`toProject()`
  ganham `approvedBudget`/`actualCost`/`forecastCost` (nullable).
- Novo módulo `web/lib/domain/financial-rollup.ts` (mesmo padrão de
  `decision-queue.ts`/`portfolio-view.ts`: uma função pura, um arquivo,
  reaproveitada por múltiplas telas): `projectVariance()` +
  `aggregateFinancials()` — soma apenas valores presentes; retorna tudo `null`
  quando nenhum Project do grupo tem dado financeiro (nunca fabrica zero).
- `/project-delivery`: 3 colunas novas na tabela existente (Orçamento/Custo
  real/Variação, "—" quando ausente) + 1 linha de rollup por Program
  (reaproveita `aggregateFinancials` sobre os Projects já carregados).
- `/program-management`: passa a carregar `useProjects()` também; rollup por
  Portfolio via `aggregateFinancials` sobre os Projects cujos Programs
  pertencem àquele Portfolio.

## 6. Testes

- Backend: estende os testes existentes de `project_delivery` (create/list/get)
  cobrindo os 3 campos novos.
- Frontend: `financial-rollup.test.ts` (unitário, casos: todos presentes, todos
  ausentes, parcialmente ausentes, variância negativa); `project-delivery/page.test.tsx`
  e `program-management/page.test.tsx` estendidos com o novo rollup.

## 7. Riscos / Não-Escopo

- Nenhum endpoint de update/edição financeira é criado (não solicitado).
- Nenhuma moeda/localização é resolvida (valores tratados como números simples,
  mesma disciplina de `progress_percentage`).
- Program/Portfolio nunca recebem coluna própria — qualquer necessidade futura
  de granularidade financeira própria de Program é uma decisão nova, fora
  deste pacote.
