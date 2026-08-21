"""Enterprise Foundation entities (STRATECH V2, Release 0.1, Épico 1).

Schema only: no authentication flow, no RBAC engine, no admin UI in this
package -- those arrive in later épicos operating on these tables. Every
tenant-scoped table carries organization_id so multi-organization isolation
is structural from day one, even though the initial operating mode is a
single main organization per installation (Founder directive, 2026-07-17).

Cross-tenant integrity that a plain FK cannot express (e.g. a membership
linking a user of org A to a project of org B) is enforced by
EnterpriseRepository -- never bypass it for writes to these tables.
"""
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)

from src.database.base import Base

# Production Embedding Provider Approval (Founder Decision, D-177):
# Voyage AI, model voyage-4, dimension 1024 -- replaces the Mock
# placeholder dimension (16) that only proved the pgvector wiring.
# Migration 0021 carries its own frozen copy of this value (never
# imports this constant, per this repo's migration discipline).
KNOWLEDGE_EMBEDDING_DIM = 1024


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    # Stable external identifier -- used by APIs, login and integrations;
    # independent of `name` after creation (0004 migration, EO-015
    # Organizational Identity Scope Correction). `name` remains purely a
    # display attribute.
    slug = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"
    # User Management (Wave 2, migration 0009): case-insensitive uniqueness
    # enforced at the database, not just at the application layer -- a
    # functional unique index on lower(email) closes the concurrent-insert
    # race a plain "check then insert" would leave open. Replaces the
    # original case-sensitive uq_users_org_email (migration 0002); callers
    # normalize email to lowercase before writing (see
    # src/services/identity/email_normalization.py), so this index and the
    # stored values agree by construction.
    __table_args__ = (
        Index(
            "uq_users_org_email_lower",
            "organization_id",
            text("lower(email)"),
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)
    # "standard" | "demo" -- distinguishes the Demo Mode user from real
    # accounts without a second boolean column (Epico 2, migration 0003).
    identity_type = Column(String(20), nullable=False, default="standard")
    # User Management (Wave 2, migration 0009): soft state, never a hard
    # delete -- consistent with every other Enterprise entity. An inactive
    # user cannot authenticate (AuthService.authenticate) nor pass any
    # permission check (SqlPermissionChecker.has_permission).
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)


