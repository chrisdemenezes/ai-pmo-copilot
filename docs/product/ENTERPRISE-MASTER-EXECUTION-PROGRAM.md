# STRATECH Enterprise Master Execution Program

**Status:** Fonte única oficial de planejamento, arquitetura, execução e evolução da STRATECH V2, a partir desta missão. Substitui a visão dupla de "Épicos" + "Capabilities" como linhas paralelas de evolução — ambas passam a ser rótulos históricos dentro de uma única estrutura de **Waves**.
**Data:** 2026-07-18
**Autor:** Claude / Principal Software Architect, Enterprise Architect, Product Architect, Program Manager
**Precondição:** RC-2 Enterprise Certification (Phase 1 encerrada), Phase 2 Foundation Architecture (aprovada conceitualmente) e Phase 2 Foundation Technical Design (produzido) — nenhum dos três é alterado por este documento.

**Regras de reconciliação seguidas neste documento (mandato da missão):**
- Nenhuma decisão arquitetural já aprovada foi alterada.
- Product Constitution, Foundation Architecture, Foundation Technical Design, Decision Logs aprovados e Technical Debts existentes **não foram modificados** — apenas referenciados/cruzados.
- Nenhuma arquitetura nova foi criada. Onde a missão pediu detalhe de implementação para algo sem nenhum Blueprint/ADR/Technical Design existente (a maior parte das Waves 3-6), este documento **declara o gap explicitamente** em vez de inventar a arquitetura — inventar violaria a própria regra da missão.
- Nenhum documento existente foi reescrito — `TECHNICAL_DEBT.md` e `DECISION-LOG.md` ganham apenas uma coluna/seção de referência cruzada, de forma aditiva (mesma convenção "append-only" já em uso).

---

## 0. Reconciliação — o que foi encontrado na revisão completa

Revisão integral realizada nesta missão: Product Constitution, Foundation Architecture, Foundation Technical Design, Master Roadmap (11 seções), Mission Control, Product Pulse, Decision Log (D-001 a D-029, íntegro), Technical Debt Register (TD-001 a TD-009 + Baseline Defects, íntegro), os 6 Épicos do Release 0.1, as 3 Capabilities do Release 0.2, o Sprint 1, e a árvore de ADRs.

### Duplicidades encontradas

| Duplicidade | Onde | Tratamento neste documento |
|---|---|---|
| **Épicos vs. Capabilities** como duas linhas de evolução paralelas (D-010, D-016) | Master Roadmap §5 (Épicos) vs. Mission Control `CAPABILITY_PROGRESS` | Eliminada — ver Seção 1. Ambas viram itens dentro das Waves, nunca mais eixos separados. |
| **"Project" (3 conceitos)** — backend real (Épico 1), `ProjectSummary` (V1), domínio `Project` (Capability 03) | TD-008, D-019 | Não resolvida por este documento (é uma decisão de implementação, Épico 4) — mas formalmente vinculada a Wave 2 com gate explícito (ver Seção 3.3 e Decision Proposal, Seção 9). |
| **"Riscos" de portfólio vs. Risk Intelligence de IA** | D-005/D-009 | Já resolvida (documentada, sem sobreposição de código) — apenas referenciada, não re-decidida. |
| **"Portfolio" (V2) vs. "Portfolio Intelligence" (V1)** | D-012 | Já resolvida — apenas referenciada. |
| **Risco de um "Enterprise Memory" (Wave 3) colidir com "Executive Memory" (V1, já em produção)** | Novo, identificado nesta revisão | Sinalizado na Seção 5 (Wave 3) — mesmo padrão de D-005/D-009/D-012/D-019: nomes próximos, conceitos que devem permanecer distintos por decisão explícita, não por acidente. |

### Inconsistências encontradas

- **ADR-V2-004** reivindicado por dois documentos distintos (colisão pré-existente, já registrada no Master Roadmap §10 e nunca resolvida). Não resolvida aqui — fora do escopo desta missão (não é uma decisão de programa, é uma limpeza de numeração pendente do Founder).
- **Rótulo "RC-1/RC-2"** usado em dois sentidos diferentes no repositório: (a) tags `v1.0.0-rc.1/rc.2` (V1, produto anterior encerrado); (b) "RC-2 Enterprise Certification" (V2, esta missão de Phase 2). Já sinalizado durante a missão RC-2; mantido como está, apenas re-registrado aqui para não se perder na consolidação.
- **"Release 0.x" vs. "Phase 1/Phase 2"**: a Executive Directive de Phase 2 assumiu que Phase 2 reorganiza as Releases 0.3-0.5, mas isso nunca foi formalmente confirmado (D-028, Roadmap Reconciliation note). Este documento **resolve essa reconciliação** — ver Seção 1.

