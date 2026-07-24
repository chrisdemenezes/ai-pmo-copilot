# WAVE COMPLETION REVIEW — RETROSPECTIVE (Waves 1-3)

**Data:** 2026-07-23
**Autor:** Claude / Tech Lead
**Gatilho:** Decision Log D-048 ("Superseding Decision — Wave Completion Policy"), que revoga todas as decisões anteriores que permitiam adiar Epics/Enterprise Analysts/Capabilities previstos e determina um levantamento retrospectivo completo desde a Wave 1, corrigindo toda divergência encontrada.

---

## 1. Método

Três auditorias independentes e exaustivas (uma por Wave), cada uma comparando: planejamento original (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md`, Domain Blueprints da Wave), Decision Log completo, Mission Control, Technical Debt Register, Executive Reports, e o código implementado (`src/`, `web/`, grep exaustivo por símbolos/arquivos esperados). Nenhum item foi assumido — cada linha da tabela abaixo foi verificada diretamente no código.

## 2. Wave 1 — Enterprise Foundation

| Componente previsto | Status |
|---|---|
| Schema, Migration (Épico 1) | ✅ Implementado |
| Identity, Authentication (Épico 2) | ✅ Implementado |
| Session (parte de Identity) | 🟡 Mecanismo existe (cookie HMAC stateless), mas sem armazenamento/revogação server-side (TD-010, aberto) |
| Organization, Multi-tenancy | ✅ Implementado |
| Request Context | ✅ Implementado e consumido |
| Repository Layer | ✅ Implementado |
| Persistence (Portfolio/Program/Project) | ✅ Implementado (migração 0005, Sprint 1 da Wave 2, atribuído retroativamente à Wave 1 per o próprio D-032) |
| API Foundation | ✅ Implementado (Sprint 2 da Wave 2) |
| RBAC seam | ✅ Implementado (Sprint 3 da Wave 2; endurecido em `intelligence.py` por D-045) |
| **Event Foundation** | ❌ **Zero implementação.** Nenhum `src/services/events/`, nenhum `EventEmitter`/`NoOpEventEmitter`, nenhuma chamada `emit()` em nenhum lugar do código. Totalmente especificado em `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §5 (Protocol + `NoOpEventEmitter` + 5 eventos nomeados), nunca implementado. |

**Gap único, real e não-ambíguo da Wave 1: Event Foundation.**

## 3. Wave 2 — Enterprise Platform

| Componente previsto (escopo original de 15 sub-áreas, `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §4.2) | Status |
|---|---|
| Usuários, Organizações, Papéis, Permissões | ✅ Implementado (User Management, D-038) |
| Auditoria (log de mutação) | ✅ Implementado (`audit_logs`, migração 0007) |
| RBAC fine-grained | ✅ Implementado |
| Domain (Portfolio/Program/Project) | ✅ Implementado, persistido, exposto via API, consumido pelo frontend |
| **Sessões** (armazenamento server-side, revogação, listagem) | ❌ Não implementado — apenas cookie HMAC stateless |
| **Convites** (fluxo de convite por e-mail) | ❌ Não implementado |
| **Workspaces** (como entidade de dados administrável, distinta da rota de UI `/workspace/:projectName`) | ❌ Não implementado |
| **API Keys** (por organização/usuário, com CRUD administrável) | ❌ Não implementado — só existe uma `API_KEY` estática de ambiente, compartilhada por todo o sistema |
| **Tenant Settings / System Settings** | ❌ Não implementado |
| **Policies, Claims** (como mecanismos distintos de RBAC) | ❌ Não adotados — decisão de design explícita (evitar segunda arquitetura de autorização); precisa reavaliação sob a nova política (Seção 5) |
| TD-008 (unificação Project/ProjectDelivery) | 🟡 Fase 3a concluída (W3-1); **Fase 3b não implementada** (aposentar `ProjectSummary`, migrar toda a superfície para `project_id`) |
| Homologação funcional completa (UAT) | ❌ Explicitamente adiada para depois da Wave 3, por instrução do Founder à época |

**Gaps da Wave 2, sob a nova política:** Sessões (armazenamento real), Convites, Workspaces (entidade), API Keys (por tenant), Tenant/System Settings, TD-008 Fase 3b. Policies/Claims exigem reavaliação de design (ver Seção 5).

## 4. Wave 3 — Enterprise Intelligence

| Sub-área | Status |
|---|---|
| **AI Platform** — Provider Strategy (multi-provider) | ❌ Ainda 1 provider por variável de ambiente |
| — Model Registry | ❌ Não existe |
| — Model Routing | ❌ Não existe |
| — Prompt Versioning | ❌ `PromptRegistry` sem conceito de versão |
| — Cost/Token Governance | 🟡 Apenas uma linha de log (`ObservabilityRecorder`); nenhum armazenamento, orçamento ou limite |
| — AI Observability/Governance | 🟡 Mesma linha de log; nenhuma camada de política/governança |
| — Evaluation Framework | ❌ Não existe |
| **Knowledge Platform** — Vector Store/pgvector | ❌ Não existe |
| — Embeddings | ❌ Não existe |
| — RAG Strategy | ❌ Não existe |
| — Semantic Search | ❌ Não existe |
| — Context Manager (generalizado) | ❌ Só existe `AIContextEngine`, específico a um Analyst por vez, não um gerenciador geral de contexto de LLM |
| — Enterprise Knowledge Base | ❌ Não existe |
| **Executive Intelligence** — Portfolio/Program/Project Intelligence (camada de insight de IA) | ❌ Não existe |
| — Executive Decision Intelligence | ❌ Não existe |
| — PMO Intelligence | ❌ Não existe (a "Digital PMO Intelligence Foundation" é infraestrutura, não esta capability) |
| — Governance Intelligence | ❌ Não existe |
| **Enterprise Advisors** — Risk Advisor | ✅ Implementado (W3-3, migrado para a Foundation) |
| — Executive, PMO, Portfolio, Delivery, Governance, Strategy, Document Advisor (7 restantes) | ❌ Nenhum código em `src/agents/` para nenhum dos 7 |
| Project Identity Unification (W3-1) | 🟡 Fase 3a concluída; Fase 3b não (mesmo item da Wave 2, TD-008) |
| TD-004/005/006 (race de invalidação React Query) | ❌ Ainda abertos |

**Gap da Wave 3, sob a nova política:** 25 dos 26 itens nomeados no Blueprint conceitual não têm implementação (só Risk Advisor existe), incluindo Knowledge Platform inteira e os 7 Advisors restantes — itens que a política anterior (D-039/D-041/D-042, revogada) tratava como Decision Proposal bloqueada.

## 5. Achado que exige decisão de design, não apenas implementação

**Policies e Claims** (Wave 2, §4.1) foram deliberadamente **não adotados** como mecanismos distintos de RBAC, com a justificativa explícita de que introduzi-los "seria criar uma segunda arquitetura de autorização" — uma violação direta de CLAUDE.md ("nunca criar arquitetura paralela"), não uma omissão de escopo. A nova Wave Completion Policy torna obrigatório todo item do planejamento original, mas **não revoga a proibição de arquitetura paralela em si** — apenas a interpretação de que um item "sem consumidor real" pode ficar de fora. Como Policies/Claims foram julgados **redundantes** (não "sem consumidor", mas "duplicariam algo que já existe"), este item precisa de uma decisão explícita do Founder sobre como reconciliar as duas regras antes de qualquer implementação: (a) manter RBAC como o único mecanismo e declarar Policies/Claims formalmente satisfeitas por ele (não uma nova capability), ou (b) implementar Policies/Claims como uma camada adicional real, aceitando a duplicação que o desenho original evitava.

## 6. Plano de fechamento (sequenciado por tamanho/dependência, seguindo o fluxo institucional completo para cada item)

| Ordem | Item | Porte | Observação |
|---|---|---|---|
| 1 | **Event Foundation** (Wave 1) | Pequeno | Já 100% especificado (`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §5) — Protocol + `NoOpEventEmitter` + wiring de 5 eventos nomeados. Nenhuma decisão de design pendente. |
| 2 | **TD-004/005/006** (race de invalidação) | Pequeno | Bug já diagnosticado (mesma causa raiz), correção pontual nos hooks de invalidação do React Query. |
| 3 | **API Keys por organização** (Wave 2) | Médio | Reaproveita o padrão RBAC/Administration já existente; CRUD + hashing, sem infraestrutura nova. |
| 4 | **Tenant/System Settings** (Wave 2) | Médio | Nova tabela `organization_settings` + endpoints Administration; reaproveita o padrão de `AdministrationRepository`. |
| 5 | **Sessões server-side** (Wave 2) | Médio-Grande | Nova tabela de sessão + revogação; precisa decidir se substitui ou complementa o cookie HMAC atual (impacto em todo o fluxo de login). |
| 6 | **Convites** (Wave 2) | Médio-Grande | Precisa de envio de e-mail — nenhuma infraestrutura de e-mail existe hoje; decisão de provedor (SMTP/SES/etc.) é pré-requisito. |
| 7 | **Workspaces como entidade** (Wave 2) | A esclarecer | O termo colide com a rota de UI `/workspace/:projectName` já existente (V1). Precisa de Domain Blueprint próprio só para definir o que esta entidade representa antes de qualquer código. |
| 8 | **TD-008 Fase 3b** (Wave 2/3) | Grande | Migrar toda a superfície (Dashboard/Portfolio/Decision Center/Executive Focus/Workspace) de `project_name` para `project_id`; o próprio Blueprint de W3-1 já apontou que isso sozinho tem escopo maior que o resto da Wave 3. |
| 9 | **AI Platform — Cost/Token Governance real + Observability/Governance** (Wave 3) | Médio | Estender `ObservabilityRecorder` de "log line" para armazenamento consultável (nova tabela) + política de limite. |
| 10 | **AI Platform — Provider Strategy/Model Registry/Model Routing/Prompt Versioning/Evaluation Framework** (Wave 3) | Grande | 5 sub-áreas inteiras, cada uma uma extensão de arquitetura real do `LLMProvider`/`PromptRegistry`. |
| 11 | **Knowledge Platform completa** (Wave 3) | Muito grande | Requer decisão de infraestrutura (adoção de pgvector/Vector Store — impacto de custo/operação), depois embeddings + RAG + semantic search + Context Manager generalizado + Knowledge Base. |
| 12 | **7 Enterprise Advisors restantes + framework de orquestração multi-agente** (Wave 3) | Muito grande | Cada Advisor é, individualmente, um trabalho da escala do Risk Advisor (Blueprint → AR → TD → Implementação → Testes → Executive Report); o framework de orquestração multi-agente é ele próprio uma peça de arquitetura nova, nunca desenhada. |
| 13 | **Executive/PMO/Governance Intelligence** (Wave 3) | Grande | Depende, em parte, dos Advisors correspondentes (item 12) e da Foundation já existente. |
| — | **Policies/Claims** (Wave 2) | Bloqueado | Aguarda decisão do Founder per Seção 5 antes de qualquer código. |

## 7. Execução

Este documento não implementa nada por si — é o levantamento exigido por D-048. A implementação de cada item segue, item a item, o fluxo institucional completo (Domain Blueprint quando necessário → Architecture Review → Technical Design → Implementação → Testes unitários/integração/E2E → Executive Report), começando pelo item 1 (Event Foundation) nesta mesma sessão, em ordem, sem pular etapas. Mission Control/Decision Log/CHANGELOG são atualizados a cada item concluído.

**Status de execução (atualizado a cada item fechado):**

| Ordem | Item | Status |
|---|---|---|
| 1 | Event Foundation (Wave 1) | ✅ Concluído — D-049. Wave 1 fechada. |
| 2 | TD-004/005/006 (race de invalidação) | ✅ Concluído — D-050. |
| 3 | API Keys por organização (Wave 2) | ✅ Concluído — D-051. Correção arquitetural retroativa: reclassificado de "depende de Integration Hub" (Nível 3) para fundamental (Nível 1) — Blueprint corrigido (`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §0), nova Architecture Review (`AR-4-API-KEYS-REVIEW.md`) e Technical Design (`TECHNICAL-DESIGN-API-KEYS.md`) produzidas. Chave autentica como o usuário criador, 100% do RBAC/auditoria/hashing reaproveitados; segunda via de autenticação aditiva em `get_request_context`. |
| 4 | Tenant/System Settings (Wave 2) | 🟡 **Governança Concluída** (não Implementado) — D-052. Auditoria exaustiva do repositório não encontrou nenhuma definição funcional concreta para "Configurações da Organização" em nenhum documento oficial — reclassificada como **Sem Escopo Funcional Definido**, não preenchida com suposições nem com melhoria de infraestrutura (rate limit por organização, avaliada e rejeitada como substituto). "Tenant/System Settings" (modelo SaaS comercial) formalmente separado e reclassificado como **Pendente de Decisão de Negócio** (Wave 6, `BUSINESS-MODEL-BLUEPRINT.md` §2, 7 perguntas sem resposta) — dependência de negócio real, não arquitetural. Ver `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §0.1. |
| 5 | Sessões server-side (Wave 2) | ✅ Concluído — D-053. Resolve TD-010: o store server-side que o Blueprint assumia existir não existia (cookie HMAC stateless). Nova tabela `sessions` + migração 0012, `session_id` cunhado pelo backend no login, `logout` revoga de verdade, enforcement de revogação em `require_permission` (fail-open para sessões não rastreadas), painel `/administracao/sessoes`. Ver `TECHNICAL-DESIGN-SESSIONS.md`. |
| 6 | Convites (Wave 2) | ✅ Concluído — D-054. Auditoria separou domínio de infraestrutura: a suposição do §6 abaixo ("precisa de envio de e-mail... provedor SMTP/SES é pré-requisito") descrevia e-mail como *mecanismo de entrega*, não como constituinte do domínio — nenhum documento acopla intrinsecamente Convites a e-mail. Domínio implementado integralmente (`Invitation`, migração 0013, estados Pendente/Aceito/Expirado/Cancelado, API admin + fluxo público de aceitação sem sessão, RBAC `invitations.manage`, auditoria) com a entrega isolada atrás de `NotificationProvider`/`NoOpNotificationProvider` — nenhum provedor concreto escolhido, o token é devolvido uma vez para entrega manual. Ver `DOMAIN-BLUEPRINT-INVITATIONS.md`, `AR-5-INVITATIONS-REVIEW.md`, `TECHNICAL-DESIGN-INVITATIONS.md`. A escolha do provedor concreto permanece decisão de negócio pendente, sem bloquear o domínio. |
| 7 | Workspaces como entidade (Wave 2) | 🟡 **Governança Concluída** (não Implementado) — D-055. Auditoria arquitetural exaustiva determinou a natureza do conceito: "workspace" tem três sentidos, dois existentes (a View/UI `/workspace/:projectName` e a sessão de autenticação Nível 1, já = `Session`/D-053) e um inexistente (a entidade administrável, sem identidade/ciclo de vida/invariantes/relacionamentos/persistência em nenhum documento). **Classificação (A): View/UI — não é entidade de domínio.** Não implementado: criar a entidade seria arquitetura paralela sobre Program/Portfolio + RBAC Organization Scope. Reservado como termo de apresentação (`DOMAIN-MODEL.md` §1, `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §0.2). |
| 8-13, — | Demais itens + Policies/Claims | Pendentes, na ordem da Seção 6. |
