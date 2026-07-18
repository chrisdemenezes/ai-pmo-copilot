# Technical Design Specification — Épico 2: Identity Foundation

STRATECH V2, Release 0.1.

> **Aviso de fidelidade documental (EO-018/AR-004):** a TDS original (Rev. 1 e Rev. 2) nunca foi persistida como arquivo — foi produzida inteiramente em turnos de conversa e nunca gravada no repositório antes desta consolidação. Este documento é uma **versão consolidada a partir da TDS aprovada e da implementação efetivamente realizada**: (a) a descrição estrutural da TDS Rev. 2 registrada no histórico desta engenharia, e (b) o código efetivamente implementado em `src/services/identity/`, que deveria refletir exatamente a TDS aprovada (EO-015 "Authorized to Implement" instruiu implementar "apenas o escopo da TDS"). **Isto não é uma transcrição literal do texto original** — o texto exato, palavra por palavra, da TDS Rev. 1/Rev. 2 não é recuperável a partir do contexto disponível para esta consolidação. Onde a consolidação é uma inferência a partir do código (e não uma citação direta do registro da conversa), isso está indicado.

---

## Histórico de revisões

| Revisão | Data | Mudança | Resultado da Architecture Review |
|---|---|---|---|
| Rev. 1 | 2026-07-18 | Versão inicial: modelo de identidade baseado em IDs simples, contrato `{email, password}` | AR-001: **CHANGES REQUESTED** (10 correções) |
| Rev. 2 | 2026-07-18 | Incorpora as 10 correções de AR-001 (ver `ARCHITECTURE_REVIEWS.md`): modelo orientado a objetos, `SessionIdentity` explícito, `interfaces.py`, bootstrap transacional, `identity_type`, headers `X-Stratech-*-Id`, `GET /api/bff/session` mais rico, parâmetros de Argon2 documentados, contrato de logout explícito, plano de normalização de ADRs (proposto) | AR-002: **APPROVED** |
| Correção pós-Rev. 2 (não numerada como nova revisão de TDS) | 2026-07-18 | Login passa a ser escopado por **organização + e-mail + senha** (antes: e-mail global), via migration aditiva `organization_slug`. Autorizada por Engineering Order (EO-015 "Organizational Identity Scope Correction"), **não por uma nova Architecture Review** — ver lacuna registrada em `ARCHITECTURE_REVIEWS.md` (entrada pendente para PR #41) | Nenhuma — pendente na revisão do PR #41 |

**Decisão final (estado hoje):** implementação completa incluindo a correção de escopo organizacional, aberta como PR #41, **aguardando Architecture Review** (a primeira a cobrir a versão final com escopo organizacional).

---

## 1. Contexto

O V1/RC-1 usa um único `WORKSPACE_PASSWORD` global, sem identidade individual. O Épico 2 introduz autenticação individual real, operando sobre o schema multi-tenant já estabelecido no Épico 1 (`organizations`, `users` com `UniqueConstraint(organization_id, email)`).

## 2. Modelo de identidade (`src/services/identity/models.py`)

Dataclasses imutáveis (`frozen=True`):

- **`AuthenticatedUser`** — `user_id`, `email`, `display_name`, `identity_type` (`"standard"` | `"demo"`, propriedade `is_demo`).
- **`OrganizationIdentity`** — `organization_id`, `name`.
- **`SessionIdentity`** — `session_id`, `expires_at` (opcional — o backend não conhece a expiração real, só o BFF).
- **`RequestContext`** — agrega `user`, `organization`, `session`, `request_id`.

## 3. Contratos (`src/services/identity/interfaces.py`)

- **`CredentialVerifier`** (Protocol) — `verify`, `hash`, `needs_rehash`. Permite trocar a estratégia de verificação de credencial (ex.: SSO/OAuth/LDAP futuros) sem alterar `AuthService`.
- **`IdentityResolver`** (Protocol) — `resolve`. Reservado para resolução de identidade por estratégias futuras.

## 4. Password hashing (`src/services/identity/password_hashing.py`)

`Argon2PasswordHasher` implementa `CredentialVerifier`. Parâmetros (configuráveis por variável de ambiente, com default):

- `time_cost = 3` (`ARGON2_TIME_COST`)
- `memory_cost = 65536` (`ARGON2_MEMORY_COST`)
- `parallelism = 4` (`ARGON2_PARALLELISM`)

`verify()` captura `VerificationError` e `InvalidHashError`. `needs_rehash()` habilita rehash transparente no login quando os parâmetros mudam.

## 5. Serviço de autenticação (`src/services/identity/auth_service.py`)

`AuthService(session_factory, credential_verifier, enterprise_repository=None)`:

- **`authenticate(organization, email, password)`** — resolve o usuário por organização + e-mail (nunca por busca global de e-mail), verifica a senha, retorna `AuthenticatedUser` + `OrganizationIdentity` em caso de sucesso, ou erro uniforme (não revela se o e-mail, a organização, ou a combinação existe) em caso de falha.
- **`logout(session_id, user_id)`** — invalida a sessão.
- **`bootstrap_administrator()`** — idempotente, transacional; lê `STRATECH_ADMIN_EMAIL`/`STRATECH_ADMIN_PASSWORD`; nunca recria/reseta um usuário existente por e-mail.
- **`bootstrap_demo_user()`** — idempotente, transacional; usuário Demo (`identity_type="demo"`) na organização `"Demo Organization"` (slug `demo-organization`), senha de `WORKSPACE_PASSWORD`.
- Módulo expõe `bootstrap_identities(auth_service)`, chamado no `lifespan` de `src/main.py`.

## 6. Contrato de API

- **`POST /api/auth/login`** — `{organization, email, password}` → `{user_id, organization_id}` ou 401 uniforme.
- **`POST /api/auth/logout`** — `{session_id, user_id}` → `{acknowledged: true}` (best-effort, nunca bloqueia o logout do lado do BFF).
- Ambos server-to-server, exigem `X-API-Key`.

## 7. RequestContext e headers institucionais (`src/api/identity_context.py`)

`get_request_context` (dependency do FastAPI) lê `X-Stratech-User-Id`, `X-Stratech-Organization-Id`, `X-Stratech-Session-Id`; `request_id` é obtido do `request_id_var` já existente em `src/api/request_context.py` (reaproveitado, não reimplementado).

## 8. Sessão do BFF (`web/lib/session.ts`, `web/app/api/bff/session/route.ts`)

- Cookie renomeado `workspace_session` → `stratech_session`.
- Payload assinado (HMAC-SHA256): `{sessionId}.{userId}.{organizationId}.{expiresAtMs}` + assinatura, TTL de 12h.
- `POST /api/bff/session` — recebe `{organization, email, password}`, encaminha idêntico ao backend, emite o cookie.
- `DELETE /api/bff/session` — logout best-effort no backend, sempre expira o cookie localmente.
- `GET /api/bff/session` — retorna `{authenticated, user_id, organization_id}` ou `{authenticated: false}`.

## 9. Schema (migrations)

- **`0003_identity_type`** — coluna `identity_type` (`String(20)`, default `"standard"`) em `users`. Aditiva, com backfill, reversível.
- **`0004_organization_slug`** — coluna `slug` em `organizations` (única, `NOT NULL` após backfill determinístico via slugify de `name`, com desambiguação de colisão). Aditiva, reversível. `name` permanece display-only.
- `UNIQUE(organization_id, email)` em `users` **mantido** — e-mail único apenas dentro da organização, nunca globalmente.

## 10. Demo Mode

Usuário Demo autentica apenas em `"Demo Organization"` (`slug = "demo-organization"`), enviado explicitamente pelo frontend em modo demo — nunca por busca global de e-mail.

## 11. Testes exigidos

165 testes de backend (97% cobertura) + 398 testes unitários de frontend, incluindo os 7 cenários da correção de escopo organizacional: (1) mesmo e-mail em duas organizações; (2) login só autentica na organização correta; (3) credencial válida em uma organização nunca autentica em outra; (4) Demo autentica somente em "Demo Organization"; (5) nenhuma consulta cruza organizações; (6) `RequestContext` carrega a organização correta; (7) resposta de erro uniforme.

## 12. Fora de escopo (explicitamente, por EO-015)

RBAC funcional, setor/área/equipe/competência, gestão de estrutura organizacional, registro de usuário, recuperação de senha.

## 13. Referência

- Architecture Review: `docs/governance/ARCHITECTURE_REVIEWS.md` — AR-001 (Rev. 1, CHANGES REQUESTED), AR-002 (Rev. 2, APPROVED), entrada pendente (PR #41, primeira revisão da versão com escopo organizacional).
- Engineering Orders: `docs/governance/ENGINEERING_ORDERS.md` — EO-015 (3 variantes).
- Débito técnico herdado: `TECHNICAL_DEBT.md` — TD-001/002/003 (Épico 1, ainda abertos, sem impacto neste épico) e TD-004/005/006 (Baseline Defects, descobertos durante a validação de regressão deste épico).