### Dependências, lacunas, sobreposições, itens órfãos, documentos obsoletos

- **Dependências:** já mapeadas corretamente no Master Roadmap §3/§5 (ex.: Épico 3 depende do Épico 2, Épico 4 depende do Épico 3) — reaproveitadas sem alteração nas Waves.
- **Lacunas:** Waves 3-6 desta missão pedem componentes (Model Registry, Vector Store, RAG, 8 Enterprise Agents nomeados, Licensing, Billing, Marketplace, White Label) que **não têm nenhum Blueprint, ADR, proposta ou menção prévia em nenhum documento aprovado da STRATECH**. Isso não é uma lacuna de execução — é uma lacuna de **decisão de arquitetura e de modelo de negócio** que antecede qualquer planejamento de Sprint. Detalhado por Wave nas Seções 5-8.
- **Itens órfãos:** nenhum artefato de governança encontrado sem dono ou sem referência — a disciplina de EO→ADR/TDS→Architecture Review→PR→merge (LL-002) manteve rastreabilidade completa até aqui.
- **Documentos obsoletos:** nenhum documento aprovado foi considerado obsoleto — inclusive os artefatos "RC-1" da V1 continuam válidos como registro histórico do produto anterior (nunca reescritos, apenas re-contextualizados no README, per RC-2).

---

## 1. A reconciliação Épico/Capability → Wave (fim da linha dupla)

A partir deste documento, **não existe mais uma sequência de Épicos e uma sequência de Capabilities evoluindo em paralelo.** Todo Épico e toda Capability já existente é reclassificado como um item **dentro** de uma Wave — a Wave é o único eixo de planejamento daqui em diante.

| Item histórico | Era rotulado como | Wave |
|---|---|---|
| Schema Foundation | Épico 1 | Wave 1 |
| Identity Foundation | Épico 2 | Wave 1 |
| Phase 2 Foundation Architecture + Technical Design (API/Persistence/Org Scoping/RBAC/Event) | "Phase 2 Foundation Architecture" (fora da numeração de Épico) | Wave 1 |
| Organização e RBAC inicial | Épico 3 | Wave 2 |
| Projeto como entidade real | Épico 4 | Wave 2 |
| Auditoria e administração mínima | Épico 5 | Wave 2 (⚠️ conflito de escopo — ver Seção 9) |
| Validação e documentação | Épico 6 | Transversal a todas as Waves (Definition of Done/Acceptance Gate, não uma Wave própria) |
| Portfolio Management | Capability 01 | Wave 2 |
| Program Management | Capability 02 | Wave 2 |
| Project Delivery | Capability 03 | Wave 2 |

**Reconciliação do Roadmap de Releases (resolve a nota de D-028):** as Releases 0.1/0.2 já executadas mapeiam para Wave 1 (0.1) e Wave 2 (0.2, parcial — Portfolio/Program/Project como domínio de frontend). As Releases 0.3 (AI Foundation) e 0.4 (Integration Hub) mapeiam para Wave 3 e Wave 4 respectivamente. A Release 0.5 (Event Orchestration) mapeia para Wave 4. Não existe hoje nenhuma Release aprovada equivalente à Wave 5 (Enterprise Analytics, além do que já está implícito no Executive Cockpit) nem à Wave 6 (Productization) — **essas duas Waves não têm um Release correspondente já aprovado**, o que é consistente com a lacuna de arquitetura/decisão de negócio identificada na Seção 0.

O rótulo "Release 0.x" não é apagado (permanece como registro histórico em `RELEASE-0.1.md`, PRs e tags) — passa a ser **referência de arquivo**, não mais o eixo de planejamento ativo. O eixo ativo é a Wave.

---

## 2. Estrutura das Waves — visão executiva

