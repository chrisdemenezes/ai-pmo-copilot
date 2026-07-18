# STRATECH V2 — Architecture Reviews Register

Registro cronológico e write-once de todas as Architecture Reviews independentes realizadas na STRATECH V2, conforme o modelo de 3 papéis (ver `GOVERNANCE_MODEL.md`): o ChatGPT (Architecture & Product Advisor) revisa de forma independente TDS e Pull Requests estruturais, emitindo uma decisão formal (APPROVED / APPROVED WITH OBSERVATIONS / CHANGES REQUESTED / REJECTED). Uma vez registrada, uma revisão não é editada — uma revisão subsequente do mesmo objeto (ex.: TDS Rev. 2 após Rev. 1) é uma nova entrada, não uma edição da anterior.

> **Nota de institucionalização (EO-018):** este documento consolida, a partir do histórico de conversa, as Architecture Reviews realizadas até aqui. Nenhuma delas havia sido persistida como arquivo antes desta EO — a reconstrução usa o nível de detalhe disponível no registro da conversa; onde esse detalhe é parcial, isso é indicado explicitamente em vez de complementado por inferência.

---

### Executive Pre-Merge Architecture Review — PR #39 (Épico 1, Schema Foundation)

- **Identificador:** Executive Pre-Merge Architecture Review (PR #39)
- **Escopo:** revisão arquitetural independente do schema relacional multi-tenant (organizations/users/roles/permissions/projects/user_project_memberships) antes do merge à `main`.
- **Conclusão:** identificados 3 débitos técnicos reais: **TD-001** (SQLite não aplica Foreign Keys — comprovado por execução real, um `DELETE FROM organizations` com filhos executa sem erro), **TD-002** (nenhuma política de exclusão definida — RESTRICT vs. CASCADE), **TD-003** (convenção de sessão do Repository inconsistente — mistura de métodos com sessão própria e sessão externa sem convenção de nome).
- **Decisão:** **APPROVED WITH OBSERVATIONS**.
- **Observações:** os 3 débitos foram conscientemente aceitos, não bloqueantes para este épico porque nenhum endpoint de exclusão é exposto ainda; registrados em `TECHNICAL_DEBT.md` com gatilho de resolução explícito.
- **Data:** 2026-07-17 (ancorada pelo merge commit `4dcf7e886467e86c37524bd0fb46f70b70a7778c`).

---

### AR-001 — TDS Épico 2 (Identity Foundation), Revisão 1

- **Identificador:** AR-001
- **Escopo:** revisão arquitetural da Technical Design Specification do Épico 2, antes de qualquer autorização de implementação.
- **Conclusão:** 10 correções obrigatórias solicitadas antes de aprovação:
  1. Modelo de identidade orientado a objetos (`AuthenticatedUser`/`OrganizationIdentity`/`SessionIdentity`) substituindo IDs crus.
  2. `SessionIdentity` explícito como conceito de primeira classe.
  3. `interfaces.py` com contratos formais (Protocols) para permitir futuras estratégias de identidade (SSO/OAuth/LDAP).
  4. Bootstrap transacional (usuário + papel na mesma transação).
  5. `identity_type` explícito para distinguir usuários Demo de usuários reais.
  6. Renomeação dos headers institucionais para o padrão `X-Stratech-*-Id`.
  7. `GET /api/bff/session` mais rico (retornar identidade, não apenas um booleano).
  8. Parâmetros de Argon2 documentados explicitamente + estratégia de rehash transparente.
  9. Contrato explícito para `POST /api/auth/logout` (não implícito).
  10. Substituição da correção pontual de renumeração do ADR-004 por um plano completo de normalização da árvore de ADRs (proposto, não executado na ocasião).
- **Decisão:** **CHANGES REQUESTED**.
- **Observações:** motivou a produção da TDS Rev. 2, incorporando as 10 correções.
- **Data:** 2026-07-18.

### AR-002 — TDS Épico 2 (Identity Foundation), Revisão 2

- **Identificador:** AR-002
- **Escopo:** revisão da TDS Rev. 2, verificando a incorporação das 10 correções de AR-001.
- **Conclusão:** as 10 correções foram incorporadas à satisfação da revisão.
- **Decisão:** **APPROVED**.
- **Observações:** aprovação que autorizou a Engineering Order EO-015 "Authorized to Implement". **Importante:** esta aprovação cobre o contrato de login `{email, password}` (sem escopo organizacional) tal como especificado na TDS Rev. 2 no momento da revisão — a correção de escopo organizacional (`{organization, email, password}`) foi decidida **depois** desta revisão, já durante a implementação (ver EO-015 "Organizational Identity Scope Correction" em `ENGINEERING_ORDERS.md`), e portanto não foi objeto desta Architecture Review nem de nenhuma revisão independente subsequente até o momento — ver a entrada "pendente" abaixo.
- **Data:** 2026-07-18.

---

### AR-003 — PR #41 (Épico 2, implementação final)

- **Identificador:** AR-003
- **Escopo:** revisão do PR #41 como um todo — inclui a implementação completa do Épico 2 **e** a correção de escopo organizacional pós-AR-002, primeira Architecture Review independente a cobrir o contrato de login escopado por organização.
- **Conclusão:** aprovado com observações registradas (aceitas pelo Architecture Board, não impeditivas para integração).
- **Decisão:** **APPROVED WITH OBSERVATIONS**.
- **Observações:** autorizou a Engineering Order EO-MERGE-001 e a conclusão do Épico 2.
- **Data:** 2026-07-18. Merge executado — commit `ef760ee426f58eb3dad48f7d3eb3ed248308107d`.

---

### AR-1 — Baseline Certification (Capabilities 01-03, Release 0.2)

- **Identificador:** AR-1 (nomenclatura do próprio Founder — trilha distinta de AR-001/002/003, que cobriam TDS/PR review sob a governança da Foundation Phase; AR-1 nasce sob o fluxo Product-First/Capability-based, EO-021).
- **Escopo:** auditoria arquitetural completa após Portfolio Management (Capability 01), Program Management (Capability 02) e Project Delivery (Capability 03) — arquitetura/camadas, DDD, Domain Model, os 3 Domain Blueprints, Executive Cockpit, Mission Control, governança (ADRs/Decision Log/Sprint Notes/Master Roadmap), engenharia (tsc/eslint/testes/build/smoke), dívida técnica, multi-tenancy. Não implementou a Capability 04, não alterou comportamento funcional.
- **Achados e correções aplicadas:**
  1. `consolidatePortfolios()`/`consolidatePrograms()` duplicavam o mesmo algoritmo de rollup — extraído `consolidateFromChildren()` (`shared.ts`), comportamento idêntico (Decision Log D-023).
  2. Faixa de KPIs do Executive Overview lia mock (`COCKPIT_KPIS`) desatualizado (8/24 contra 4/7 reais; "Decisões Pendentes" nem batia com o próprio mock de Decision Center) — corrigida para dado real (D-024).
  3. `PortfolioSituation`/`ProgramSituation` (mock) sem nenhum consumidor desde as Capabilities 01/02 — removidos (D-025).
- **Dívida técnica identificada:** TD-007 (domínio sem persistência/multi-tenant ainda — aceito, prospectivo) e TD-008 (3 conceitos "Project" sem unificação — aceito até o Épico 4). Nenhuma bloqueia a Capability 04.
- **Nenhuma nova ADR necessária** — as correções são ajustes de qualidade dentro dos princípios já decididos em ADR-V2-009, não uma mudança de decisão arquitetural (D-026).
- **Entregável:** `docs/architecture/ARCHITECTURE-BASELINE-RC2.md` (nova baseline oficial), `docs/product/governance/AR-1-EXECUTIVE-REPORT.md` (relatório executivo completo).
- **Decisão:** **APPROVED WITH OBSERVATIONS**.
- **Observações:** observações = as 2 dívidas técnicas aceitas (TD-007/008) e a colisão de numeração ADR-V2-004 pré-existente (não introduzida nem resolvida por esta AR-1). Nenhuma impede o início da Capability 04. Recomendação registrada: segunda opinião independente (ex.: revisão externa) antes de iniciar a Capability 04, por decisão do próprio Founder.
- **Data:** 2026-07-18.
