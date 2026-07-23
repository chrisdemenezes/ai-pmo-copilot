# Phase 2 — Foundation Architecture — Technical Design

**Status:** TECHNICAL DESIGN — implementation-level detail, no code produced. Per Executive Directive (Phase 2 Foundation Technical Design), the Foundation Architecture proposal (`docs/architecture/PHASE-2-FOUNDATION-ARCHITECTURE.md`) was approved conceptually by the Architecture Review Board. This document is the next governance layer down: it fixes concrete Protocols, contracts, directory structures, call sequences, test strategy and migration plans for the same 5 areas, so that a future implementation mission can proceed without re-deriving design decisions.
**Date:** 2026-07-18
**Author:** Claude / Chief Software Architect
**Precondition:** `PHASE-2-FOUNDATION-ARCHITECTURE.md` (proposal, approved conceptually). RC-2 Enterprise Certification, merged to `main`.
**Hard constraints (explicit, from the Executive Directive):** não implementar código. Não criar ADR. Não alterar a Baseline (`ARCHITECTURE-BASELINE-RC2.md`). Não modificar funcionalidades existentes. Nenhum código foi produzido nesta missão — every snippet below is illustrative design notation, not a diff to apply.

---

## 0. How to read this document

Each of the 5 areas below is specified with the same 15 elements, in the same order, so the areas are comparable and nothing is silently skipped:

1. Objetivo — 2. Responsabilidades — 3. Componentes envolvidos — 4. Interfaces (Protocols) — 5. Fluxo de execução — 6. Dependências — 7. Estrutura de diretórios — 8. Contratos públicos — 9. Contratos internos — 10. Diagrama lógico (ASCII) — 11. Sequência de chamadas — 12. Estratégia de testes — 13. Critérios de aceite — 14. Impactos na arquitetura existente — 15. Riscos — 16. Plano de migração (quando aplicável).

(16 numbered because "Impactos" and "Riscos" are kept as two distinct elements, matching the Executive Directive's list exactly; "Plano de migração" is last since it doesn't apply uniformly.)

Every Protocol/class name below is a **design name**, chosen for consistency with existing code (`CredentialVerifier`, `IdentityResolver`, `EnterpriseRepository`, `verify_api_key`) — none of it exists on disk yet.

---

## 1. API Strategy

### 1.1 Objetivo
Give Portfolio/Program/Project a real network-addressable API surface, replacing the in-memory-only `web/lib/domain/*.ts` reads, without introducing a second API convention alongside `intelligence.py`'s.

### 1.2 Responsabilidades
- Expose CRUD-plus-consolidation reads for the 3 Bounded Contexts (Domain Blueprints CB-001/002/003).
- Enforce the same auth/rate-limit/org-scope/permission gates every other route already enforces.
- Keep the BFF's job unchanged: hide `API_KEY`/`SESSION_SECRET` from the browser, translate backend errors into the existing `DashboardErrorBody` shape.

### 1.3 Componentes envolvidos
- **New:** `src/api/routes/portfolio.py`, `program.py`, `project_delivery.py` (file named `project_delivery`, not `project.py`, to avoid ever importing ambiguously alongside a future `project.py` for the Épico-1 entity — see §2.5).
- **New:** `web/app/api/bff/portfolio/route.ts`, `program/route.ts`, `project-delivery/route.ts`.
- **Reused, unchanged:** `verify_api_key`, `enforce_rate_limit`, `get_request_context`, the BFF's session-secret handling pattern from `web/app/api/bff/dashboard/route.ts`.
- **Modified (bodies only, signatures unchanged):** `web/lib/domain/portfolio.ts`'s `listPortfolios()`, `program.ts`'s `listPrograms()`, `project.ts`'s `listProjects()`.

### 1.4 Interfaces (Protocols)
No new Protocol needed at the API layer itself — FastAPI's `APIRouter` + Pydantic models are the existing contract mechanism (`intelligence.py` has no Protocol either; routes are thin, services hold behavior). The Protocols that matter for this area belong to §4 (RBAC) and are consumed here via `Depends(...)`.

```python
# Design notation only -- not implemented.
class PortfolioSummaryResponse(BaseModel):
    id: int
    name: str
    status: str          # DomainStatus, mirrors web/lib/domain/shared.ts
    health: str           # DomainHealth
    progress: float
    organization_id: int

class ProgramSummaryResponse(BaseModel):
    id: int
    portfolio_id: int
    name: str
    status: str
    health: str
    progress: float

class ProjectDeliverySummaryResponse(BaseModel):
    id: int
    program_id: int
    name: str
    status: str
    health: str
    progress: float
    owner: str
```

