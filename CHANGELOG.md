# Changelog

Formato leve, cronológico, por Sprint — não substitui o Decision Log (decisões) nem o Technical Debt Register (débitos). Cada entrada lista apenas o que mudou de fato no produto.

## Wave 2 — Sprint 1 (2026-07-19): Enterprise Domain persistence

**Adicionado**
- `Portfolio` e `Program` como tabelas reais persistidas (`portfolios`, `programs`), org-escopadas: `Portfolio.organization_id` direto, `Program` escopado transitivamente via `portfolio_id` (Foundation Technical Design §3.10).
- Campos de domínio de `Project` (`program_id`, `code`, `description`, `objective`, `sponsor`, `project_manager`, `status`, `health`, `priority`, datas, `progress_percentage`, `owner_json`, `milestones_json`, `team_json`) adicionados à tabela `projects` já existente (Épico 1) — **sem criar uma tabela `projects_delivery` separada**, per `DOMAIN-BLUEPRINT-PROJECT.md` (Opção A, Fase 1). Todas as colunas novas são nullable; nenhuma linha legada é afetada.
- Migração `0005_domain_persistence` (upgrade/downgrade completos, testados).
- `DomainRepository` (`src/database/domain_repository.py`): criação e leitura org-escopada de Portfolio/Program/Project, com guarda de cross-tenant (`CrossTenantViolationError`, reaproveitado do Épico 1) e o caminho de unificação de um Project legado (`attach_project_to_program`).

**Testes**
- `tests/test_migration_0005_domain_persistence.py` (4 testes: criação de tabelas, ausência de `projects_delivery`, nulidade em linhas legadas, round-trip completo de downgrade/upgrade).
- `tests/test_domain_repository.py` (12 testes: segregação de Portfolio/Program/Project por organização, criação e vínculo de Project, guardas de cross-tenant).
- Suíte completa: 179 testes passando (100% no novo módulo `domain_repository.py`, 98% de cobertura total do backend). `ruff check src tests`: sem apontamentos.

**Não incluído nesta Sprint (próxima Sprint recomendada)**
- API/rotas para Portfolio/Program/Project (Foundation Technical Design §1) — persistência ainda não é lida pelo frontend.
- RBAC enforcement (Foundation Technical Design §4 / `DOMAIN-BLUEPRINT-RBAC.md`).
- Frontend (`web/lib/domain/*.ts`) continua lendo dos arrays semeados em memória — a troca para a API real é a próxima Sprint, não esta.

## Wave 2 — Sprint 2 (2026-07-20): Enterprise API Layer

**Adicionado**
- API REST completa (GET list, GET by id, POST create) para Portfolio (`/api/portfolios`), Program (`/api/programs`) e Project Delivery (`/api/projects-delivery`) — `src/api/routes/{portfolio,program,project_delivery}.py`.
- `DomainService` (`src/services/domain_service.py`): camada de aplicação entre rotas e `DomainRepository`, com a regra "não encontrado" e "não é seu" sempre mapeadas para o mesmo 404 (nunca um 403 que confirme a existência do id em outra organização).
- Toda rota protegida por `verify_api_key` + `enforce_rate_limit` (mesmo padrão de `intelligence.py`) + `get_request_context` — **primeiro consumidor real** dessa dependência desde que foi construída no Épico 2. Escopo por organização é resolvido do header institucional (`X-Stratech-Organization-Id`), nunca de um parâmetro de query informado pelo cliente.
- **RBAC ainda não aplicado nesta Sprint** (por desenho, per diretriz do Founder): a estrutura de autenticação/escopo está pronta para receber `require_permission(...)` (`DOMAIN-BLUEPRINT-RBAC.md`) como mais um `Depends(...)` por rota, na próxima Sprint, sem alterar nenhuma assinatura de rota.
- OpenAPI/Swagger: `/docs` e `/openapi.json` documentam as 9 novas rotas (tags `portfolio`/`program`/`project-delivery`, descrições por endpoint). Versão da API elevada para `0.2.0` (`src/main.py`), com nota de escopo/RBAC na descrição do app.

**Testes**
- `tests/test_portfolio_api.py`, `test_program_api.py`, `test_project_delivery_api.py` (33 testes novos): CRUD básico, escopo por organização (inclusive listagem/`GET by id` cross-tenant retornando 404), 401 sem API key, 400 sem headers institucionais, exclusão de Projects legados sem Program da listagem.
- Suíte completa: 201 testes passando, 98% de cobertura total (100% em `domain_service.py`, `program.py`, `project_delivery.py`; 99% em `portfolio.py`, único gap é a função de wiring de DI nunca exercida sem override, mesmo padrão já aceito em `intelligence.py`). `ruff check src tests`: sem apontamentos.