class Portfolio(Base):
    """Enterprise Domain persistence (Wave 2, Domain Blueprint
    `DOMAIN-BLUEPRINT-PROJECT.md`). Root of the Portfolio -> Program ->
    Project chain -- the only table in the chain that carries
    organization_id directly; Program and Project derive their
    organization transitively (Foundation Technical Design §3/§3.10)."""

    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_portfolios_org_code"),)

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(String(1000), nullable=True)
    category = Column(String(255), nullable=True)
    executive_owner = Column(String(255), nullable=True)
    strategic_objective = Column(String(1000), nullable=True)
    status = Column(String(20), nullable=False, default="Ativo")
    health = Column(String(10), nullable=False, default="green")
    priority = Column(String(10), nullable=False, default="Média")
    start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    progress_percentage = Column(Integer, nullable=False, default=0)
    program_count = Column(Integer, nullable=False, default=0)
    project_count = Column(Integer, nullable=False, default=0)
    linked_demands = Column(Integer, nullable=False, default=0)
    linked_risks = Column(Integer, nullable=False, default=0)
    linked_issues = Column(Integer, nullable=False, default=0)
    pending_decisions = Column(Integer, nullable=False, default=0)
    sponsor = Column(String(255), nullable=True)
    pmo_owner = Column(String(255), nullable=True)
    last_updated = Column(Date, nullable=True)
    next_review = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Program(Base):
    """Belongs to exactly one Portfolio -- FK is NOT NULL by design (Domain
    Blueprint CB-002 invariant, now enforced at the schema level, not just
    by the frontend's `Program.create()`)."""

    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("portfolio_id", "code", name="uq_programs_portfolio_code"),)

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(String(1000), nullable=True)
    sponsor = Column(String(255), nullable=True)
    program_manager = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="Ativo")
    health = Column(String(10), nullable=False, default="green")
    priority = Column(String(10), nullable=False, default="Média")
    objective = Column(String(1000), nullable=True)
    start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    progress_percentage = Column(Integer, nullable=False, default=0)
    project_count = Column(Integer, nullable=False, default=0)
    linked_demands = Column(Integer, nullable=False, default=0)
    linked_risks = Column(Integer, nullable=False, default=0)
    linked_issues = Column(Integer, nullable=False, default=0)
    pending_decisions = Column(Integer, nullable=False, default=0)
    pending_actions = Column(Integer, nullable=False, default=0)
    pmo_owner = Column(String(255), nullable=True)
    last_updated = Column(Date, nullable=True)
    next_review = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Project(Base):
    """Unified per `DOMAIN-BLUEPRINT-PROJECT.md` (Opção A, Fase 1): the
    domain fields (program_id onward) extend this same Épico-1 table
    instead of a separate `projects_delivery` table, so TD-008's three
    "Project" concepts collapse toward one instead of becoming a fourth.
    Every column below is nullable -- pre-existing rows (migrated from
    legacy `project_name`, Épico 1) have none of them populated; only
    Projects created through the Enterprise Domain going forward set
    them, via `program_id`."""

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_projects_org_name"),)

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    # Exact original free-text value this Project was migrated from (0002
    # migration); NULL for the fallback project and for projects born native.
    legacy_project_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # -- Enterprise Domain fields (Wave 2) ---------------------------------
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=True, index=True)
    code = Column(String(50), nullable=True)
    description = Column(String(1000), nullable=True)
    objective = Column(String(1000), nullable=True)
    sponsor = Column(String(255), nullable=True)
    project_manager = Column(String(255), nullable=True)
    status = Column(String(20), nullable=True)
    health = Column(String(10), nullable=True)
    priority = Column(String(10), nullable=True)
    start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    progress_percentage = Column(Integer, nullable=True)
    last_updated = Column(Date, nullable=True)
    next_review = Column(Date, nullable=True)
    # Value objects not yet promoted to entities (Domain Blueprint CB-003
    # §1) -- stored as JSON, matching the frontend's Owner/Milestone[]/Team
    # shape exactly, so no data is lost by not modeling them relationally.
    owner_json = Column(JSON, nullable=True)
    milestones_json = Column(JSON, nullable=True)
    team_json = Column(JSON, nullable=True)

    # -- Financial fields (V1 Product & Capability Completion, Package K) --
    # Only Project carries these; Program/Portfolio compute their financial
    # KPI as a runtime rollup over their own Projects, never a duplicated
    # column (same discipline progress_percentage/health already use).
    approved_budget = Column(Numeric(14, 2), nullable=True)
    actual_cost = Column(Numeric(14, 2), nullable=True)
    forecast_cost = Column(Numeric(14, 2), nullable=True)


class ProjectPerformanceBaseline(Base):
    """Wave 8 (Executive Analytics): one row per period of a Project's
    planned-value curve, human-authored (PM/PMO) -- never inferred or
    linearized by the system (Founder Decision, EVM Temporal Baseline).

    `baseline_version` follows the append-only discipline already used by
    `DocumentVersion`/`AnalysisRecord`: a rebaseline inserts a brand new set
    of rows with `baseline_version + 1`, never updating or deleting a prior
    version. The "current" baseline for live KPI computation is always the
    row set with the highest `baseline_version` for a given project.

    `bac_reference` freezes the BAC used when this baseline point was
    authored -- it may differ from `Project.approved_budget` later, since
    the project's actual budget can change independently of a specific
    baseline version.
    """

    __tablename__ = "project_performance_baselines"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "baseline_version",
            "period_date",
            name="uq_performance_baseline_project_version_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    baseline_version = Column(Integer, nullable=False)
    period_date = Column(Date, nullable=False)
    planned_progress_percentage = Column(Numeric(5, 2), nullable=False)
    planned_value = Column(Numeric(14, 2), nullable=False)
    bac_reference = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ProjectPerformanceSnapshot(Base):
    """Wave 8 (Executive Analytics): one row per periodic capture of a
    Project's real actual-cost/progress state -- append-only, never
    retroactive (Founder Decision, EVM Temporal Baseline §B/E). Existing
    Projects have zero rows until the first capture; history accumulates
    strictly prospectively from that point on.

    `UNIQUE(project_id, snapshot_date)` makes capture idempotent: a second
    capture on the same day returns the existing row rather than
    overwriting it.
    """

    __tablename__ = "project_performance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "snapshot_date", name="uq_performance_snapshot_project_date"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)
    actual_cost = Column(Numeric(14, 2), nullable=False)
    progress_percentage = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class UserProjectMembership(Base):
    __tablename__ = "user_project_memberships"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    role_in_project = Column(String(50), nullable=False, default="member")


