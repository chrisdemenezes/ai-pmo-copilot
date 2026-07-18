# Capability 02 — Program Management

STRATECH V2, Release 0.2. Artefato vivo — atualizado a cada entrega, não ao final da Capability. Registra o que foi feito, evidência (commit + screenshot), limitações conhecidas e o próximo passo. Não duplica o Decision Log (decisões de produto/técnicas) nem o Master Roadmap (planejamento).

Continuidade de `CAPABILITY-01-PORTFOLIO-MANAGEMENT.md` (aprovada e encerrada pelo Founder antes desta Capability começar).

---

### Domain Blueprint

- **Entregue:** `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-002-Program-Management.md` — entidades, relacionamentos, impactos arquiteturais e pontos preparados para a Capability 03 (vínculo Program → Project).

### Program como entidade DDD real

- **Entregue:** `web/lib/domain/shared.ts` (vocabulário compartilhado `DomainHealth`/`DomainStatus`/`DomainPriority`/`worstHealth`, Decision Log D-015); `web/lib/domain/program.ts` — classe `Program` com invariante de construção (`portfolioId` obrigatório) e comportamento (`belongsToPortfolio`, `isAtRisk`, `isOverdue`), primeira entidade sob a nova Diretriz Arquitetural Permanente contra modelos anêmicos (D-014). `portfolio.ts` refatorado para reaproveitar `shared.ts` em vez de duplicar os 3 vocabulários.
- **Entregue:** `consolidatePortfolios()` — deriva `programCount`/`progressPercentage`/`health` de cada Portfolio a partir de seus Programs reais (pior-caso de saúde, progresso médio).
- **Limitações:** ainda sem persistência em banco (mesma decisão D-011, agora estendida a Program); Program → Project preparado apenas via `projectCount` como indicador, sem FK real.

### Executive Cockpit consumindo Programs reais

- **Entregue:** `usePrograms()` (mesmo padrão de `usePortfolios()`); `ProgramSituationGrid` migrado de `ProgramSituation` (mock) para `Program` real; bloco "Situação do Portfólio" agora exibe indicadores **consolidados** de Program, nunca mais o valor semeado do Portfolio.
- **Limitações:** KPI strip "Programas em Execução" (Executive Overview) ainda não lê de `usePrograms()` — substituição prevista para uma próxima entrega, mesma disciplina incremental da Capability 01.

### Nova página Program Management

- **Entregue:** `/program-management` — listagem funcional (sem CRUD) de todos os Programs, agrupados por Portfolio pai, com saúde/progresso/projetos/sponsor/program manager. Item de navegação adicionado (4ª posição, ícone `Network`); rota protegida pelo gate de sessão (`proxy.ts`).

### Mission Control

- **Entregue:** Capability Progress atualizado — Capability 01 (Done, 100%), Capability 02 (In Progress, 60%); nova seção "Evolução do Domínio" com o diagrama Portfolio → Program → Project → Demand → Risk → Decision → Action → Knowledge, estado real (Project marcado como "já existe, ainda não vinculado").

### Correção incidental — Mission Control sem Sidebar

- **Entregue:** ao criar `app/program-management/layout.tsx`, notou-se que `app/mission-control/` nunca teve o seu (lacuna da Sprint 1) — corrigido com o mesmo `<AppShell>` de uma linha usado pelas demais rotas reais (D-017). Visível nos screenshots desta entrega: Mission Control agora renderiza com a Sidebar.

### Verificação

- **Evidência:** `tsc --noEmit` limpo, `eslint .` limpo, `vitest run` — 418 testes verdes (9 novos em `program.test.ts` para `Program`/`consolidatePortfolios`, 3 novos em `program-management/page.test.tsx`, 1 ajuste em `navigation.test.ts`).
- **Commit:** `(a registrar no push desta entrega)`.

---

**Próximo passo:** Capability 03 — vínculo real Program → Project (Project ganha `programId`), conforme preparado no Domain Blueprint CB-002 §4.
