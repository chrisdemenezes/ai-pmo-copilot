# Technical Design — Convites (Invitations)

**Base:** `DOMAIN-BLUEPRINT-INVITATIONS.md` + `AR-5-INVITATIONS-REVIEW.md` (aprovado sem ressalvas).
**Status:** implementação segue imediatamente, per a Decisão do Founder (item 6). Item 6 do Wave Completion Review retrospectivo, Decision Log D-054.

---

## 1. Modelo e migração

`Invitation` (`src/database/models.py`), tabela `invitations`, migração `0013`:

```
id, organization_id (FK), email, role_name, invited_by_user_id (FK),
token_prefix, hashed_token, created_at, expires_at, accepted_at?, cancelled_at?
```

Migração 0013 também semeia a permissão `invitations.manage` para `organization_admin` (mesmo bloco idempotente das migrações 0011/0012).

Constantes de módulo (`administration_service.py`):
```
INVITATION_TOKEN_PREFIX = "inv_"
INVITATION_DISPLAY_PREFIX_LENGTH = len("inv_") + 8
INVITATION_TTL = timedelta(days=7)   # default de implementação; ver Blueprint §4
```

## 2. Estado derivado

`Invitation` expõe uma propriedade/função `status(now) -> "pending"|"accepted"|"cancelled"|"expired"`:
```
if cancelled_at is not None: "cancelled"
elif accepted_at is not None: "accepted"
elif expires_at <= now: "expired"
else: "pending"
```
A API devolve esse `status` computado (valores em inglês, neutros de idioma); o frontend mapeia para os rótulos PT (Pendente/Aceito/Expirado/Cancelado), como já faz para papéis/status em outras telas.

## 3. Repositório (`AdministrationRepository`)

- `create_invitation(organization_id, email, role_name, invited_by_user_id, token_prefix, hashed_token, expires_at) -> Invitation`
- `list_invitations(organization_id) -> list[Invitation]` (ordenado por `created_at desc`)
- `get_invitation(invitation_id, organization_id) -> Invitation | None`
- `cancel_invitation(invitation_id, organization_id) -> Invitation | None` — só cancela um Pendente; retorna `None` se inexistente/já-terminal (idempotência, como `revoke_api_key`)
- `list_pending_invitations_by_prefix(token_prefix) -> list[Invitation]` — candidatos para verificação Argon2 (narrow-by-prefix), exclui aceitos/cancelados
- `accept_invitation(invitation_id, display_name, password_hash) -> User | None` — **uma transação**: recarrega o convite `FOR UPDATE`, revalida que ainda está Pendente (não expirado/aceito/cancelado), cria o usuário + papel (via `create_user_in_session`+`assign_role_in_session`), seta `accepted_at`, comita; mapeia `IntegrityError` de e-mail para `EmailConflictError`.

## 4. Serviço (`AdministrationService`)

- `create_invitation(organization_id, email, role_name, actor_user_id) -> tuple[Invitation, str]` — gera `plaintext_token = "inv_" + secrets.token_urlsafe(32)`, hash Argon2, persiste, audita `invitation.created`, chama `notification_provider.notify_invitation_created(invitation, plaintext_token)` (NoOp hoje), devolve `(invitation, plaintext_token)`. O token puro só existe aqui e na resposta de criação.
- `list_invitations(organization_id)`
- `cancel_invitation(invitation_id, organization_id, actor_user_id) -> Invitation | None` — audita `invitation.cancelled`
- `preview_invitation(plaintext_token) -> Invitation | None` — narrow-by-prefix + Argon2 verify; devolve o convite (para a tela de aceitação mostrar org/papel/estado) sem exigir sessão
- `accept_invitation(plaintext_token, display_name, password) -> User | None` — verifica o token, confirma `status == pending`, hash da senha, chama `repository.accept_invitation(...)`, audita `invitation.accepted`; retorna `None` para token inválido/convite não-Pendente

O `AdministrationService.__init__` ganha um parâmetro opcional `notification_provider: NotificationProvider | None = None`, default `NoOpNotificationProvider()` — injeção por construtor, sem quebrar chamadas existentes.