### 1.5 Fluxo de execução
1. Browser requests a page (e.g. `/program-management`).
2. Page's data hook (`usePrograms()`) calls `web/lib/domain/program.ts`'s `listPrograms()`.
3. `listPrograms()` body issues `fetch("/api/bff/program")` (same-origin, session cookie attached automatically) instead of returning the hardcoded array.
4. `web/app/api/bff/program/route.ts` reads the session, attaches `X-Stratech-User-Id`/`X-Stratech-Organization-Id`/`X-Stratech-Session-Id` + `X-API-Key` server-side, calls the real backend `GET /programs`.
5. `src/api/routes/program.py`'s handler runs through `verify_api_key` → `enforce_rate_limit` → `get_request_context` → `require_permission("program.read")` (§4) → service → repository → DB, filtered by `organization_id` (§3).
6. Response flows back through the BFF (error-shape-normalized) to the hook, which maps it to the existing `Program` domain class via `Program.create(...)` — the frontend's DDD invariant enforcement point does not move.

### 1.6 Dependências
`get_request_context` (existing, unused today), `verify_api_key`, `enforce_rate_limit` (existing), the new RBAC dependency (§4), the new persistence repositories (§2), Next.js route handlers convention already used by `dashboard`/`workspace` BFF routes.

### 1.7 Estrutura de diretórios
```
src/api/routes/
  intelligence.py        (existing, unchanged)
  portfolio.py            (new)
  program.py              (new)
  project_delivery.py     (new)

web/app/api/bff/
  dashboard/route.ts      (existing, unchanged)
  workspace/route.ts      (existing, unchanged)
  portfolio/route.ts      (new)
  program/route.ts        (new)
  project-delivery/route.ts (new)
```

### 1.8 Contratos públicos
- `GET /portfolios` → `list[PortfolioSummaryResponse]` (org-scoped, RBAC `portfolio.read`).
- `GET /programs?portfolio_id=` → `list[ProgramSummaryResponse]`.
- `GET /projects-delivery?program_id=` → `list[ProjectDeliverySummaryResponse]`.
- Same read-only surface for Phase 2 Foundation; write endpoints (`POST`/`PATCH`) are explicitly **out of scope** for this Technical Design pass — today's domain layer only reads seeded data, so the first implementation increment should match that (read-only parity), with writes following once RBAC's write permissions (`*.write`) are exercised.

### 1.9 Contratos internos
- Route handler → Service (`PortfolioService.list_for_organization(organization_id: int) -> list[Portfolio]`) → Repository (`PortfolioRepository.list_by_organization(organization_id: int) -> list[PortfolioRow]`).
- Service is the layer that raises domain-shaped errors (404 mapping), never the repository — mirrors `ProjectSummaryService`'s existing split from `AnalysisRepository`.

### 1.10 Diagrama lógico (ASCII)
```
Browser
  |  fetch (session cookie)
  v
Next.js BFF route (web/app/api/bff/program)
  |  fetch + X-API-Key + X-Stratech-* headers
  v
FastAPI router (src/api/routes/program.py)
  |  Depends: verify_api_key -> enforce_rate_limit -> get_request_context -> require_permission
  v
ProgramService (src/services/)
  |
  v
ProgramRepository (src/database/)
  |
  v
PostgreSQL (programs, portfolios FK)
```

### 1.11 Sequência de chamadas
`GET /program-management` (page load) → `usePrograms()` → `listPrograms()` → `fetch /api/bff/program` → BFF attaches headers → `GET /programs` → `verify_api_key` → `enforce_rate_limit` → `get_request_context` → `require_permission("program.read")` → `ProgramService.list_for_organization` → `ProgramRepository.list_by_organization` → SQL `SELECT ... WHERE organization_id = :org_id` (joined through `portfolios`) → rows → `ProgramSummaryResponse[]` → BFF passthrough → `Program.create(...)` per row → `consolidatePortfolios()` unchanged.

### 1.12 Estratégia de testes
- Backend: `tests/test_program_api.py` (mirrors `test_project_summary_api.py`'s shape — TestClient, fixture DB session, asserts 401/403/200 paths, asserts org-scoping via 2-org fixture like `test_enterprise_repository.py`'s segregation tests).
- BFF: mirrors `dashboard.spec.ts`'s "never exposes API_KEY or SESSION_SECRET to the browser" assertion, applied to the 3 new BFF routes.
- Frontend: existing `usePrograms`/`usePortfolios`/`useProjects` hook tests gain a "calls fetch, not the hardcoded array" case; component tests (`page.test.tsx` files) stay unchanged since they mock the hook, not the transport.

### 1.13 Critérios de aceite
- All 3 GET endpoints return 401 without `X-API-Key`, 400 without the 3 `X-Stratech-*` headers, 200 with them.
- Response shape matches the existing frontend `Portfolio`/`Program`/`Project` types exactly (no frontend model changes needed).
- Cross-organization requests never return another organization's rows (verified by a 2-org fixture test, not just code review).
- No existing route's behavior changes.

### 1.14 Impactos na arquitetura existente
None to existing routes. Adds 3 new routers, mounted the same way `intelligence.py`'s router is mounted today (checked against the app's route-registration point at implementation time — not located or touched in this design-only mission).

### 1.15 Riscos
- **Response-shape drift risk:** the Pydantic response model and the frontend `Portfolio`/`Program`/`Project` type must stay in lockstep by hand (no shared schema codegen exists in this codebase yet) — mitigated by contract tests on both sides (§1.12), not by a generator.
- **Sequencing risk:** this area's routes are meaningless without §2 (persistence) and are unsafe to expose without §4 (RBAC) — must not ship API before either.

