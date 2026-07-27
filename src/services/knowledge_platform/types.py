"""Value types returned by the Enterprise Knowledge Platform (Fase 1).

Plain dataclasses, same shape convention as the Digital PMO Intelligence
Foundation's `Evidence`/`Recommendation`/`Explanation`
(`src/services/ai_foundation/types.py`) -- no ORM object ever crosses the
`KnowledgeRepository` boundary.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IngestedDocument:
    id: int
    organization_id: int
    project_id: int | None
    source_name: str
    version_id: int


@dataclass(frozen=True)
class DocumentVersionInfo:
    id: int
    document_id: int
    created_at: datetime


@dataclass(frozen=True)
class ScoredChunk:
    chunk_id: int
    document_id: int
    text: str
    score: float
    document_version_created_at: datetime


@dataclass(frozen=True)
class MemoryRecordInfo:
    id: int
    organization_id: int
    document_id: int
    category: str
    created_at: datetime
