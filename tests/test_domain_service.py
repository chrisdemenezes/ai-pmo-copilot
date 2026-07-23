"""DomainService's event emission (Wave 1, Event Foundation -- closed
retrospectively per D-048). Uses a fake EventEmitter test double, same
convention `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §5.12 prescribes and
`test_identity_auth_service.py` already established for other Protocol
dependencies (fake instead of hitting a real bus/DB in unit scope).
"""
import pytest

from src.database.repository import AnalysisRepository
from src.services.domain_service import DomainService
from tests.db import temp_database_url


class RecordingEventEmitter:
    def __init__(self):
        self.events: list[tuple[str, dict, int]] = []

    def emit(self, event_name: str, payload: dict, organization_id: int) -> None:
        self.events.append((event_name, payload, organization_id))


@pytest.fixture()
def repository():
    with temp_database_url("domain_service_events") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def emitter():
    return RecordingEventEmitter()


@pytest.fixture()
def service(repository, emitter):
    return DomainService(repository=repository, emitter=emitter)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


@pytest.fixture()
def actor_id(repository, org_id):
    return repository.enterprise.create_user(org_id, "actor@example.com", "Actor")


def test_create_portfolio_emits_portfolio_created_after_the_write_succeeds(
    service, emitter, org_id, actor_id
):
    portfolio = service.create_portfolio(org_id, "Portfólio A", "PF-A", actor_id)

    assert emitter.events == [
        ("portfolio.created", {"portfolio_id": portfolio.id}, org_id),
    ]


def test_create_program_emits_created_and_linked_to_portfolio(service, emitter, org_id, actor_id):
    portfolio = service.create_portfolio(org_id, "Portfólio A", "PF-A", actor_id)
    emitter.events.clear()

    program = service.create_program(org_id, portfolio.id, "Programa A", "PG-A", actor_id)

    payload = {"program_id": program.id, "portfolio_id": portfolio.id}
    assert emitter.events == [
        ("program.created", payload, org_id),
        ("program.linked_to_portfolio", payload, org_id),
    ]


def test_create_project_emits_created_and_linked_to_program(service, emitter, org_id, actor_id):
    portfolio = service.create_portfolio(org_id, "Portfólio A", "PF-A", actor_id)
    program = service.create_program(org_id, portfolio.id, "Programa A", "PG-A", actor_id)
    emitter.events.clear()

    project = service.create_project(org_id, program.id, "Projeto A", actor_id)

    payload = {"project_id": project.id, "program_id": program.id}
    assert emitter.events == [
        ("project_delivery.created", payload, org_id),
        ("project_delivery.linked_to_program", payload, org_id),
    ]


def test_create_program_never_emits_when_the_portfolio_does_not_resolve(
    service, emitter, org_id, actor_id
):
    result = service.create_program(org_id, 999, "Programa A", "PG-A", actor_id)

    assert result is None
    assert emitter.events == []


def test_create_project_never_emits_when_the_program_does_not_resolve(
    service, emitter, org_id, actor_id
):
    result = service.create_project(org_id, 999, "Projeto A", actor_id)

    assert result is None
    assert emitter.events == []
