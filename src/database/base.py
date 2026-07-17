"""Shared SQLAlchemy declarative base for every table in the platform.

Extracted from repository.py so the V2 enterprise models (models.py) and the
V1 AnalysisRecord can share one metadata without a circular import. Import
order matters only for create_all: repository.py imports models so that a
fresh install (no alembic) still creates the full schema.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
