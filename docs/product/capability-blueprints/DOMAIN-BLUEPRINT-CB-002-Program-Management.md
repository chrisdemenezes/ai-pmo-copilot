# Domain Blueprint — Capability 02: Program Management

**Release:** 0.2 — Portfolio & Governance Foundation
**Status:** Alinhamento prévio à implementação (não é um gate de aprovação, mesma convenção da CB-001).
**Objetivo:** transformar Program em entidade real, estabelecendo a relação Estratégia (Portfolio) → Transformação (Program) → Execução (Project).

---

## 1. Entidades, atributos e responsabilidades

| Entidade | Nesta Capability | Responsabilidade |
|---|---|---|
| **Program** | **Implementada** — classe de domínio (DDD), não interface anêmica | Representa a Transformação: agrupa Projects sob um objetivo comum, sempre vinculado a exatamente um Portfolio |
| Portfolio | Já existe (CB-001) — ganha uma função de consolidação, não uma reescrita | Representa a Estratégia; passa a **derivar** (não armazenar) `programCount`/`progressPercentage`/`health` a partir de seus Programs reais |
| Project | Já existe (Épico 1), fora de escopo | Representa a Execução; ainda não referencia Program (preparado para Capability 03) |

**Atributos de Program** (`web/lib/domain/program.ts`): Identificação (id, name, code, description), Gestão (portfolioId — obrigatório, sponsor, programManager, status, health, priority), Planejamento (objective, startDate, plannedEndDate, actualEndDate), Indicadores (progressPercentage, projectCount, linkedDemands, linkedRisks, linkedIssues, pendingDecisions, pendingActions), Governança (pmoOwner, lastUpdated, nextReview).

**DDD, não modelo anêmico** (diretriz desta Capability): `Program` é uma classe com invariante de construção (`Program.create()` recusa um Program sem `portfolioId`) e comportamento próprio (`belongsToPortfolio()`, `isAtRisk()`, `isOverdue()`) — não um `interface` decorativo manipulado de fora. `Portfolio` (CB-001) permanece como estava — a diretriz de DDD vale a partir desta Capability, retrofitá-la agora seria uma refatoração desnecessária sem requisito que a exija.

## 2. Relacionamentos

```
Portfolio (1) ──< Program (N)     [IMPLEMENTADO nesta Capability — portfolioId obrigatório]
Program   (1) ──< Project (N)     [PREPARADO — Program.projectCount existe; Project ainda não referencia Program]
```

`consolidatePortfolios(portfolios, programs)` (`program.ts`) deriva, para cada Portfolio, a partir de seus Programs reais: contagem, progresso médio e saúde por pior-caso (`worstHealth` — vermelho vence amarelo vence verde). O Dashboard nunca mais lê os indicadores agregados gravados no próprio Portfolio seed — sempre a versão derivada.

## 3. Impactos na arquitetura existente

- **Backend (`src/`)**: nenhum impacto — mesma decisão da CB-001 (D-011): Program é domínio de frontend, sem migração.
- **Frontend (`web/`)**: novo `web/lib/domain/shared.ts` — vocabulário (`DomainHealth`/`DomainStatus`/`DomainPriority`/`worstHealth`) reaproveitado por Portfolio e Program, evitando duplicar 3 union types idênticos entre as duas entidades (CLAUDE.md, "nunca duplicar código"). `portfolio.ts` passa a importar desse módulo em vez de declarar os seus próprios.
- **Executive Cockpit**: bloco "Situação do Portfólio" passa a exibir indicadores **derivados** de Program (não mais o valor semeado do Portfolio); bloco "Situação dos Programas" migra de `PROGRAM_SITUATIONS` (mock) para Programs reais — segunda substituição progressiva.
- **Nova página `/program-management`**: listagem funcional (sem CRUD) de todos os Programs, agrupados por Portfolio.
- **Mission Control**: Capability Progress atualizado (Capability 01 concluída; Capability 02 em andamento) + diagrama textual da evolução do domínio (Portfolio → Program → Project → Demand → Risk → Decision → Action → Knowledge), mostrando o que é real hoje.
- **Sem regressões**: Design System, testes e demais painéis mock do Cockpit permanecem intocados.

## 4. Pontos preparados para Capability 03

Capability 03 é, pela própria hierarquia reafirmada pelo Founder (Portfolio→Program→Project), a ligação real de **Project a Program** (`programId` em Project — hoje inexistente, Project é Épico 4/RC-1 puro). Esta Capability já deixa prontos: `Program.projectCount` como indicador (a ser substituído por uma contagem real quando o vínculo existir) e `Program.belongsToPortfolio()`/invariante de `portfolioId` como o padrão de vínculo obrigatório que `Project.programId` deverá repetir.

---

Após este Domain Blueprint, a implementação prossegue imediatamente, conforme instrução do Founder.
