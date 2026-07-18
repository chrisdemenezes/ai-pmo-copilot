# Capability 03 — Project Delivery

STRATECH V2, Release 0.2. Artefato vivo — atualizado a cada entrega, não ao final da Capability. Registra o que foi feito, evidência (commit + screenshot), limitações conhecidas e o próximo passo. Não duplica o Decision Log (decisões de produto/técnicas) nem o Master Roadmap (planejamento).

Continuidade de `CAPABILITY-02-PROGRAM-MANAGEMENT.md` (aprovada pelo Founder antes desta Capability começar).

---

### Domain Blueprint

- **Entregue:** `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-003-Project-Delivery.md` — entidades, relacionamentos, impactos arquiteturais e preparação para a Capability 04 (Demand).

### Project como Bounded Context (Project Delivery)

- **Entregue:** `web/lib/domain/project.ts` — classe `Project` com invariante de construção (`programId` obrigatório), comportamento (`belongsToProgram`, `belongsToPortfolio` derivado via Program pai, `isOverdue`, `isAtRisk`, `completionPercentage()`, `health()`); objetos de apoio internos `Owner`/`Milestone`/`Team` (não promovidos a entidade ainda, D-018). `consolidatePrograms()` deriva Program a partir de Projects reais.
- **Entregue:** cadeia de consolidação transitiva no Dashboard — Program deriva de Project primeiro, Portfolio deriva desse Program já consolidado (D-020).
- **Limitações:** ainda sem persistência em banco (mesma decisão D-011/D-014, agora estendida a Project); `portfolioId` nunca é armazenado em Project, sempre derivado via Program.

### Executive Cockpit

- **Entregue:** "Situação dos Programas" agora reflete indicadores consolidados por Projects reais; novo painel **Program Execution** (por Program: Projects/progresso/saúde/Projetos Críticos) + **Top 5 Projects que exigem atenção** (`rankProjectsNeedingAttention`, ranqueado por saúde e progresso).
- **Limitações:** KPI strip "Projetos em Andamento" (Executive Overview) ainda não lê de `useProjects()` (Project Delivery) — continua mostrando o valor mock; substituição prevista para uma próxima entrega.

### Nova página Project Delivery

- **Entregue:** `/project-delivery` — listagem funcional (sem CRUD) de todos os Projects, agrupados por Program pai. Item de navegação adicionado (5ª posição, ícone `Rocket`); rota protegida pelo gate de sessão.

### Domain Model

- **Entregue:** `docs/architecture/DOMAIN-MODEL.md` — novo artefato permanente consolidando os 3 Blueprints (CB-001/002/003): linguagem ubíqua, hierarquia, entidades, relacionamentos, regra de consolidação, estado de implementação, preparação para Capabilities futuras.

### Governança

- **Entregue:** `ADR-V2-009-frontend-domain-layer.md` (decisão formal de modelar Portfolio/Program/Project como camada de domínio de frontend, DDD, pré-persistência); Decision Log D-018 a D-022 (incluindo o registro da recomendação de Architecture Review AR-1 antes da Capability 04).

### Verificação

- **Evidência:** `tsc --noEmit` limpo, `eslint .` limpo, `vitest run` — 436 testes verdes (18 novos em `project.test.ts`, 3 novos em `project-delivery/page.test.tsx`, ajuste em `navigation.test.ts`).
- **Commit:** `(a registrar no push desta entrega)`.

---

**Próximo passo:** conforme recomendação do Founder (D-022), uma Architecture Review (AR-1) antes de iniciar a Capability 04 — Demand.
