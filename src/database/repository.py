import logging
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, sessionmaker

# Imported for its side effect: registers the Enterprise Foundation tables on
# Base.metadata so create_all provisions the full schema on installs that do
# not run alembic (the SQLite/demo path).
from src.database import models  # noqa: F401
from src.database.administration_repository import AdministrationRepository
from src.database.base import Base
from src.database.domain_repository import DomainRepository
from src.database.engine import build_engine, resolve_database_url
from src.database.enterprise_repository import (
    EnterpriseRepository,
    ProjectNotFoundError,
)
from src.database.project_identity import FALLBACK_PROJECT_NAME

logger = logging.getLogger(__name__)


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(50), nullable=False)
    # TD-008 Fase 3b, Etapa 4b (D-060): a coluna legada `project_name` foi
    # removida do banco (migração 0015) e do ORM. `project_id` é a ÚNICA chave
    # de acesso interno ao Project e agora é obrigatória (NOT NULL); o nome de
    # exibição deriva sempre de `Project.name` via o relacionamento `project`.
    project_id = Column(
        Integer, ForeignKey("projects.id"), nullable=False, index=True
    )
    # Tenant isolation (Security Hardening Gate, migration 0010). NOT NULL
    # at the database level; every write path resolves it from the real
    # RequestContext, never a client-supplied value.
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Read-only link to the resolved Project (TD-008 Fase 3b). `lazy="joined"`
    # eager-loads it in the same query, so `record.project` is available after
    # the session closes (no DetachedInstanceError) and display names derive
    # from `Project.name` -- the sole source of the project name now that the
    # legacy `project_name` column is gone (Etapa 4b, migração 0015).
    project = relationship("Project", lazy="joined")


def analysis_display_name(record: "AnalysisRecord") -> str | None:
    """Display name of an analysis derived from its Project (TD-008 Fase 3b) --
    `Project.name` via `project_id`. The single fallback Project
    (`FALLBACK_PROJECT_NAME`, for analyses saved without an identifiable
    project) maps back to `None`, preserving the "sem projeto" semantics the
    removed `project_name` column once carried as a null value.
    """
    project = record.project
    if project is None:
        return None
    return None if project.name == FALLBACK_PROJECT_NAME else project.name


class AnalysisRepository:
    def __init__(self, database_url: str | None = None):
        self.database_url = resolve_database_url(database_url)
        self.engine = build_engine(self.database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.enterprise = EnterpriseRepository(self.SessionLocal)
        self.domain = DomainRepository(self.SessionLocal)
        self.administration = AdministrationRepository(self.SessionLocal, self.enterprise)

    def save_analysis(
        self, kind: str, payload: dict, organization_id: int, project_name: str | None = None
    ) -> int:
        with self.SessionLocal() as session:
            # Same transaction: the analysis row and its Project resolution
            # commit (or roll back) together, so no orphan can be written.
            # `project_name` is the free-text the user informed; it is resolved
            # to a real Project here (name -> project_id) and never stored --
            # the legacy `project_name` column no longer exists (TD-008 Fase
            # 3b, Etapa 4b). The preserved name-based UX is exactly this:
            # resolve a name to the identity key before the domain write.
            project = self.enterprise.get_or_create_project_for_name(
                session, organization_id, project_name
            )
            record = AnalysisRecord(
                kind=kind,
                payload=payload,
                project_id=project.id,
                organization_id=organization_id,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(
                "Saved analysis id=%s kind=%s organization_id=%s project_id=%s",
                record.id,
                kind,
                organization_id,
                record.project_id,
            )
            return record.id

    def resolve_scope_id(
        self,
        organization_id: int,
        project_name: str | None = None,
        project_id: int | None = None,
    ) -> tuple[int | None, bool]:
        """Resolve a caller-supplied name/id to the `project_id` reads should
        scope by (TD-008 Fase 3b, Etapa 4a). Returns `(scope_id, unmatched)`:

        - `project_id` given            -> `(project_id, False)` (exact key).
        - no name and no id             -> `(None, False)` (portfolio scope).
        - name that resolves            -> `(project.id, False)`.
        - name with no Project at all   -> `(None, True)` (empty scope: a
          genuinely never-analyzed project has no analyses; callers return an
          empty result instead of falling through to the portfolio scope).

        Reuses `enterprise.resolve_project_reference` so name resolution lives
        in one place; an ambiguous name still raises (never silently picks
        one) -- routes map it to 409 before ever reaching here.
        """
        if project_id is not None:
            return project_id, False
        if project_name is None or project_name.strip() == "":
            return None, False
        try:
            project = self.enterprise.resolve_project_reference(
                organization_id, project_name=project_name
            )
        except ProjectNotFoundError:
            return None, True
        return (project.id if project is not None else None), False

    def list_analyses(
        self,
        organization_id: int,
        kind: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int | None = 20,
        offset: int = 0,
        project_id: int | None = None,
    ) -> list[AnalysisRecord]:
        with self.SessionLocal() as session:
            query = (
                session.query(AnalysisRecord)
                .filter(AnalysisRecord.organization_id == organization_id)
                .order_by(AnalysisRecord.created_at.desc(), AnalysisRecord.id.desc())
            )
            # TD-008 Fase 3b, Etapa 4a: `project_id` is the ONLY project scope
            # key. The legacy `project_name` filter is gone -- callers resolve
            # a name to an id (via `resolve_scope_id`) before scoping.
            if project_id is not None:
                query = query.filter(AnalysisRecord.project_id == project_id)
            if kind is not None:
                query = query.filter(AnalysisRecord.kind == kind)
            if created_from is not None:
                query = query.filter(AnalysisRecord.created_at >= created_from)
            if created_to is not None:
                query = query.filter(AnalysisRecord.created_at <= created_to)
            query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            records = query.all()
            logger.info(
                "Listed %d analyses organization_id=%s project_id=%s kind=%s created_from=%s created_to=%s limit=%s offset=%d",
                len(records),
                organization_id,
                project_id,
                kind,
                created_from,
                created_to,
                limit,
                offset,
            )
            return records

    def get_analysis(self, analysis_id: int, organization_id: int) -> AnalysisRecord | None:
        with self.SessionLocal() as session:
            record = (
                session.query(AnalysisRecord)
                .filter(
                    AnalysisRecord.id == analysis_id,
                    AnalysisRecord.organization_id == organization_id,
                )
                .one_or_none()
            )
            logger.info("Fetched analysis id=%s found=%s", analysis_id, record is not None)
            return record