| Wave | Nome | Status agregado | % concluído | Bloqueia a próxima Wave? |
|---|---|---|---|---|
| 1 | Enterprise Foundation | Em andamento | Schema+Identity: 100%. Persistence/RBAC/Org Scoping/API/Event Foundation: Technical Design produzido, 0% implementado. | Sim — Wave 2 depende de Wave 1 completa (persistência real). |
| 2 | Enterprise Platform | Em andamento (parcial) | RBAC: 0% implementado (Technical Design existe). Administration: 0%, **escopo em conflito** (ver Seção 9). Domain (Portfolio/Program/Project): ~75% (frontend, sem persistência). | Sim — Wave 3 depende de RBAC + Domain unificado (Épico 4). |
| 3 | Enterprise Intelligence | Não iniciado, **sem Blueprint próprio** | 0% (3 de 12 Accelerators do AI-Accelerators-Map existem, mas sobre o modelo V1 antigo) | Sim — Wave 4/5 dependem de dados/eventos que a Wave 3 consome. |
| 4 | Enterprise Operations | Não iniciado (parcialmente já aprovado como Release 0.4/0.5) | 0% | Parcial — Wave 5 se beneficia, mas não depende estritamente. |
| 5 | Enterprise Analytics | Não iniciado como programa formal (Executive Cockpit já cobre parte) | ~15-20% (Dashboard/Executive Brief do RC-1) | Não. |
| 6 | Productization | **Sem nenhuma base aprovada** — decisão de modelo de negócio ainda não tomada pelo Founder | 0%, não planejável ainda | N/A — não é um bloqueio técnico, é um pré-requisito de decisão de produto/negócio. |

---

## 3. Wave 1 — Enterprise Foundation

Consolida toda a fundação técnica: Persistence, Schema, Migration, Identity, Authentication, Session, Organization, Multi-tenancy, Request Context, Repository Layer, API Foundation, Event Foundation, Clean Architecture, DDD, Hexagonal Architecture.

| Componente pedido pela missão | Grounding hoje | Fonte |
|---|---|---|
| Schema, Migration | ✅ Implementado (Épico 1) | `src/database/models.py`, Alembic, PR #39 |
| Identity, Authentication, Session | ✅ Implementado (Épico 2) | `src/services/identity/*`, `AuthService`, PR #41 |
| Organization, Multi-tenancy | ✅ Implementado (Épico 1) | `organizations`, `CrossTenantViolationError`, `EnterpriseRepository` |
| Request Context | ✅ Já construído, ainda não consumido por nenhuma rota | `src/api/identity_context.py` (`get_request_context`) |
| Repository Layer | ✅ Padrão estabelecido, a estender | `EnterpriseRepository`, `AnalysisRepository` |
| Persistence (Portfolio/Program/Project) | 📐 Technical Design produzido, não implementado | `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §2 |
| API Foundation | 📐 Technical Design produzido, não implementado | idem, §1 |
| Event Foundation | 📐 Technical Design produzido, não implementado | idem, §5 |
| Clean Architecture, DDD, Hexagonal | ✅ Já é a convenção seguida (routes=adapters, services=casos de uso, repositories=ports, domínio como classes DDD a partir da Capability 02) | ADR-V2-009, `DOMAIN-MODEL.md`, `ARCHITECTURE-BASELINE-RC2.md` |

**Definition of Done da Wave 1:** os 5 componentes do Foundation Technical Design implementados e testados (Persistence, Organizational Scoping, RBAC seam, API, Event seam), sem alterar nenhum comportamento existente — critérios de aceite já especificados item a item em `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §1.13/§2.13/§3.13/§4.13/§5.13, reaproveitados aqui sem duplicação.

