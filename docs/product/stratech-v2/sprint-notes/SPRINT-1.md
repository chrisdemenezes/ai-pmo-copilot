# Sprint 1 — Sprint Notes

STRATECH V2. Artefato vivo — atualizado a cada entrega, não ao final da Sprint. Registra o que foi feito, evidência (commit + screenshot), limitações conhecidas e o próximo passo — não duplica o Decision Log (decisões de produto/técnicas) nem o Roadmap (planejamento).

---

### Dia 1 — Design System

- **Entregue:** auditoria do Design System V1 (RFC-001) reaproveitado; novos primitivos `Table`, `Progress`, `Tooltip`, `Avatar` (mesmo padrão Radix+Tailwind); marca renomeada de "AI PMO Copilot" para "STRATECH" (sidebar, metadata, style guide).
- **Commit:** `6b2d822`.
- **Evidência:** screenshot de `/style-guide`, `tsc`/`eslint`/398 testes verdes.
- **Limitações:** nenhuma tela de produto nova ainda.

### Entrega 2.1 — Executive Cockpit: estrutura, header, KPIs

- **Entregue:** faixa de KPIs (Portfólios/Programas/Projetos/Decisões) no topo do `/dashboard`, dado mock centralizado em `lib/mock/cockpit-data.ts`.
- **Commit:** `755d3a8`.
- **Evidência:** screenshot logado via mock backend, dashboard real.
- **Limitações:** redundância visual com o strip real existente logo abaixo (a resolver na Entrega 2.5).

### Entrega 2.2 — Situação do Portfólio / Programas

- **Entregue:** `PortfolioSituationGrid`, `ProgramSituationGrid` (tabela md+/cards mobile), mesmo padrão do `ProjectHealthGrid` real.
- **Commit:** `5aa92be`.
- **Evidência:** screenshot do dashboard completo.
- **Limitações:** Portfólio/Programa/Projeto ainda são 3 fontes de mock independentes, sem árvore navegável real.

### Entrega 2.3 — Demandas, Riscos, Issues, Mudanças

- **Entregue:** `WorkItemsOverview` — 4 cards (Demandas/Riscos/Issues/Mudanças) com contagem total + aberto/em andamento/concluído + badge de críticos. Dado mock em `cockpit-data.ts` (`WORK_ITEM_BREAKDOWN`).
- **Commit:** `(ver commit desta entrega)`.
- **Evidência:** screenshot do dashboard completo.
- **Limitações:** nenhuma das 4 categorias é uma entidade real; candidatas a ADR de extensão do Domain Map (ver Architecture Evolution Proposal, Seção 8).

### Mission Control (painel do Founder)

- **Entregue:** nova rota `/mission-control`, protegida pela sessão (proxy.ts) — mas **sem RBAC real ainda** (Épico 3 não iniciado), então hoje qualquer usuário autenticado acessa, não só o Founder. Painel mostra: status dos 6 Épicos da Release 0.1, progresso das 5 Releases (0.1-0.5), últimos 5 PRs, resumo de governança (débito técnico, Baseline Defects, ADRs + colisão pendente, Lessons Learned), checklist de entregas da própria Sprint 1, e as últimas entradas do Decision Log — todos com dados **reais** (não mock), lidos manualmente dos artefatos de governança reais no momento da construção (sem wiring de API ainda).
- **Commit:** `(ver commit desta entrega)`.
- **Evidência:** screenshot da rota completa.
- **Limitações:** dado estático (não busca ao vivo dos arquivos `docs/governance/*.md` ou da API do GitHub); acesso não restrito ao Founder de fato.
