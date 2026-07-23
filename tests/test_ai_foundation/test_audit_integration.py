import pytest

from src.database.repository import AnalysisRepository
from src.services.ai_foundation.audit_integration import AIFoundationAudit
from src.services.ai_foundation.types import SessionContext
from tests.db import temp_database_url


@pytest.fixture()
def repository():
    with temp_database_url("ai_foundation_audit") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


@pytest.fixture()
def user_id(repository, org_id):
    return repository.enterprise.create_user(org_id, "user@example.com", "User")


def test_record_question_uses_the_analyst_prefixed_action(repository, org_id, user_id):
    session = SessionContext(
        organization_id=org_id, user_id=user_id, session_id="session-1", project_name="Aurora"
    )

    AIFoundationAudit.record_question(repository, session, "risk_advisor", "Qual o risco mais crítico?")

    entries = repository.administration.list_audit_log(org_id)
    assert len(entries) == 1
    assert entries[0].action == "risk_advisor.question_asked"
    assert entries[0].actor_user_id == user_id
    assert entries[0].organization_id == org_id
    assert entries[0].details == {"project_name": "Aurora", "question": "Qual o risco mais crítico?"}


def test_record_question_never_includes_an_answer_field(repository, org_id, user_id):
    session = SessionContext(organization_id=org_id, user_id=user_id, session_id="session-1")

    AIFoundationAudit.record_question(repository, session, "schedule_advisor", "Algum atraso?")

    entries = repository.administration.list_audit_log(org_id)
    assert "answer" not in entries[0].details
