# STRATECH V2 — Architecture Baseline RC-2

**Status:** baseline arquitetural oficial da STRATECH após as Capabilities 01-03 (Portfolio Management, Program Management, Project Delivery).
**Certificada por:** Architecture Review AR-1 (Release 0.2), 2026-07-18.
**Papel:** ponto de referência estável para comparar qualquer evolução futura do domínio. Não substitui `docs/architecture/DOMAIN-MODEL.md` (referência viva, atualizada a cada Capability) — esta baseline é uma fotografia certificada em um momento específico; o Domain Model continua a fonte corrente.

---

## 1. Estado atual da arquitetura

### 1.1 Camadas

```
web/app/              -- rotas Next.js (App Router), "use client" nas páginas com dado
web/components/       -- componentes de apresentação (cockpit/, dashboard/, shell/, ui/)
web/lib/hooks/        -- acesso a dado via React Query (um hook por fonte)
web/lib/domain/       -- ENTIDADES DE DOMÍNIO (Portfolio, Program, Project, shared) -- nova camada, Capabilities 01-03
web/lib/mock/         -- dado simulado sem entidade de domínio (Decision Center, Actions Center, AI Recommendations etc.)
web/lib/dashboard/    -- ProjectSummary (V1 real, BFF) + Executive Focus
web/lib/portfolio-intelligence/ -- V1 real, priorização executiva por projeto
src/                  -- backend Python (api/agents/database/llm/prompts/services/workflows) -- INTOCADO pelas Capabilities 01-03
```

`web/lib/domain/` é a camada nova certificada por esta baseline. Ela não depende de `web/lib/mock/` nem o contrário — cada Capability progressivamente substitui um consumidor de mock por um consumidor de domínio (nunca o inverso).

### 1.2 Bounded Contexts

| Bounded Context | Entidades | Capability | Status |
|---|---|---|---|
| **Portfolio Management** | Portfolio | 01 | Concluído |
| **Program Management** | Program | 02 | Concluído |
| **Project Delivery** | Project (+ Owner/Milestone/Team como value objects internos) | 03 | Concluído |

### 1.3 Domain Model consolidado

Ver `docs/architecture/DOMAIN-MODEL.md` (referência viva). Resumo: Portfolio (Estratégia) → Program (Transformação) → Project (Execução), cada um com invariante de vínculo obrigatório ao pai a partir de Program, comportamento encapsulado (nunca modelo anêmico a partir da Capability 02), e uma função de consolidação que deriva os indicadores do pai a partir dos filhos reais.

### 1.4 Relação entre entidades

```
Portfolio (1) ──< Program (N)     portfolioId obrigatório em Program (Capability 02)
Program   (1) ──< Project (N)     programId obrigatório em Project (Capability 03)
```

Nenhuma é uma foreign key de banco — ambas são invariantes de domínio de frontend, validadas em `.create()`.

### 1.5 Fluxo de consolidação

```
Portfolio
   ↑ consolidatePortfolios() (program.ts)
Program
   ↑ consolidatePrograms() (project.ts)
Project
```

Execução real (`dashboard/page.tsx`): `consolidatePrograms()` roda primeiro (Program deriva de Project), o resultado alimenta `consolidatePortfolios()` (Portfolio deriva do Program já consolidado) — rollup transitivo, não dois pares isolados. Regra de agregação (filtrar por pai, média de progresso, saúde por pior-caso) vive uma única vez em `consolidateFromChildren()` (`shared.ts`), extraída durante esta AR-1 depois de encontrada duplicada entre as duas funções.

---

## 2. Princípios arquiteturais permanentes

1. **Clareza do domínio** antes de qualquer funcionalidade nova (Diretriz Arquitetural Permanente, Capability 03).
2. **Evolução incremental** — nunca reescrita total (ADR-V2-001, reafirmado a cada Capability).
3. **Estabilidade da arquitetura** — RC-1, Design System e testes preservados integralmente a cada entrega.
4. **Substituição gradual de dados simulados por entidades reais** — um widget do Cockpit de cada vez, nunca uma reescrita completa do Dashboard.
5. **Baixo acoplamento e alta coesão** — `web/lib/domain/` depende apenas na direção Portfolio ← Program ← Project (Project pode importar Program, Program nunca importa Project como valor, apenas como tipo quando necessário).
6. **Preparação para multi-tenant e regras por organização** — reconhecida como pendência (TD-007), não implementada prematuramente.

## 3. Convenções DDD