### 1.16 Plano de migração
Not applicable at the API layer itself (no existing API to migrate away from — Portfolio/Program/Project have zero API surface today). The "migration" is entirely on the frontend seam: swap `list*()` bodies from array-return to `fetch()`, one Bounded Context at a time (Portfolio, then Program, then Project), each independently shippable and independently revertible.

---

## 2. Persistence Strategy

### 2.1 Objetivo
Give Portfolio/Program/Project durable, org-scoped storage, replacing `web/lib/domain/*.ts`'s hardcoded seed arrays, using the exact Alembic + SQLAlchemy + `EnterpriseRepository` pattern Épico 1 already proved.

### 2.2 Responsabilidades
- Persist the 3 entities with the fields already specified in Domain Blueprints CB-001/002/003.
- Enforce the parent-chain FK invariant at the schema level (a `Program` row cannot exist without a valid `portfolio_id`; a `ProjectDelivery` row cannot exist without a valid `program_id`) — the same invariant the frontend's `Program.create()`/`Project.create()` already enforce in-memory, now enforced twice (defense in depth, not redundancy: the frontend check protects UX, the DB constraint protects data integrity against any future non-frontend writer).
- Resolve TD-008 by construction: decide, before writing the migration, whether `projects_delivery` is a new table or the same table as the existing `projects` (Épico 1).

### 2.3 Componentes envolvidos
- **New SQLAlchemy models** in `src/database/models.py`: `Portfolio`, `Program`, `ProjectDelivery` (working name, see §2.9).
- **New Alembic migration** (next sequential revision after the existing chain — exact revision ID assigned at implementation time, not guessed here).
- **New or extended repository**: `PortfolioRepository`/`ProgramRepository`/`ProjectDeliveryRepository`, or three read/write method groups added to a sibling of `EnterpriseRepository` (decision deferred to implementation — see §2.9 open question, unchanged from the proposal).

### 2.4 Interfaces (Protocols)
```python
# Design notation only.
class PortfolioRepository(Protocol):
    def list_by_organization(self, organization_id: int) -> list[Portfolio]: ...
    def get(self, portfolio_id: int, organization_id: int) -> Portfolio | None: ...

class ProgramRepository(Protocol):
    def list_by_portfolio(self, portfolio_id: int, organization_id: int) -> list[Program]: ...

class ProjectDeliveryRepository(Protocol):
    def list_by_program(self, program_id: int, organization_id: int) -> list[ProjectDelivery]: ...
```
Protocols here (not concrete classes) so the service layer (§1.9) depends on an abstraction, matching `CredentialVerifier`/`IdentityResolver`'s existing pattern — a future non-SQL implementation (e.g., a read replica or cache) could satisfy the same Protocol without touching services.

