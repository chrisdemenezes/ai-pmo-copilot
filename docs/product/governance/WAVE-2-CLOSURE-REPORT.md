# Wave 2 Closure Report — STRATECH Enterprise Platform

**Data:** 2026-07-27 · **Missão:** Wave Closure Review (encerramento formal da Wave 2, antes do planejamento da Wave 3)
**Referências:** `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §4 (escopo original) · `DECISION-LOG.md` D-030 a D-061 · `WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md` (auditoria retrospectiva completa)

---

## 1. Objetivos originalmente definidos para a Wave 2

Per `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §4 ("Wave 2 — Enterprise Platform"), a Wave 2 tinha três Epics:

1. **4.1 Enterprise Identity** — Roles, Permissions, Authorization (enforcement), Organization Scope. Policies/Claims explicitamente **não adotados** (evitar segunda arquitetura de autorização, per CLAUDE.md).
2. **4.2 Enterprise Administration** — escopo em disputa desde a abertura da Wave (Decision Proposal, §9): "administração mínima" já aprovada (Épico 5/EO-016: Org/User/Role/Project + auditoria de mutações) vs. escopo completo pedido pela missão de reconciliação (Usuários, Organizações, Workspaces, Convites, Papéis, Permissões, Sessões, API Keys, Configurações, Segurança, Auditoria, Health, Logs, Tenant Settings, System Settings).
3. **4.3 Enterprise Domain** — Portfolio, Program, Project como domínio real, com persistência e resolução da tríplice duplicidade "Project" (TD-008).

---

## 2. Itens implementados

| # | Item | Sprint/Item | Decisão |
|---|---|---|---|
| 1 | Persistência real de Portfolio/Program/Project | Sprint 1 | D-032 |
| 2 | Enterprise API Layer (9 rotas, OpenAPI) | Sprint 2 | D-033 |
| 3 | RBAC fine-grained enforcement | Sprint 3 | D-034 |
| 4 | Enterprise Administration Nível 1+2 (Org/User/Role/Auditoria/Logs/Segurança) | Sprint 4 | D-035 |
| 5 | Frontend migrado para a API real (seed no banco, demo user com `viewer`) | Sprint 5 | D-036 |
| 6 | PostgreSQL oficial; suíte migrada de SQLite | RC-2 | D-037 |
| 7 | Capability User Management (CRUD, ativação, RBAC, auditoria) | Encerramento | D-038 |
| 8 | Event Foundation (`EventEmitter`/`NoOpEventEmitter`, 5 eventos de domínio) | Retrospectivo item 1 | D-049 |
| 9 | TD-004/005/006 (race de invalidação do React Query, 3 painéis) | Retrospectivo item 2 | D-050 |
| 10 | API Keys (Nível 1, reclassificado — autentica como o usuário criador) | Retrospectivo item 3 | D-051 |
| 11 | Sessões server-side (revogação real, resolve TD-010) | Retrospectivo item 5 | D-053 |
| 12 | Convites (domínio desacoplado de e-mail via `NotificationProvider`) | Retrospectivo item 6 | D-054 |
| 13 | TD-008 Fase 3b completa (Etapas 1, 2, 3, 5, 4a, 4b) — `project_id` é a única chave de acesso ao Project | Retrospectivo item 8 | D-056 a D-061 |

**Nota sobre item 8 (TD-008):** originalmente atribuído à Wave 2 (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §4.3/§11), sua Fase 3a foi executada durante a Wave 3 (Epic W3-1, D-040) e sua Fase 3b (a maior parte do trabalho) durante o Wave Completion Review retrospectivo — mas o item pertence à Wave 2 por origem, não à Wave 3 por cronologia. Por isso está listado aqui, não no relatório de encerramento de uma Wave 3 (que segue em andamento).

---

## 3. Itens reclassificados como Governança

Item auditado, natureza esclarecida, formalmente documentado — **sem código produzido**, porque a auditoria concluiu que não há requisito de engenharia pendente:

| Item | Decisão | Classificação final |
|---|---|---|
| Configurações da Organização (preferências funcionais) | D-052 | **Sem Escopo Funcional Definido** — nenhum documento oficial especifica qualquer campo concreto; não é bloqueio arquitetural nem de negócio, é ausência de requisito de produto |
| Workspaces administrativos (entidade) | D-055 | **Governança Concluída** — "Workspace" é termo de apresentação (View/UI `/workspace/:projectName` + sinônimo herdado de sessão), nunca uma entidade de domínio; construí-la seria arquitetura paralela |

---

## 4. Itens classificados como Business Pending