**Sequenciamento interno (já definido, reaproveitado sem alteração):** Persistence → Organizational Scoping → RBAC → API → Event seams (`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §6).

---

## 4. Wave 2 — Enterprise Platform

### 4.1 Enterprise Identity (RBAC, Roles, Permissions, Policies, Claims, Authorization, Organization Scope)

| Componente pedido | Grounding hoje |
|---|---|
| Roles, Permissions | ✅ Tabelas existentes desde o Épico 1 (`roles`, `permissions`, `role_permissions`, `user_roles`), populadas, nunca aplicadas por rota alguma |
| Authorization (enforcement) | 📐 Technical Design produzido (`PermissionChecker` Protocol, `require_permission()`) — não implementado | `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4 |
| Organization Scope | 📐 Technical Design produzido | idem, §3 |
| **Policies** | ⚠️ Não existe hoje conceito de "Policy" distinto de "Permission" na STRATECH — introduzir um novo mecanismo de Policy ao lado de Roles/Permissions seria **criar uma segunda arquitetura de autorização**, proibido por CLAUDE.md. Mapeado para o vocabulário já desenhado (`resource.action`, ex. `program.read`), não como conceito novo. |
| **Claims** | ⚠️ Mesmo tratamento — a STRATECH usa RBAC relacional (roles→permissions), não claims-based auth. Adotar "Claims" duplicaria o propósito das tabelas já existentes. **Não adotado** — para não violar "nunca criar novo provider/registry" (CLAUDE.md). Se um caso de uso real exigir claims (ex.: federação externa), isso é uma decisão de ADR futura, não implícita nesta consolidação. |

Este sub-Wave reaproveita 100% do que já foi desenhado em `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4 (Épico 3). Nenhuma arquitetura nova.

### 4.2 Enterprise Administration

**Ver Decision Proposal, Seção 9 — conflito de escopo não resolvido silenciosamente.** A missão pede escopo completo (Usuários, Organizações, Workspaces, Convites, Papéis, Permissões, Sessões, API Keys, Configurações, Segurança, Auditoria, Health, Logs, Tenant Settings, System Settings); o que está aprovado até hoje (Release 0.1, Épico 5, EO-016) é "administração mínima" (telas básicas de Org/User/Role/Project + log de auditoria de mutações). Este documento não decide isso unilateralmente.

| Sub-item | Grounding hoje |
|---|---|
| Usuários, Organizações, Papéis, Permissões | ✅ Schema existe (Épico 1); UI/endpoints administrativos não existem |
| Auditoria (log de mutações) | ❌ Não implementado — Épico 5 |
| Sessões | ✅ Modelo existe (`SessionIdentity`, `stratech_session` cookie); painel administrativo de sessões não existe |
| Workspaces, Convites, API Keys, Tenant Settings, System Settings, Health, Logs | ❌ Nenhum conceito destes existe hoje na STRATECH — nem como schema, nem como Blueprint, nem como ADR. "Workspace" já é um termo de produto **diferente** (a página `/workspace/{project}` da V1) — reutilizá-lo para "Workspaces" administrativos (multi-workspace por organização) é uma nova decisão de domínio, coberta pela mesma nota do Master Roadmap §3.1 ("Workspace" não é um Programa/domínio separado hoje). |

### 4.3 Enterprise Domain (Portfolio, Program, Project)

| Componente | Grounding hoje |
|---|---|
| Portfolio | ✅ Implementado como domínio de frontend (Capability 01) |
| Program | ✅ Implementado como domínio de frontend, DDD (Capability 02) |
| Project | ✅ Implementado como domínio de frontend, DDD (Capability 03) — **mas coexiste com 2 outros conceitos "Project"** (TD-008) |
| **Eliminar duplicidade Project / Project Delivery** | 📐 Já endereçado no Foundation Technical Design (§2.9/§2.16): `projects_delivery` é desenhado como tabela **deliberadamente temporária**, com gate obrigatório antes de qualquer migração real de dados, até o Épico 4 decidir a unificação definitiva. Este documento reforça esse gate — não o resolve, porque resolver é uma decisão de implementação (Épico 4), não de consolidação de programa. |

**Consolidação transitiva já implementada e preservada sem alteração:** Project → Program → Portfolio (`consolidateFromChildren()`, `shared.ts`), documentada em `DOMAIN-MODEL.md`.

---

## 5. Wave 3 — Enterprise Intelligence

**Aviso explícito, per a própria regra da missão ("não criar arquitetura nova"):** nenhum dos componentes abaixo tem Blueprint, ADR, proposta ou Technical Design aprovado na STRATECH hoje, com exceção dos 3 AI Accelerators já em produção (V1) e do Event Map (taxonomia de referência). Esta seção **organiza o espaço-alvo** (a mesma função que uma Wave deve cumprir), mas **não projeta a arquitetura** de Model Registry, Vector Store, RAG ou dos 8 Enterprise Agents nomeados — fazer isso agora seria inventar arquitetura nova dentro de uma missão que proíbe exatamente isso.

### 5.1 AI Platform

| Sub-item | Grounding hoje |
|---|---|
| Prompt Registry | ✅ Existe — `src/prompts/registry.py` (`PromptRegistry`) |
| Provider Manager | 🟡 Parcial — `src/llm/providers/factory.py` seleciona 1 provider ativo por configuração; não é multi-model routing |
| Model Registry, Model Routing, Prompt Versioning, Cost Control, Token Analytics, AI Governance, AI Observability, Evaluation Framework | ❌ Nenhum existe. Nenhuma menção prévia em nenhum Blueprint/ADR. |

### 5.2 Knowledge Platform

| Sub-item | Grounding hoje |
|---|---|
| Document Intelligence | 🟡 Já aprovado como camada de referência (não GED nativo, ADR-V2-005), escopado para Release 0.4 — não implementado |
| Knowledge Base, Semantic Search, Vector Store, Embeddings, RAG, Context Manager | ❌ Nenhum existe, nenhuma menção prévia |
| **"Enterprise Memory"** | ⚠️ **Risco de colisão de nome com "Executive Memory"**, já real e em produção desde a V1 (insights "Mudou"/"Persistiu"/"Reapareceu" no Workspace/Dashboard, D-005 padrão de separação de conceitos). Se esta capability for desenhada no futuro, precisa de uma decisão explícita de nomenclatura antes do código, mesmo padrão já usado 4 vezes neste projeto (D-005/D-009/D-012/D-019) — sinalizado aqui preventivamente. |

### 5.3 Executive Intelligence

| Sub-item | Grounding hoje |
|---|---|
| Portfolio/Program/Project Intelligence | 🟡 Parcial — os 3 domínios existem (Wave 2), mas sem a camada de "intelligence" (insight de IA) sobre eles ainda |
| Risk Intelligence | ✅ Já existe como Accelerator real (`risk_review` agent) — **distinto** do conceito "Riscos" de portfólio (D-005) |
| Decision Intelligence, PMO Intelligence, Governance Intelligence, Executive Briefing | ❌ Nenhum existe |

### 5.4 Enterprise Agents

| Sub-item | Grounding hoje |
|---|---|
| Executive Advisor, Strategy Advisor, PMO Advisor, Portfolio Advisor, Delivery Advisor, Governance Advisor, Risk Advisor, Document Advisor | ❌ **Nenhum existe.** A STRATECH tem hoje 3 agentes de propósito único (`project_status`, `risk_review`, `meeting_intelligence`), construídos diretamente sobre `LLMProvider` + `PromptRegistry`, sem framework de orquestração multi-agente. Introduzir 8 "Advisors" nomeados é uma decisão de arquitetura de produto inteiramente nova, sem precedente em nenhum documento aprovado. |

**Pré-requisito explícito para a Wave 3 sair do papel:** um Domain Blueprint (mesmo padrão de CB-001/002/003) e uma Architecture Review dedicados à "Enterprise Intelligence", antes de qualquer Technical Design — este documento não substitui essa etapa, apenas identifica que ela ainda não existe.

---

## 6. Wave 4 — Enterprise Operations

| Sub-item | Grounding hoje |
|---|---|
| Event Bus | 🟡 Taxonomia de referência existe (Event Map), seam de emissão desenhado (`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §5, `NoOpEventEmitter`) — barramento real não existe. Aprovado como Release 0.5. |
| Integrations | 🟡 Aprovado como Release 0.4 (Integration Hub) — não implementado |
| Workflow Engine, Automation | 🟡 Aprovado em princípio (ADR-V2-007, human-in-the-loop obrigatório) — motor de workflow não existe |
| Scheduler, Notifications, Background Workers, API Gateway | ❌ Nenhum existe, nenhuma menção prévia — FastAPI é chamado diretamente, sem gateway |
| Monitoring, Observability, Telemetry | 🟡 Descrito como camada transversal do Blueprint ("Data & Observability"), 0% medido — TD-009 (cobertura de testes frontend) é o único item concreto de observabilidade hoje |

