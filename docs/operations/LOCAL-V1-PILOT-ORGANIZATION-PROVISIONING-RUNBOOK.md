# Local V1 Pilot Organization Provisioning Runbook

- **Escopo:** Controlled Pilot pre-provisioning (Cenário A, `docs/product/governance/LOCAL-V1-PILOT-FINDINGS-REVIEW.md` Seção 8). Prepara uma organização (tenant) e seus usuários **antes** de uma sessão de piloto, sem UI de Organization Administration (que não existe — Finding 04b, não implementada nesta missão).
- **Não é self-service onboarding.** Requer acesso ao ambiente de deployment (variáveis de ambiente do backend). Um cliente/usuário externo nunca executa este runbook sozinho.
- **Mecanismo:** reutiliza integralmente o padrão já existente de bootstrap idempotente em boot (`src/services/identity/auth_service.py`, `bootstrap_identities()`), generalizado por `AuthService.bootstrap_organization()` — a mesma lógica transacional de `bootstrap_administrator()`/`bootstrap_demo_user()`, parametrizada por nome de organização em vez de um valor fixo. **Nenhum endpoint novo, nenhuma UI nova.**

## 1. Criar/provisionar a organização + organization_admin

Definir 3 variáveis de ambiente no backend antes do boot (mesmo arquivo `.env` do backend, ou `demo/.env` no fluxo local — ver `.env.example`):

```
PILOT_ORGANIZATION_NAME=Piloto Externo A
PILOT_ORGANIZATION_ADMIN_EMAIL=admin@piloto-a.example
PILOT_ORGANIZATION_ADMIN_PASSWORD=<senha real, nunca commitada>
```

O nome acima (com espaços, sem aspas) é copy/paste-safe: `demo/start-demo.sh` carrega `demo/.env` por um loader linha-a-linha (não mais `source`), que não re-interpreta o valor como sintaxe de shell — funciona igual com ou sem aspas ao redor do valor (Local V1 Pilot Final Hardening, H2/D-223; `tests/shell/test_start_demo_env_loader.sh`, cenários A-H).

Reiniciar o backend (`bash demo/stop-demo.sh && bash demo/start-demo.sh`, ou o equivalente de produção/staging). No boot, `bootstrap_identities()` chama `AuthService.bootstrap_organization(...)`:

- Se a organização com esse nome já existir, é reaproveitada (idempotente — nunca duplica).
- Se o e-mail do admin já existir naquela organização, o bootstrap é pulado (nunca recria/reseta a senha de um usuário existente — mesma disciplina do bootstrap do Administrator).
- Caso contrário, cria a organização, cria o usuário, e atribui o papel `organization_admin` — tudo numa única transação.

**Nunca deixar essas 3 variáveis definidas permanentemente após o boot inicial** — elas só precisam estar presentes na primeira subida com a organização nova; removê-las depois evita reprocessamento desnecessário a cada boot (o bootstrap já é idempotente, mas a intenção operacional é "provisionar uma vez").

## 2. Confirmar o slug da organização (necessário para login)

O slug é derivado automaticamente do nome (`organization_slug()`, `src/database/project_identity.py`) — minúsculas, acentos removidos, espaços e caracteres não-alfanuméricos viram `-`. Para `"Piloto Externo A"`, o slug é `piloto-externo-a`. Confirmar via:

```
GET /api/admin/organization
Headers: X-Stratech-User-Id, X-Stratech-Organization-Id, X-Stratech-Session-Id (do admin recém-provisionado, obtidos no passo 5)
```

## 3. Confirmar roles/permissions do admin

```
GET /api/admin/users/{user_id}/roles
```

Deve retornar exatamente `["organization_admin"]`. Se vazio ou incorreto, **não prosseguir** — investigar antes de convidar usuários reais.

## 4. Criar/convidar os usuários reais do piloto

Duas opções, ambas já reais e testadas — **nenhuma exige endpoint novo**:

- **Criação direta** (`POST /api/admin/users`, corpo `{email, display_name, password, role_name}`) — o admin do piloto define a senha inicial diretamente. Mais simples para um piloto pequeno e controlado.
- **Convite** (`POST /api/admin/invitations`, corpo `{email, role_name}`) — gera um token; como não há provedor de e-mail real configurado (`NotificationProvider` é `NoOp`), o link precisa ser entregue manualmente ao convidado, que define sua própria senha em `POST /api/invitations/accept`.

Escolher conforme o perfil do piloto (poucos usuários pré-combinados → criação direta; usuários que devem escolher a própria senha → convite).

## 5. Validar login

Navegador → `/entrar` → organização = slug do passo 2, e-mail/senha do usuário provisionado → confirmar redirecionamento para `/dashboard`. Equivalente via API: `POST /api/auth/login` com `{organization, email, password}` → `200` com `user_id`/`organization_id`/`session_id`.

## 6. Validar tenant isolation

Com dois usuários de organizações diferentes (o admin do piloto e qualquer usuário de outra organização já existente, ex. "Organização Principal"), confirmar que um não acessa recursos do outro — a convenção do produto é sempre **404** (nunca 403, nunca vazamento de existência), tanto para leitura quanto escrita. Reproduzido mecanicamente em `tests/test_pilot_organization_provisioning.py::test_tenant_isolation_holds_between_pilot_and_default_organization`.

## 7. Validar acesso esperado às Capabilities

Confirmar que o admin do piloto acessa normalmente: Dashboard, Priorização, Projetos, Program Management, Project Delivery, Ações, Decisões, Aprendizados, Documentos, Administração (Usuários/Convites/Sessões) — a mesma jornada crítica já validada em missões anteriores, agora sob a identidade do tenant do piloto em vez da organização padrão.

## Rehearsal (ensaio) desta missão

O ensaio completo dos 7 itens acima foi executado como teste de integração real (`tests/test_pilot_organization_provisioning.py`), contra um Postgres real (via `tests/db.py::temp_database_url`, o mesmo mecanismo de toda a suíte de integração do repositório), com dados exclusivamente sintéticos (`"Piloto Externo A"`, `admin@piloto-a.example`) — nunca dados reais. Isso prova mecanicamente, em CI, que: a organização é criada; o admin é funcional (login real via `POST /api/auth/login`); o papel correto é atribuído; um usuário do piloto pode ser criado e faz login; o isolamento entre tenants se mantém (404 cross-tenant); e o acesso à própria organização funciona. **Isso valida o mecanismo de ponta a ponta, mas não substitui um ensaio manual na máquina física antes do piloto externo real** — recomendado como próximo passo operacional, não bloqueante para este gate técnico.

## O que este runbook explicitamente NÃO cobre

- Autoatendimento (self-service) de criação de organização por um cliente — não existe hoje (Finding 04b, `LOCAL-V1-PILOT-FINDINGS-REVIEW.md` Seção 8b), fica para uma missão futura de Organization Administration UI.
- Provisionamento de mais de uma organização simultânea em escala — cada organização exige repetir este runbook uma vez (variáveis de ambiente diferentes, boot separado ou reboot com as novas variáveis). Viável para um punhado de organizações de piloto controlado; não é a solução para dezenas/centenas.
