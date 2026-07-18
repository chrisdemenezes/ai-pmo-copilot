# ADR-V2-009: Portfolio/Program/Project as a Frontend Domain Layer (DDD, Pre-Persistence)

- **Status:** Accepted
- **Date:** 2026-07-18
- **Context layer:** Implementação (per the 4-layer model of the Enterprise Architecture Blueprint v2.0)

**Nota de numeração:** o próximo ID livre em sequência seria `ADR-V2-008`, mas esse número já está reservado em prosa (`STRATECH-V2-Architecture-Evolution-Proposal.md`, Revisão 2 §R2.3) para a extensão do Domain Map com Demand/Resource/Issue/Change Request, proposta ao Founder e nunca formalmente autorizada nem criada como arquivo. Para não colidir com uma decisão pendente (a própria árvore de ADRs já tem uma colisão não resolvida em `ADR-V2-004`, ver `docs/architecture/adr/NORMALIZATION-PLAN.md`), esta ADR usa `ADR-V2-009`. Registrado aqui para rastreabilidade, não decidido unilateralmente.

## Contexto

A partir da Capability 01 (Release 0.2), o Founder autorizou implementar Portfolio, Program e Project como entidades reais de domínio, formando a cadeia Portfolio → Program → Project → Demand → Risk → Decision → Action → Knowledge — mas explicitamente instruiu manter o backend mockado nesta fase e preservar a arquitetura RC-1 (nenhuma migração, model ou provider novo em `src/`).

## Problema

Sem uma decisão explícita, cada Capability poderia reinventar sua própria convenção de "o que é uma entidade de domínio" — arriscando exatamente o tipo de inconsistência que a Diretriz Arquitetural Permanente (DDD, anti-modelo-anêmico, introduzida na Capability 02) existe para prevenir.

## Alternativas consideradas

1. **Persistir Portfolio/Program/Project no backend desde já** (migração real em `src/database/`) — rejeitada: o Founder explicitamente pediu backend mockado nesta fase, e a Release 0.1 (Épicos 3-6) ainda não está completa; adiantar uma migração de banco agora romperia o sequenciamento já aprovado do Release Roadmap.
2. **Modelar como dados simulados simples (interfaces + arrays), sem comportamento** — rejeitada a partir da Capability 02: viola a Diretriz Arquitetural Permanente contra modelos anêmicos.
3. **Camada de domínio de frontend com classes DDD-lite (invariante de construção + comportamento) e acessores repository-shaped (assíncronos)** — **escolhida**. Permite ao domínio ser correto e testável agora, e trocar a implementação por uma chamada real de backend depois sem alterar nenhum consumidor.

## Decisão

- `web/lib/domain/{portfolio,program,project}.ts`: cada entidade (a partir de Program) é uma classe com `static create()` validando o invariante de vínculo ao pai (`portfolioId`/`programId` obrigatório) e métodos de comportamento (`belongsToPortfolio`, `isAtRisk`, `isOverdue`, etc.).
- `web/lib/domain/shared.ts`: vocabulário comum (`DomainHealth`/`DomainStatus`/`DomainPriority`/`worstHealth`), evitando duplicação entre entidades.
- Cada entidade pai deriva seus indicadores agregados (`count`/`progressPercentage`/`health`) dos filhos reais via uma função de consolidação (`consolidatePortfolios`, `consolidatePrograms`) — nunca de um valor próprio semeado, tornando o rollup transitivo por toda a cadeia.
- `listPortfolios()`/`listPrograms()`/`listProjects()` são assíncronos e retornam de dados semeados em memória hoje, mas com o mesmo contrato que uma chamada real ao BFF teria.
- Nenhuma alteração em `src/` — CLAUDE.md ("nunca criar arquitetura paralela, nunca duplicar código, nunca novo provider/registry") permanece integralmente respeitado.

## Justificativa

- Cumpre a instrução explícita do Founder (backend mockado nesta fase, RC-1 preservado) sem sacrificar a correção do domínio.
- A Diretriz Arquitetural Permanente (DDD) é satisfeita sem esperar por persistência real — o comportamento e os invariantes já existem hoje, testados.
- O contrato assíncrono dos acessores elimina o custo de retrabalho quando a Release 0.2 eventualmente wireia um backend real: troca-se o corpo de 3 funções, não os hooks/componentes que as consomem.

## Consequências

- **Positivas:** Executive Cockpit, Program Management e Project Delivery já consomem um domínio consistente e comportamental, não dados soltos; a base está pronta para a Capability 04 (Demand) repetir exatamente o mesmo padrão.
- **Negativas / dívida assumida:** três entidades chamadas "Project"/"Portfolio" coexistem no código com significados diferentes (este domínio, `ProjectSummary` do V1, e o `Project` real do backend do Épico 1) — risco de confusão documentado explicitamente (Decision Log D-012, D-019) para mitigar, não eliminar, até a unificação do Épico 4.
- **Impacto futuro:** quando o backend for wireado para Portfolio/Program/Project, esta ADR deve ser revisitada — a escolha de "backend mockado" foi condicionada à fase atual (Release 0.1 ainda incompleta), não permanente.
