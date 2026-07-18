# STRATECH V2 — Domain Model

**Status:** referência oficial e permanente do domínio da STRATECH, a partir da Capability 03 (Release 0.2).
**Papel:** este documento **consolida** os Capability Blueprints (`docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-NNN-*.md`) — eles continuam existindo como o registro histórico de cada Capability; este arquivo é atualizado a cada nova Capability que amplia um Bounded Context, para que o domínio inteiro seja legível em um único lugar, sem precisar recompor a história lendo todos os Blueprints em sequência.

---

## 1. Linguagem Ubíqua

| Termo | Significado na STRATECH |
|---|---|
| **Portfolio** | Representa a **Estratégia**. Agrupamento estratégico de Programs. |
| **Program** | Representa a **Transformação**. Agrupamento de Projects sob um objetivo comum. |
| **Project** | Representa a **Execução**. Unidade real de trabalho, primeiro nível onde a plataforma gere trabalho operacional. |
| **Demand** *(futuro)* | Intake anterior à aprovação como Project. |
| **Risk** *(futuro)* | Risco formal de portfólio/programa/projeto, com mitigação — distinto do Risk Intelligence de IA (V1). |
| **Decision** *(futuro)* | Objeto de primeira classe de decisão executiva formal. |
| **Action** *(futuro)* | Ação de acompanhamento vinculada a um Decision/Project. |
| **Knowledge** *(futuro)* | Camada de inteligência/conhecimento corporativo (Accelerator futuro, Release 0.3+). |
| **Bounded Context** | Um agrupamento coeso de entidades + regras que evolui junto (ex.: "Project Delivery" = Project + seus objetos de apoio). |
| **Consolidação** | Regra pela qual uma entidade pai deriva seus indicadores (contagem, progresso, saúde) a partir dos filhos reais, nunca de valores próprios estáticos. |

## 2. Hierarquia do Domínio

```
Portfolio   (Estratégia)      -- IMPLEMENTADO (Capability 01)
   ↓
Program     (Transformação)   -- IMPLEMENTADO (Capability 02)
   ↓
Project     (Execução)        -- IMPLEMENTADO (Capability 03)
   ↓
Demand                        -- NÃO INICIADO (Capability 04)
   ↓
Risk                          -- NÃO INICIADO
   ↓
Decision                      -- NÃO INICIADO
   ↓
Action                        -- NÃO INICIADO
   ↓
Knowledge                     -- NÃO INICIADO
```

**Diretriz Arquitetural Permanente** (reafirmada a cada Capability desde a 02): nenhuma entidade é implementada fora de ordem nesta cadeia. Cada nova Capability amplia exatamente um Bounded Context.

## 3. Entidades implementadas

Todas vivem em `web/lib/domain/` — camada de domínio de **frontend**, sem persistência em banco (ver §6). Todas seguem DDD desde a Capability 02: entidades são classes com invariante de construção e comportamento próprio, nunca dados anêmicos manipulados de fora.

### 3.1 Portfolio (`portfolio.ts`)

- **Atributos:** Identificação (id, name, code, description, category), Gestão (executiveOwner, strategicObjective, status, health, priority, datas), Indicadores (progressPercentage, programCount, projectCount, linkedDemands/Risks/Issues, pendingDecisions), Governança (sponsor, pmoOwner, lastUpdated, nextReview).
- **Invariante:** nenhum — é a raiz da cadeia.
- **Forma:** `interface` + array semeado (não é uma classe DDD — implementada antes da Diretriz Arquitetural Permanente contra modelos anêmicos, que só passou a valer a partir da Capability 02; não retrofitada, para não gerar refatoração sem justificativa, Decision Log D-014).
- **Não confundir com:** `lib/portfolio-intelligence/` (feature V1 real, priorização executiva por projeto — Decision Log D-012).

### 3.2 Program (`program.ts`)

- **Atributos:** Identificação (id, name, code, description), Gestão (**portfolioId — obrigatório**, sponsor, programManager, status, health, priority), Planejamento (objective, datas), Indicadores (progressPercentage, projectCount, linkedDemands/Risks/Issues, pendingDecisions, pendingActions), Governança (pmoOwner, lastUpdated, nextReview).
- **Invariante:** `Program.create()` recusa um Program sem `portfolioId`.
- **Comportamento:** `belongsToPortfolio()`, `isAtRisk()`, `isOverdue()`, `toProps()`.
- **Forma:** classe DDD (primeira entidade sob a nova diretriz, Decision Log D-014).