### 2.5 Fluxo de execução
Migration applies in dependency order: `portfolios` → `programs` (FK `portfolio_id`, `ON DELETE RESTRICT` — matches Épico 1's conservative FK policy, no cascading deletes anywhere in the existing schema) → `projects_delivery` (FK `program_id`, same policy). Seed data currently in `web/lib/domain/*.ts` is inserted once via a data migration (not a schema migration) after the tables exist.

### 2.6 Dependências
Épico 1's Alembic setup (`alembic/`, `alembic.ini`), `src/database/models.py`'s existing `Base`, `organization_slug`/`normalize_project_name`-style helpers if any naming normalization is needed (TBD at implementation).

### 2.7 Estrutura de diretórios
```
src/database/
  models.py                    (gains Portfolio, Program, ProjectDelivery)
  enterprise_repository.py     (existing, unchanged, OR gains 3 method groups)
  portfolio_repository.py      (new, if kept separate -- see open question)
alembic/versions/
  000X_portfolio_program_project_delivery.py   (new, one migration for the 3 tables together, since they are FK-chained and must land atomically)
```

### 2.8 Contratos públicos
None directly (persistence is not a public contract; §1's API is the public surface). The internal contract is the Repository Protocol signatures in §2.4.

### 2.9 Contratos internos
**Open decision carried forward from the proposal, now made concrete for the Technical Design:** `projects_delivery` is proposed as its own table (not merged into the existing `projects` table) **for this Technical Design**, because merging requires Épico 4's unification decision (adding `program_id`, `sponsor`, `objective` to the Épico-1 `Project` model) which has not been made. This Technical Design documents `projects_delivery` as a **deliberately temporary, separately-named table**, with the migration plan (§2.16) stating explicitly how it collapses into `projects` once Épico 4 resolves TD-008 — so the temporary state is designed, not accidental.

### 2.10 Diagrama lógico (ASCII)
```
organizations
     ^
     | organization_id FK
     |
portfolios ----FK organization_id---> organizations
     ^
     | portfolio_id FK
programs
     ^
     | program_id FK
projects_delivery                     projects (Épico 1, separate, org_id direct)
     (no FK to projects -- unrelated until Épico 4)
```

### 2.11 Sequência de chamadas
`ProgramRepository.list_by_portfolio(portfolio_id, organization_id)` → SQLAlchemy session → `SELECT * FROM programs JOIN portfolios ON programs.portfolio_id = portfolios.id WHERE portfolios.organization_id = :org_id AND programs.portfolio_id = :portfolio_id` → mapped to `Program` SQLAlchemy rows → mapped to `ProgramSummaryResponse` (Pydantic, `from_attributes`) at the route layer (§1.4) — repository never returns Pydantic models, matching `AnalysisRepository`'s existing convention of returning ORM rows.

### 2.12 Estratégia de testes
- `tests/test_migration_000X_portfolio_program_project.py`, mirroring `test_migration_0003_identity_type.py`/`test_migration_0004_organization_slug.py`'s shape: apply migration on a throwaway DB, assert tables/FKs/constraints exist, assert downgrade reverses cleanly.
- `tests/test_portfolio_repository.py` (+ program/project variants), mirroring `test_enterprise_repository.py`'s segregation-test style: 2-organization fixture, assert no cross-org leakage on every read method.

### 2.13 Critérios de aceite
- Migration applies and reverses cleanly against a fresh DB (matches the existing `test_alembic_migration.py` pattern's bar).
- FK constraints reject an orphaned `Program` (no matching `portfolio_id`) at the DB level, not just in application code.
- All 3 repositories' read methods are org-scoped by construction (query includes `organization_id` in the `WHERE`, verified by test, not by inspection alone).

### 2.14 Impactos na arquitetura existente
Adds 3 tables; does not alter the existing `projects`/`organizations`/`users` schema. `EnterpriseRepository` either grows (3 new method groups) or gains a sibling — either choice preserves "single write path per bounded context," so neither violates CLAUDE.md's "no new registry" rule as long as the sibling (if chosen) is a repository, not a second architecture.

### 2.15 Riscos
- **TD-008 amplification risk (the same one already named in the proposal, now sharper):** if `projects_delivery` ships now and Épico 4's unification is deferred indefinitely, the codebase permanently carries a 4th "Project" concept instead of resolving the existing 3 (Decision Log D-019). This Technical Design does not remove that risk — it only makes the eventual collapse plan explicit (§2.16) so the risk is tracked, not hidden.
- **FK policy risk:** `ON DELETE RESTRICT` (chosen to match Épico 1) means a `Portfolio` can never be deleted while any `Program` references it — acceptable for now (nothing in the frontend deletes Portfolios), but must be revisited if a future Capability adds delete functionality.

### 2.16 Plano de migração
1. Land the 3-table migration (empty tables, additive, zero risk to existing data).
2. One-time data migration: insert today's `web/lib/domain/*.ts` seed rows as real rows (script, not a schema migration).
3. Swap `list*()` bodies to call the new API (§1) instead of returning the arrays — arrays are then deleted from the frontend, not kept as a fallback (no dual-source-of-truth period).
4. **Épico 4 checkpoint (explicit gate, not optional):** before or immediately after step 3, decide `projects_delivery`'s fate — either it merges into `projects` (schema migration adding `program_id` etc. to the existing table, then dropping `projects_delivery`), or it is confirmed as permanently separate with a documented reason. This Technical Design recommends resolving this **before** step 1 ships to production data, to avoid migrating real rows twice.

---

## 3. Organizational Scoping

### 3.1 Objetivo
Make every Portfolio/Program/Project row invisible outside its owning organization, closing TD-007, using Épico 1's exact `organization_id` + `CrossTenantViolationError` pattern.

### 3.2 Responsabilidades
- Attach organizational identity to the root of the chain (`portfolios.organization_id`), not to every table.
- Guard every write against linking a child to a parent from a different organization.
- Guard every read query to filter by the requester's `organization_id` at the root.

### 3.3 Componentes envolvidos
`portfolios.organization_id` (FK, `NOT NULL`), the existing `CrossTenantViolationError` class (reused, not redefined), the write-guard pattern from `enterprise_repository.py` lines ~200-230 (the existing cross-tenant check block).

### 3.4 Interfaces (Protocols)
```python
# Design notation only -- extends the existing pattern, no new abstraction.
def assert_same_organization(child_org_id: int, parent_org_id: int) -> None:
    if child_org_id != parent_org_id:
        raise CrossTenantViolationError(
            f"organization mismatch: {child_org_id} != {parent_org_id}"
        )
```
This is a function, not a Protocol — Épico 1's own guard is a private method inside `EnterpriseRepository`, not a Protocol-based abstraction, so this Technical Design keeps the same shape rather than over-abstracting a one-branch check into a new interface.

### 3.5 Fluxo de execução
On write: repository loads the parent row, compares `parent.organization_id` (or, for `Program`/`ProjectDelivery`, the organization_id resolved transitively through the parent chain) against the requester's `organization_id` from `RequestContext`; mismatch raises `CrossTenantViolationError`, caught at the route layer and mapped to HTTP 403. On read: query root always includes `WHERE portfolios.organization_id = :org_id`, joined downward — `programs`/`projects_delivery` never carry their own `organization_id` column (single source of truth, matching §2.10's diagram).

### 3.6 Dependências
`get_request_context` (resolves the requester's `organization_id`), the existing `CrossTenantViolationError`, the FK chain from §2.

### 3.7 Estrutura de diretórios
No new directory — this is behavior inside the repositories from §2.7, not a separate module (matching Épico 1, where scoping lives inside `EnterpriseRepository`, not in a dedicated "scoping" file).

### 3.8 Contratos públicos
None new — scoping is invisible to the API contract (§1.8); it manifests only as "you get fewer rows" or "403" for a wrong-org actor, never a different response shape.

### 3.9 Contratos internos
Every repository method in §2.4 takes `organization_id` as an explicit parameter (never inferred implicitly inside the repository) — mirrors `EnterpriseRepository`'s existing methods, all of which take organization context explicitly rather than reading a global/session-implicit value.

### 3.10 Diagrama lógico (ASCII)
```
Request (organization_id=7)
   |
   v
Repository.list_by_organization(organization_id=7)
   |
   v
SQL: SELECT ... FROM programs
     JOIN portfolios ON programs.portfolio_id = portfolios.id
     WHERE portfolios.organization_id = 7
   |
   v
Rows visible ONLY if portfolios.organization_id = 7
(a Program under a portfolio from org 3 is never returned, never leaked)
```

### 3.11 Sequência de chamadas
Same as §1.11/§2.11, with the org filter as a non-optional clause baked into every repository method's SQL, not an application-level post-filter (post-filtering after an unscoped query was explicitly the anti-pattern Épico 1's tests were written to rule out).

### 3.12 Estratégia de testes
Reuses the exact segregation-test shape already in `tests/test_enterprise_repository.py` (2-organization fixture, assert zero cross-visibility) — the same 7 dedicated segregation tests cited in the proposal are the template, applied to the 3 new repositories.

### 3.13 Critérios de aceite
- Zero cross-organization rows returned or writable, verified by test, for all 3 entities.
- No table beyond `portfolios` carries its own `organization_id` column (schema review criterion, prevents the two-source-of-truth risk named in the proposal).

### 3.14 Impactos na arquitetura existente
None — this is a direct application of an already-accepted, already-tested pattern; no new architectural surface.

### 3.15 Riscos
Low — this is the one area the proposal already flagged as having "no real design decision left," and this Technical Design confirms that remains true; the only execution risk is a developer forgetting the `WHERE` clause on one query path, mitigated entirely by the mandatory segregation tests in §3.12 (a missing filter fails the test, not just a code review).

### 3.16 Plano de migração
Included in §2.16's migration (the `organization_id` column ships with the first migration, not retrofitted later) — this was the proposal's explicit point: "closing TD-007 by construction, not retrofit."

---

## 4. RBAC Architecture

### 4.1 Objetivo
Make the existing `roles`/`permissions`/`role_permissions`/`user_roles` tables (populated since Épico 1, enforced nowhere) actually gate route access, starting with the new Portfolio/Program/Project routes from §1.

### 4.2 Responsabilidades
- Resolve "can this user do this action in this organization" from the existing tables.
- Provide a FastAPI dependency any route (new or existing) can declare, the same way routes already declare `Depends(verify_api_key)`.
- Keep AI-agent actions and human actions under the same permission vocabulary (no parallel "AI permission" system), per ADR-V2-007.

### 4.3 Componentes envolvidos
**New:** `src/services/authorization/interfaces.py` (`PermissionChecker` Protocol), `src/services/authorization/checker.py` (concrete implementation querying `role_permissions`/`user_roles`), `src/api/authorization.py` (`require_permission()` FastAPI dependency factory). Placed in a new `src/services/authorization/` package rather than folded into `src/services/identity/`, because identity (who you are) and authorization (what you can do) are already modeled as separate concerns in the schema (separate tables) — the code structure should mirror that, not conflate them into one package.

### 4.4 Interfaces (Protocols)
```python
# Design notation only.
class PermissionChecker(Protocol):
    def has_permission(
        self, user_id: int, organization_id: int, permission: str
    ) -> bool: ...
```
Mirrors `CredentialVerifier`/`IdentityResolver`'s exact shape: one Protocol, one method, no inheritance hierarchy — consistent with the codebase's existing "small Protocol, one job" convention.

### 4.5 Fluxo de execução
1. Route declares `Depends(require_permission("program.read"))` after `Depends(get_request_context)`.
2. `require_permission`'s inner dependency function receives the already-resolved `RequestContext` (via `Depends(get_request_context)`) and a `PermissionChecker` (via its own `Depends`).
3. Calls `checker.has_permission(context.user.user_id, context.organization.organization_id, "program.read")`.
4. `False` → `HTTPException(403)`. `True` → request proceeds; nothing is injected into the route's own signature beyond the existing `RequestContext` (permission check is a gate, not a value the route needs).

### 4.6 Dependências
`get_request_context` (existing), the existing `roles`/`permissions`/`role_permissions`/`user_roles` tables (already populated with 4 seed roles per Épico 1), a session/engine dependency (reuses the existing `sessionmaker` injection pattern from `build_repository()` in `intelligence.py`).

### 4.7 Estrutura de diretórios
```
src/services/authorization/
  __init__.py
  interfaces.py     (PermissionChecker Protocol)
  checker.py        (SQL-backed implementation)
src/api/
  authorization.py  (require_permission() dependency factory)
```

### 4.8 Contratos públicos
None directly — RBAC is a cross-cutting gate, not an endpoint. Its only externally visible contract is the 403 response shape, matching FastAPI's existing default `HTTPException` JSON shape (no new error envelope invented).

### 4.9 Contratos internos
```python
# Design notation only.
def require_permission(permission: str):
    def _check(
        context: RequestContext = Depends(get_request_context),
        checker: PermissionChecker = Depends(build_permission_checker),
    ) -> None:
        if not checker.has_permission(
            context.user.user_id, context.organization.organization_id, permission
        ):
            raise HTTPException(status_code=403, detail=f"missing permission: {permission}")
    return _check
```
Permission string vocabulary: `{resource}.{action}` — `portfolio.read`, `portfolio.write`, `program.read`, `program.write`, `program.approve`, `project_delivery.read`, `project_delivery.write` — resource names match the 3 Bounded Context names, action names match the existing `permissions` table's seeded verbs (confirmed against Épico 1's seed data at implementation time, not re-verified in this design-only pass).

### 4.10 Diagrama lógico (ASCII)
```
Route: GET /programs
  Depends(verify_api_key)
  Depends(enforce_rate_limit)
  Depends(get_request_context)  -----> RequestContext(user_id, organization_id)
  Depends(require_permission("program.read"))
        |
        v
  PermissionChecker.has_permission(user_id, organization_id, "program.read")
        |
        v
  SELECT 1 FROM user_roles
    JOIN role_permissions ON user_roles.role_id = role_permissions.role_id
    JOIN permissions ON role_permissions.permission_id = permissions.id
   WHERE user_roles.user_id = :user_id
     AND permissions.name = 'program.read'
     -- organization scoping on user_roles itself, per Épico 3's exact schema (TBD there)
        |
        v
  bool -> 403 or proceed
```

### 4.11 Sequência de chamadas
Identical chain to §1.11, with `require_permission` inserted immediately after `get_request_context` and before the service call — a request that fails the permission check never reaches `ProgramService`, matching the existing pattern where `verify_api_key` failures never reach any handler body.

### 4.12 Estratégia de testes
`tests/test_authorization.py`, mirroring `test_identity_auth_service.py`'s style: seed 2 users with different roles, assert `has_permission` returns the expected bool per (user, permission) pair; `tests/test_program_api.py` (§1.12) gains a 403 case for a user lacking `program.read`, alongside its existing 401/200 cases.

### 4.13 Critérios de aceite
- A user with no relevant role gets 403, not 200 with empty data (fails closed, not silently empty — an important distinction the design must state explicitly, since an empty-list 200 would be indistinguishable from "no data exists").
- Every new route from §1 declares an explicit `require_permission(...)`; no route defaults to "no check" (fails closed by convention, not by exception-list).
- Existing routes (`intelligence.py`) are untouched — RBAC is additive to new routes only in this Technical Design; retrofitting it onto `intelligence.py` is explicitly out of scope here (would be a functional change to an existing route, which the Executive Directive forbids in this mission).

### 4.14 Impactos na arquitetura existente
Adds one new package (`src/services/authorization/`) and one new module (`src/api/authorization.py`); does not modify `src/services/identity/*` or any existing route. Reuses `get_request_context` for the first time since it was built in Épico 2 — this is the "already exists, already built... consumed by zero routes today" gap finally closing, exactly as flagged in the Domain Model/AR-1 findings.

### 4.15 Riscos
- **Sequencing risk (carried over from the proposal, unchanged):** this design assumes Épico 3 ("Organização e RBAC inicial") has defined the exact role/permission seed set and the `user_roles` table's organization-scoping column — if Épico 3's schema differs from what's assumed in §4.9's SQL sketch (e.g., if `user_roles` needs its own `organization_id` for users with different roles per org), this design's SQL sketch must be revised before implementation, not after.
- **Fail-open risk:** if `require_permission` is ever accidentally omitted from a route, that route fails open (no check = allowed) under FastAPI's dependency model. Mitigation is procedural, not architectural: a required checklist item in code review ("does every new route declare require_permission?"), since no automatic enforcement mechanism is proposed in this design.

### 4.16 Plano de migração
No migration — `roles`/`permissions`/`role_permissions`/`user_roles` already exist and are already seeded (Épico 1). This area is pure behavior addition (a dependency + a checker), not a schema change. Sequencing: land alongside or before §1's routes (a route without RBAC should not ship even briefly, per the RC-2 "AI NOT READY" finding this design intends to close).

---

## 5. Event Architecture

### 5.1 Objetivo
Ensure the new Portfolio/Program/Project routes (§1) emit events at the correct seams from day one, without building the Event Bus itself (that stays later-phase infrastructure, per the proposal).

### 5.2 Responsabilidades
- Extend the existing Event Map (`docs/product/stratech-v2/Event-Map.html`) with the new chain's events.
- Provide a single call-site seam (`emit_event`) that every mutating route calls, regardless of whether the backing implementation is a no-op/log or a real bus later.
- Keep the human-in-the-loop rule (ADR-V2-007) enforced by RBAC (§4), never by the event layer itself.

### 5.3 Componentes envolvidos
**New:** `src/services/events/interfaces.py` (`EventEmitter` Protocol), `src/services/events/noop_emitter.py` (`NoOpEventEmitter`, log-only implementation). No message queue, no new infrastructure component.

### 5.4 Interfaces (Protocols)
```python
# Design notation only.
class EventEmitter(Protocol):
    def emit(self, event_name: str, payload: dict, organization_id: int) -> None: ...

class NoOpEventEmitter:
    """Logs and does nothing else -- the seam exists, the bus doesn't yet."""
    def emit(self, event_name: str, payload: dict, organization_id: int) -> None:
        logger.info("event emitted (no-op): %s org=%s", event_name, organization_id)
```

### 5.5 Fluxo de execução
Any route that mutates state (future `POST`/`PATCH` on §1's routers — not in this Technical Design's read-only scope, but designed for now so the seam is correct when writes are added) calls `emitter.emit("program.created", {...}, organization_id)` immediately after a successful repository write, inside the same service method, before returning — same position a real event-sourcing emit would occupy, so promoting `NoOpEventEmitter` to a real emitter later changes zero call sites.

### 5.6 Dependências
None beyond standard logging; deliberately zero coupling to any message-queue library in this phase.

### 5.7 Estrutura de diretórios
```
src/services/events/
  __init__.py
  interfaces.py       (EventEmitter Protocol)
  noop_emitter.py      (NoOpEventEmitter)
```

### 5.8 Contratos públicos
None — events are internal-only in this phase (no event ever crosses the API boundary in Phase 2 Foundation).

### 5.9 Contratos internos
New Event Map rows (extending the existing table, same document, same columns — producer/consumer/human-in-the-loop):

| Event | Producer | Consumer(s) | Human-in-the-loop |
|---|---|---|---|
| `portfolio.created` | Portfolio service | (none yet — logged only) | No |
| `program.created` | Program service | (none yet) | No |
| `program.linked_to_portfolio` | Program service | (none yet) | No |
| `project_delivery.created` | ProjectDelivery service | (none yet) | No |
| `project_delivery.linked_to_program` | ProjectDelivery service | (none yet) | No |

None of these are human-in-the-loop events (unlike `recommendation.pending_validation`) because none of them represent an AI action yet — Phase 2 Foundation has no AI agent writing to this domain; that arrives in AI Foundation, the next Phase 2 sub-stage, at which point new rows with `human_in_the_loop = true` get added following ADR-V2-007's existing rule, not a new rule.

### 5.10 Diagrama lógico (ASCII)
```
ProgramService.create(...)
       |
       v
  ProgramRepository.insert(...)  -- DB write succeeds
       |
       v
  EventEmitter.emit("program.created", {...}, organization_id)
       |
       v
  NoOpEventEmitter: logger.info(...)   [Phase 2 Foundation]
       |
       v  (future, Workflow Automation phase, NOT this design)
  Real bus: publish to queue/topic, consumed by Knowledge Platform / Executive Copilot
```

### 5.11 Sequência de chamadas
Extends §1.11's chain: after `ProgramRepository.insert` succeeds (write path, not the read path this Technical Design otherwise scopes), `ProgramService` calls `self._emitter.emit(...)` before returning to the route. Read paths (§1's actual scope) never emit events — only mutations do, matching the Event Map's existing "created"/"raised"/"pending" verb pattern, none of which describe reads.

