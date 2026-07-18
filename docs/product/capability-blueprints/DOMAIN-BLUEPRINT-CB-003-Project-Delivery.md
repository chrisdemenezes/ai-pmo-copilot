# Domain Blueprint — Capability 03: Project Delivery

**Release:** 0.2 — Portfolio & Governance Foundation
**Status:** Alinhamento prévio à implementação (mesma convenção de CB-001/CB-002, não é gate de aprovação).
**Objetivo:** implementar o Bounded Context **Project Delivery** — não apenas uma entidade `Project`, mas o contexto responsável por governar a execução.

---

## 1. Entidades, atributos e responsabilidades

| Entidade | Nesta Capability | Responsabilidade |
|---|---|---|
| **Project** | **Implementada** — classe DDD, terceira entidade da cadeia | Representa a Execução: unidade de trabalho real, sempre vinculada a exatamente um Program |
| Program | Já existe (CB-002) — ganha consolidação a partir de Projects | Passa a **derivar** `projectCount`/`progressPercentage`/`health` de seus Projects reais, em vez de manter valores próprios estáticos |
| Portfolio | Já existe (CB-001) | Continua consolidando através de Programs — como os Programs agora se consolidam de Projects, o rollup se torna transitivo (Project → Program → Portfolio) |

**Atributos de Project** (`web/lib/domain/project.ts`): Identificação (id, name, code, description), Organização (programId — obrigatório; portfolioId é **derivado**, nunca armazenado, via `belongsToPortfolio()`; sponsor, projectManager), Planejamento (objective, startDate, plannedEndDate, actualEndDate), Indicadores (progressPercentage, health, status, priority), Governança (lastUpdated, nextReview).

**Comportamento, não modelo anêmico**: `Project.create()` recusa um Project sem `programId`. Métodos: `belongsToProgram()`, `belongsToPortfolio(portfolioId, programs)` (deriva via o Program pai), `isOverdue()`, `isAtRisk()`, `completionPercentage()`, `health()` — os dois últimos expostos como método, não campo público, por serem os indicadores mais lidos externamente (leitura controlada, mesmo padrão de encapsulamento pedido pela Diretriz Arquitetural Permanente).

**Objetos de apoio internos (não promovidos a entidade ainda)**: `Owner` (nome, papel), `Milestone` (nome, prazo, status), `Team` (tamanho, líder) — vivem como *value objects* dentro de `Project`, sem módulo próprio, exatamente como pedido. Serão promovidos a entidades quando uma Capability futura exigir (ex.: Milestones com progressão própria).

## 2. Relacionamentos

```
Portfolio (1) ──< Program (N)     [CB-002]
Program   (1) ──< Project (N)     [IMPLEMENTADO nesta Capability — programId obrigatório]
```

`consolidatePrograms(programs, projects)` (`project.ts`) deriva, para cada Program, a partir de seus Projects reais: contagem, progresso médio, saúde por pior-caso. O resultado alimenta `consolidatePortfolios()` (CB-002) — a cadeia de consolidação passa a ser **transitiva**: Portfolio deriva de Programs já consolidados por Projects, não mais dos valores semeados de Program.

## 3. Impactos na arquitetura existente

- **Backend (`src/`)**: nenhum impacto — mesma decisão de CB-001/CB-002 (D-011/D-014): Project (este) é domínio de frontend, sem migração.
- **Atenção — colisão de nome, não de dado**: este `Project` (`lib/domain/project.ts`) é um terceiro conceito distinto de dois já existentes no código, e nenhum dos três compartilha ID ou tabela:
  1. O `Project` real do backend (`src/database/models.py`, Épico 1) — persistido, hoje só usado para associar organização/membership, ainda não referenciado pelas análises de IA.
  2. `ProjectSummary` (`web/lib/dashboard/types.ts`) — dado real do V1, vindo do BFF (`/api/bff/dashboard`), chaveado por `project_name` (texto livre), usado pelo Executive Cockpit "Projetos"/Risk Concentration/Health Distribution.
  3. **Este** `Project` (Capability 03) — domínio de frontend, chaveado a um `Program`, ainda sem persistência.
  Os três permanecem deliberadamente desconectados até o Épico 4 (unificação de `Project`) — registrado no Decision Log (D-019) para não confundir o próximo engenheiro, mesmo padrão de D-005/D-012.
- **Executive Cockpit**: novo painel "Program Execution" (por Program: Projects, progresso, saúde, Projetos Críticos) + "Top 5 Projects que exigem atenção" (ranqueado por risco, via `rankProjectsNeedingAttention()`).
- **Nova página `/project-delivery`**: listagem funcional (sem CRUD) de Projects agrupados por Program.
- **Mission Control**: Capability Progress (01/02 concluídas, 03 em andamento) + Evolução do Domínio atualizada (Project deixa de ser "Not Started").
- **Novo documento permanente**: `docs/architecture/DOMAIN-MODEL.md` — consolida os 3 Blueprints (CB-001/002/003) em uma referência única de domínio.
- **Sem regressões**: Design System, testes e demais painéis mock do Cockpit permanecem intocados.

## 4. Preparação para Capability 04

Capability 04, pela hierarquia (Project → Demand → Risk → Decision → Action → Knowledge), é **Demand** — o intake anterior à aprovação como Project. Esta Capability já deixa como padrão replicável: o invariante de vínculo obrigatório ao pai (`programId` aqui, `portfolioId` em Program) e a função de consolidação pai-a-partir-do-filho (`consolidatePrograms`, mesmo formato de `consolidatePortfolios`) — Demand deverá seguir a mesma forma ao se vincular a Project.

---

Após este Domain Blueprint, a implementação prossegue imediatamente, conforme instrução do Founder.
