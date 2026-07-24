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

## Wave 3 — Abertura (2026-07-23): Architecture Review AR-2 + Epic Ledger

**Autorização do Founder** para abrir a Wave 3 (Enterprise Intelligence), sob o fluxo Architecture Review → Domain Blueprint → Technical Design → Implementation → Testing → Executive Report por Epic, sem nova autorização entre Epics salvo 5 gatilhos explícitos.

**Adicionado**
- `docs/architecture/AR-2-WAVE-3-ARCHITECTURE-REVIEW.md`: auditoria de código (nenhum desvio, grounding do Blueprint da Wave 3 revalidado), auditoria de governança e verificação de engenharia (todas as suítes verdes, reaproveitadas da verificação de encerramento da Wave 2 -- nenhuma mudança de código no intervalo).
- Epic Ledger da Wave 3: **W3-1** Project Identity Unification (TD-008 Fase 3), **W3-2** AI Platform Foundation, **W3-3** Risk Advisor (prova de conceito) liberados; Knowledge Platform e os demais 7 Enterprise Agents bloqueados por Decision Proposal ao Founder (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §15, nova seção aditiva).
- `docs/product/governance/AR-2-EXECUTIVE-REPORT.md`.

**Mudado**
- Nenhum código de produção alterado nesta etapa -- apenas documentação/governança. `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §11 corrigido (não reescrito): o gatilho de TD-008 Fase 3 nunca dependeu de uma tabela `projects_delivery` separada (que nunca chegou a existir), apenas do início da Wave 3.

**Decision Log:** D-039.

## Wave 3 — Epic W3-1 (2026-07-23): Project Identity Unification (TD-008, Fase 3a)

**Adicionado**
- `docs/architecture/DOMAIN-BLUEPRINT-PROJECT-IDENTITY-UNIFICATION.md` e `TECHNICAL-DESIGN-PROJECT-IDENTITY-UNIFICATION.md`.
- `tests/test_project_summary_service.py`: teste novo cobrindo o bug de agrupamento por variação de espaço em branco.

**Mudado**
- `src/services/project_summary_service.py`: `summarize()`/`summarize_portfolio()` agrupam por `project_id` (já populado em toda escrita desde o Épico 1) em vez de `project_name` bruto -- corrige duplicidade real no portfólio agregado quando o mesmo projeto é referenciado com variação de espaço em branco.
- `src/api/routes/intelligence.py`: `ProjectSummaryResponse` ganha `project_id: int | None` (aditivo).
- `web/lib/dashboard/types.ts`: `ProjectSummary` ganha `project_id?: number` (opcional -- nenhuma fixture de teste existente precisou mudar).

**Testes**
- Backend: 282 passando (281 + 1 novo). `ruff` limpo.
- Frontend: `tsc`/`eslint` limpos, 437 testes inalterados. Spot-check E2E (`dashboard.spec.ts`+`portfolio.spec.ts`, `lg`) 20/20 -- mudança não toca comportamento de frontend nem o mock E2E.

**Escopo explicitamente não incluído:** migrar toda a superfície de Dashboard/Portfólio/Decision Center/Executive Focus/Workspace de `project_name` para `project_id`, aposentando `ProjectSummary` (TD-008 Fase 3b) -- documentado como trabalho futuro de escopo muito maior, não decidido silenciosamente.

**Decision Log:** D-040. Ver `docs/product/governance/W3-1-EXECUTIVE-REPORT.md`.

## Wave 3 — Epic W3-2 (2026-07-23): AI Platform Foundation avaliado e adiado

**Nenhum código produzido.** O Domain Blueprint deste Epic (`docs/architecture/DOMAIN-BLUEPRINT-AI-PLATFORM-FOUNDATION.md`) auditou as 7 sub-áreas propostas (Provider Strategy, Model Registry, Model Routing, Prompt Versioning, Cost/Token Governance, AI Observability, Evaluation Framework) e encontrou zero consumidor real hoje para 6 delas, e nenhum requisito ativo para a sétima (Cost/Token, apesar de um gap real: `ProductionLLMProvider` descarta o `usage`/tokens que a Anthropic já devolve). Construir qualquer uma delas agora seria arquitetura especulativa sem caso de uso -- contra a disciplina "não fazer mais do que o necessário".

Epic marcado como **adiado, não cancelado**, com gatilhos explícitos de reabertura documentados. A Wave 3 avança para o Epic W3-3 (Risk Advisor), que tem um entregável concreto.

**Decision Log:** D-041.

## Repository Audit — Wave 3 Gate (2026-07-23)

Full repository audit (structure, code/dependencies, database/PostgreSQL, tests/quality, security, docs/governance coherence) required by the Founder before updating `main` and starting Epic W3-3. Full report: `docs/product/governance/REPOSITORY-AUDIT-WAVE-3.md`.

**Found (Critical, pre-existing since V1, not introduced by any Wave 2/3 work)**: `src/api/routes/intelligence.py` applies no RBAC or organization scoping on any of its 8 routes; `AnalysisRecord` has no `organization_id`, causing a real cross-tenant data leak now that two real organizations coexist in the same database. **No code fix applied** -- registered as a Decision Proposal (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §16) per the Founder's explicit instruction not to decide architectural-impact fixes silently.

**Fixed (low-risk, no product/architecture impact)**:
- `web/lib/mock/mission-control-data.ts`: `EPIC_STATUS`/`RELEASE_STATUS` were stale (Épicos 3-5 "Not Started" despite being done since Wave 2; Releases 0.1/0.2 "In Progress" despite being 100% done); `DOMAIN_EVOLUTION` note on TD-008 updated.
- `README.md`: status line updated from "Wave 2 RC-2" to "Wave 3 in progress."

**Tests**: backend 282 passed, 97% coverage; frontend tsc/eslint clean, 437 vitest passed; full E2E suite (241 tests, 3 projects) 230 passed / 11 failed -- isolated re-run confirmed only 6 failures reproduce deterministically, all already tracked as TD-004/005/006; the rest were transient (environment resource contention, not a regression). A PostgreSQL service outage during the audit (environment issue, confirmed via `pg_isready`) caused one contaminated test run, resolved by restarting the service and revalidating clean.

**Recommendation: GO WITH CONDITIONS.** `main` update authorized (this session's changes don't touch the vulnerable files). Epic W3-3 (Risk Advisor) implementation is held pending the Founder's decision on the security Decision Proposal -- it would build directly on the unprotected route.

**Decision Log:** D-042.

## Wave 3 — Epic W3-3 (2026-07-23): Risk Advisor Enterprise Domain Blueprint

`docs/architecture/DOMAIN-BLUEPRINT-RISK-ADVISOR.md` -- covers purpose, actors, domain model (no new entities: reuses `Project`/`AnalysisRecord`), decision flow, LLM integration (no `LLMProvider`/`PromptRegistry` extension needed), explainability (every answer cites its source `AnalysisRecord`), confidence, RBAC, organization scope, audit, conversational interface, acceptance criteria, risks/dependencies, and explicit non-scope (no multi-agent framework, vector store, RAG, long-term memory, orchestration engine, model registry, new prompt registry, or provider router -- confirming the AR-2 guardrail holds).

**No code produced.** Implementation is explicitly held pending two dependencies outside this Epic's control: the Founder's decision on the C-1/C-2 security Decision Proposal (the Risk Advisor would otherwise inherit intelligence.py's missing RBAC/org-scoping), and the main branch merge (PR #45).

**Decision Log:** D-043.

## Baseline consolidation — PR #45 merged to main (2026-07-23)

Per the Founder's authorization, PR #45 (Wave 2 closure + Wave 3 opening, Phase 2 Foundation through the Repository Audit) merged into `main`. Final `main` hash: **`d8ff04d5db3999a3defafdc8ee9362e0ab7308b3`**. Merge commit tree confirmed identical to the source branch (`git diff` empty) -- no surprises introduced. `origin/main` confirmed synchronized.

**Essential checks re-validated directly on `main`:**
- Backend (`pytest`): 282 passed
- `ruff check src tests`: clean
- Frontend `tsc --noEmit`: clean
- Frontend `eslint .`: clean
- Frontend `vitest run`: 437 passed
- PostgreSQL integration: confirmed (entire integration suite already runs on real Postgres)
- Migrations: full upgrade (0001→0009) → downgrade (base) → re-upgrade round trip validated clean on a disposable database

**Incidental finding while validating PR #45**: the real CI failure GitHub reported on the PR revealed `.github/workflows/ci.yml`'s `validate` job never provisioned a PostgreSQL service -- a deterministic failure (not flakiness) since RC-2 made Postgres required for the integration suite. Fixed in the same session (`postgres:16` service, `aipmo`/`aipmo`, `pg_isready` healthcheck) -- both required checks were green before the merge was authorized.

**Per the Founder's explicit instruction, Risk Advisor implementation has not started.** Next: Security Hardening Gate (C-1/C-2).

**Decision Log:** D-044.

## Security Hardening Gate (2026-07-23): C-1 (RBAC in intelligence.py) and C-2 (AnalysisRecord tenant isolation) closed

Closes the 2 critical, pre-existing-since-V1 findings the Repository Audit (D-042) registered as a Decision Proposal. Technical Design (`docs/architecture/TECHNICAL-DESIGN-SECURITY-HARDENING-GATE.md`) confirmed no architectural impact outside the approved scope, so implementation proceeded directly.

**C-1 -- RBAC**: all 8 routes in `src/api/routes/intelligence.py` now require `Depends(get_request_context)` + `Depends(require_permission("intelligence.read"|"intelligence.write"))` -- the same pattern already used by `portfolio.py`/`program.py`/`project_delivery.py`/`administration.py`. New `intelligence.read` (all 4 seed roles) and `intelligence.write` (all except viewer) permissions seeded via migration `0010`.

**C-2 -- Tenant isolation**: `AnalysisRecord` gains `organization_id` (migration `0010`: nullable column -> backfill via a join with `projects.organization_id` -> `NOT NULL` -> FK -> index, with a loud `RuntimeError` if any row can't be backfilled). `save_analysis`/`list_analyses`/`get_analysis` now filter/require `organization_id`. **Deeper root cause found during the Technical Design**: `get_or_create_project_for_name` always resolved to a single hardcoded "Default Organization" regardless of the real caller -- fixed to use the request's actual `organization_id`.

**Added**
- `alembic/versions/0010_security_hardening.py` -- permissions + `organization_id` + backfill + constraints + index.
- `src/api/dependencies.py` -- `build_repository` extracted from `intelligence.py` to break a circular import (`authorization.py` -> `intelligence.py` -> `authorization.py`) once `intelligence.py` needed `require_permission`.
- `docs/architecture/TECHNICAL-DESIGN-SECURITY-HARDENING-GATE.md`.

**Changed**
- `web/lib/bff/domain-proxy.ts`: exported `readSessionIdentity`/`institutionalHeaders` for the 9 BFF routes (Dashboard, Ações, Riscos, and the 6 Workspace routes) that proxy to `intelligence.py` but have bespoke timeout/error-mapping/field-renaming logic that doesn't fit the generic `forwardDomainRequest()` helper. All 9 now resolve the session cookie and forward institutional headers, 401ing without one -- a real, necessary consequence of C-1 that had no coverage before, since the backend routes didn't require it either.
- Audit trail: the 3 analyze routes now record `analysis.meeting_created`/`analysis.risk_created`/`analysis.status_created` via the existing `AdministrationRepository.record_audit`, not a new mechanism.

**Tests**
- `tests/test_intelligence_api.py` rewritten onto the real-Postgres + real-RBAC convention (`test_portfolio_api.py`'s pattern): RBAC 403s parametrized across all 8 routes, `test_meeting_analyzed_by_org_a_is_invisible_to_org_b` (end-to-end proof the audit's live leak can't recur), and audit-trail assertions.
- Migration `0010` validated by a full manual round-trip (upgrade -> downgrade -> re-upgrade) on a disposable database, including a legacy-shape row to prove the backfill.
- **305 backend tests** (282 existing + 23 new/rewritten), **452 frontend tests** (437 existing + 15 new, including the new 401-without-session cases), `ruff`/`tsc`/`eslint` clean.
- Full E2E suite (3 projects) run twice; the 6 observed failures were isolated and confirmed pre-existing to this Gate via an A/B comparison (`git stash`) against the pre-Gate baseline -- none are new regressions.

**Every Founder acceptance criterion confirmed**: no intelligence route accessible without authorization; no `AnalysisRecord` accessible across organizations; PostgreSQL as the official database; migration upgrade/downgrade/re-upgrade validated; full regression approved; multi-tenant isolation tests in place; audit trail updated; no historical-data exposure during the backfill (the `NOT NULL` constraint only applies after the backfill is confirmed complete, with a loud `RuntimeError` otherwise).

**Next, per the Founder's explicit sequencing**: resume Epic W3-3 (Risk Advisor PoC) with the already-approved Blueprint (`DOMAIN-BLUEPRINT-RISK-ADVISOR.md`) -- the dependency that blocked its Implementation (D-043) is now resolved.

**Decision Log:** D-045.

## Wave 3 — Epic W3-2 (2026-07-23): Digital PMO Intelligence Foundation

Per a new permanent strategic decision from the Founder ("STRATECH is an Executive Decision Operating System... the AI operates, executives decide"), Epic W3-2 is redefined from the previously deferred "AI Platform Foundation" (D-041) into the **Digital PMO Intelligence Foundation** -- shared infrastructure every Enterprise Analyst (the Risk Advisor today; any future specialist) must reuse instead of reimplementing.

Full institutional flow followed: `DOMAIN-BLUEPRINT-W3-2-Digital-PMO-Intelligence-Foundation.md` -> `AR-3-W3-2-DIGITAL-PMO-FOUNDATION-REVIEW.md` (approved without reservations) -> `TECHNICAL-DESIGN-W3-2-DIGITAL-PMO-FOUNDATION.md` -> implementation.

**Added**
- `src/services/ai_foundation/` -- 6 shared components: `AIContextEngine` (resolves already-persisted evidence via `AnalysisRepository`, no new query), `RecommendationEngine` (normalizes model output, discards any evidence citation the model invented), `ExplanationEngine` (every recommendation carries a standard rationale, per ADR-V2-007), `render_analyst_prompt` (composes one shared institutional preamble over the existing `PromptRegistry` -- no new registry), `AIFoundationAudit` (delegates to `AdministrationRepository.record_audit`, never logs the model's answer), `ObservabilityRecorder` (latency + token logging via the project's existing structured `logging`, closing the real gap D-041 flagged: `ProductionLLMProvider` discarding `message.usage`).
- `ProductionLLMProvider.last_usage` -- aditive, optional attribute; `LLMProvider` Protocol unchanged.

**Changed**
- Risk Advisor (`ask_risk_advisor`, `RiskAdvisorAgent`) migrated to consume the Foundation -- proof of real reuse, not just a theoretical design. **HTTP contract unchanged** (`RiskAdvisorRequest`/`RiskAdvisorResponse` identical), no BFF/frontend migration needed.
- **Deliberate, registered behavior change** (not a silent regression): the Risk Advisor now synthesizes over the project's **entire risk-analysis history**, not just the latest one -- a genuine improvement for a conversational advisor (historical questions like "has this risk happened before?" now have data to answer), without violating any acceptance criterion.

**No item from the Founder's prohibition list was introduced**: Vector Store, pgvector, embeddings, RAG, Knowledge Platform, permanent Executive Memory, Multi-Agent Framework, autonomous planning/reflection/self-execution, collaborative agents -- none appear in any component. `SessionContext` is explicitly ephemeral (never persisted).

**Tests**
- **335 backend tests** (314 existing + 21 new: 20 Foundation unit tests + 1 for the migrated agent), **468 frontend tests** unchanged (no HTTP contract change), `ruff`/`tsc`/`eslint` clean, Risk Advisor E2E test confirmed passing across all 3 breakpoints after the migration.

**Decision Log:** D-047.

## Wave 3 — Epic W3-3 (2026-07-23): Risk Advisor implemented

Both dependencies blocking the Blueprint's Implementation (D-043) are resolved: C-1/C-2 closed by the Security Hardening Gate (D-045), `main` consolidated (D-044). Technical Design (`docs/architecture/TECHNICAL-DESIGN-RISK-ADVISOR.md`) confirmed no architectural impact outside the Blueprint's approved scope.

**Added**
- `src/agents/risk_advisor/` -- new agent, same convention as the 3 existing Accelerators. `advise(question, risks)` (not `analyze()`: this agent never creates a new analysis, only synthesizes over risks already identified).
- `POST /api/risk-advisor/ask` in `src/api/routes/intelligence.py` -- protected by `intelligence.read` (the same permission already protecting `GET /risks/latest`, its data source; no new permission introduced). Returns a canned "no risks yet" answer without calling the LLM when the project has none. Every question is audited (`risk_advisor.question_asked`), never the model's answer.
- `web/app/api/bff/workspace/[projectName]/risk-advisor/route.ts` -- same bespoke BFF pattern as the 3 `.../analyze/*` routes (session resolution, 60s timeout, error mapping).
- `web/components/workspace/risk-advisor-section.tsx` -- new Workspace section: question field, answer with source-analysis citation, no persisted conversation history.

**No new entity, no migration, no `LLMProvider`/`PromptRegistry` extension** -- confirms the AR-2 guardrail and the Blueprint's own non-scope (no multi-agent framework, vector store, RAG, or long-term memory).

**Tests**
- `tests/test_risk_advisor_agent.py` (3 new) + `tests/test_intelligence_api.py::TestRiskAdvisor` (6 new): RBAC, organization isolation (a risk from another organization is never synthesized over), audit trail without the LLM's answer, and the no-LLM-call fast path when a project has no risks yet.
- **314 backend tests** (305 existing + 9 new), **468 frontend tests** (452 existing + 16 new), `ruff`/`tsc`/`eslint` clean.
- New end-to-end Playwright test (mock backend -> BFF -> hook -> component) passing across all 3 breakpoints; Workspace suite spot-checked (60/63 -- the 3 failures already confirmed pre-existing and unrelated during the Security Hardening Gate's own verification).

**Decision Log:** D-046.

## Superseding Decision (2026-07-23): official Wave Completion Policy; retrospective Wave Completion Review (Waves 1-3) opened

The Founder issued a superseding decision revoking every prior decision that allowed deferring an originally-planned Epic, Capability, or Enterprise Analyst, treating built infrastructure as sufficient to close a Wave, carrying planned scope forward as an open Decision Proposal, or closing a Wave with remaining functional backlog.

**New permanent Wave Completion Policy**: a Wave can only be declared CONCLUÍDA when, simultaneously: 100% of technical and functional scope is implemented; 100% of originally-planned Epics, Capabilities, and Enterprise Analysts are implemented and functional; 100% of Domain Blueprints and Technical Designs have matching implementation; 100% of Executive Reports are published; all unit/integration/E2E tests pass; and zero placeholder/TODO/stub/partial implementation remains in the Wave's scope.

**Substantive change, not just a stricter checklist**: the permanent prohibition on speculative architecture now applies only to work outside a Wave's official plan. Anything that was already part of an approved Wave plan (e.g., Knowledge Platform and the 7 Enterprise Advisors beyond Risk Advisor, both named in `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md`) stops being speculative and becomes mandatory -- reversing the reasoning D-039/D-041/the Repository Audit (D-042) and the initial `WAVE-3-COMPLETION-REVIEW.md` used to treat them as blocked Decision Proposals that didn't gate Wave 3's closure.

**Immediate action mandated**: a full retrospective Wave Completion Review across Waves 1, 2, and 3 -- comparing original planning, Decision Logs, Mission Control, Domain Blueprints, Technical Designs, Executive Reports, implemented code, and the running application -- to surface and then close every remaining gap.

**No Wave is declared complete by this entry.** This entry records the policy change itself; the retrospective audit and the implementation of whatever gaps it finds are tracked in subsequent Decision Log entries as each is resolved.

**Decision Log:** D-048.

## Wave Completion Review retrospective, item 1 (2026-07-23): Event Foundation implemented

The retrospective Wave Completion Review (D-048) audited Wave 1 against `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §5 and found the Event Foundation 0% implemented despite being fully specified since the Technical Design Sprint. Sequenced as item 1 of the closure plan (`WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md` §6) -- no pending design decision, only implementation of already-approved scope.

**Added**
- `src/services/events/` -- `EventEmitter` (Protocol: `emit(event_name, payload, organization_id) -> None`), `NoOpEventEmitter` (logs only, no other effect -- "the seam exists, the bus doesn't yet"). Wired via `src/api/dependencies.py::build_event_emitter`.
- `DomainService.__init__` now requires an `emitter: EventEmitter` (no default). Its 3 mutating methods emit the 5 events already named in the Technical Design after the repository write and audit record both succeed: `portfolio.created`; `program.created` + `program.linked_to_portfolio`; `project_delivery.created` + `project_delivery.linked_to_program`.
- Design note: since `create_program`/`create_project` always create an entity already linked to its parent atomically (no separate re-parenting API is exposed), the `.created` event and its matching `.linked_to_*` event are emitted together from the same creation call rather than inventing a new "link" operation.

**No item from the Founder's permanent prohibition list was introduced.** No Event Bus, Workflow Engine, or real consumer was built -- `NoOpEventEmitter` is deliberately log-only, exactly as the Technical Design describes for this phase.

**Tests**
- `tests/test_domain_service.py` (5 new, using a `RecordingEventEmitter` fake) + `tests/test_events_noop_emitter.py` (1 new).
- 4 existing API test files updated for `DomainService`'s new constructor signature.
- **341 backend tests** (335 existing + 6 new), `ruff check src tests` clean. No HTTP contract change.

**Decision Log:** D-049.

## Wave Completion Review retrospective, item 2 (2026-07-23): TD-004/005/006 fixed (React Query invalidation race)

The Riscos panel, Comunicação panel, and Executive Memory's "Mudou" insight all read the mutated data through `useWorkspaceLatestByKind`/`useRecentAnalysesByKind`. When "Analisar Projeto"'s mutation invalidated those queries while their first-mount fetch was still in flight, React Query reused the in-flight promise instead of starting a new fetch -- the invalidation was silently discarded once that stale promise resolved.

**Fixed**
- `useSubmitRiskReview`, `useSubmitMeetingIntelligence`, `useSubmitProjectStatus` now call `queryClient.cancelQueries(...)` on the relevant `workspace-latest`/`workspace-recent` keys before `invalidateQueries` in their `onSuccess` -- cancelling the in-flight fetch resets it to idle so the invalidation always starts a genuinely new one.

**Verification**
- Controlled A/B on the same running dev server (no restart between runs): baseline code fails 8/8 on a repeated isolated run of the TD-006 test; with the fix, 8/8 passes. TD-004+TD-005 together: 20/20 passing (`--repeat-each=5`).
- Full E2E suite, all 3 breakpoints: 81/81 (lg), 81/81 (md), 82/82 (mobile), 341 backend tests unchanged, `ruff`/`tsc`/`eslint`/468 frontend tests clean.
- A stale Next.js dev-server build cache (`.next`) was found to cause broad, unrelated full-suite flakiness under this session's sustained hot-reload load -- confirmed independent of this fix (`rm -rf web/.next` eliminated it); noted in `TECHNICAL_DEBT.md` so it isn't mistaken for a regression later.

**Decision Log:** D-050.

## Wave Completion Review retrospective, item 3 (2026-07-24): API Keys implemented -- architectural correction, not a new dependency

The Founder issued a permanent decision: an architectural dependency never authorizes leaving a planned Epic pending -- when one is found, the correct response is to review and remove it if artificial, not wait on a future decision. Specifically for API Keys, the prior Blueprint classified it as depending on a future Integration Hub (Wave 4); auditing that dependency found it was never real -- just the result of an earlier architectural decision. Corrected: **no foundational component may depend on a future component; the reverse is always allowed.** API Keys is reclassified from "depends on Integration Hub" to foundational (same tier as Users/Organizations/Roles/Audit).

**Added**
- `ApiKey` model + migration `0011` (table + `api_keys.manage` permission, `organization_admin` only).
- `AdministrationRepository`/`AdministrationService`: CRUD (create/list/revoke) + `authenticate_api_key` (narrows candidates by non-secret `key_prefix`, then verifies via the same `Argon2PasswordHasher` already used for passwords -- no new hashing infrastructure).
- A second, additive authentication path in `get_request_context`: header `X-Stratech-Api-Key`, alternative to the existing 3 session headers. **Every existing permission-protected route gains API Key auth automatically, with zero changes to its own route wiring** -- a key authenticates as the user who created it, inheriting that user's RBAC exactly as a session would.
- Routes `GET/POST /api/admin/api-keys`, `DELETE /api/admin/api-keys/{id}` (revoke returns `200` with the resource, not `204` -- `forwardDomainRequest`, the shared BFF proxy helper, can't represent a body-less 204; same convention as `remove_role`).
- Frontend: `/administracao/api-keys` page (new "Chaves de API" nav entry), two-step creation dialog (form -> one-time plaintext reveal, does not auto-close), revoke button with confirmation.

**Fixed (pre-existing gaps found during implementation, corrected in-scope, not deferred)**
- `web/proxy.ts::config.matcher` never included `/administracao`/`/administracao/:path*` -- an unauthenticated visitor could load the Administração page shell (BFF calls still 401'd). Affected `/administracao/usuarios` too, not just the new page.
- `app.dependency_overrides` leaked in 3 tests across `tests/test_api_security.py` and `tests/test_rate_limit_api.py` -- exposed only because the new end-to-end auth-path test was the first to exercise the real (non-overridden) `build_repository` path in the full suite.

**Design note (DI):** `AdministrationService` is constructed via a plain function call inside the `X-Stratech-Api-Key` branch, not a declared `Depends(...)` parameter -- a declared dependency on a widely-shared function like `get_request_context` would force FastAPI to eagerly build a real repository on every request, across every existing test file, even when no API key is sent.

**Fixed (E2E infra, found while adding the API Keys nav entry)**
- Adding an 11th nav item exposed the same known Next.js dev-overlay (`nextjs-portal`) click-interception artifact already documented in `workspace.spec.ts`, this time on `portfolio.spec.ts`'s mobile "Priorização" nav-click test (confirmed via controlled A/B: 2/2 pass on baseline, 5/5 fail with the change). Since this test must click the nav bar link itself, it hides the overlay via `page.addStyleTag` before clicking, rather than using `workspace.spec.ts`'s in-page-link workaround.

**Tests**
- New: `tests/test_migration_0011_api_keys.py`, `tests/test_administration_service.py`, `tests/test_identity_context_api_key_auth.py`, `web/e2e/api-keys-admin.spec.ts`.
- Extended: `tests/test_administration_repository.py`, `tests/test_administration_api.py`, `web/components/shell/navigation.test.ts`, `web/e2e/shell.spec.ts` (nav count 10 -> 11).

**Decision Log:** D-051.

## Wave Completion Review retrospective, item 4 (2026-07-24): Configurações da Organização / Tenant System Settings separated and reclassified -- Governance Concluded, not Implemented

Sequencing item 4 ("Tenant/System Settings") initially considered per-organization rate limiting as the buildable scope for "Configurações da Organização." The Founder corrected this: making rate limiting organization-aware is a platform infrastructure improvement, not an Organização Settings feature, and using it to close the Epic would violate the explicit rule against "using infrastructure improvements just to justify closing an Epic." A mandatory repository-wide audit followed: does any official document (Blueprints, Technical Designs, Business Model Blueprint, Mission Control, Decision Log, backlog, roadmap) specify any concrete content for "Configurações da Organização"?

**Result: no.** Every occurrence of the term across the repository is either a bare label in a list of admin sub-areas, or an explicit statement that scope is still undefined -- no field (language, timezone, branding, notifications, default role, feature flags) is named anywhere. `Organization` (`src/database/models.py`) has no settings column.

**Reclassified (`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` new §0.1), two distinct concepts, two distinct statuses:**
- **Configurações da Organização** (functional preferences) -> **No Defined Functional Scope.** Not an architectural or business-model block -- a genuine absence of a product requirement. Stays out of scope until the Founder defines concrete content; must not be filled with invented behavior or a repurposed infrastructure improvement.
- **Tenant/System Settings** (SaaS commercial model -- plans, billing, per-paying-tenant isolated config) -> **Pending Business Decision (Wave 6 -- `BUSINESS-MODEL-BLUEPRINT.md`).** Depends entirely on that document's 7 unanswered questions -- a real, never-answered business decision, not an eliminable architectural dependency under D-051's permanent principle.

**No code produced.** This item closes as Governance Concluded: the audit is complete, both concepts are formally separated and documented in a non-ambiguous, trackable state, but there is no functional requirement to implement until the Founder changes either status.

**Decision Log:** D-052.
