# Capability 01 — Portfolio Management

STRATECH V2, Release 0.2. Artefato vivo — atualizado a cada entrega, não ao final da Capability. Registra o que foi feito, evidência (commit + screenshot), limitações conhecidas e o próximo passo. Não duplica o Decision Log (decisões de produto/técnicas) nem o Master Roadmap (planejamento).

Este é o primeiro artefato de acompanhamento organizado por Capability de negócio, não mais por Sprint/Dia/entrega numerada — ver Sprint 1 (`SPRINT-1.md`) para o histórico anterior, encerrado e aprovado.

---

### Domain Blueprint

- **Entregue:** `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-001-Portfolio-Management.md` — entidades envolvidas, relacionamentos, responsabilidades, impactos arquiteturais e nota de transparência sobre o sequenciamento Release 0.1/0.2, conforme solicitado antes da implementação.
- **Limitações:** documento de alinhamento, não um gate de aprovação (conforme instrução explícita do Founder) — implementação prosseguiu imediatamente após.

### Portfolio como entidade real de domínio

- **Entregue:** `web/lib/domain/portfolio.ts` — interface `Portfolio` completa (Identificação: nome/código/descrição/categoria; Gestão: responsável executivo/objetivo estratégico/status/saúde/prioridade/datas; Indicadores: progresso/programas/projetos/demandas/riscos/issues/decisões pendentes; Governança: sponsor/PMO/última atualização/próxima revisão) e `listPortfolios()`, acessor assíncrono com a forma de um repositório real (Decision Log D-011).
- **Entregue:** `web/lib/hooks/use-portfolios.ts` — hook React Query (`usePortfolios`), mesmo padrão de `usePortfolioSummary`.
- **Limitações:** sem persistência em banco ainda (backend mockado nesta fase, por instrução explícita do Founder); Program ainda não existe como entidade — os contadores (`programCount`, etc.) são indicadores do próprio Portfolio, não uma relação real.

### Executive Cockpit consumindo Portfolio real

- **Entregue:** `PortfolioSituationGrid` migrado de `PortfolioSituation` (mock) para `Portfolio` (domínio real); `dashboard/page.tsx` — bloco "Situação do Portfólio" agora lê de `usePortfolios()`, primeira substituição progressiva de mock por dado real do Cockpit.
- **Limitações:** o restante do Cockpit (KPI strip "Portfólios Ativos", Situação dos Programas, Work Items, Decision/Actions Center, AI Recommendations) permanece mock — substituição incremental prevista para as próximas Capabilities.

### Mission Control — Capability Progress

- **Entregue:** nova seção "Capability Progress" — Capability 01 (Portfolio Management), 55% (In Progress), Próximo Marco: Program Management. Dado real (não mock), refletindo o estado desta entrega.
- **Limitações:** progresso calculado por avaliação qualitativa (Domínio parcial, Experiência parcial, Engenharia completa, Governança completa nesta entrega) — sem fórmula automatizada ainda.

### Verificação

- **Evidência:** `tsc --noEmit` limpo, `eslint .` limpo, `vitest run` — 405 testes verdes (nenhum teste novo dedicado: `listPortfolios()`/dados semeados não têm lógica condicional própria, consistente com a disciplina de testes já registrada em D-004).
- **Commit:** `(a registrar no push desta entrega)`.

---

**Próximo passo:** Program como entidade real (Capability 02), com relação real a Portfolio; substituir o restante dos blocos mock do Executive Cockpit progressivamente.