---

## 7. Wave 5 — Enterprise Analytics

| Sub-item | Grounding hoje |
|---|---|
| Executive Cockpit | ✅ Existe — `/dashboard`, KPIs reais (Capabilities 01-03) |
| Portfolio/Program/Project Analytics | 🟡 Parcial — os cálculos de consolidação (`consolidateFromChildren`) já são uma forma primitiva disso |
| Strategic/Operational Indicators | 🟡 Já existem **como documento de governança** (Master Roadmap §Executive Dashboard, §8 Product Maturity Model) — nunca surfaced como tela de produto. Oportunidade futura (não decidida aqui): expor esses indicadores no próprio Mission Control em vez de apenas em Markdown. |
| Operational Cockpit, AI Analytics, Audit Analytics | ❌ Não existe. Audit Analytics depende de Auditoria (Wave 2/Épico 5) existir primeiro. |

---

## 8. Wave 6 — Productization

**Nenhum item desta Wave tem qualquer base aprovada.** A STRATECH Product Constitution (V1) e o Enterprise Architecture Blueprint (V2) descrevem a STRATECH como uma plataforma de PMO — inicialmente single-tenant (V1), evoluindo para multi-organização (V2) — **em nenhum momento como um produto comercial multi-cliente com cobrança, licenciamento ou marketplace**. Licensing, Billing, Marketplace, Customer Success, White Label, Feature Flags, Subscription, Usage Analytics não têm precedente em nenhum documento aprovado.

