# Domain Evolution Report — Wave 2 (Enterprise Platform)

**Data:** 2026-07-27 · Complementa `DOMAIN-MODEL.md` (referência viva do domínio) com a leitura evolutiva específica da Wave 2 — o que mudou no modelo de domínio, não apenas no código ao redor dele.

---

## 1. Quais Aggregates mudaram

### Portfolio / Program / Project
Nenhuma mudança na **forma** do Aggregate (atributos, invariantes, comportamento) — a mudança foi inteiramente de **onde vive o estado real**:
- Antes da Wave 2: Aggregates existiam só como classes de frontend sobre arrays semeados em memória.
- Depois da Wave 2 (Sprints 1 e 5): os mesmos Aggregates persistem em tabelas reais (`portfolios`, `programs`, `projects` estendida), lidos/escritos via API real. O invariante `Program.create()` recusa sem `portfolioId`, `Project.create()` recusa sem `programId` — preservados sem alteração; agora aplicados também no caminho de escrita do backend (`DomainRepository`, `CrossTenantViolationError`).
- A cadeia de consolidação transitiva (`consolidateFromChildren()`) não mudou.

### Project — identidade unificada (TD-008)
O Aggregate `Project` do domínio de Entrega (`web/lib/domain/project.ts`, Capability 03) não mudou. O que mudou foi o **outro** "Project" do backend (`src/database/models.py`, Épico 1): `project_id` passou de FK opcional coexistindo com uma coluna de nome livre para a **única chave de identidade** que toda a superfície de Intelligence usa — filtro, agrupamento, join, exibição. A entidade real (org/membership) e a projeção de inteligência (`ProjectIntelligenceSummary`) agora compartilham inequivocamente a mesma identidade (`project_id`), embora continuem sendo bounded contexts distintos (ver §2).

---

## 2. Quais entidades foram consolidadas

- **`ProjectSummary` (Dashboard/V1) + `WorkspaceSummary` (Workspace)** → **`ProjectIntelligenceSummary`** (`web/lib/project/intelligence-summary.ts`). Eram dois espelhos duplicados do mesmo read-model — a projeção de inteligência de um Project (`total_analyses`/`open_risks`/`pending_action_items`/`latest_health_status`), já ambos ancorados em `project_id` desde a Fase 3a (W3-1). A consolidação foi de-duplicação de tipo, não de arquitetura de domínio.
- **`ProjectSummaryService`/`ProjectSummaryResponse` (backend) NÃO foram consolidados nem renomeados** — foram explicitamente classificados como o *produtor* legítimo da projeção acima (projeção de leitura / serviço de composição), não como um modelo de domínio paralelo a fundir com nada (Decisão 2 do Founder, D-060). Uma decisão de **não-consolidação deliberada**, registrada para não ser reaberta por engano no futuro.
- **Rejeitado explicitamente:** fundir `ProjectIntelligenceSummary` com a entidade de Entrega `Project` (`lib/domain/project.ts`). São bounded contexts diferentes (Intelligence read-model vs. Delivery aggregate) — a fusão teria sido conflação de bounded contexts, perdendo os agregados analíticos e misturando identidades. Consolidar ≠ fundir.

---

## 3. Quais conceitos deixaram de existir

- **`ProjectSummary` e `WorkspaceSummary`** como tipos de frontend — removidos por completo (D-059).
- **`analysis_records.project_name`** como coluna de banco e campo de ORM — removida (migração 0015, D-061). Era o último lugar onde o "nome" ainda podia, em teoria, funcionar como uma chave alternativa ao `project_id`.
- **"Workspace" como possibilidade de entidade administrável** — nunca chegou a existir como código, mas deixou de existir como *possibilidade em aberto* no roadmap: a auditoria de D-055 provou que nenhum critério DDD (identidade, invariante, ciclo de vida, relacionamento, responsabilidade de negócio) se aplica ao termo — ele permanece exclusivamente vocabulário de apresentação (a View `/workspace/:projectName` e, por metonímia herdada, a sessão de autenticação Nível 1).
- **A suposição de que "Sessão" e "API Keys" eram capacidades já parcialmente existentes** — ambas as premissas de Blueprints anteriores (`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` original) foram corrigidas: nenhum store de sessão existia; API Keys nunca dependeu de fato do Integration Hub.

---

## 4. Quais novos princípios passam a reger o domínio

1. **`project_id` é a identidade técnica única do Project; `project_name`/`Project.name` é exclusivamente apresentação.** Regra permanente daqui em diante para qualquer novo consumidor de Project — nunca introduzir um segundo caminho de resolução por nome como chave.
2. **Uma projeção de leitura (read-model) sobre um Aggregate nunca deve ser fundida com o próprio Aggregate**, mesmo quando ambos compartilham identidade (`project_id`). `ProjectIntelligenceSummary` e o `Project` de Entrega provam essa distinção na prática — a mesma identidade, dois bounded contexts, nunca um objeto único.
3. **Nem toda tela ou conceito de vocabulário de produto é uma entidade de domínio.** Critério DDD explícito (identidade + invariantes + ciclo de vida + relacionamentos + responsabilidade de negócio) deve ser satisfeito antes de qualquer promoção — "Workspace" é o primeiro caso registrado formalmente de um termo **rejeitado** como entidade após auditoria (D-055), estabelecendo o precedente para o próximo candidato duvidoso.
4. **Migração de identidade em produção segue aditiva-primeiro/destrutiva-por-último, nunca em um único passo.** TD-008 Fase 3b prova o padrão: 5 etapas incrementais, cada uma verde de ponta a ponta, com a etapa destrutiva final exigindo prova de reversibilidade (downgrade com restauração de dados) **antes** da aprovação, não depois.
5. **A cadeia de domínio (Portfolio → Program → Project → [Demand → Risk → Decision → Action → Knowledge, futuros])** permanece a única ordem permitida de expansão — nenhuma Capability futura pula um nível, princípio reafirmado sem exceção durante toda a Wave 2.

---

## 5. Estado do domínio ao final da Wave 2

```
Portfolio   (Estratégia)      -- IMPLEMENTADO, persistido (Sprint 1), servido por API real (Sprint 2/5)
   ↓
Program     (Transformação)   -- IMPLEMENTADO, persistido, servido por API real
   ↓
Project     (Execução)        -- IMPLEMENTADO, persistido, servido por API real
   ↓                              + identidade única (project_id) na superfície de Intelligence (TD-008 resolvido)
Demand                        -- NÃO INICIADO (Capability 04, próxima na cadeia)
   ↓
Risk / Decision / Action / Knowledge -- NÃO INICIADOS
```

Nenhuma entidade foi implementada fora de ordem durante a Wave 2 — a Diretriz Arquitetural Permanente (`DOMAIN-MODEL.md` §2) permanece integralmente respeitada.