class ApiKey(Base):
    """Enterprise Administration -- organization-scoped credential for
    programmatic API access (D-051, superseding the original API Keys
    deferral in `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`). A
    foundational identity primitive alongside Users/Roles/Sessions, not an
    Integration Hub artifact: it authenticates AS the user who created it
    (`get_request_context`'s second auth path), reusing every RBAC/audit
    check that path already has. Any future consumer (Integration Hub or
    otherwise) authenticates through this, never the reverse."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    # First characters of the plaintext key, safe to display forever so an
    # admin can tell keys apart without the full secret ever being shown
    # again after creation.
    key_prefix = Column(String(20), nullable=False)
    hashed_secret = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class UserSession(Base):
    """Enterprise Administration -- server-side record of a login session
    (item 5 of the Wave Completion Review retrospective, resolving TD-010).
    Named `UserSession`, not `Session`, to avoid colliding with
    `sqlalchemy.orm.Session` -- every repository method already uses
    `session` as the local variable name for the SQLAlchemy ORM session.

    The BFF's HMAC-signed cookie (`web/lib/session.ts`) is unchanged; this
    table only makes the `session_id` it already carries revocable before
    its natural 12h expiry -- `id` is that same UUID, minted by the backend
    at login (`AuthService.create_session`) instead of by the BFF, so the
    two sides agree on one identifier. `revoked_at` is the only field that
    matters for enforcement (`AdministrationRepository.is_session_revoked`);
    an id with no row at all is treated as still active, never as revoked,
    so sessions that predate this table are never retroactively broken."""

    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class Invitation(Base):
    """Enterprise Administration -- onboarding credential that lets a
    not-yet-registered person join an organization with a predetermined
    role (item 6 of the Wave Completion Review retrospective, D-054).
    A foundational identity primitive alongside Users/Roles/ApiKey/
    UserSession -- NOT an email artifact: the invitation carries a
    single-use token deliverable by any channel; email is only the
    (future, abstracted-away) automatic delivery mechanism
    (`NotificationProvider`), never a constituent of the domain.

    Reuses the same "narrow by non-secret prefix, then Argon2-verify the
    secret" discipline as ApiKey (D-051): `hashed_token` is never re-exposed
    after creation; the plaintext token is returned exactly once, at
    creation, for manual delivery until a concrete notification provider
    exists. State (Pendente/Aceito/Expirado/Cancelado) is derived from the
    timestamps below, never stored as a mutable column -- "Expirado" needs
    no background job to flip a flag."""

    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    email = Column(String(255), nullable=False)
    role_name = Column(String(100), nullable=False)
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # First characters of the plaintext token, safe to display forever so an
    # admin can tell invitations apart without the secret being shown again.
    token_prefix = Column(String(20), nullable=False)
    hashed_token = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    def status(self, now: datetime) -> str:
        """Derived state (Domain Blueprint §3): terminal transitions win,
        then expiry by elapsed time. `now` is passed in (not read here) so
        callers control the clock and the value is deterministic in tests."""
        if self.cancelled_at is not None:
            return "cancelled"
        if self.accepted_at is not None:
            return "accepted"
        if self.expires_at <= now:
            return "expired"
        return "pending"


class AuditLog(Base):
    """Enterprise Administration, Wave 2 (Épico 5, Nível 1 -- auditoria de
    mutações). Doubles as the "Logs" surface (Nível 2,
    `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`) -- one structured
    store, not a separate logging system alongside it."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # e.g. "organization.renamed", "user.created", "role.assigned",
    # "portfolio.created" -- resource.verb, mirrors the RBAC permission
    # vocabulary (DOMAIN-BLUEPRINT-RBAC.md §2) without being the same field.
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


