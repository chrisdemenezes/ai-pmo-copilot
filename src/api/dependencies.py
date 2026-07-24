"""Shared FastAPI DI factories used by more than one route module.

Extracted from `intelligence.py` (Security Hardening Gate, C-1): once
`intelligence.py` itself needed `require_permission` (defined in
`src.api.authorization`, which in turn depended on `build_repository`
living in `intelligence.py`), leaving it there would have created a
circular import. Moved here instead of duplicated -- no new registry,
same single `AnalysisRepository` instance shared by every route module
via `@lru_cache`.
"""
from functools import lru_cache

from src.database.repository import AnalysisRepository
from src.services.events.interfaces import EventEmitter
from src.services.events.noop_emitter import NoOpEventEmitter
from src.services.notifications.interfaces import NotificationProvider
from src.services.notifications.noop_provider import NoOpNotificationProvider


@lru_cache
def build_repository() -> AnalysisRepository:
    return AnalysisRepository()


@lru_cache
def build_event_emitter() -> EventEmitter:
    return NoOpEventEmitter()


@lru_cache
def build_notification_provider() -> NotificationProvider:
    # Item 6 (Convites, D-054): the delivery seam. NoOp today -- no concrete
    # SMTP/SES provider is chosen; the invitation token is returned once at
    # creation for manual delivery. Same pattern as build_event_emitter.
    return NoOpNotificationProvider()