| Sub-item | Grounding hoje |
|---|---|
| Versioning, Release Management | ✅ Existe como **processo de engenharia** (EO→ADR/TDS→Architecture Review→PR→merge, LL-002) — não como capability de produto voltada a clientes externos |
| Licensing, Billing, Marketplace, Customer Success, White Label, Feature Flags, Subscription, Usage Analytics | ❌ Zero grounding |

**Esta Wave não é apenas "não implementada" — ela não é sequer planejável hoje**, porque requer uma decisão de modelo de negócio (a STRATECH se torna um produto comercial multi-cliente?) que pertence exclusivamente ao Founder e precede qualquer arquitetura. Registrar isso como Wave 6 é apropriado (mantém uma estrutura única, per o objetivo da missão), mas este documento não avança nenhum detalhe além de nomear o espaço.

---

## 9. Decision Proposal — Enterprise Administration: escopo mínimo vs. completo

Per a própria instrução da missão ("Caso exista conflito arquitetural, produzir Decision Proposal antes da implementação"), este é exatamente esse caso.

**Contexto:** o Release 0.1 (aprovado via EO-016/EO-016A, `Release-0.1-Macro-Backlog.html`, `RELEASE-0.1.md`, Master Roadmap §5/§6) define o Épico 5 como **"Auditoria e administração mínima"**: log de auditoria de mutações de Org/User/Role/Project + telas administrativas mínimas sob um item de navegação "Administração". Este é o único compromisso já aprovado pelo Founder para esta área.

A missão atual pede: "Implementar completamente. Não utilizar conceito de administração mínima." — com escopo obrigatório de 15 sub-áreas (Usuários, Organizações, Workspaces, Convites, Papéis, Permissões, Sessões, API Keys, Configurações, Segurança, Auditoria, Health, Logs, Tenant Settings, System Settings).

**Conflito:** isso é uma expansão de escopo de aproximadamente 4x sobre o que já foi aprovado, incluindo conceitos inteiramente novos ao domínio da STRATECH (Workspaces multi-organização, API Keys, Tenant/System Settings, Health, Logs administrativos) que nunca passaram por Blueprint, ADR ou Architecture Review.

**Opções:**

