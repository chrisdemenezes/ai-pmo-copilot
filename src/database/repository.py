import logging
import os
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, JSON, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(50), nullable=False)
    project_name = Column(String(255), nullable=True, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AnalysisRepository:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "sqlite:///./ai_pmo_copilot.db",
        )
        connect_args = {"check_same_thread": False} if self.database_url.startswith("sqlite") else {}
        self.engine = create_engine(self.database_url, connect_args=connect_args)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def save_analysis(self, kind: str, payload: dict, project_name: str | None = None) -> int:
        with self.SessionLocal() as session:
            record = AnalysisRecord(kind=kind, payload=payload, project_name=project_name)
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info("Saved analysis id=%s kind=%s project_name=%s", record.id, kind, project_name)
            return record.id

    def list_analyses(
        self,
        project_name: str | None = None,
        kind: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int | None = 20,
        offset: int = 0,
    ) -> list[AnalysisRecord]:
        with self.SessionLocal() as session:
            query = session.query(AnalysisRecord).order_by(
                AnalysisRecord.created_at.desc(), AnalysisRecord.id.desc()
            )
            if project_name is not None:
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
                "Listed %d analyses project_name=%s kind=%s created_from=%s created_to=%s limit=%s offset=%d",
                len(records),
                project_name,
                kind,
                created_from,
                created_to,
                limit,
                offset,
            )
            return records

    def get_analysis(self, analysis_id: int) -> AnalysisRecord | None:
        with self.SessionLocal() as session:
            record = session.get(AnalysisRecord, analysis_id)
            logger.info("Fetched analysis id=%s found=%s", analysis_id, record is not None)
            return record
