# Domain Blueprint — Capability 01: Portfolio Management

**Release:** 0.2 — Portfolio & Governance Foundation
**Status:** Alinhamento prévio à implementação (não é um gate de aprovação — Founder, Release 0.2/Capability 01).
**Objetivo:** transformar Portfólio de representação visual em entidade real do domínio, primeiro elo da cadeia Portfolio → Program → Project → Demand → Risk → Decision → Action → Knowledge.

---

## 1. Entidades envolvidas

| Entidade | Nesta Capability | Papel na cadeia |
|---|---|---|
| **Portfolio** | **Implementada** — entidade real com identidade própria | Raiz da cadeia de gestão estratégica |
| Program | Preparada apenas como relação (`portfolio_id` futuro) — **não implementada** | Agregação de Projects sob um Portfolio |
| Project | Já existe como entidade real (Épico 1); ainda não referencia Portfolio/Program | Unidade de execução |
| Demand, Risk, Decision, Action, Knowledge | Fora de escopo desta Capability | Elos seguintes da cadeia (Capabilities futuras) |

Nenhuma entidade além de Portfolio é criada nesta entrega — a Diretriz Arquitetural Permanente (Portfolio → Program → Project → Demand → Risk → Decision → Action → Knowledge) é respeitada ao não pular etapas.

## 2. Relacionamentos

```
Portfolio (1) ──< Program (N)      [futuro — Capability 02]
Portfolio (1) ──< Project (N)      [hoje: indicador agregado, não FK]
Portfolio (1) ──< Demand/Risk/Issue/Decision  [futuro]
```

Nesta Capability, Portfolio não possui uma foreign key real para `Project` no backend (isso exigiria migração de schema — fora de escopo). Em vez disso, Portfolio carrega **indicadores agregados** (`programCount`, `projectCount`, etc.) como parte de sua própria estrutura, deixando o relacionamento real para quando o backend for wireado (Capability 02+, quando Program também existir).

## 3. Responsabilidades de cada entidade

- **Portfolio**: representa um agrupamento estratégico de programas/projetos com identidade, governança e indicadores próprios. É a fonte de verdade para "Situação do Portfólio" no Executive Cockpit. Não conhece o conteúdo de Programs/Projects — apenas os agrega numericamente (hoje) ou por relação (quando o backend existir).
- **Program** (futuro): agrega Projects sob um Portfolio; ainda não existe.
- **Project** (já real, Épico 1): unidade de execução; nesta Capability permanece sem alteração de schema.

## 4. Impactos na arquitetura existente

- **Backend (`src/`)**: **nenhum impacto.** Nenhuma migração, model, provider ou registry novo — CLAUDE.md permanece integralmente respeitado. Portfolio **não** é persistido em banco nesta Capability.
- **Frontend (`web/`)**: novo diretório `web/lib/domain/` — primeira camada de domínio explícita do RC-1, paralela (não substituta) a `lib/mock/` (dados de demonstração sem estrutura de entidade) e a `lib/portfolio-intelligence/` (feature V1 real, de priorização executiva por projeto — **não confundir com a entidade Portfolio**, ver Decision Log D-012).
- **Padrão de acesso**: `listPortfolios()` é uma função assíncrona (`Promise<Portfolio[]>`), com a mesma forma de um repositório real, ainda que resolvida hoje a partir de dados semeados em memória. Isso cumpre a diretriz "estruturar como se já fosse persistida" — quando a Release 0.2 wireener um endpoint real (BFF + backend), apenas o corpo de `listPortfolios()` muda; nenhum consumidor (`usePortfolios()`, `PortfolioSituationGrid`, `dashboard/page.tsx`) precisa mudar.
- **Executive Cockpit**: o bloco "Situação do Portfólio" passa a consumir `usePortfolios()` em vez do array estático `PORTFOLIO_SITUATIONS` — primeira substituição progressiva de mock por domínio real (diretriz do Founder).
- **Mission Control**: ganha a seção "Capability Progress", mostrando o avanço real desta e das próximas Capabilities.
- **Sem regressões**: Design System, testes e demais painéis do Cockpit (Decision Center, Actions Center, Recent Activity, AI Recommendations) permanecem mock, sem alteração de forma.

## 5. Nota sobre sequenciamento (transparência, não bloqueio)

A Release 0.2 inicia oficialmente enquanto a Release 0.1 ainda está em progresso (Épicos 3-6 não iniciados) — avanço explícito e deliberado do Founder. Isso não gera um conflito técnico real nesta Capability porque nenhuma migração de banco foi feita: Portfolio existe apenas como domínio de frontend (§4), preservando toda dependência real (RBAC, Projeto como entidade totalmente real) para quando for implementada. Registrado aqui para rastreabilidade, não como impedimento.

---

Após este Domain Blueprint, a implementação prossegue imediatamente, conforme instrução do Founder.
