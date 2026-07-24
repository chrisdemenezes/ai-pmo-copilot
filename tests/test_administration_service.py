"""AdministrationService -- API Keys (D-051): key generation, Argon2
hashing/verification, and the authenticate_api_key() path
`get_request_context`'s API Key auth branch consumes."""
import pytest

from src.database.repository import AnalysisRepository
from src.services.administration_service import (
    API_KEY_PREFIX,
    AdministrationService,
)
from tests.db import temp_database_url


@pytest.fixture()
def repository():
    with temp_database_url("administration_service_api_keys") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def service(repository):
    return AdministrationService(repository=repository)


@pytest.fixture()
def org_id(repository):
    return repository.enterprise.create_organization("Org A")


@pytest.fixture()
def actor_id(repository, org_id):
    return repository.enterprise.create_user(org_id, "admin@example.com", "Admin")


class TestCreateApiKey:
    def test_plaintext_key_has_the_expected_prefix_and_is_never_persisted(
        self, service, repository, org_id, actor_id
    ):
        api_key, plaintext_key = service.create_api_key(org_id, "CI pipeline", actor_id)

        assert plaintext_key.startswith(API_KEY_PREFIX)
        assert api_key.key_prefix == plaintext_key[: len(api_key.key_prefix)]
        # The stored hash is never the plaintext itself.
        stored = repository.administration.get_api_key(api_key.id, org_id)
        assert stored.hashed_secret != plaintext_key
        assert plaintext_key not in stored.hashed_secret

    def test_two_keys_never_collide(self, service, org_id, actor_id):
        _, first = service.create_api_key(org_id, "Key A", actor_id)
        _, second = service.create_api_key(org_id, "Key B", actor_id)

        assert first != second

    def test_records_an_audit_entry(self, service, repository, org_id, actor_id):
        api_key, _ = service.create_api_key(org_id, "CI pipeline", actor_id)

        entries = repository.administration.list_audit_log(org_id)
        assert entries[0].action == "api_key.created"
        assert entries[0].entity_id == api_key.id


class TestAuthenticateApiKey:
    def test_authenticates_with_the_correct_plaintext_key(self, service, org_id, actor_id):
        api_key, plaintext_key = service.create_api_key(org_id, "CI pipeline", actor_id)

        authenticated = service.authenticate_api_key(plaintext_key)

        assert authenticated is not None
        assert authenticated.id == api_key.id
        assert authenticated.organization_id == org_id
        assert authenticated.created_by_user_id == actor_id

    def test_rejects_a_key_with_the_right_prefix_but_wrong_secret(
        self, service, org_id, actor_id
    ):
        api_key, plaintext_key = service.create_api_key(org_id, "CI pipeline", actor_id)
        tampered = plaintext_key[:-1] + ("a" if plaintext_key[-1] != "a" else "b")

        assert service.authenticate_api_key(tampered) is None

    def test_rejects_garbage_input_without_raising(self, service):
        assert service.authenticate_api_key("not-an-api-key-at-all") is None
        assert service.authenticate_api_key("") is None

    def test_rejects_a_revoked_key(self, service, repository, org_id, actor_id):
        api_key, plaintext_key = service.create_api_key(org_id, "CI pipeline", actor_id)
        service.revoke_api_key(api_key.id, org_id, actor_id)

        assert service.authenticate_api_key(plaintext_key) is None

    def test_updates_last_used_at_on_successful_authentication(
        self, service, repository, org_id, actor_id
    ):
        api_key, plaintext_key = service.create_api_key(org_id, "CI pipeline", actor_id)
        assert repository.administration.get_api_key(api_key.id, org_id).last_used_at is None

        service.authenticate_api_key(plaintext_key)

        assert repository.administration.get_api_key(api_key.id, org_id).last_used_at is not None


class TestRevokeApiKey:
    def test_revoke_records_an_audit_entry(self, service, repository, org_id, actor_id):
        api_key, _ = service.create_api_key(org_id, "CI pipeline", actor_id)

        service.revoke_api_key(api_key.id, org_id, actor_id)

        entries = repository.administration.list_audit_log(org_id)
        assert entries[0].action == "api_key.revoked"
        assert entries[0].entity_id == api_key.id

    def test_revoke_unknown_key_returns_none(self, service, org_id, actor_id):
        assert service.revoke_api_key(999999, org_id, actor_id) is None