class Document(Base):
    """Enterprise Knowledge Platform, Wave 3 Fase 1 (Foundation).

    `project_id` is an optional metadata pointer, never a key -- the same
    TD-008 discipline (`project_id`, never a name) already final for
    `AnalysisRecord`."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    source_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class DocumentVersion(Base):
    """One row per (re)ingestion of a Document -- never overwritten, per
    `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.10
    (Versionamento do conhecimento)."""

    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Chunk(Base):
    """A retrievable unit of a DocumentVersion, with its embedding vector.

    `organization_id` is denormalized from the owning Document -- the same
    technique already used by `AnalysisRecord.organization_id` -- so
    similarity search filters by tenant directly, with no join required."""

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_version_id = Column(
        Integer, ForeignKey("document_versions.id"), nullable=False, index=True
    )
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    chunk_index = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    embedding = Column(Vector(KNOWLEDGE_EMBEDDING_DIM), nullable=False)
    # Minimal provenance (Founder Decision D-175/D-177): which provider/
    # model produced this vector -- nullable, no versioning table, no
    # multi-model coexistence mechanism (rejected as unneeded abstraction
    # in TECHNICAL-DESIGN-PRODUCTION-EMBEDDING-CONTRACT-VECTOR-MIGRATION.md).
    embedding_provider = Column(String(length=64), nullable=True)
    embedding_model = Column(String(length=64), nullable=True)


class MemoryRecord(Base):
    """Enterprise Memory Model, Wave 3 Fase 2 -- classifies a Document
    already ingested by the Knowledge Platform into one of the 5 memory
    categories (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §2). Never a
    second storage of the document's content -- only a reference
    (`document_id`) plus its classification. Distinct in every dimension
    (layer, persistence, mechanism, consumer) from `Executive Memory`
    (`web/lib/executive-memory/`, frontend-only, stateless) -- see that
    Blueprint's §0 collision checklist."""

    __tablename__ = "memory_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    category = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class EventRecord(Base):
    """Wave 4, Enterprise Operations, Epic W4-1 -- Event Audit: the durable
    envelope of every event published via `EventPublisher`
    (`docs/architecture/TECHNICAL-DESIGN-WAVE-4-ENTERPRISE-OPERATIONS.md`
    §5.3). Distinct from `AuditLog` (domain mutation audit, Wave 2) --
    this table answers "what facts were published", never a replacement
    for domain auditing. `event_id` is the envelope's own identifier
    (UUID), not the table's primary key surrogate."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(36), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    correlation_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    origin = Column(String(100), nullable=False)
    payload_version = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)


class DeadLetterEvent(Base):
    """Wave 4, Enterprise Operations, Epic W4-1 -- minimal Dead Letter
    Strategy (Technical Design §4): a published event whose dispatch to a
    registered handler failed `MAX_ATTEMPTS` times. No automatic
    reprocessing, no administrative interface -- inspection is direct
    database query only, per the Founder's explicit restriction."""

    __tablename__ = "dead_letter_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(36), ForeignKey("events.event_id"), nullable=False, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    correlation_id = Column(String(64), nullable=False, index=True)
    attempts = Column(Integer, nullable=False)
    last_error = Column(String(2000), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class WorkflowExecution(Base):
    """Wave 4, Enterprise Operations, Epic W4-4 -- Execution Tracking
    (Technical Design §3/§12). Answers "what processes ran, and how" --
    distinct from `EventRecord` (Event Audit, "what facts were published").
    `WorkflowRuntime` is the only component aware of this table
    (`src/workflows/execution_tracking.py::ExecutionTracker`); `EventDispatcher`
    never reads or writes it (Founder's explicit separation principle).

    `UNIQUE(event_id, workflow_name)` is the idempotency key (§12.4): the
    same event redispatched by `EventDispatcher`'s own synchronous retry
    reuses this row (upsert) instead of inserting a second one -- enforced
    at the database, not only in application code."""

    __tablename__ = "workflow_executions"
    __table_args__ = (
        UniqueConstraint("event_id", "workflow_name", name="uq_workflow_executions_event_workflow"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(36), ForeignKey("events.event_id"), nullable=False, index=True)
    workflow_name = Column(String(200), nullable=False)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    correlation_id = Column(String(64), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(String(500), nullable=True)