| Opção | Descrição | Impacto |
|---|---|---|
| **A — Manter "administração mínima" (Épico 5 como aprovado)** | Wave 2 implementa exatamente o que já foi decidido: auditoria de mutações + telas mínimas de Org/User/Role/Project | Sem risco de escopo — é o que já está no roadmap aprovado. Não atende à ambição desta missão. |
| **B — Expandir para Enterprise Administration completa** | Todas as 15 sub-áreas pedidas | Requer: (1) Blueprint novo (Enterprise Administration não é um dos 8 domínios do Domain Map atual), (2) ADR formal alterando o escopo do Épico 5, (3) decisão explícita sobre "Workspaces" (colisão de nome com o Workspace já existente da V1) e "API Keys"/"Tenant Settings" (conceitos multi-tenant SaaS que a STRATECH ainda não decidiu adotar formalmente) |
| **C — Faseada (recomendada)** | Épico 5 mínimo primeiro (já aprovado, sem novo risco), com as 11 sub-áreas adicionais tratadas como uma extensão formal do Domain Map — sujeita a um Blueprint próprio antes de qualquer Sprint — dentro da Wave 2, não como parte silenciosa do Épico 5 | Preserva o roadmap já aprovado; não bloqueia Wave 1/2; dá ao Founder um ponto de decisão explícito antes de comprometer arquitetura nova |

**Recomendação deste documento:** Opção C. Nenhuma das 3 é aplicada unilateralmente por este documento — a decisão é do Founder.

---

## 10. Sprint Ledger — reconstrução

Sprints já executados, reclassificados por Wave (histórico preservado, não reescrito — apenas remapeado):

| Sprint/Entrega | Wave | Objetivo | Status |
|---|---|---|---|
| Sprint 1 (Design System, Dashboard V2, Mission Control, Decision Center) | Wave 1 (parcial: Mission Control é governança, não arquitetura) | Consolidar UI executiva sobre dado real/mock existente | Concluído |
| Épico 1 — Schema Foundation | Wave 1 | Schema multi-tenant relacional | Concluído |
| Épico 2 — Identity Foundation | Wave 1 | Identidade individual escopada por organização | Concluído |
| Capability 01 — Portfolio Management | Wave 2 | Portfolio como domínio DDD de frontend | Concluído |
| Capability 02 — Program Management | Wave 2 | Program como domínio DDD + consolidação de Portfolio | Concluído |
| Capability 03 — Project Delivery | Wave 2 | Project como domínio DDD + consolidação transitiva | Concluído |
| Architecture Review AR-1 | Transversal (governança) | Certificar baseline pós Capabilities 01-03 | Concluído — Approved with Observations |
| RC-2 Enterprise Certification | Transversal (governança) | Certificar Release/main/Phase 1→2 | Concluído — Autorizada com condições |
| Phase 2 Foundation Architecture | Wave 1 | Propor os 5 componentes de fundação | Concluído — aprovado conceitualmente |
| Phase 2 Foundation Technical Design | Wave 1 | Detalhar os 5 componentes para implementação | Concluído |
| **Este documento (Enterprise Master Execution Program)** | Transversal (governança) | Eliminar a dualidade Épico/Capability, consolidar planejamento | Concluído |

**Template obrigatório para Sprints futuras** (Objetivo, Escopo, Dependências, Critério de entrada, Critério de saída, Definition of Done, Acceptance Gate): reaproveita a Definition of Done já definida em `STRATECH_V2_MASTER_ROADMAP.md` §9 (de Épico/Programa/Release) — não duplicada aqui. Toda Sprint futura, a partir de agora, deve pertencer a exatamente uma Wave (nunca a um Épico ou Capability isolados) e declarar seu **Critério de entrada** (o que precisa estar pronto na Wave anterior) e **Acceptance Gate** (o que precisa ser verdadeiro para a Wave avançar) explicitamente no plano técnico apresentado antes da implementação — mesma disciplina já em uso ("Antes de codificar", CLAUDE.md).

---

## 11. Technical Debt ↔ Wave (referência cruzada, aditiva)

| TD | Wave | Bloqueia a Wave? |
|---|---|---|
| TD-001, TD-002 | Wave 1 (Persistence) / Wave 2 (Administration, primeiro DELETE) | Não hoje |
| TD-003 | Wave 2 (RBAC) | Não |
| TD-004/005/006 (Baseline Defects) | Nenhuma Wave nova — pré-existentes ao V1/V2, candidatos a resolução dentro de Wave 3 (Risk Intelligence) quando essa Wave for desenhada | Não |
| TD-007 | Wave 1 (Persistence) / Wave 2 (Domain) | Sim — resolver antes de persistir Portfolio/Program/Project |
| TD-008 | Wave 2 (Domain — Project/Project Delivery) | Sim — resolver antes de migrar dados reais de `projects_delivery` |
| TD-009 | Wave 5 (Analytics/Observability) | Não |