| Item | Decisão | Depende de |
|---|---|---|
| Tenant/System Settings (modelo comercial SaaS: planos, billing, isolamento por cliente pagante) | D-052 | As 7 perguntas sem resposta de `BUSINESS-MODEL-BLUEPRINT.md` §2 — decisão de negócio do Founder, nunca respondida em nenhum documento. Se a resposta à pergunta 1 for "não", o conceito deixa de existir, não fica apenas adiado. |
| Escolha de um provedor de notificação concreto (SMTP/SES/etc., para Convites) | D-054 | Decisão de negócio/modelo de comunicação (Wave 6) — não bloqueia o domínio de Convites, que é plenamente funcional sem ele (`NoOpNotificationProvider`) |
| Nomenclatura backend `ProjectSummaryResponse`/`ProjectSummaryService` (manter vs. renomear) | D-060 | Decidido pelo Founder na própria Etapa 4a: **manter** — classificados como projeção de leitura/serviço de composição, não modelos de domínio paralelos |

---

## 5. Débitos técnicos encerrados

Ver `TECHNICAL_DEBT.md` §"Classificação Final — Wave 2 Closure Review" para a tabela completa. Resumo:

- **TD-004/005/006** (race de invalidação do React Query) — Resolvido, D-050.
- **TD-007** (Portfolio/Program/Project sem persistência) — Resolvido, Wave 2 Sprint 1 (D-032).
- **TD-008** (três conceitos "Project") — Resolvido, D-061. O único débito cuja resolução exigiu uma migração destrutiva (`0015`), executada sob gate explícito do Founder em duas etapas (4a aditiva, 4b destrutiva), com downgrade íntegro provado em PostgreSQL real.
- **TD-010** (sem armazenamento server-side de sessão) — Resolvido, D-053.

## 6. Débitos técnicos remanescentes

| TD | Classificação | Por quê não bloqueia a Wave 3 |
|---|---|---|
| TD-001 (FK não aplicadas em SQLite) | Postergado | Gatilho ("qualquer DELETE exposto") auditado nesta revisão — os 4 `DELETE` reais são revogações de registros-folha, nenhum aciona o cenário de órfãos; Postgres (ambiente oficial) já aplica FK por padrão |
| TD-002 (Delete Policy indefinida) | Postergado | Mesma auditoria — nenhum `DELETE` real de entidade com filhos por FK existe hoje |
| TD-003 (convenção de sessão do Repository) | Postergado | Cresceu ao longo de toda a Wave 2 sem incidente registrado; baixo risco, baixo esforço |
| TD-009 (cobertura de frontend não instrumentada) | Futuro Roadmap | Lacuna de instrumentação, não um risco ativo — candidato à Wave 5 (Observabilidade) |

**Nenhum item bloqueia o início da Wave 3.**

---

## 7. Decisões arquiteturais relevantes

- **D-030:** Épicos e Capabilities deixam de ser eixos paralelos; Waves passam a ser o único eixo de planejamento.
- **D-034:** premissa de schema do RBAC Blueprint corrigida (`user_roles` não precisa de `organization_id` — `users.organization_id` já é FK única).
- **D-035:** premissa de "Sessões ser extensão de baixo risco" corrigida (não existia store server-side algum).
- **D-048 (Superseding Decision — Wave Completion Policy):** revoga toda decisão anterior que permitia declarar uma Wave concluída com Epics/Capabilities/Enterprise Analysts previstos pendentes, tratados como Decision Proposal "que não bloqueia o fechamento". Esta é a decisão-mãe que tornou este próprio Closure Review possível e necessário — sem ela, a Wave 2 teria permanecido formalmente "encerrada" (D-038) com 6 gaps reais não endereçados.
- **D-051 (princípio permanente):** nenhum componente fundamental pode depender da existência de um componente futuro; o inverso é sempre permitido. Corrigiu a classificação artificial de API Keys como dependente do Integration Hub.
- **D-055:** critério DDD explícito para nunca promover uma tela a entidade de domínio sem identidade/invariantes/ciclo de vida/relacionamentos/responsabilidade de negócio próprios.
- **D-056–D-061 (TD-008):** migração dual-key aditiva-primeiro/destrutiva-por-último como padrão de referência para toda futura mudança estrutural que remova uma coluna/chave em produção — 5 etapas, cada uma testada e commitada separadamente, com 2 gates de aprovação explícita do Founder antes de qualquer operação irreversível.

---

## 8. Riscos residuais

