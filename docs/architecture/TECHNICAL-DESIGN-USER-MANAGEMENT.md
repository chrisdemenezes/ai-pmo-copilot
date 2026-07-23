# Technical Design — User Management (Enterprise Administration, Nível 1)

**Base:** `DOMAIN-BLUEPRINT-USER-MANAGEMENT.md` (aprovado com condições pelo Founder, 2026-07-23).
**Status:** resolve os 8 critérios obrigatórios exigidos na aprovação. Nenhum código ainda —
implementação segue imediatamente após este documento, sem nova autorização, salvo achado de
conflito arquitetural (nenhum encontrado).

---

## 1. Mecanismo de credencial inicial (ponto de decisão explícito do Founder)

**Decisão: o administrador define a senha inicial diretamente no formulário de cadastro.** Nenhum
e-mail, token ou link é enviado; nenhum fluxo de "convite" ou "reset" é criado.

Isso não constitui uma capacidade nova: `EnterpriseRepository.create_user_in_session` já exige
`password_hash` como parâmetro obrigatório desde o Épico 2 (é assim que
`bootstrap_administrator`/`bootstrap_demo_user` criam usuários hoje). A Capability User Management
reaproveita exatamente esse mecanismo — o admin informa uma senha em texto no formulário, o backend
aplica `Argon2PasswordHasher.hash()` antes de qualquer persistência, e o texto puro nunca é
armazenado, logado, retornado na resposta ou incluído no audit log.

**Por que isto não exige uma Decision Proposal:** o Founder pediu para parar caso o mecanismo de
credencial "torne indispensável alguma capacidade semelhante a convite ou reset de senha". Definir
a senha diretamente evita essa necessidade por completo — é estritamente equivalente ao padrão já
existente de bootstrap, não uma capacidade de e-mail/token nova. Nenhum fluxo de "trocar senha no
primeiro login" é implementado (ficaria fora do escopo de Frontend aprovado, que lista apenas
listar/pesquisar/filtrar/cadastrar/editar/ativar/inativar/atribuir-remover role).

## 2. Normalização e unicidade de e-mail

- `email` é normalizado (`strip()` + `lower()`) em um único helper (`src/services/identity/email_normalization.py::normalize_email`) reaproveitado em 3 pontos: cadastro (`AdministrationRepository.create_user`), edição de e-mail (`AdministrationRepository.update_user`), e login (`AuthService.authenticate`, para que um e-mail cadastrado como `Ana@Empresa.com` autentique também como `ana@empresa.com`).
- **Unicidade garantida no banco, não só na aplicação** (fecha a exigência de "tratar conflitos de e-mail e atualizações concorrentes" sem depender de um `SELECT` prévio que teria uma janela de corrida): migração `0009` substitui a constraint `uq_users_org_email` (case-sensitive, sobre o valor bruto) por um índice único funcional `uq_users_org_email_lower` sobre `(organization_id, lower(email))`. Uma violação de concorrência vira `IntegrityError` no Postgres, capturada pelo repository e mapeada para `EmailConflictError` (nova exceção de domínio, mesmo padrão de `CrossTenantViolationError`), que a rota mapeia para **HTTP 409**.
- Dados existentes (hoje: só o usuário demo, já em minúsculas) não exigem migração de dado — documentado explicitamente, não uma omissão silenciosa.
- `display_name` obrigatório — já é `NOT NULL` no schema; validação Pydantic (`min_length=1`) apenas formaliza na borda da API.

## 3. Transações

`AdministrationRepository.create_user` compõe `EnterpriseRepository.create_user_in_session` +
`EnterpriseRepository.assign_role_in_session` (ambas já desenhadas para rodar na mesma sessão) +
`record_audit`, tudo em uma única sessão/commit — se a atribuição de papel falhar, o usuário não
fica órfão sem papel (mesmo padrão já testado em `AuthService.bootstrap_administrator`,
`test_atomic_when_role_assignment_fails`).

## 4. Proteções de governança (bloqueio de auto-exclusão e do último administrador)

Ambas as checagens rodam **dentro da mesma transação** da mutação, com `SELECT ... FOR UPDATE`
sobre as linhas de usuário administrador da organização (fecha a corrida entre duas requisições
concorrentes tentando inativar/despromover admins diferentes ao mesmo tempo):

