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

### *(pendente)* — PR #41 (Épico 2, implementação final)

- **Identificador:** a atribuir quando a revisão ocorrer (ex.: AR-003).
- **Escopo:** revisão do PR #41 como um todo — inclui a implementação completa do Épico 2 **e** a correção de escopo organizacional pós-AR-002, que ainda não foi objeto de nenhuma Architecture Review independente.
- **Conclusão:** não realizada.
- **Decisão:** não emitida — PR #41 está em estado **READY FOR ARCHITECTURE REVIEW**.
- **Observações:** esta é a primeira revisão independente que efetivamente cobrirá o contrato de login escopado por organização — uma lacuna relevante a fechar antes de qualquer merge.
- **Data:** —