- Toda entidade a partir de Program é uma `class`, não uma `interface` manipulada de fora.
- Construção via `static create()`, nunca `new` público — o único lugar onde o invariante de vínculo ao pai (`portfolioId`/`programId`) é verificado.
- Comportamento como método (`belongsToPortfolio`, `isAtRisk`, `isOverdue`, `completionPercentage()`, `health()`), nunca um campo manipulado externamente para decidir uma regra de negócio.
- Vocabulário compartilhado (`DomainHealth`/`DomainStatus`/`DomainPriority`, `shared.ts`) — nunca redeclarado por entidade.
- Acessores de leitura (`listPortfolios()`/`listPrograms()`/`listProjects()`) são assíncronos e repository-shaped mesmo sem backend real — o contrato já é o de uma chamada real, para trocar a implementação sem tocar consumidores.
- **Exceção documentada:** `Portfolio` (Capability 01) é `interface` + array, não uma classe — precede a diretriz DDD (que vale a partir da Capability 02) e não foi retrofitada, por não haver requisito que justifique essa refatoração (Decision Log D-014).

## 4. Regras de evolução

- Nenhuma entidade nova fora de ordem na cadeia Portfolio → Program → Project → Demand → Risk → Decision → Action → Knowledge.
- Toda nova Capability começa por um Domain Blueprint (`docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-NNN-*.md`), aprovado antes da implementação.
- Todo Bounded Context novo deve repetir o padrão desta baseline (invariante de vínculo ao pai + função de consolidação), a menos que uma ADR registre uma exceção justificada.
- `docs/architecture/DOMAIN-MODEL.md` é atualizado a cada Capability que amplia um Bounded Context — não é retroativo, é vivo.

## 5. Dívidas técnicas aceitas

| TD | Resumo | Severidade | Bloqueia Capability 04? |
|---|---|---|---|
| TD-001 | SQLite não aplica Foreign Keys | Alto (pré-existente, Épico 1) | Não |
| TD-002 | Delete Policy indefinida | Alto (pré-existente, Épico 1) | Não |
| TD-003 | Convenção de sessão do Repository inconsistente | Baixo (pré-existente, Épico 1) | Não |
| TD-004/005/006 | Baseline Defects (race de invalidação React Query) | Médio (pré-existentes) | Não |
| **TD-007** | Domínio Portfolio/Program/Project sem persistência, sem multi-tenant ainda | Médio (aceito, ADR-V2-009) | **Não** — só relevante quando o backend for wireado |
| **TD-008** | 3 conceitos "Project" coexistem sem unificação | Médio (aceito até o Épico 4) | **Não** — mitigado por documentação explícita (D-019) |

Nenhuma dívida listada bloqueia o início da Capability 04.

## 6. Riscos conhecidos

1. **Confusão de nomenclatura "Project"** (TD-008) — mitigado por docstrings + Decision Log, não por um mecanismo em tempo de compilação. Risco residual: baixo, mas real, para um engenheiro novo sem contexto.
2. **Colisão de numeração ADR-V2-004** — pré-existente, não introduzida nem resolvida por esta AR-1; permanece pendência de decisão do Founder.
3. **Executive Cockpit com mock residual** — Work Items, Decision Center, Actions Center, Recent Activity e AI Recommendations continuam simulados (nenhuma regressão, mas o risco de "número simulado parecendo real" já se materializou uma vez nesta auditoria — ver §5 do AR-1 Executive Report — e pode se repetir se um widget novo for adicionado sem essa checagem).
4. **Sequenciamento Release 0.1/0.2 em paralelo** — Release 0.2 (Capabilities 01-03) avançou por decisão explícita do Founder antes de Release 0.1 (Épicos 3-6) terminar. Sem risco técnico hoje (nenhuma persistência), mas exige atenção quando o backend real for wireado, para não colidir com o RBAC ainda não implementado (Épico 3).

## 7. Próximas Capabilities

- **Capability 04 — Demand**: intake anterior à aprovação como Project. Deve repetir o padrão (invariante `projectId`, `consolidateFromChildren` reaproveitado).
- **Épico 4 (Release 0.1, paralelo)**: unificação real de `Project` — candidato natural para também resolver TD-008.
- **Quando o backend for wireado** para Portfolio/Program/Project: revisitar ADR-V2-009 e resolver TD-007 (adicionar `organization_id` desde a primeira migração, mesmo padrão do Épico 1).

---

## Referências

- `docs/architecture/DOMAIN-MODEL.md`
- `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-001-Portfolio-Management.md`
- `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-002-Program-Management.md`
- `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-003-Project-Delivery.md`
- `docs/architecture/adr/ADR-V2-009-frontend-domain-layer.md`
- `docs/architecture/TECHNICAL_DEBT.md`
- `docs/product/stratech-v2/DECISION-LOG.md` (D-011 a D-022+)