**Não incluído nesta Sprint (próxima Sprint recomendada)**
- RBAC enforcement fino (`require_permission`) — `DOMAIN-BLUEPRINT-RBAC.md`.
- Migração do frontend (`web/lib/domain/*.ts`) para consumir esta API em vez do array semeado — explicitamente adiada até a API estar estável (diretriz do Founder).
- `PATCH`/`DELETE` — não implementados (delete policy TD-001/002 ainda indefinida; nenhuma Capability hoje precisa de update).

## Wave 2 — Sprint 3 (2026-07-20): RBAC fine-grained enforcement

**Adicionado**
- Migração `0006_rbac_permission_catalog`: catálogo de 6 permissões (`portfolio`/`program`/`project_delivery` × `read`/`write`) + atribuição aos 4 papéis seed do Épico 1 (`organization_admin`/`pmo`: acesso total; `project_manager`: leitura de Portfolio, leitura+escrita de Program/Project; `viewer`: somente leitura).
- `src/services/authorization/` (`interfaces.py`: `PermissionChecker` Protocol; `checker.py`: `SqlPermissionChecker`) + `src/api/authorization.py` (`require_permission(...)` dependency).
- As 9 rotas da Wave 2 Sprint 2 ganham `Depends(require_permission("recurso.ação"))`, inserido após `get_request_context`, sem alterar nenhuma assinatura de rota além disso.
- **Correção de premissa registrada, não uma mudança de Blueprint:** `DOMAIN-BLUEPRINT-RBAC.md` §1 recomendava adicionar `organization_id` a `user_roles` para suportar um usuário com papéis diferentes por organização — na implementação, confirmou-se que `users.organization_id` já é uma FK única (NOT NULL, Épico 1): um usuário nunca pertence a mais de uma organização hoje, então essa extensão de schema não é necessária. Documentado no Decision Log (D-034), não uma edição retroativa do Blueprint.

**Testes**
- `tests/test_authorization.py` (5 testes: `SqlPermissionChecker` contra o catálogo real da migração 0006, por papel).
- `test_portfolio_api.py`/`test_program_api.py`/`test_project_delivery_api.py` reescritos para usar usuários reais com papéis reais (antes usavam um `user_id` sem nenhum papel) + 5 testes novos de enforcement (403 para `viewer` tentando escrever, 403 para usuário sem papel).
- Suíte completa: 211 testes passando, 98% de cobertura (100% em `authorization/checker.py`, `program.py`, `project_delivery.py`; gaps residuais são funções de wiring de DI nunca exercidas sem override, mesmo padrão já aceito em `intelligence.py`). `ruff check src tests`: sem apontamentos.

**Não incluído nesta Sprint (próxima Sprint recomendada)**
- Migração do frontend (`web/lib/domain/*.ts`) para a API real — agora protegida por RBAC de fato, não apenas por autenticação.
- Enterprise Administration (Épico 5 / `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`) — aguardando ratificação do Founder sobre o nível de escopo (Decision Proposal ainda aberta).

## Wave 2 — Sprint 4 (2026-07-20): Enterprise Administration (Nível 1 + Nível 2 ratificados)

**Ratificação do Founder:** Nível 1 (Usuários, Organizações, Papéis, Auditoria — já era o Épico 5 aprovado) + Nível 2 (Sessões, Segurança, Logs, Health, Configurações — extensão de baixo risco), per `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`.

**Adicionado**
- Migração `0007_enterprise_administration`: tabela `audit_logs` + permissões `administration.read`/`administration.write` (organization_admin/pmo leem; só organization_admin escreve).
- `AdministrationRepository` + `AdministrationService` + `src/api/routes/administration.py`: 8 endpoints — `GET`/`PATCH /admin/organization`, `GET /admin/users`, `GET /admin/roles`, `GET /admin/roles/{id}/permissions`, `POST /admin/users/{id}/roles`, `GET /admin/audit-log`, `GET /admin/security`.
- **Auditoria retroativa:** `DomainService.create_portfolio/create_program/create_project` (Sprint 1-3) agora registram uma entrada de auditoria a cada mutação — não é uma feature nova isolada, é o Épico 5 aplicado ao que já existia.
- **"Logs" (Nível 2) não é um sistema de logging novo** — reaproveita a mesma tabela `audit_logs` de "Auditoria" (Nível 1), um único store estruturado.
- **"Segurança" (Nível 2)** — endpoint mínimo, somente leitura (`GET /admin/security`): expõe apenas o que já existe (algoritmo de hash Argon2, ausência de MFA). Nenhuma configuração de política nova foi inventada.