## 5. NotificationProvider

`src/services/notifications/interfaces.py`:
```python
class NotificationProvider(Protocol):
    def notify_invitation_created(self, invitation: Invitation, plaintext_token: str) -> None: ...
```
`src/services/notifications/noop_provider.py`: `NoOpNotificationProvider` — loga "would notify" e nada mais (o seam existe, o provedor não). Wired em `src/api/dependencies.py::build_notification_provider` (`lru_cache`), injetado no serviço pela factory de rotas.

**Nenhum provedor concreto (SMTP/SES/etc.) é criado.** A escolha permanece uma decisão de negócio pendente (Blueprint §9/§10), que não bloqueia o domínio.

## 6. Rotas (`src/api/routes/invitations.py`, registrado em `main.py`)

Router com deps de nível de router `verify_api_key` + `enforce_rate_limit` (infra BFF→backend), como todos os outros.

Administrativas (exigem `require_permission("invitations.manage")`):
| Rota | Efeito |
|---|---|
| `POST /api/admin/invitations` | Cria; resposta `201` inclui `plaintext_token` (uma vez) |
| `GET /api/admin/invitations` | Lista (com `status` computado); nunca inclui `hashed_token` |
| `DELETE /api/admin/invitations/{id}` | Cancela; `200` com o recurso (não `204` — `forwardDomainRequest`, mesma convenção de `remove_role`/API Keys/Sessions) |

Públicas (autenticadas só pelo token, **sem** `require_permission`):
| Rota | Efeito |
|---|---|
| `GET /api/invitations/{token}` | Pré-visualização: org, papel, status, e-mail. `404` se token inválido |
| `POST /api/invitations/accept` | `{token, display_name, password}` → cria a conta, marca Aceito. `200` com `{user_id, organization_id}`. `404`/`409` para token inválido/convite não-Pendente/e-mail já existente |

## 7. Frontend

- **Admin** `/administracao/convites` (13º item de navegação, "Convites"): lista com status colorido, diálogo de criação em duas etapas (formulário e-mail+papel → revelação única do link/token, com botão copiar), botão cancelar com confirmação. Mesmo padrão de `/administracao/api-keys`.
- **Pública** `/convite/[token]`: página **fora** do gate de sessão do `proxy.ts`; busca a pré-visualização, mostra "Você foi convidado para {org} como {papel}", formulário de nome + senha, chama a aceitação, e em sucesso redireciona para `/entrar`.
- BFF: `/api/bff/admin/invitations` (GET/POST), `/api/bff/admin/invitations/[id]` (DELETE) — gated; `/api/bff/invitations/[token]` (GET), `/api/bff/invitations/accept` (POST) — **isentas** do gate no `proxy.ts` (mesma lista de `LOGIN_ROUTE`).
- `proxy.ts`: adiciona as rotas BFF públicas de convite à isenção e mantém `/convite/:path*` fora do `config.matcher` (página pública).

## 8. Testes

- Migração 0013 (tabela + permissão; upgrade/downgrade).
- Repositório (`TestInvitations`): CRUD, narrow-by-prefix exclui terminais, aceitação atômica cria user+papel e marca Aceito, idempotência de cancelamento, conflito de e-mail.
- Serviço: criação (token/hash/prefixo + NoOp chamado), preview, aceitação (sucesso, token inválido, convite expirado/cancelado/aceito rejeitado), cancelamento.
- Provider: `NoOpNotificationProvider` não lança e não tem efeito além de log.
- API: 3 rotas admin (RBAC 403 sem permissão, isolamento por org), 2 públicas (preview/accept sem sessão, token inválido → 404).
- Frontend vitest: domínio/hooks; E2E `convites-admin.spec.ts` (nav, criar+revelar, listar com status, cancelar) e fluxo público de aceitação (preview → aceitar → login).

## 9. Veredito

Domínio fundamental e completo, sem provedor de e-mail, sem placeholder no domínio. A infraestrutura de entrega fica isolada atrás de `NotificationProvider`/`NoOp`, adiável sem bloquear a capacidade — um futuro provedor concreto a consome, nunca o contrário.