1. **TD-001/002 (SQLite FK/Delete Policy):** risco real, mas hoje confinado ao fallback de instalação zero-dependência. Se um `DELETE` de Organization/User/Project for exposto no futuro, este TD deve ser resolvido antes, não em paralelo.
2. **Tenant/System Settings em Business Pending indefinido:** se a Wave 6 nunca receber uma decisão de modelo de negócio do Founder, este conceito nunca se materializa — não é um risco técnico, mas um risco de produto que a documentação já torna explícito.
3. **Nenhum risco de segurança residual conhecido:** o Security Hardening Gate (C-1 RBAC em `intelligence.py`, C-2 Tenant Isolation em `AnalysisRecord`) foi fechado antes desta Wave (D-045), fora do escopo da Wave 2 mas relevante por tocar as mesmas tabelas que TD-008 modificou.

---

## 9. Lições aprendidas

1. **Encerrar uma Wave sem uma auditoria retrospectiva explícita permite gaps invisíveis.** A Wave 2 foi declarada "100% completa" em D-038 — e essa declaração não sobreviveu ao escrutínio da nova Wave Completion Policy (D-048), que encontrou 6 gaps reais (API Keys, Tenant/System Settings, Sessões, Convites, Workspaces, TD-008 Fase 3b). O padrão que emerge desta Wave: **a auditoria retrospectiva deveria ser parte do próprio critério de encerramento**, não uma correção posterior.
2. **"Dependência arquitetural" e "decisão de negócio pendente" são categorias diferentes e devem ser tratadas de forma diferente.** API Keys parecia bloqueada por dependência (Integration Hub) — auditoria provou que era arquitetural e artificial, corrigível imediatamente (D-051). Tenant/System Settings parece semelhante, mas é genuinamente uma decisão de negócio nunca tomada (D-052) — não corrigível por arquitetura. Confundir as duas categorias leva a adiar o que poderia ser resolvido, ou a inventar solução para o que não deveria ser resolvido sem decisão do Founder.
3. **Migração destrutiva de produção se beneficia de divisão em aditiva-primeiro/destrutiva-por-último com gates explícitos.** TD-008 Fase 3b (5 etapas + 2 gates) é o primeiro caso real desse padrão na STRATECH — zero incidente, rollback comprovado em banco real antes de qualquer aprovação da etapa irreversível. Candidato a padrão de referência documentado (`WAVE-2-CLOSURE-REPORT.md` §7 acima).
4. **Documentação viva tem drift silencioso se não for auditada contra o código periodicamente.** `DOMAIN-MODEL.md` §6 descreveu "nenhuma persistência" por múltiplas Sprints depois de a persistência real já existir — encontrado e corrigido apenas nesta revisão de encerramento (ver `WAVE-2-GOVERNANCE-REVIEW.md`).
5. **"Nem toda tela é uma entidade" e "nem toda dependência é técnica" são o mesmo princípio aplicado duas vezes:** nunca inventar arquitetura para preencher uma lacuna de decisão — nem uma entidade de domínio (Workspace), nem um mecanismo de autorização (Policies/Claims), nem um provedor concreto (e-mail, backend de eventos).

---

## 10. Readiness Assessment para Wave 3

Avaliação de bloqueadores técnicos, arquiteturais e documentais para o início da Wave 3 (Enterprise Intelligence):

| Dimensão | Bloqueador encontrado? | Evidência |
|---|---|---|
| **Técnico** | Não | Suíte completa verde: `ruff` limpo, `pytest` 450 passando, `tsc`/`eslint` limpos, `vitest` 491 passando, Playwright E2E 292 passando (2 skipped, ambos o mesmo teste mobile-only pré-existente, sem relação com qualquer item desta Wave). |
| **Arquitetural** | Não | Nenhum débito técnico remanescente bloqueia (TD-001/002/003 Postergados sem gatilho disparado; TD-009 Futuro Roadmap sem risco ativo). `project_id` como identidade única do Project remove a última ambiguidade estrutural que a Wave 3 (Intelligence sobre Project) herdaria. |
| **Documental** | Não (1 drift corrigido nesta revisão) | `DOMAIN-MODEL.md` §6 estava desatualizado (descrevia "nenhuma persistência" quando a persistência real já existia desde a Sprint 1/5) — corrigido nesta revisão. Decision Log, Mission Control, CHANGELOG, Technical Debt Register e os Blueprints de Wave 2 (`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §0/§0.1/§0.2) auditados e confirmados consistentes com o código atual (ver `WAVE-2-GOVERNANCE-REVIEW.md`). |
| **Governança** | Não | Wave Completion Policy (D-048) satisfeita: 100% dos Epics/Capabilities originalmente previstos para a Wave 2 estão implementados, reclassificados como Governança Concluída, ou formalmente registrados como Business Pending — nenhum permanece como Decision Proposal aberto sem status rastreável. |

### Declaração formal

> **"Wave 3 Ready."**

Nenhum bloqueador técnico, arquitetural, documental ou de governança impede o início do planejamento executivo da Wave 3. A Wave 2 (Enterprise Platform) está formalmente encerrada.
