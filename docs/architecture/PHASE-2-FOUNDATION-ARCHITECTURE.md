# Phase 2 — Foundation Architecture

**Status:** PROPOSAL — architecture and governance only. No functional implementation in this mission, per Executive Directive (Phase 2 — Enterprise AI Platform). Pending Founder approval before any Engineering Order/Technical Design/Implementation begins, per the existing Product-First flow (`docs/governance/GOVERNANCE_MODEL.md` §2A).
**Date:** 2026-07-18
**Author:** Claude / Chief Software Architect
**Precondition:** RC-2 Enterprise Certification (`docs/product/governance/RC-2-ENTERPRISE-CERTIFICATION.md`), merged to `main` (`3eb9f185`).

---

## 0. Roadmap Reconciliation (read before the rest)

The existing Master Roadmap organizes remaining work as **Releases** (0.2 Portfolio & Governance → 0.3 AI Foundation → 0.4 Integration Hub → 0.5 Event Orchestration). The Executive Directive organizes Phase 2 as **Foundation Architecture → AI Foundation → Knowledge Platform → Executive Copilot → Workflow Automation → Executive Intelligence**. These cover overlapping ground (both have an "AI Foundation," both eventually need event orchestration) but are not the same shape, and nothing has yet said which one governs going forward.

**This document assumes Phase 2 reorganizes and supersedes Release 0.2's remaining scope (Program/Project unification, Épico 3 RBAC) onward** — i.e., Release 0.1 (Épicos 1-2, done) stays as-is, but the Release 0.3-0.5 labels are retired in favor of the Phase 2 sequence. This is stated as an assumption, not a unilateral decision — the Master Roadmap itself is **not rewritten in this document**; that would be presumptuous ahead of confirmation. If this assumption is wrong, only `STRATECH_V2_MASTER_ROADMAP.md`'s Release section needs updating, nothing architectural changes.

---

## 1. API Strategy

