# Technical Design — Server-side Sessions (Enterprise Administration, item 5 — resolves TD-010)

**Base:** `WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md` §6 item 5; `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` (Sessões, Nível 2); Technical Debt `TD-010`.
**Status:** implementação concluída — segue diretamente do fluxo institucional, sem impacto arquitetural fora do escopo já aprovado de Enterprise Administration.

---

## 1. O problema (TD-010)

A sessão da STRATECH sempre foi um cookie HMAC-assinado **sem estado no servidor** (`web/lib/session.ts`; `AuthService.logout()` era um no-op documentado: "No server-side session store exists yet"). Consequências:

- Não havia como **listar** as sessões ativas de uma organização.
- Não havia como **revogar** uma sessão antes da expiração natural de 12h — um "logout" era apenas o cliente descartando o cookie; o token continuava criptograficamente válido.
- Um usuário desativado/removido mantinha acesso por até 12h.

O Blueprint de Administration assumiu incorretamente que "Sessões" era "só leitura+revogação sobre o que já existe". TD-010 registrou a correção: não existia store para ler nem revogar.

## 2. Decisão central — o backend passa a ser a autoridade da sessão, o mecanismo do cookie não muda

Uma nova tabela `sessions` (`id` = o próprio UUID da sessão, `user_id`, `organization_id`, `created_at`, `last_seen_at`, `revoked_at`). O `session_id` deixa de ser gerado pelo BFF (`crypto.randomUUID()`) e passa a ser **cunhado pelo backend** em `AuthService.create_session`, chamado por `POST /api/auth/login` logo após `authenticate()` ter sucesso. O BFF apenas assina, no cookie HMAC, o `session_id` que o backend retorna — o mecanismo do cookie em si (assinatura, TTL, verificação) é inalterado. Assim os dois lados concordam sobre um único identificador que a tabela `sessions` rastreia.

`AuthService.logout()` deixa de ser no-op e passa a revogar a linha correspondente (idempotente — um `session_id` sem linha é silenciosamente ignorado).

## 3. Enforcement de revogação — sem quebrar o caminho DB-free de `get_request_context`

O ponto sensível: revogar "em toda requisição" implicaria checar o banco no caminho de 3 headers de `get_request_context`, que hoje é deliberadamente livre de banco, e ~12 arquivos de teste sobrescrevem `build_permission_checker` sem um repositório real. Piggyback ingênuo forçaria esses testes a um banco real.

**Solução:** a checagem de revogação entra em `require_permission` (por onde toda rota protegida já passa) via uma dependência dedicada e sobrescritível, `build_session_revocation_checker` (um callable `session_id -> is_revoked`). O `conftest` autouse a sobrescreve, para toda a suíte, com "nunca revogada" — exatamente o mesmo padrão já usado para `verify_api_key`/`enforce_rate_limit`. Produção nunca sobrescreve, então roda o check real DB-backed; os testes que exercitam revogação de fato (`test_session_revocation_enforcement.py`) sobrescrevem com o checker real apontado ao seu próprio banco temporário. Custo zero para todo teste existente, enforcement real em produção.

**Fail-open por design:** `is_session_revoked` só retorna `True` quando existe uma linha **com `revoked_at` explícito**. Um `session_id` desconhecido (que precede o store, ou um id fabricado de fixture) é tratado como ativo, nunca revogado — é isso que permite ligar o enforcement sem quebrar retroativamente nenhuma sessão não rastreada. Sessões `api-key:` (o caminho de API Key) são puladas, pois já têm sua própria revogação via a chave.

## 4. Rotas administrativas (`sessions.manage`, migração 0012, `organization_admin` apenas)

| Rota | Efeito |
|---|---|
| `GET /api/admin/sessions` | Lista as sessões ativas (não revogadas) da organização. |
| `DELETE /api/admin/sessions/{id}` | Revoga; responde `200` com o recurso (não `204` — mesma convenção de `revoke_api_key`, `forwardDomainRequest` sempre parseia corpo JSON). |

Sem rota de criação — sessões nascem do login, não de um formulário. **Isolamento por tenant** é imposto no `AdministrationService`: `session_id` é um UUID globalmente único, então a revogação verifica `get_session(...).organization_id` antes de revogar (uma sessão de outra organização retorna `None` → 404), em vez de escopar no repositório como `ApiKey` (que usa id inteiro sequencial e precisa de escopo composto). Cada revogação é auditada (`session.revoked`), nunca o conteúdo da sessão.

## 5. Frontend

Página `/administracao/sessoes` (12º item de navegação, "Sessões"), mesmo padrão de dados de `/administracao/api-keys` (hook de leitura + mutação de revogação, invalidação de `["admin-sessions"]`), com diálogo de confirmação de revogação. Sem criação (sessões vêm do login).

## 6. Impacto e compatibilidade

- Aditivo: nova tabela, nova permissão, novas rotas. Nenhuma rota existente muda de assinatura.
- `LoginResponse` ganha `session_id` (campo novo, aditivo). O BFF passa a ler e assinar esse campo.
- Nenhuma migração de dado. Sessões anteriores a este store simplesmente não são rastreadas (fail-open) — expiram naturalmente como sempre fizeram.

## 7. Testes

- Migração (`test_migration_0012_sessions.py`): tabela + permissão; downgrade.
- Repositório (`TestSessions` em `test_administration_repository.py`): CRUD, escopo por organização, idempotência de revogação, semântica fail-open de `is_session_revoked`.
- Serviço (`TestSessions` em `test_administration_service.py`): auditoria, isolamento por tenant na revogação.
- API (`TestSessions` em `test_administration_api.py`): as 2 rotas, RBAC (`403`), isolamento por organização.
- Enforcement ponta a ponta (`test_session_revocation_enforcement.py`): sessão ativa → 200; revogada → 401 na requisição seguinte; id não rastreado → 200.
- Login (`test_auth_api.py`): a resposta agora carrega `session_id` e cria a linha.
- Frontend: `session.test.ts` (o cookie preserva o id do backend), `sessions-admin.spec.ts` (E2E: navegação, redirecionamento não autenticado, listagem, revogação com confirmação).

## 8. Veredito

Nenhum conflito arquitetural. TD-010 resolvido: a revogação de sessão que o Blueprint assumia existir agora existe de fato, sem quebrar o mecanismo de cookie nem o caminho DB-free de `get_request_context`.