### 3.3 Project (`project.ts`)

- **Atributos:** Identificação (id, name, code, description), Organização (**programId — obrigatório**; **portfolioId é derivado**, nunca armazenado; sponsor, projectManager), Planejamento (objective, datas), Indicadores (progressPercentage e health encapsulados via método, não campo público; status, priority), Governança (lastUpdated, nextReview).
- **Objetos de apoio internos** (ainda não são entidades próprias): `Owner` (name, role), `Milestone` (name, dueDate, status), `Team` (size, leadName).
- **Invariante:** `Project.create()` recusa um Project sem `programId`.
- **Comportamento:** `belongsToProgram()`, `belongsToPortfolio(portfolioId, programs)` (deriva via o Program pai), `isOverdue()`, `isAtRisk()`, `completionPercentage()`, `health()`.
- **Não confundir com** (Decision Log D-019) — dois outros "Project" já existentes no código, nenhum compartilha ID:
  1. O `Project` real do backend (`src/database/models.py`, Épico 1) — persistido, hoje só usado para organização/membership.
  2. `ProjectSummary` (`lib/dashboard/types.ts`) — dado real do V1 (BFF), chaveado por `project_name` livre, usado pelo Cockpit "Projetos"/Risk Concentration/Health Distribution.
  Os três permanecem desconectados até o Épico 4 (unificação de `Project`).

## 4. Relacionamentos

```
Portfolio (1) ──< Program (N)     portfolioId obrigatório em Program
Program   (1) ──< Project (N)     programId obrigatório em Project
```

Nenhuma relação é uma foreign key real de banco — todas vivem como campo de domínio no frontend, validadas na construção (`.create()`), não no schema (§6).

## 5. Regra de Consolidação

Toda entidade pai deriva `count`/`progressPercentage`/`health` dos filhos reais, nunca de um valor próprio semeado:

- `consolidatePrograms(programs, projects)` (`project.ts`): Program deriva de seus Projects.
- `consolidatePortfolios(portfolios, programs)` (`program.ts`): Portfolio deriva de seus Programs.

Desde a Capability 03, a cadeia é **transitiva**: o Executive Cockpit primeiro consolida Program a partir de Project, e só então consolida Portfolio a partir desse Program já consolidado (`dashboard/page.tsx`) — nunca mais o valor semeado isolado de um nível intermediário.

**Saúde:** pior-caso (`worstHealth()`, `shared.ts`) — vermelho vence amarelo vence verde. **Progresso:** média aritmética simples dos filhos.

## 6. Estado de implementação (o que é real hoje)

- **Frontend (`web/lib/domain/`):** Portfolio, Program, Project existem como domínio real, com invariantes e comportamento, consumidos pelo Executive Cockpit, Program Management e Project Delivery.
- **Backend (`src/`):** **nenhuma migração, model ou tabela nova.** CLAUDE.md ("nunca criar arquitetura paralela, nunca duplicar código, nunca novo provider/registry") permanece integralmente respeitado. Este domínio é preparação estrutural, não persistência.
- **Quando o backend for wireado** (fora do escopo de qualquer Capability até aqui): os acessores `listPortfolios()`/`listPrograms()`/`listProjects()` são repository-shaped (assíncronos) exatamente para que só o corpo dessas 3 funções mude — nenhum hook, componente ou página precisa mudar.

## 7. Preparação para Capabilities futuras

- **Capability 04 (Demand):** deve repetir o mesmo padrão — invariante de vínculo obrigatório ao pai (`projectId` em Demand) e uma função de consolidação (`consolidateProjects(projects, demands)` ou equivalente).
- **Risk, Decision, Action, Knowledge:** ainda não modelados; a ordem da cadeia (§2) não deve ser pulada.
- **Architecture Review (AR-1):** o Founder recomendou uma pausa de uma iteração após a Capability 03 para validar a consistência do domínio antes de avançar para contextos mais complexos — não para refatorar, mas para checar.

## 8. Referências

- `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-001-Portfolio-Management.md`
- `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-002-Program-Management.md`
- `docs/product/capability-blueprints/DOMAIN-BLUEPRINT-CB-003-Project-Delivery.md`
- `docs/product/stratech-v2/DECISION-LOG.md` (D-011 a D-020+)
- `docs/architecture/adr/ADR-V2-009-frontend-domain-layer.md`
