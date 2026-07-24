# AR-5 — Architecture Review: Convites (Invitations)

**Escopo:** revisão arquitetural de `DOMAIN-BLUEPRINT-INVITATIONS.md` antes da Technical Design, per o fluxo institucional obrigatório.
**Data:** 2026-07-24
**Item:** 6 do Wave Completion Review retrospectivo (D-054).

---

## 1. A dependência de e-mail é real ou artificial?

**Artificial como bloqueio de domínio; real apenas como mecanismo de entrega.** A auditoria documental (registrada na Blueprint §0) confirmou que nenhum artefato define o Convite como intrinsecamente dependente de e-mail — o acoplamento existe só como suposição do plano de fechamento (`WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md:90`). Um Convite é uma credencial tokenizada com estado; o token pode ser entregue por qualquer canal. Logo, o domínio existe independentemente de qualquer provedor, e a dependência de infraestrutura é isolada atrás de `NotificationProvider` (default `NoOp`) — exatamente o padrão que o Event Foundation (D-049) já estabeleceu com `NoOpEventEmitter`.

## 2. Consistência com a arquitetura oficial (CLAUDE.md)

| Regra | Verificação |
|---|---|
| Nunca criar arquitetura paralela | ✅ `Invitation` em `models.py` ao lado de `ApiKey`/`UserSession`; métodos em `AdministrationRepository`/`AdministrationService`; rotas num router coeso registrado em `main.py` como os demais. |
| Nunca duplicar código | ✅ Aceitação reaproveita `create_user` (composição `create_user_in_session` + `assign_role_in_session` + tratamento de `EmailConflictError`) já usada por User Management; hashing via `Argon2PasswordHasher`; auditoria via `record_audit`. |
| Nunca criar novo provider | ✅ `NotificationProvider` é uma **abstração de domínio nova para uma responsabilidade nova** (notificação), não um segundo `LLMProvider`; nenhum provedor concreto é criado. O `NoOp` é o análogo de `NoOpEventEmitter`. |
| Nunca criar novo registry | ✅ Nenhum registry novo. |
| Reutilizar componentes existentes | ✅ `EnterpriseRepository`, `Argon2PasswordHasher`, `record_audit`, `require_permission`, `get_request_context`, padrão de token "narrow-by-prefix + Argon2 verify" de D-051. |
| SOLID / DI | ✅ `NotificationProvider` injetado por construtor/DI (`build_notification_provider`, `lru_cache`), default sobrescrevível em teste — mesmo padrão de `build_event_emitter`. |

## 3. Ponto arquitetural: rota pública de aceitação

Pré-visualização e aceitação são autenticadas pelo **token**, não por sessão — o convidado ainda não tem conta. Elas ficam num router que só carrega os deps de infraestrutura de nível de router (`verify_api_key` + `enforce_rate_limit`), sem `require_permission` — mesmo desenho de `auth.py` (login/logout não usam `get_request_context`). No frontend, o gate de sessão do `proxy.ts` precisa isentar as rotas BFF públicas de convite (`/api/bff/invitations/*`) e a página pública de aceitação, exatamente como já isenta `LOGIN_ROUTE` — uma extensão do mecanismo existente, não um novo mecanismo.

## 4. Checagem da lista de proibições permanentes do Founder

Vector Store, embeddings, RAG, Knowledge Platform, Multi-Agent Framework, provedor de e-mail especulativo, implementação provisória — **nenhum aparece.** Em particular: nenhum SMTP/SES/SendGrid é escolhido ou stubado; o `NoOpNotificationProvider` é definitivo para esta fase (não um placeholder a ser "completado"), e o domínio é completo e funcional sem ele.

## 5. Grounding: consumidor real hoje?

Sim — um administrador que precise trazer um novo usuário para a organização hoje tem uma necessidade real e presente. Sem Convites, a única via é o admin definir a senha inicial diretamente (User Management), o que exige o admin conhecer/transmitir a senha. O Convite permite que o próprio convidado defina sua senha ao aceitar, sem o admin nunca vê-la — um ganho real de segurança de onboarding, independente de e-mail.

## 6. Impacto em código existente

- Nova tabela `invitations` (migração 0013) + permissão `invitations.manage`. Nenhuma migração de dado existente.
- Novo router `invitations.py` registrado em `main.py` — aditivo. `CORSMiddleware` já permite `GET`/`POST` (as rotas públicas são GET/POST); o `DELETE` de cancelamento é server-to-server via BFF, fora do CORS do browser, como os DELETEs de API Keys/Sessions.
- `proxy.ts` ganha isenção para as rotas públicas de convite — mesma lista de `LOGIN_ROUTE`.
- Nenhuma mudança de contrato em rota pré-existente.

## 7. Risco de sobre-engenharia

Mitigado: o domínio é CRUD + token + máquina de estados derivada de timestamps + uma composição de criação de usuário já existente. A única abstração nova (`NotificationProvider`) corresponde a uma responsabilidade real e distinta (entrega), com a implementação mínima possível (`NoOp`) — não uma hierarquia especulativa de provedores.

## 8. Veredito

**Aprovado para Technical Design, sem ressalvas.** O domínio é fundamental e completo sem qualquer provedor de e-mail; a dependência de infraestrutura fica corretamente isolada e adiada atrás de uma abstração, sem bloquear a entrega. Nenhuma Decision Proposal adicional necessária — a Decisão do Founder (item 6) já forneceu a especificação e autorizou a implementação.