### 5.12 Estratégia de testes
`tests/test_program_service.py` (new, or extended if a service test file already exists at implementation time) asserts `emit` is called exactly once with the right event name/payload/org after a successful create, using a fake `EventEmitter` (test double implementing the Protocol) — mirrors how `test_identity_auth_service.py` likely fakes `CredentialVerifier`/`IdentityResolver` rather than hitting real Argon2/DB in unit scope (pattern confirmed by the Protocol-based DI design itself, not re-read in this pass).

### 5.13 Critérios de aceite
- Every mutating service method emits exactly one event, at the correct name, after (not before) the write succeeds — a failed write must never emit a "created" event.
- `NoOpEventEmitter` is the only implementation shipped in Phase 2 Foundation; no queue/broker dependency is added to `pyproject.toml`/`requirements` in this phase.
- Event Map document is extended, not replaced — existing rows (`project.created`, `risk.raised`, etc.) stay untouched.

### 5.14 Impactos na arquitetura existente
Adds one new small package; touches no existing route or service. The Event Map document gains rows but keeps its existing shape.

### 5.15 Riscos
- **Premature promotion risk:** the temptation to make `NoOpEventEmitter` "a little bit real" (e.g., write to a table) inside this phase would quietly start Workflow Automation work inside Foundation Architecture, contradicting the phase boundary the Executive Directive itself drew. This design explicitly recommends resisting that temptation — no-op means no-op.
- **Naming risk:** `project_delivery.*` event names (not `project.*`) were chosen deliberately to avoid colliding with the Event Map's pre-existing `project.created` (which describes the Épico-1 `Project`, an unrelated concept per TD-008) — implementers must not "clean this up" to `project.*` without first resolving Épico 4.

