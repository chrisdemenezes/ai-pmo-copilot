import os
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, JSON, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(50), nullable=False)
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

    def save_analysis(self, kind: str, payload: dict) -> int:
        with self.SessionLocal() as session:
            record = AnalysisRecord(kind=kind, payload=payload)
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.id
