import logging
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON

from src.database.base import Base
from src.database.engine import build_engine, resolve_database_url
# Imported for its side effect: registers the Enterprise Foundation tables on
# Base.metadata so create_all provisions the full schema on installs that do
# not run alembic (the SQLite/demo path).
from src.database import models  # noqa: F401
from src.database.enterprise_repository import EnterpriseRepository
from src.database.domain_repository import DomainRepository
from src.database.administration_repository import AdministrationRepository
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(50), nullable=False)
    project_name = Column(String(255), nullable=True, index=True)
    # Real Project link (V2 Release 0.1). Nullable during the transition:
    # records written before migration 0002 are backfilled by it; records
    # written after are linked at save time below. The NOT NULL constraint
    # lands in Épico 4, when the API itself starts requiring a project_id.
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    # Tenant isolation (Security Hardening Gate, migration 0010). NOT NULL
    # at the database level; every write path resolves it from the real
    # RequestContext, never a client-supplied value.
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


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
            project = self.enterprise.get_or_create_project_for_name(
                session, organization_id, project_name
            )
            record = AnalysisRecord(
                kind=kind,
                payload=payload,
                project_name=project_name,
                project_id=project.id,
                organization_id=organization_id,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(
                "Saved analysis id=%s kind=%s organization_id=%s project_name=%s project_id=%s",
                record.id,
                kind,
                organization_id,
                project_name,
                record.project_id,
            )
            return record.id

    def list_analyses(
        self,
        organization_id: int,
        project_name: str | None = None,
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
            # TD-008 Phase 3b (Etapa 1): when a project_id is provided it is
            # the exact key (the migration's whole point -- two projects can
            # share a name but never an id); it takes precedence over the
            # legacy name filter. Name-only callers are unchanged.
            if project_id is not None:
                query = query.filter(AnalysisRecord.project_id == project_id)
            elif project_name is not None:
                query = query.filter(AnalysisRecord.project_name == project_name)
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
                "Listed %d analyses organization_id=%s project_name=%s kind=%s created_from=%s created_to=%s limit=%s offset=%d",
                len(records),
                organization_id,
                project_name,
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