### 5.16 Plano de migração
Not applicable — no existing event mechanism to migrate from (the Event Map is reference taxonomy only, "nenhum evento desta tabela existe ainda em código").

---

## 6. Cross-Area Sequencing (implementation order, if/when authorized)

This Technical Design does not authorize implementation, but records the safe build order so a future mission does not have to re-derive it:

1. **Persistence (§2)** first — nothing else has anything to read/write without tables.
2. **Organizational Scoping (§3)** lands inside the same migration/repositories as §2 — never a separate later step (closes TD-007 by construction, not retrofit, per the proposal).
3. **RBAC (§4)** next — must exist before §1's routes are reachable, so no route is ever briefly unprotected.
4. **API (§1)** — routes wired last, once persistence, scoping and RBAC are all real.
5. **Event seams (§5)** — can be added alongside §1 (same service methods), since `NoOpEventEmitter` has no dependency on anything else being ready.

Épico 3 (RBAC) and Épico 4 (Project unification) fold into steps 3 and 2/2.16 respectively, per the proposal's recommendation — this design does not re-open that recommendation, only restates it in sequence form.

---

## 7. Validation Questions (mandatory, per Executive Directive)

**1. O Technical Design está completo?**
Sim. Os 5 componentes (API, Persistence, Organizational Scoping, RBAC, Event Architecture) estão especificados com os 15 elementos exigidos cada, com nomes concretos de Protocols, estrutura de diretórios, contratos e planos de teste/migração — grounded em código real já existente (`intelligence.py`, `identity_context.py`, `enterprise_repository.py`, `identity/interfaces.py`) e não em abstrações genéricas.

