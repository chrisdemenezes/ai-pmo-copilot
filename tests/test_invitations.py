"""Convites (Invitations, item 6 -- D-054): repository + service + the
NoOp notification provider. Uses a migrated database so the seeded roles
(viewer/organization_admin) exist -- acceptance assigns a real role."""
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from src.database.enterprise_repository import EmailConflictError
from src.database.repository import AnalysisRepository
from src.services.administration_service import (
    INVITATION_TOKEN_PREFIX,
    AdministrationService,
)
from src.services.notifications.noop_provider import NoOpNotificationProvider
from tests.db import temp_database_url


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture()
def repository():
    with temp_database_url("invitations") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")
        yield AnalysisRepository(database_url=database_url)


class RecordingNotificationProvider:
    def __init__(self):
        self.calls = []

    def notify_invitation_created(self, invitation, plaintext_token):
        self.calls.append((invitation.id, plaintext_token))


@pytest.fixture()
def notifier():
    return RecordingNotificationProvider()


@pytest.fixture()
def service(repository, notifier):
    return AdministrationService(repository=repository, notification_provider=notifier)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


@pytest.fixture()
def actor_id(repository, org_id):
    return repository.enterprise.create_user(org_id, "admin@example.com", "Admin")


class TestCreateInvitation:
    def test_token_has_prefix_and_is_never_persisted(self, service, repository, org_id, actor_id):
        invitation, token = service.create_invitation(
            org_id, "invitee@example.com", "viewer", actor_id
        )
        assert token.startswith(INVITATION_TOKEN_PREFIX)
        stored = repository.administration.get_invitation(invitation.id, org_id)
        assert stored.hashed_token != token
        assert token not in stored.hashed_token
        assert stored.token_prefix == token[: len(stored.token_prefix)]

    def test_email_is_normalized(self, service, repository, org_id, actor_id):
        invitation, _ = service.create_invitation(
            org_id, "  Invitee@Example.COM ", "viewer", actor_id
        )
        assert invitation.email == "invitee@example.com"

    def test_new_invitation_is_pending_with_future_expiry(self, service, org_id, actor_id):
        invitation, _ = service.create_invitation(org_id, "a@b.com", "viewer", actor_id)
        now = datetime.now(timezone.utc)
        assert invitation.status(now) == "pending"
        assert invitation.expires_at > now

    def test_notification_provider_is_invoked(self, service, notifier, org_id, actor_id):
        invitation, token = service.create_invitation(org_id, "a@b.com", "viewer", actor_id)
        assert notifier.calls == [(invitation.id, token)]

    def test_records_audit(self, service, repository, org_id, actor_id):
        invitation, _ = service.create_invitation(org_id, "a@b.com", "viewer", actor_id)
        entries = repository.administration.list_audit_log(org_id)
        assert entries[0].action == "invitation.created"
        assert entries[0].entity_id == invitation.id