- **Auto-inativação:** `AdministrationService.set_user_active` rejeita com `400` se
  `target_user_id == actor_user_id` e a operação for inativar (ativar a si mesmo sempre é permitido,
  não há risco).
- **Último administrador ativo:** antes de (a) inativar um usuário com papel `organization_admin`,
  ou (b) remover o papel `organization_admin` de um usuário, `AdministrationRepository` conta
  usuários **ativos** da organização com esse papel (com `with_for_update()`); se o alvo é o único,
  rejeita com `409` (estado do sistema em conflito com a operação pedida, não um erro de input do
  cliente — `400` fica reservado para auto-inativação, que é sempre inválida independente do
  estado do sistema).

## 5. `is_active` — enforcement em toda a cadeia, não só no login

- Migração `0009` adiciona `users.is_active BOOLEAN NOT NULL DEFAULT TRUE` (aditiva, sem impacto em
  linhas existentes).
- **Login:** `AuthService.authenticate` retorna `None` se `user.is_active is False` (mesmo
  tratamento uniforme de falha já usado para organização/usuário/senha incorretos — EO-015 exige
  que essas causas sejam indistinguíveis para quem chama).
- **APIs protegidas:** `SqlPermissionChecker.has_permission` — o único ponto por onde toda rota
  protegida já passa (`require_permission`, sem exceção) — ganha um `JOIN` adicional contra
  `users.is_active`. Um usuário inativo nunca tem `has_permission()` retornando `True`, para
  nenhuma permissão, em nenhuma rota, sem precisar tocar em cada rota individualmente.

## 6. Escopo de organização

Toda leitura/mutação de usuário já filtra por `User.organization_id == context.organization.organization_id` (mesmo padrão de `assign_role` hoje) — usuário de outra organização retorna **404**, nunca 403 (convenção já estabelecida desde a Sprint 2, "not found e not yours mapeiam para a mesma resposta").

## 7. Auditoria — estado anterior/posterior, nunca credenciais

`record_audit`'s `details` (JSON) recebe um dicionário com chaves explícitas e uma allowlist — nunca o corpo bruto da requisição, para que `password`/`password_hash` jamais alcancem o audit log por acidente:

| Ação | `details` |
|---|---|
| `user.created` | `{"email": ..., "display_name": ..., "organization_id": ...}` (sem senha) |
| `user.updated` | `{"before": {"email": ..., "display_name": ...}, "after": {...}}` |
| `user.activated` / `user.deactivated` | `{"before": {"is_active": ...}, "after": {"is_active": ...}}` |
| `user.role_assigned` | `{"role_name": ...}` (já existe, sem mudança) |
| `user.role_removed` | `{"role_name": ...}` |

## 8. API (novas rotas em `src/api/routes/administration.py`)

| Método | Rota | Permissão | Resposta de erro |
|---|---|---|---|
| `POST` | `/admin/users` | `administration.write` | `409` conflito de e-mail |
| `GET` | `/admin/users/{id}` | `administration.read` | `404` cross-tenant/inexistente |
| `PATCH` | `/admin/users/{id}` | `administration.write` | `404`, `409` |
| `PATCH` | `/admin/users/{id}/status` | `administration.write` | `404`, `400` auto-inativação, `409` último admin |
| `DELETE` | `/admin/users/{id}/roles/{role_name}` | `administration.write` | `404`, `409` último admin |

`UserResponse` ganha o campo `is_active`.

## 9. BFF e Frontend

5 rotas BFF novas (`web/app/api/bff/admin/users/**`), reaproveitando `forwardDomainRequest` sem
alteração. Frontend: `web/app/administracao/usuarios/page.tsx` — tabela com busca (nome/e-mail),
filtro por status e por role, badge de status, formulário de cadastro/edição, diálogo de
confirmação para inativar/remover role, estados de loading/vazio/sucesso/erro — mesmo padrão visual
já usado nas telas de Portfolio/Program/Project.

## 10. PostgreSQL

Migração `0009` testada com upgrade/downgrade completo em Postgres real; todos os testes novos
usam `tests/db.py::temp_database_url` (nenhuma dependência de SQLite); seed (migração 0008)
permanece idempotente e inalterado (usuários criados por esta Capability não fazem parte do seed).

## 11. Fora de escopo (reafirmado)

Convites por e-mail, SSO, MFA, session store, recuperação/reset de senha, stakeholders,
configurações gerais, Wave 3 — nenhum destes é tocado, per §1 acima.