(Tabela completa permanece em `docs/architecture/TECHNICAL_DEBT.md` — esta é uma referência cruzada, não uma cópia.)

## 12. Decision Log ↔ Wave (referência cruzada, aditiva)

| Decisões | Wave |
|---|---|
| D-001 a D-009 (Sprint 1) | Transversal / Wave 5 (Executive Cockpit) |
| D-010, D-013, D-016 (convenções de processo) | Transversal (governança) |
| D-011, D-012, D-014, D-015, D-017, D-018, D-019, D-020, D-021 (Capabilities 01-03) | Wave 2 |
| D-022 a D-027 (AR-1, RC-2) | Transversal (governança) |
| D-028, D-029 (Phase 2 Foundation Architecture/Technical Design) | Wave 1 |

(Registro completo permanece em `docs/product/stratech-v2/DECISION-LOG.md` — não duplicado.)

---

## 13. Dependências arquiteturais ainda não resolvidas (consolidado)

1. **Roadmap Reconciliation** (D-028): resolvida por este documento (Seção 1) — Waves substituem Releases 0.3-0.5 como eixo ativo.
2. **Escopo exato do Épico 3 (RBAC)** — schema de `user_roles` multi-organização ainda não confirmado; bloqueia o detalhe final de `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4.9.
3. **Escopo do Épico 5 / Enterprise Administration** — conflito não resolvido, ver Decision Proposal (Seção 9).
4. **Unificação de "Project"** (TD-008, Épico 4) — não decidida.
5. **Wave 3 (Enterprise Intelligence)** — sem Blueprint próprio; nenhum Sprint pode ser planejado em detalhe até essa etapa existir.
6. **Wave 6 (Productization)** — decisão de modelo de negócio pendente do Founder; não é sequer planejável hoje.

---

## 14. Respostas às perguntas de validação (obrigatórias)

**1. Existe apenas um roadmap oficial?**
Sim, a partir deste documento — a Wave é o único eixo. `STRATECH_V2_MASTER_ROADMAP.md` permanece como registro histórico/factual (Executive Dashboard, Épicos 1-2 fechados, ADRs, PRs, Technical Debt), mas deixa de ser o eixo de planejamento ativo.

**2. Existe alguma duplicidade entre Épicos e Capabilities?**
Não mais — ambos foram reclassificados como itens dentro de Waves (Seção 1). A duplicidade de eixo foi eliminada.

**3. Todas as Sprints pertencem a uma única Wave?**
Sim, para as já executadas (Seção 10, remapeadas). Para as futuras, a regra é obrigatória a partir de agora (Seção 10, template).

**4. Todos os Technical Debts estão vinculados ao plano?**
Sim — todos os 9 TDs + 3 Baseline Defects têm uma Wave associada (Seção 11).

**5. Todas as Decision Logs estão reconciliadas?**
Sim — todas as 29 decisões têm uma Wave associada (Seção 12), sem nenhuma reescrita do conteúdo original.

**6. Existe alguma dependência arquitetural ainda não resolvida?**
**Sim, várias** (Seção 13, itens 2-6) — resolvida apenas a nº 1 (Roadmap Reconciliation).

**7. O programa está pronto para iniciar a implementação ponta a ponta sem necessidade de nova reorganização?**
**Não.** A Wave 1 e o início da Wave 2 (RBAC, Domain, itens já com Technical Design) estão prontos para implementação sem nova reorganização. As Waves 3, 4 (parcialmente), 5 e 6 **não estão** — faltam, no mínimo: um Blueprint dedicado para Enterprise Intelligence (Wave 3) e uma Architecture Review associada; a resolução do Decision Proposal de Enterprise Administration (Seção 9); a confirmação do escopo exato do Épico 3; a decisão de unificação de Project (Épico 4); e, para a Wave 6, uma decisão de modelo de negócio do Founder que nem sequer existe como pergunta em nenhum documento anterior a esta missão.

**Por regra explícita da própria missão** ("Se a resposta para qualquer item for não, interrompa a missão e apresente as pendências antes de prosseguir"): esta missão é encerrada **sem autorizar o início da implementação ponta a ponta**. As pendências que bloqueiam esse início estão listadas na Seção 13 e resumidas abaixo, no Executive Report.