class TestPreviewAndAccept:
    def test_preview_returns_invitation_for_valid_token(self, service, org_id, actor_id):
        _, token = service.create_invitation(org_id, "a@b.com", "viewer", actor_id)
        preview = service.preview_invitation(token)
        assert preview is not None
        assert preview.role_name == "viewer"

    def test_preview_unknown_token_returns_none(self, service):
        assert service.preview_invitation("inv_does_not_exist") is None
        assert service.preview_invitation("not_even_prefixed") is None

    def test_accept_creates_user_with_role_and_marks_accepted(
        self, service, repository, org_id, actor_id
    ):
        invitation, token = service.create_invitation(
            org_id, "newuser@example.com", "viewer", actor_id
        )
        user = service.accept_invitation(token, "New User", "s3cret-pass")
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.organization_id == org_id

        stored = repository.administration.get_invitation(invitation.id, org_id)
        assert stored.status(datetime.now(timezone.utc)) == "accepted"

        # The accepted user gained the invitation's role.
        roles = {
            r.name
            for r in repository.administration.list_roles_for_user(user.id, org_id)
        }
        assert "viewer" in roles

    def test_accept_audits_invitation_accepted(self, service, repository, org_id, actor_id):
        invitation, token = service.create_invitation(org_id, "n@e.com", "viewer", actor_id)
        service.accept_invitation(token, "N", "pw-123456")
        actions = [e.action for e in repository.administration.list_audit_log(org_id)]
        assert "invitation.accepted" in actions

    def test_accept_invalid_token_returns_none(self, service):
        assert service.accept_invitation("inv_bogus", "N", "pw-123456") is None

    def test_accept_twice_fails_the_second_time(self, service, org_id, actor_id):
        _, token = service.create_invitation(org_id, "once@e.com", "viewer", actor_id)
        assert service.accept_invitation(token, "N", "pw-123456") is not None
        # Second acceptance: invitation is no longer pending (and the token
        # is excluded from the prefix lookup once accepted).
        assert service.accept_invitation(token, "N2", "pw-654321") is None

    def test_accept_duplicate_email_raises_conflict(self, service, repository, org_id, actor_id):
        # A user with this email already exists in the org.
        repository.administration.create_user(
            org_id, "taken@example.com", "Taken", "hash", "viewer"
        )
        _, token = service.create_invitation(org_id, "taken@example.com", "viewer", actor_id)
        with pytest.raises(EmailConflictError):
            service.accept_invitation(token, "Dup", "pw-123456")

    def test_accept_expired_invitation_returns_none(
        self, repository, notifier, org_id, actor_id
    ):
        service = AdministrationService(
            repository=repository, notification_provider=notifier
        )
        _, token = service.create_invitation(org_id, "late@e.com", "viewer", actor_id)
        # Force expiry by rewriting expires_at into the past.
        invitations = repository.administration.list_invitations(org_id)
        with repository.SessionLocal() as session:
            from src.database.models import Invitation

            inv = session.get(Invitation, invitations[0].id)
            inv.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            session.commit()
        assert service.accept_invitation(token, "Late", "pw-123456") is None


class TestCancel:
    def test_cancel_marks_cancelled_and_audits(self, service, repository, org_id, actor_id):
        invitation, _ = service.create_invitation(org_id, "c@e.com", "viewer", actor_id)
        result = service.cancel_invitation(invitation.id, org_id, actor_id)
        assert result is not None
        stored = repository.administration.get_invitation(invitation.id, org_id)
        assert stored.status(datetime.now(timezone.utc)) == "cancelled"
        actions = [e.action for e in repository.administration.list_audit_log(org_id)]
        assert "invitation.cancelled" in actions

    def test_cancel_is_idempotent(self, service, org_id, actor_id):
        invitation, _ = service.create_invitation(org_id, "c@e.com", "viewer", actor_id)
        assert service.cancel_invitation(invitation.id, org_id, actor_id) is not None
        assert service.cancel_invitation(invitation.id, org_id, actor_id) is None

    def test_cancelled_invitation_cannot_be_accepted(self, service, org_id, actor_id):
        invitation, token = service.create_invitation(org_id, "c@e.com", "viewer", actor_id)
        service.cancel_invitation(invitation.id, org_id, actor_id)
        assert service.accept_invitation(token, "N", "pw-123456") is None

    def test_cancel_other_org_invitation_returns_none(self, service, repository, org_id, actor_id):
        other_org = repository.enterprise.create_organization("Org B")
        invitation, _ = service.create_invitation(org_id, "c@e.com", "viewer", actor_id)
        # An admin of another org cannot cancel this org's invitation.
        assert service.cancel_invitation(invitation.id, other_org, actor_id) is None


class TestListAndIsolation:
    def test_list_is_scoped_to_organization(self, service, repository, actor_id, org_id):
        other_org = repository.enterprise.create_organization("Org B")
        other_actor = repository.enterprise.create_user(other_org, "b@b.com", "B")
        service.create_invitation(org_id, "a@e.com", "viewer", actor_id)
        service.create_invitation(other_org, "b@e.com", "viewer", other_actor)
        assert len(service.list_invitations(org_id)) == 1
        assert len(service.list_invitations(other_org)) == 1


class TestNoOpNotificationProvider:
    def test_noop_does_not_raise(self, service, org_id, actor_id):
        provider = NoOpNotificationProvider()
        invitation, token = service.create_invitation(org_id, "a@e.com", "viewer", actor_id)
        # No return, no raise, no side effect beyond a log line.
        assert provider.notify_invitation_created(invitation, token) is None
