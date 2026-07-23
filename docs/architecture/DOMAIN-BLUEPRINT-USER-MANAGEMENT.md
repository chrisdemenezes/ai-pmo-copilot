# Domain Blueprint — User Management (Enterprise Administration, Nível 1)

**Wave:** 2 (Enterprise Master Execution Program)
**Epic:** Enterprise Administration — fecha a sub-área "Usuários" do Nível 1, já aprovada em
`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §2 ("tela é só CRUD sobre o que já existe").
**Status:** Blueprint conceitual — não implementa, não produz código. Aguarda aprovação do Founder.
**Gatilho:** revisão de fechamento da Wave 2 (2026-07-23) identificou que Enterprise Administration
está incompleto exclusivamente por esta Capability faltar — Organizações, Papéis e Auditoria já
estão fechados.

---

## 0. Escopo — o que este Blueprint cobre e o que não cobre

**Dentro do escopo (per Nível 1, sem novo conceito de domínio):**
- Listagem de usuários (já existe — `GET /admin/users` — este Blueprint só formaliza o restante)
- Cadastro de usuários
- Edição de usuários
- Ativação/Inativação
- Associação à Organização (já existe no schema — `User.organization_id` — sem mudança)
- Associação de Roles (já existe — `POST /admin/users/{id}/roles` — sem mudança)
- RBAC aplicado (reaproveita `administration.write`/`administration.read`, migração 0007 — nenhuma
  permissão nova)
- Auditoria das operações (reaproveita `audit_logs`, mesma tabela de "Auditoria" — nenhum store novo)
- Integração Backend → BFF → Frontend completa (hoje: zero BFF, zero Frontend administrativo)

**Fora do escopo (explicitamente, per o próprio Nível 3 do Blueprint de Administration e per
diretriz desta missão):**
- Convites (pertence a "Convites e Stakeholders", Master Roadmap §3.2 — item separado, não tocado aqui)
- SSO — não existe em nenhum Blueprint/ADR da STRATECH; introduzi-lo seria criar um novo provider de
  identidade, proibido por CLAUDE.md sem uma decisão de arquitetura prévia
- MFA — mencionado apenas como possibilidade futura em "Segurança" (Nível 2), nunca como parte de
  User Management; nenhum schema/decisão existe hoje
- Sessões (revogação, listagem) — não implementado por D-035 (não existe session store); não
  reaberto por este Blueprint
- Qualquer coisa de Wave 3 (Enterprise Intelligence) — não antecipada

---

## 1. Estado atual (o que já existe, reaproveitado sem alteração)

| Componente | Onde | Reaproveitado como |
|---|---|---|
| `User` model (`id`, `organization_id`, `email`, `display_name`, `password_hash`, `identity_type`, `created_at`) | `src/database/models.py` | Base da entidade — ganha 1 coluna nova (ver §2) |
| `EnterpriseRepository.create_user_in_session` | `src/database/enterprise_repository.py` | Reaproveitado tal qual para o cadastro (já cria com `password_hash`) |
| `EnterpriseRepository.assign_role_in_session` (idempotente) | idem | Reaproveitado tal qual — já é a operação de "Associação de Roles" |
| `AdministrationRepository.list_users_by_organization` | `src/database/administration_repository.py` | Reaproveitado tal qual — já é "Listagem" |
| `Argon2PasswordHasher` | `src/services/identity/password_hashing.py` | Reaproveitado para gerar `password_hash` no cadastro — nenhum novo mecanismo de hash |
| `administration.read`/`administration.write` (migração 0007) | `alembic/versions/0007_*.py` | Cobrem exatamente estas operações — descrição já é "Administrar organização, **usuários** e papéis". Nenhuma permissão nova. |
| `AuditLog` / `record_audit` | `src/database/administration_repository.py` | Reaproveitado — cada mutação de usuário grava uma entrada, mesmo padrão de Portfolio/Program/Project (Sprint 4) |
| `require_permission()` | `src/api/authorization.py` | Reaproveitado nas novas rotas, mesmo padrão de todas as outras |

**Nenhum componente novo de infraestrutura é necessário.** Esta Capability é, estritamente, a
mesma extensão de "CRUD sobre o que já existe" que o Blueprint original previu — o motivo de não
ter sido fechada na Sprint 4 foi de sequenciamento (a Sprint priorizou Organização/Papéis/Auditoria
primeiro), não uma decisão de excluir Usuários.

## 2. Lacuna de schema — 1 coluna nova, sem migração de dado

`User` não tem hoje nenhuma coluna de estado ativo/inativo. Necessário:

```
users.is_active BOOLEAN NOT NULL DEFAULT TRUE
```

- Aditiva, sem impacto em linhas existentes (default `TRUE` preserva todo usuário já cadastrado
  como ativo).
- Inativação é **lógica** (soft state), nunca um DELETE — consistente com o resto do domínio
  (nenhuma entidade Enterprise tem hard delete hoje; RBAC nunca teve um caso de uso de exclusão
  física de usuário).
- Login (`AuthService.authenticate`) precisa checar `is_active` — um usuário inativo não deve
  autenticar. Este é o único ponto de código fora de `src/services/administration_service.py` que
  este Blueprint toca, e é a extensão mínima necessária para "Inativação" significar algo real (não
  apenas um campo cosmético).

## 3. Camada de API (Backend)

Novos endpoints em `src/api/routes/administration.py`, mesmo router, mesmo padrão de autenticação
já usado por todas as rotas de Administration (`verify_api_key` + `enforce_rate_limit` +
`get_request_context` + `require_permission`):

| Método | Rota | Permissão | Operação |
|---|---|---|---|
| `GET` | `/admin/users` | `administration.read` | Já existe — sem mudança |
| `POST` | `/admin/users` | `administration.write` | Cadastro — organização vem do contexto (`X-Stratech-Organization-Id`), nunca do corpo (evita criar usuário em outra organização) |
| `GET` | `/admin/users/{id}` | `administration.read` | Detalhe de um usuário (necessário para a tela de edição) |
| `PATCH` | `/admin/users/{id}` | `administration.write` | Edição (`display_name`, `email`) — mesmo padrão de `PATCH /admin/organization` |
| `PATCH` | `/admin/users/{id}/status` | `administration.write` | Ativação/Inativação (`{"is_active": bool}`) — rota própria, não misturada em `PATCH /{id}`, mesmo raciocínio de "uma mutação, uma intenção clara" já usado por `assign_role` ser uma rota separada |
| `POST` | `/admin/users/{id}/roles` | `administration.write` | Já existe — sem mudança |

Todas as rotas de escrita seguem o padrão já estabelecido em Sprint 4: 404 (nunca 403) para um
`user_id` de outra organização (cross-tenant guard idêntico ao já usado por
`AdministrationRepository.assign_role`), e uma entrada em `audit_logs` por mutação
(`user.created`, `user.updated`, `user.activated`/`user.deactivated`, `user.role_assigned` — este
último já existe desde a Sprint 4).

## 4. Camada de Serviço e Repositório

- `AdministrationRepository` ganha: `create_user`, `get_user`, `update_user`, `set_user_active`.
  Todos seguem o padrão já existente de cross-tenant guard + `record_audit` interno, mesmo
  desenho de `assign_role`.
- `AdministrationService` ganha os métodos correspondentes — mesma divisão de responsabilidade já
  documentada (rotas finas, serviço decide auditoria e mapeamento de erro).
- **Nenhum novo Bounded Context, nenhum novo Repository sibling.** `AdministrationRepository`
  permanece o dono de todas as operações administrativas (já é o sibling correto desde a Sprint 4).

## 5. BFF (Backend-for-Frontend)

Hoje **não existe nenhuma rota BFF de administração** — este é o primeiro ponto genuinamente novo,
mas segue exatamente o padrão já estabelecido pelo Domain BFF (Sprint 5,
`web/lib/bff/domain-proxy.ts`):

- `web/app/api/bff/admin/users/route.ts` (`GET`, `POST`)
- `web/app/api/bff/admin/users/[id]/route.ts` (`GET`, `PATCH`)
- `web/app/api/bff/admin/users/[id]/status/route.ts` (`PATCH`)
- `web/app/api/bff/admin/users/[id]/roles/route.ts` (`POST`)
- `web/app/api/bff/admin/roles/route.ts` (`GET` — necessário para a tela de associação de papéis
  já listar as opções disponíveis; `AdministrationRepository.list_roles` já existe)

Reaproveita `forwardDomainRequest` (`web/lib/bff/domain-proxy.ts`) tal qual — nenhum novo helper de
proxy, nenhum novo contrato de erro/timeout.

## 6. Frontend

Também greenfield (nenhuma tela administrativa existe hoje):

- Nova rota `web/app/administracao/usuarios/page.tsx` (ou equivalente sob um item de navegação
  "Administração" já previsto pelo Blueprint original) — lista usuários da organização, com ação de
  cadastro, edição e ativação/inativação inline, e um seletor de papel reaproveitando
  `GET /api/bff/admin/roles`.
- Camada de domínio `web/lib/domain/user.ts` (ou `web/lib/admin/user.ts`, a definir em Technical
  Design) seguindo o mesmo padrão de accessor assíncrono já pago 3 vezes (D-011: `listPortfolios`/
  `listPrograms`/`listProjects`) — `listUsers()`, `createUser()`, `updateUser()`, `setUserActive()`,
  `assignRole()`.
- Nenhum componente de UI novo além do que o design system já oferece (tabela, formulário, toggle —
  todos já usados em outras telas do produto).

## 7. RBAC

Nenhuma permissão nova. `administration.write` (já atribuída a `organization_admin`) cobre todas as
mutações; `administration.read` (já atribuída a `organization_admin` e `pmo`) cobre listagem e
detalhe. `viewer` e `project_manager` continuam sem acesso a nenhuma rota de Administration — sem
mudança de comportamento para eles.

## 8. Auditoria

Cada mutação grava exatamente uma entrada em `audit_logs`, mesmo padrão já usado por
Portfolio/Program/Project e por `assign_role`:

| Ação | `entity_type` | Quando |
|---|---|---|
| `user.created` | `user` | Cadastro |
| `user.updated` | `user` | Edição de `display_name`/`email` |
| `user.activated` / `user.deactivated` | `user` | Mudança de `is_active` |
| `user.role_assigned` | `user` | Já existe desde a Sprint 4 (renomear para este padrão se o nome atual divergir — verificar em Technical Design) |

## 9. Testes (escopo esperado, não implementado por este documento)

- Migração (schema `is_active`, default, backfill implícito, downgrade).
- `AdministrationRepository`: create/get/update/set_active, cross-tenant guard em cada um.
- `AdministrationService`: mapeamento de erro, chamadas de auditoria.
- `AdministrationRepository.create_user` + login: usuário inativo não autentica (`AuthService`).
- API: as 5 rotas novas, RBAC (403 para `viewer`/`project_manager`, 404 cross-tenant), auditoria
  end-to-end (criar usuário via API, confirmar entrada em `audit_logs`).
- BFF: as 5 rotas novas, 401 sem sessão, forwarding correto de headers institucionais.
- Frontend: componente/página de listagem+cadastro+edição+ativação, mesmo padrão de teste já usado
  para Portfolio/Program/Project.
- E2E: pelo menos 1 fluxo completo (login como `organization_admin` → cadastrar usuário → atribuir
  papel → inativar), cobrindo a cadeia página → hook → fetch → BFF → backend → banco.

## 10. Fundamentado vs. depende do Founder vs. exige definição arquitetural

| Fundamentado (pode virar Technical Design assim que ratificado) | Depende do Founder | Exige definição arquitetural antes de qualquer decisão |
|---|---|---|
| Todo o escopo deste documento (§1-9) — schema, API, BFF, Frontend, RBAC, Auditoria, todos reaproveitando mecanismos já existentes | — | — |

Nenhum item deste Blueprint exige uma decisão de arquitetura nova — é estritamente a extensão já
prevista e aprovada em `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §2 ("Usuários... Nível 1 —
já aprovado"), fechando o que a Sprint 4 deixou parcial.

---

## 11. Critério de encerramento da Wave 2

Com esta Capability implementada e testada, o Epic Enterprise Administration fecha o Nível 1
(Usuários, Organizações, Papéis, Auditoria) integralmente, e a Wave 2 do Enterprise Master
Execution Program pode ser declarada oficialmente encerrada — restando apenas os itens já
registrados como fora de escopo por decisão própria (Sessões/TD-010, Configurações, Convites/
Stakeholders), nenhum dos quais bloqueia o fechamento da Wave.
