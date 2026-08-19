# Technical Design — API Keys (Enterprise Administration, Nível 1, D-051)

**Base:** `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §0 (reclassificação Nível 3 → Nível 1) + `AR-4-API-KEYS-REVIEW.md` (aprovado sem ressalvas).
**Status:** implementação segue imediatamente após este documento, sem nova autorização, per a decisão do Founder ("não interrompa a execução... apenas em caso de impossibilidade técnica objetiva" — nenhuma encontrada).

---

## 1. Modelo de domínio

Uma `ApiKey` pertence a uma organização e a um usuário criador; autentica **como esse usuário** em toda requisição subsequente — não introduz um segundo modelo de identidade/permissão.

```
ApiKey
  id
  organization_id      -> organizations.id
  created_by_user_id    -> users.id
  name                   texto livre, definido pelo usuário (ex.: "CI Pipeline")
  key_prefix             primeiros len("sk_live_") + 8 caracteres do segredo, exibido para sempre
  hashed_secret          Argon2, nunca exposto após a criação
  created_at
  last_used_at            atualizado a cada autenticação bem-sucedida
  revoked_at              NULL enquanto ativa; setado uma vez, nunca desfeito
```

Migração `0011`: cria `api_keys` + índices em `id`/`organization_id`; semeia a permissão `api_keys.manage`, atribuída apenas a `organization_admin` — mesmo padrão de toda permissão administrativa existente (nenhuma permissão nova de leitura separada: quem gerencia, lista).

## 2. Formato e ciclo de vida da chave

- Prefixo público `sk_live_` + `secrets.token_urlsafe(32)` — convenção legível (reconhecível como chave de API em logs/diffs acidentais) sem depender de um formato proprietário novo.
- `key_prefix` (primeiros `len("sk_live_") + 8` caracteres) é armazenado e devolvido em toda listagem — permite ao usuário reconhecer qual chave é qual sem nunca reexibir o segredo completo.
- O valor em texto puro (`plaintext_key`) só existe na resposta HTTP da criação (`201`) — nunca persistido, nunca logado, nunca reexibido por nenhuma outra rota. Este é o único momento em que o usuário pode copiá-lo.
- Revogação é permanente e idempotente por design: `revoke_api_key` retorna `None` tanto para "não encontrada" quanto para "já revogada" — ambos os casos mapeiam para o mesmo comportamento na rota (idempotência, mesmo padrão já usado em `remove_role`), evitando um cliente tratar re-revogação como erro.

## 3. Autenticação — reaproveitando 100% do RBAC existente

**Decisão central:** uma segunda via de autenticação em `get_request_context`, aditiva aos 3 headers de sessão já existentes (`X-Stratech-User-Id`/`X-Stratech-Organization-Id`/`X-Stratech-Session-Id`), nunca os substituindo:

```
X-Stratech-Api-Key: sk_live_...
```

- Lookup em duas etapas, mesmo raciocínio de "estreitar por campo barato, depois verificar segredo" já usado no login por e-mail: `list_active_api_keys_by_prefix(key_prefix)` filtra por `key_prefix` (não secreto, indexável) excluindo revogadas; cada candidata tem seu `hashed_secret` verificado via `Argon2PasswordHasher.verify` até achar a correspondência (ou nenhuma, retornando `401`).
- Uma vez autenticada, a chave produz o mesmo `RequestContext` que qualquer sessão produziria: `AuthenticatedUser(user_id=api_key.created_by_user_id, ...)`, `OrganizationIdentity(organization_id=api_key.organization_id, ...)`, `SessionIdentity(session_id=f"api-key:{api_key.id}")` (prefixo distinto, para que audit logs de ações feitas via chave sejam identificáveis sem precisar de um campo novo). **Toda rota já protegida por `require_permission(...)` passa a aceitar API Keys automaticamente, sem nenhuma mudança na própria rota** — o RBAC é resolvido a partir do usuário resultante, exatamente como uma sessão normal.
- **Ponto de Dependency Injection:** `build_repository()`/`AdministrationService(...)` são chamados como função Python simples, dentro do `if x_stratech_api_key:`, não como um parâmetro `Depends(...)` declarado na assinatura de `get_request_context`. Um `Depends(...)` ali seria resolvido pelo FastAPI em toda chamada da função — que roda em toda rota autenticada, em toda suíte de teste existente — forçando a construção de um repositório real mesmo quando nenhuma chave é enviada. A chamada direta é genuinamente lazy: só executa quando o header está presente. Custo aceito: esse caminho não é interceptável via `app.dependency_overrides` (mitigado, no único teste que precisa, via `build_repository.cache_clear()` + `DATABASE_URL` de teste).
- `last_used_at` é atualizado a cada autenticação bem-sucedida (`touch_api_key_last_used`) — dá ao administrador visibilidade sobre quais chaves estão realmente em uso antes de revogar uma.

## 4. Rotas (Administration, `api_keys.manage`)

| Rota | Efeito |
|---|---|
| `GET /api/admin/api-keys` | Lista chaves da organização — nunca inclui `hashed_secret`. |
| `POST /api/admin/api-keys` | Cria; resposta única (`201`) inclui `plaintext_key`. |
| `DELETE /api/admin/api-keys/{id}` | Revoga; responde `200` com o recurso atualizado (`revoked_at` preenchido) — não `204`. |

**Por que `200` com corpo, não `204`:** `web/lib/bff/domain-proxy.ts::forwardDomainRequest` (o helper de proxy compartilhado por toda rota BFF) sempre chama `backendResponse.json()` e reconstrói a resposta via `NextResponse.json(responseBody, {status})` — incompatível com um `204` sem corpo. `remove_role` (a única outra mutação tipo-DELETE neste arquivo) já segue essa convenção; API Keys mantém a mesma, em vez de introduzir uma segunda convenção de resposta.

## 5. Auditoria

`api_key.created` e `api_key.revoked` são registrados via `AdministrationRepository.record_audit` (mesmo mecanismo de toda mutação administrativa) com `details` limitado a `name`/`key_prefix` — nunca o segredo, nunca o hash.

## 6. Frontend

Página `/administracao/api-keys` (novo item de navegação, "Chaves de API"), seguindo o mesmo padrão de dados de `/administracao/usuarios` (hook de leitura + hooks de mutação, invalidação de `["admin-api-keys"]`). O diálogo de criação é a única superfície que já exibe o segredo em texto puro — em duas etapas (formulário → revelação única, sem fechar automaticamente), com botão de cópia via `navigator.clipboard`. A lista subsequente mostra sempre apenas `key_prefix`.

## 7. Correção adicional descoberta durante a implementação (fora do escopo de API Keys em si)

`web/proxy.ts::config.matcher` nunca incluiu `/administracao`/`/administracao/:path*` — gap pré-existente (um visitante não autenticado podia carregar o shell da página; as chamadas BFF já retornavam `401`). Corrigido para toda a seção Administração, não apenas a página nova, já que o mesmo gap afetava `/administracao/usuarios`.

## 8. Testes

- Migração (`tests/test_migration_0011_api_keys.py`): upgrade cria tabela + semeia permissão; downgrade remove ambos.
- Repositório (`TestApiKeys` em `tests/test_administration_repository.py`): CRUD, filtro por prefixo excluindo revogadas, idempotência de revogação.
- Serviço (`tests/test_administration_service.py`): criação (hash + prefixo + retorno único do texto puro), autenticação (sucesso, prefixo desconhecido, hash não confere, chave revogada), revogação (auditoria, idempotência).
- API (`TestApiKeys` em `tests/test_administration_api.py`): as 3 rotas, RBAC (`403` sem `api_keys.manage`), isolamento por organização.
- Autenticação ponta a ponta (`tests/test_identity_context_api_key_auth.py`): uma chave real autentica uma rota já protegida por `require_permission`, sem nenhuma mudança na rota; chave revogada e chave desconhecida retornam `401`; chave de um usuário com papel `viewer` retorna `403` em rota de escrita — prova de que o RBAC do usuário criador é herdado, não substituído.
- E2E (`web/e2e/api-keys-admin.spec.ts`): navegação, estado vazio, criação com revelação única, cópia, revogação com confirmação, redirecionamento de visitante não autenticado.

## 9. Veredito

Nenhum conflito arquitetural. Capacidade fundamental, completa, sem placeholder e sem dependência de Integration Hub — pronta para consumo por qualquer capacidade futura, incluindo um eventual Integration Hub (Wave 4), que a consumiria como mais um caso de uso, não como seu pré-requisito.