**Correção de premissa registrada, não uma mudança de Blueprint:** `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §2 descreveu "Sessões" como "painel é só leitura+revogação sobre o que já existe" — na implementação, confirmou-se que **não existe** armazenamento server-side de sessões (`auth_service.py`: "No server-side session store exists yet", cookie HMAC stateless). Um painel real de Sessões exigiria um componente de arquitetura novo (session store), fora do escopo de "extensão de baixo risco" assumido pelo Blueprint. **Não implementado** — registrado no Decision Log (D-035), não construído como uma lista falsa. "Configurações" também não implementado, per o próprio adiamento do Blueprint (precisa de definição de produto antes de Technical Design).

**Testes**
- `tests/test_administration_repository.py` (13 testes) + `tests/test_administration_api.py` (17 testes, incluindo um teste end-to-end que cria um Portfolio via API e confirma que aparece no audit log).
- Bug encontrado e corrigido durante o desenvolvimento: `AdministrationRepository.assign_role()` retornava um objeto SQLAlchemy expirado após `commit()` sem `refresh()`, causando `DetachedInstanceError` na serialização da resposta — mesmo padrão já usado em `create_organization`/`create_user`, só que esquecido aqui; corrigido antes do commit.
- Suíte completa: 241 testes passando, 98% de cobertura, `ruff check src tests` sem apontamentos.

**Não incluído nesta Sprint (aguardando decisão futura)**
- Sessões (requer session store — não existe hoje, decisão de arquitetura nova).
- Configurações (requer definição de produto — Blueprint já adiou isso).
- Migração do frontend para a API real (Sprint 5, aprovada e em andamento).

## Wave 2 — Sprint 5 (2026-07-20): Frontend migrado para a API real (fim do mock de domínio)

**Aprovação do Founder:** migração do frontend para a Enterprise Domain API, condicionada à API estar estável e versionada (0.3.0, RBAC aplicado) — condição satisfeita.

**Mudado**
- `web/lib/domain/{portfolio,program,project}.ts`: os corpos de `listPortfolios()`/`listPrograms()`/`listProjects()` agora fazem `fetch()` real via BFF — **os arrays semeados foram deletados do frontend** (sem período de dupla fonte de verdade, per Foundation Technical Design §2.16 passo 3). Nenhum hook, página ou componente mudou — o seam prometido desde a Capability 01 (D-011) pagou exatamente como desenhado.
- Migração `0008_domain_seed`: os dados semeados mudam de casa (frontend → banco), nas duas organizações por desenho ("Organização Principal" e "Demo Organization"), preservando o que toda página exibia. **Unificação Fase 2 executada para nomes colidentes:** um Project legado com o mesmo nome de um seed ("Multilift", "Aurora") é atualizado in-place com os campos de domínio — nunca duplicado (testado, inclusive no downgrade, que preserva linhas legadas).
- Demo user agora recebe o papel `viewer` no bootstrap (novo E existente — reassegurado a cada boot, idempotente): sem isso, o Demo Mode receberia 403 em toda a Domain API. `assign_role_in_session` tornou-se idempotente para suportar isso.
- Novos BFF routes `web/app/api/bff/{portfolio,program,project-delivery}/route.ts` sobre um helper compartilhado (`web/lib/bff/domain-proxy.ts`): sessão → headers institucionais `X-Stratech-*` resolvidos server-side (nunca do browser), 401 sem sessão, mesmo contrato de timeout/erro do BFF do dashboard.
- E2E mock backend (`web/e2e/mock-backend.mjs`) ganhou os 3 endpoints de domínio com os mesmos dados do seed real — a cadeia página → hook → fetch → BFF → backend é exercitada de ponta a ponta pela suíte Playwright.

**Testes**
- Backend: 245 passando (4 novos: migração 0008 × 3, papel do demo user × 1; 2 testes de migração pré-existentes ajustados por afirmarem contagens que o seed 0008 legitimamente muda). `ruff` limpo.
- Frontend: `tsc` limpo, `eslint` limpo, 436 testes unitários passando.
- **E2E completo executado localmente: 3 projetos (lg/md/mobile), 203 testes passando** — a disciplina D-027 aplicada; a cadeia real de fetch validada em navegador de verdade.

## Wave 2 — RC-2 (2026-07-23): PostgreSQL oficial + suíte de testes em PostgreSQL

**Missão de Release Engineering (não uma Sprint) — sem novas funcionalidades, sem tocar domínio/arquitetura.**

**Adicionado**
- `src/database/engine.py` — `resolve_database_url()`/`build_engine()`, seam único reutilizado por `AnalysisRepository` e `alembic/env.py`; pool de conexões (`DB_POOL_SIZE`/`DB_MAX_OVERFLOW`/`DB_POOL_TIMEOUT_SECONDS`/`DB_POOL_RECYCLE_SECONDS`/`DB_POOL_PRE_PING`) totalmente configurável por variável de ambiente.
- `Makefile` + `scripts/rc2-db.sh`/`.ps1` + `scripts/prepare-env.sh`: pipeline completo `setup → db-create → migrate → seed → dev/test`, idempotente, com fallback automático de peer-auth para `sudo -u postgres` em instalações Linux nativas.
- `tests/db.py::temp_database_url` — banco Postgres efêmero por teste (cria/derruba), substituindo os arquivos SQLite temporários em 22 arquivos de teste (~35 ocorrências).
- `docs/product/release-candidate/RC-2/Quick-Start.md` e `Release-Validation-Checklist.md` (novos).
- `docker-compose.yml`: healthcheck no serviço `database` + passthrough das variáveis de pool.

**Mudado**
- `demo/start-demo.sh` roda `alembic upgrade head` antes de iniciar o backend (idempotente) — antes, migrations não rodavam automaticamente por esse caminho.
- `docs/technical/03-development-environment.md` e `docs/technical/05-database-model.md` atualizados para refletir PostgreSQL como banco oficial e a suíte de testes real.
- `.env.example`, `README.md` atualizados.

**Testes**
- Backend: 245 passando, 98% cobertura — cada teste contra seu próprio banco Postgres efêmero.
- Frontend: 436 passando (sem dependência de banco).
- E2E: 203 passando nos 3 projetos (`lg`/`md`/`mobile`) — mock backend mantido por decisão de arquitetura de teste pré-existente (ver D-037).
- `ruff check src tests`: limpo.
- Validação manual completa contra PostgreSQL real: login, CRUD Portfolio/Program/Project, RBAC (403 para viewer), audit log, dashboard, health check — ver Release Validation Checklist.

**Decision Log:** D-037.

## Wave 2 — Encerramento (2026-07-23): Capability User Management (Enterprise Administration)

**Aprovação condicionada do Founder** com 8 critérios técnicos obrigatórios (`DOMAIN-BLUEPRINT-USER-MANAGEMENT.md`, `TECHNICAL-DESIGN-USER-MANAGEMENT.md`), para fechar a lacuna encontrada na revisão de fechamento da Wave 2: o Épico Enterprise Administration estava incompleto por ausência desta Capability.

**Adicionado**
- Migração `0009_user_management`: `users.is_active` (default `true`) + índice único funcional case-insensitive `uq_users_org_email_lower` sobre `(organization_id, lower(email))`, substituindo a constraint case-sensitive anterior.
- `src/services/identity/email_normalization.py` — `normalize_email()`, reutilizado no cadastro, na edição de e-mail e no login.
- 6 novos endpoints REST (`POST/GET/PATCH /admin/users`, status, roles) + 8 novas rotas BFF sob `web/app/api/bff/admin/`.
- Página `/administracao/usuarios` (10º item de navegação): listar, pesquisar, filtrar por status/papel, cadastrar, editar, ativar/inativar (com confirmação), atribuir/remover papel.

**Mudado**
- `AdministrationRepository` passa a compor `EnterpriseRepository` (reuso de `create_user_in_session`/`assign_role_in_session`) em vez de duplicar lógica de criação de usuário.
- `SqlPermissionChecker.has_permission` e `AuthService.authenticate` passam a rejeitar usuários inativos (dois pontos de enforcement, não um filtro espalhado).
- `web/lib/bff/domain-proxy.ts::forwardDomainRequest` generalizado de GET-only para forwarding completo de método/corpo/status.
- `sidebar.tsx`: corrigido um bug latente de overflow no bottom-nav mobile (itens `flex` sem `min-w-0`, exposto pelo 10º item de navegação).

**Governança**
- Auto-inativação do próprio admin e inativação/despromoção do último admin ativo de uma organização bloqueadas com `SELECT ... FOR UPDATE` (fecha corridas entre requisições concorrentes).
- Auditoria: `user.created`, `user.updated`, `user.activated`, `user.deactivated`, `role.assigned`, `role.removed` — nunca com senha/hash.
- Fora de escopo, por decisão explícita do Founder: convites, SSO, MFA, session store, recuperação/reset de senha, stakeholders, configurações gerais de organização.

**Testes**
- Backend: 281 passando (245 pré-existentes + 36 novos), contra PostgreSQL efêmero real. `ruff` limpo.
- Frontend: `tsc`/`eslint` limpos, 437 testes unitários passando.
- E2E completo nos 3 projetos (`lg`/`md`/`mobile`, 81 testes cada) — disciplina D-027 cumprida.

**Wave 2 (Enterprise Platform) declarada 100% completa** para os 3 Épicos que a compõem. Homologação funcional completa permanece adiada para depois da Wave 3, por instrução do Founder.

**Decision Log:** D-038. Ver `docs/product/governance/USER-MANAGEMENT-EXECUTIVE-REPORT.md`.