### Current state
- `src/api/routes/intelligence.py` is the only real API surface — X-API-Key auth (`verify_api_key`), rate limiting, one router per concern. Portfolio/Program/Project (Capabilities 01-03) have **no API surface at all** — they exist only as seeded data inside `web/lib/domain/`, read directly by the frontend with no network hop.
- `src/api/identity_context.py` (`get_request_context`) already exists as unused infrastructure — built during Épico 2 specifically "for Epics 3-5," reading `X-Stratech-User-Id`/`X-Stratech-Organization-Id`/`X-Stratech-Session-Id` headers into a `RequestContext`. No route consumes it yet.
- The frontend already has a BFF layer (`web/app/api/bff/*`) that proxies real backend calls (`usePortfolioSummary` → `/api/bff/dashboard`) while keeping `API_KEY`/`SESSION_SECRET` server-side only (verified by `dashboard.spec.ts`'s "never exposes API_KEY or SESSION_SECRET to the browser").

### Proposed architecture
1. **New backend routers** under `src/api/routes/` (`portfolio.py`, `program.py`, `project.py`), each following `intelligence.py`'s exact shape: `APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])`, plus **newly wired** `Depends(get_request_context)` for org/user/session — the first routes in the codebase to actually consume that dependency.
2. **New BFF routes** under `web/app/api/bff/{portfolio,program,project}` mirroring the existing `dashboard`/`workspace` BFF pattern — same session-secret handling, same error-shape convention (`DashboardErrorBody`).
3. **`web/lib/domain/{portfolio,program,project}.ts`'s `list*()` functions get their body swapped** for a real `fetch()` call to the new BFF route — this is the exact seam these functions were built for (Decision Log D-011); no consumer (hooks, components, pages) changes.
4. **Versioning:** no new version prefix needed yet — `/api/*` has no version segment today (`/api/portfolio/summary`, not `/api/v1/portfolio/summary`); introducing one now would be a bigger, unrelated change. Revisit only if a breaking change to an existing route is ever needed.

### Open questions
- Should Portfolio/Program/Project ship as one combined route file or three, given they're one Bounded Context each (Domain Blueprints CB-001/002/003)? Recommendation: three files, mirroring the three Blueprints — consistent with "one Bounded Context, one boundary" already used in `web/lib/domain/`.

---

## 2. Persistence Strategy

### Current state
- `src/database/models.py` has no `Portfolio`/`Program`/`Project`-chain tables — `Project` there is the Épico-1 real entity (org-scoped, used for membership), unrelated to the domain-layer `Project` from Capability 03 (TD-008).
- The Épico 1 migration pattern is proven: Alembic migration + SQLAlchemy model + `EnterpriseRepository` as the single write path, with a `CrossTenantViolationError` guard.

### Proposed architecture
1. **New tables**: `portfolios`, `programs`, `projects_delivery` (working name — avoids colliding with the existing `projects` table until Épico 4 unifies them, see TD-008 and §3 below), each with the exact fields already specified in Domain Blueprints CB-001/002/003, plus `organization_id` (FK to `organizations`, `NOT NULL`) from the first migration — closing TD-007 by construction, not retrofit.
2. **Migration order** follows the domain hierarchy itself: `portfolios` → `programs` (FK `portfolio_id`) → `projects_delivery` (FK `program_id`) — same dependency order already enforced in the frontend domain layer (`Program` requires `portfolioId`, `Project` requires `programId`).
3. **Seed data retirement**: `web/lib/domain/*.ts`'s hardcoded `PROGRAMS`/`PROJECTS` arrays are replaced by real rows migrated once (a one-time data migration, not a schema concern) — the *shape* doesn't change, only where it lives.
4. **`EnterpriseRepository` gains three new write paths** (or a sibling repository, if this Enterprise Repository is judged to be reaching a responsibility limit — a call for whoever writes the Technical Design, not decided here).

### Relationship to Épico 4 (Project unification)
This is the natural moment to resolve TD-008: once `projects_delivery` is a real table, the question "is this the same as the Épico-1 `Project`, or a second `Project` table forever?" must be answered **before** writing the migration, not after. Recommendation: Épico 4 and this persistence work should be a single Engineering Order, not two — splitting them risks building the wrong shape twice.

### Open questions
- Does Épico 4's unification mean `projects_delivery` and `projects` become the *same* table (Project gains `program_id`, `sponsor`, `objective`, etc.)? This is the architecturally cleaner answer and avoids ever having two `Project` tables — but it's a data-modeling decision for the Technical Design phase, not this document.

---

## 3. Organizational Scoping

### Current state
- Épico 1 established the pattern: `organization_id` on every tenant-scoped table, composite unique constraints (`uq_users_org_email`, `uq_projects_org_name`), and `EnterpriseRepository` guarding every write against cross-tenant linkage.
- Portfolio/Program/Project (frontend domain) have **no organization concept at all today** — every seeded Portfolio is implicitly visible to every session, because nothing scopes it (TD-007).

### Proposed architecture
Repeat the Épico 1 pattern exactly — no new scoping mechanism invented:
1. `organization_id` on `portfolios` (root of the chain); `programs`/`projects_delivery` inherit scope transitively through their parent FK, not by duplicating `organization_id` on every table (avoids the two-source-of-truth risk the Épico 1 schema already avoided).
2. `EnterpriseRepository` (or its sibling) enforces the same guard: any write to a `Program` whose `portfolio_id` belongs to a different organization than the requester's raises `CrossTenantViolationError`.
3. Read paths filter by `organization_id` at the query root (`WHERE portfolios.organization_id = :org_id`), joined down — same shape as the existing Project/AnalysisRepository queries.

### Open questions
None — this is the one area with no real design decision left to make; it's directly copying a pattern already proven and tested (7 dedicated segregation tests exist for the Épico 1/2 schema).

---

## 4. RBAC Architecture

### Current state
- `roles`, `permissions`, `role_permissions`, `user_roles` tables exist since Épico 1 — **populated, never enforced**. No route checks a permission; RBAC is currently storage without behavior.
- `get_request_context` (§1) already resolves `user_id`/`organization_id` per request — the missing piece is *what the user is allowed to do*, not *who they are*.
- The identity layer's `Protocol`-based extensibility (`CredentialVerifier`, `IdentityResolver` in `src/services/identity/interfaces.py`) is the exact shape to replicate for authorization.

### Proposed architecture
1. **New `PermissionChecker` Protocol** (`src/services/identity/interfaces.py` or a new `src/services/authorization/interfaces.py`, TBD at Technical Design time): `def has_permission(user_id: int, organization_id: int, permission: str) -> bool`.
2. **New FastAPI dependency** `require_permission(permission: str)`, composed with the existing `get_request_context` — routes declare `Depends(require_permission("portfolio.write"))` the same way they declare `Depends(verify_api_key)` today.
3. **Permission naming**: `{resource}.{action}` (e.g., `portfolio.read`, `portfolio.write`, `program.approve`) — resource names should match the Bounded Context names already established (Portfolio Management, Program Management, Project Delivery), not invent a parallel vocabulary.
4. **AI-specific permissions**: any future AI agent action that mutates state (per ADR-V2-007, "toda ação crítica de IA exige validação humana por padrão") is itself a permission-checked action, attributed to the human who approved it — not a separate, agent-only authorization path. This keeps Explainable AI and RBAC as one mechanism, not two.

### Relationship to Épico 3
Épico 3 ("Organização e RBAC inicial," Release 0.1) already owns this scope. This section does not duplicate or race Épico 3 — it specifies how RBAC, once built, plugs into the *new* Portfolio/Program/Project routes (§1) rather than only the original Enterprise Foundation entities. Recommendation: Épico 3 and this RBAC extension should be delivered together, since building permission checks for a domain that doesn't have an API yet (§1) has no route to protect, and building an API without RBAC re-creates the exact gap RC-2 flagged as "AI NOT READY."

### Open questions
- Reference RBAC model cites 14 roles eventually (vs. today's 4) — whether Phase 2 needs all 14 or a subset for the new domain is an Épico 3 scoping question, not decided here.

---

## 5. Event Architecture

### Current state
- `docs/product/stratech-v2/Event-Map.html` already defines a taxonomy: `project.created`, `risk.raised`, `decision.pending`, `recommendation.pending_validation`, etc. — producer, consumer(s), human-in-the-loop flag per event. **None of these events exist in code yet** — it's reference taxonomy only, explicitly scoped to Release 0.5 (Event Bus/Workflow Engine).
- ADR-V2-007 (toda ação crítica de IA exige validação humana por padrão) already governs the human-in-the-loop rule this taxonomy encodes.

### Proposed architecture
Phase 2 Foundation Architecture's job here is **not** to build the Event Bus (that remains later-phase, heavier infrastructure work) — it is to make sure the new domain (§1-§4) **emits events at the right seams from day one**, so nothing needs retrofitting when the Bus arrives:
1. **Extend the existing Event Map** (not replace it) with Portfolio/Program/Project-chain events: `portfolio.created`, `program.created`, `program.linked_to_portfolio`, `project.created`, `project.linked_to_program` — same table shape (producer/consumer/human-in-the-loop), same document.
2. **No new event bus, no new message queue, no new infrastructure** in this phase — routes (§1) call a single `emit_event()` seam (even a no-op/log-only implementation initially) at the same point a real event would fire later. This is the same "repository-shaped accessor" discipline already used for `listPortfolios()` etc. (Decision Log D-011): build the seam now, fill in the real mechanism later, change nothing at the call site.
3. **Human-in-the-loop stays enforced by RBAC (§4), not by the event layer** — an event records that something happened; it never becomes the approval gate itself (ADR-V2-007's existing distinction).

### Open questions
- Whether `emit_event()` becomes real infrastructure in this same Phase or stays a documented no-op until Workflow Automation (later Phase 2 stage) is a Technical Design decision, not an architectural one — either way, the call sites are the same.

---

## 6. Summary of What This Proposal Reuses (nothing new invented)

| Area | Reuses |
|---|---|
| API | `intelligence.py`'s router shape, `verify_api_key`/`enforce_rate_limit`, the BFF pattern already used by `dashboard`/`workspace` |
| Persistence | Épico 1's Alembic + SQLAlchemy + `EnterpriseRepository` pattern, `web/lib/domain/*`'s repository-shaped accessor seam |
| Organizational Scoping | Épico 1's `organization_id` + composite-unique + `CrossTenantViolationError` pattern, unchanged |
| RBAC | `get_request_context` (already built, unused), the `Protocol`-based extensibility already used for identity |
| Events | The existing Event Map taxonomy, ADR-V2-007's human-in-the-loop rule |

No new provider, no new registry, no new architecture tree — CLAUDE.md's rules hold throughout this proposal.

---

## 7. Governance Impact (to update once this proposal is approved, not before)

- New ADRs (one per area, or one consolidated "Phase 2 Foundation" ADR — recommendation: one consolidated ADR, since all five areas are one coherent decision made together) once approved and a Technical Design exists.
- `docs/architecture/DOMAIN-MODEL.md` gains a "Phase 2: persistence and API" section once implementation starts.
- `docs/architecture/TECHNICAL_DEBT.md`: TD-007 and TD-008 both get a "resolution planned in Phase 2 Foundation Architecture" cross-reference.
- Master Roadmap: Release 0.2's remaining rows (Program/Project unification, Épico 3) get reconciled with the Phase 2 sequence per §0, pending confirmation.

---

## Recommendation

**STRATECH is not yet ready to start AI Foundation.** This Foundation Architecture proposal must first be reviewed and approved, then implemented (API + Persistence + Organizational Scoping + RBAC + Event seams) before AI Foundation begins — building AI Constitution/Enterprise AI Architecture/Context Builder on top of a domain that has no API, no persistence, and no enforced permissions would mean AI Foundation immediately inherits exactly the "AI NOT READY" gaps RC-2 already named. Recommended sequence: approve this proposal → Technical Design per area (or one consolidated TDS) → implementation, with Épico 3 (RBAC) and Épico 4 (Project unification) folded into this work rather than run separately → re-certify readiness → begin AI Foundation.