**2. Existe alguma inconsistência arquitetural?**
Não surgiu nenhuma inconsistência nova nesta passagem. Seguem em aberto as duas questões já sinalizadas na proposta e não resolvidas aqui (corretamente, por não serem decisões de Technical Design e sim decisões de escopo/roadmap): (a) a Reconciliação de Roadmap (Phase 2 vs. Releases 0.3-0.5); (b) o escopo exato de RBAC do Épico 3 (schema de `user_roles` multi-organização), do qual §4.9/§4.15 dependem.

**3. Existe risco de refatoração futura?**
Sim, um risco nomeado e não eliminado: se `projects_delivery` (§2.9) for implementado antes da decisão de unificação do Épico 4, a base de código passa a ter um 4º conceito de "Project" em vez de resolver os 3 já existentes (TD-008). Este Technical Design não elimina esse risco — apenas o torna explícito e propõe um gate obrigatório antes da migração de dados reais (§2.16, passo 4).

**4. Todos os componentes respeitam DDD, Clean Architecture e Hexagonal?**
Sim. Rotas são adapters finos (nenhuma lógica de negócio no handler, mesmo padrão de `intelligence.py`); Services são a camada de aplicação/casos de uso; Repositories são ports para a persistência (Protocol-based, substituíveis); RBAC e Events são cross-cutting concerns injetados via dependência (Protocol + DI), nunca acoplados ao domínio; a camada de domínio do frontend (`web/lib/domain/*`) permanece livre de qualquer mecanismo de entrega (fetch fica em `list*()`'s corpo, nunca dentro das classes `Program`/`Project`).

**5. A STRATECH está pronta para iniciar a implementação da Foundation?**
Sim, condicionado a duas confirmações que este documento não pode tomar sozinho: (a) confirmação do Founder/Architecture Review Board sobre a Reconciliação de Roadmap (§0 da proposta); (b) definição do escopo exato do Épico 3 (RBAC) antes de finalizar §4.9. Com essas duas confirmações, a sequência de implementação está definida (§6) e não há bloqueio arquitetural remanescente.

---

## 8. What this Technical Design reuses (nothing new invented, extends the proposal's own table)

| Area | Reuses |
|---|---|
| API | `intelligence.py`'s router/dependency shape, `get_request_context` (first real consumer), the BFF pattern |
| Persistence | Épico 1's Alembic + SQLAlchemy + repository pattern, `web/lib/domain/*`'s repository-shaped accessor seam (D-011) |
| Organizational Scoping | Épico 1's `organization_id` + `CrossTenantViolationError`, unchanged |
| RBAC | `identity/interfaces.py`'s Protocol shape (`CredentialVerifier`/`IdentityResolver`), the existing seeded `roles`/`permissions` tables |
| Events | The existing Event Map document, ADR-V2-007's human-in-the-loop rule, D-011's "seam now, mechanism later" discipline |

No new provider, no new registry, no parallel architecture tree — CLAUDE.md's rules hold throughout.
