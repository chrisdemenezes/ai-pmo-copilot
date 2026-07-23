import pytest

from src.database.enterprise_repository import EnterpriseRepository
from src.database.models import Role, User, UserRole
from src.database.repository import AnalysisRepository
from src.services.identity.auth_service import (
    DEFAULT_ORGANIZATION_SLUG,
    DEMO_ORGANIZATION_NAME,
    DEMO_ORGANIZATION_SLUG,
    DEMO_USER_EMAIL,
    AuthService,
)
from src.services.identity.password_hashing import Argon2PasswordHasher
from tests.db import temp_database_url


@pytest.fixture()
def repo():
    """AnalysisRepository's create_all() provisions schema only -- the
    roles seeded by migration 0002 (organization_admin, pmo,
    project_manager, viewer) are inserted here to mirror a real
    alembic-migrated database, since AuthService.bootstrap_administrator
    depends on organization_admin already existing."""
    with temp_database_url("auth_service") as database_url:
        instance = AnalysisRepository(database_url=database_url)
        with instance.SessionLocal() as session:
            for name in ("organization_admin", "pmo", "project_manager", "viewer"):
                session.add(Role(name=name))
            session.commit()
        yield instance


@pytest.fixture()
def auth_service(repo):
    return AuthService(repo.SessionLocal, Argon2PasswordHasher())


class TestAuthenticate:
    def test_correct_credentials_return_identity(self, auth_service):
        auth_service.bootstrap_administrator("admin@example.com", "correct-password")

        result = auth_service.authenticate(
            DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password"
        )

        assert result is not None
        user, org = result
        assert user.email == "admin@example.com"
        assert user.display_name == "Administrator"
        assert org.slug == DEFAULT_ORGANIZATION_SLUG

    def test_wrong_password_returns_none(self, auth_service):
        auth_service.bootstrap_administrator("admin@example.com", "correct-password")

        assert (
            auth_service.authenticate(DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong")
            is None
        )

    def test_inactive_user_cannot_authenticate(self, repo, auth_service):
        """User Management (Wave 2): an inactivated user must not log in,
        even with the correct password -- same uniform-failure treatment
        as every other authentication failure (EO-015)."""
        auth_service.bootstrap_administrator("admin@example.com", "correct-password")
        with repo.SessionLocal() as session:
            user = session.query(User).filter(User.email == "admin@example.com").one()
            user.is_active = False
            session.commit()

        assert (
            auth_service.authenticate(
                DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password"
            )
            is None
        )

    def test_login_normalizes_email_case(self, auth_service):
        """A user cadastrado com e-mail normalizado (lowercase) autentica
        independentemente da caixa digitada no login."""
        auth_service.bootstrap_administrator("admin@example.com", "correct-password")

        result = auth_service.authenticate(
            DEFAULT_ORGANIZATION_SLUG, "Admin@Example.com", "correct-password"
        )

        assert result is not None

    def test_unknown_email_returns_none(self, auth_service):
        assert (
            auth_service.authenticate(
                DEFAULT_ORGANIZATION_SLUG, "nobody@example.com", "irrelevant"
            )
            is None
        )

    def test_unknown_organization_returns_none(self, auth_service):
        auth_service.bootstrap_administrator("admin@example.com", "correct-password")

        assert (
            auth_service.authenticate(
                "no-such-organization", "admin@example.com", "correct-password"
            )
            is None
        )

    def test_two_distinct_users_authenticate_independently(self, repo, auth_service):
        auth_service.bootstrap_administrator("admin@example.com", "admin-password")
        auth_service.bootstrap_demo_user("demo-password")

        admin_result = auth_service.authenticate(
            DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "admin-password"
        )
        demo_result = auth_service.authenticate(
            DEMO_ORGANIZATION_SLUG, DEMO_USER_EMAIL, "demo-password"
        )

        assert admin_result is not None
        assert demo_result is not None
        admin_user, admin_org = admin_result
        demo_user, demo_org = demo_result
        assert admin_user.user_id != demo_user.user_id
        assert admin_org.organization_id != demo_org.organization_id

        # Wrong password on one account never authenticates the other.
        assert (
            auth_service.authenticate(
                DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "demo-password"
            )
            is None
        )
        assert (
            auth_service.authenticate(DEMO_ORGANIZATION_SLUG, DEMO_USER_EMAIL, "admin-password")
            is None
        )

    def test_same_email_in_two_organizations_each_authenticates_only_in_its_own(
        self, repo, auth_service
    ):
        """EO-015 requirement 1+2+3: the same e-mail may exist validly in
        two different organizations (uq_users_org_email scopes uniqueness
        per organization, not globally); each organization+email pair
        authenticates only in the organization it belongs to."""
        shared_email = "shared@example.com"
        with repo.SessionLocal() as session:
            enterprise = EnterpriseRepository(repo.SessionLocal)
            org_a = enterprise.get_or_create_organization(session, "Organização Compartilhada A")
            org_b = enterprise.get_or_create_organization(session, "Organização Compartilhada B")
            hasher = Argon2PasswordHasher()
            enterprise.create_user_in_session(
                session,
                organization_id=org_a.id,
                email=shared_email,
                display_name="Usuário A",
                password_hash=hasher.hash("password-a"),
            )
            enterprise.create_user_in_session(
                session,
                organization_id=org_b.id,
                email=shared_email,
                display_name="Usuário B",
                password_hash=hasher.hash("password-b"),
            )
            session.commit()
            slug_a, slug_b = org_a.slug, org_b.slug

        result_a = auth_service.authenticate(slug_a, shared_email, "password-a")
        result_b = auth_service.authenticate(slug_b, shared_email, "password-b")
        assert result_a is not None
        assert result_b is not None
        assert result_a[0].user_id != result_b[0].user_id
        assert result_a[1].organization_id != result_b[1].organization_id

        # A credential valid in one organization never authenticates in the other.
        assert auth_service.authenticate(slug_a, shared_email, "password-b") is None
        assert auth_service.authenticate(slug_b, shared_email, "password-a") is None

    def test_demo_user_authenticates_only_in_demo_organization(self, repo, auth_service):
        """EO-015 requirement 4."""
        auth_service.bootstrap_demo_user("demo-password")

        assert (
            auth_service.authenticate(DEMO_ORGANIZATION_SLUG, DEMO_USER_EMAIL, "demo-password")
            is not None
        )
        assert (
            auth_service.authenticate(
                DEFAULT_ORGANIZATION_SLUG, DEMO_USER_EMAIL, "demo-password"
            )
            is None
        )

    def test_uniform_error_never_reveals_which_part_was_wrong(self, auth_service):
        """EO-015 requirement 7: unknown organization, unknown user and
        wrong password must all be indistinguishable to the caller -- here,
        all three collapse to the same None."""
        auth_service.bootstrap_administrator("admin@example.com", "correct-password")

        unknown_org = auth_service.authenticate(
            "no-such-organization", "admin@example.com", "correct-password"
        )
        unknown_user = auth_service.authenticate(
            DEFAULT_ORGANIZATION_SLUG, "nobody@example.com", "correct-password"
        )
        wrong_password = auth_service.authenticate(
            DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "wrong"
        )

        assert unknown_org is unknown_user is wrong_password is None

    def test_rehash_on_login_when_parameters_are_outdated(self, repo, monkeypatch):
        monkeypatch.setenv("ARGON2_TIME_COST", "2")
        weak_hasher = Argon2PasswordHasher()
        weak_auth = AuthService(repo.SessionLocal, weak_hasher)
        weak_auth.bootstrap_administrator("admin@example.com", "correct-password")

        with repo.SessionLocal() as session:
            old_hash = session.query(User).filter(User.email == "admin@example.com").one().password_hash

        monkeypatch.setenv("ARGON2_TIME_COST", "4")
        strong_auth = AuthService(repo.SessionLocal, Argon2PasswordHasher())
        result = strong_auth.authenticate(
            DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password"
        )
        assert result is not None

        with repo.SessionLocal() as session:
            new_hash = session.query(User).filter(User.email == "admin@example.com").one().password_hash
        assert new_hash != old_hash
        # The rehashed password still verifies with the new parameters.
        assert (
            strong_auth.authenticate(
                DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "correct-password"
            )
            is not None
        )


class TestBootstrapAdministrator:
    def test_creates_exactly_one_admin_with_role(self, repo, auth_service):
        auth_service.bootstrap_administrator("admin@example.com", "correct-password")

        with repo.SessionLocal() as session:
            users = session.query(User).filter(User.email == "admin@example.com").all()
            assert len(users) == 1
            admin_role = session.query(Role).filter(Role.name == "organization_admin").one()
            membership = (
                session.query(UserRole)
                .filter(UserRole.user_id == users[0].id, UserRole.role_id == admin_role.id)
                .one_or_none()
            )
            assert membership is not None

    def test_second_call_never_recreates_or_resets(self, repo, auth_service):
        auth_service.bootstrap_administrator("admin@example.com", "first-password")
        with repo.SessionLocal() as session:
            hash_after_first = (
                session.query(User).filter(User.email == "admin@example.com").one().password_hash
            )

        # Even with a different password supplied, an existing admin is untouched.
        auth_service.bootstrap_administrator("admin@example.com", "different-password")

        with repo.SessionLocal() as session:
            users = session.query(User).filter(User.email == "admin@example.com").all()
            assert len(users) == 1
            assert users[0].password_hash == hash_after_first

        assert (
            auth_service.authenticate(
                DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "first-password"
            )
            is not None
        )
        assert (
            auth_service.authenticate(
                DEFAULT_ORGANIZATION_SLUG, "admin@example.com", "different-password"
            )
            is None
        )

    def test_atomic_when_role_assignment_fails(self, repo, auth_service, monkeypatch):
        """If assigning the role fails for any reason, the user is not left
        behind either -- proves user+role are written in one transaction
        (AR-001 item 4), not two independent steps."""

        def _boom(self, session, user_id, role_name):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(EnterpriseRepository, "assign_role_in_session", _boom)

        with pytest.raises(RuntimeError):
            auth_service.bootstrap_administrator("admin@example.com", "correct-password")

        with repo.SessionLocal() as session:
            assert session.query(User).filter(User.email == "admin@example.com").count() == 0


class TestBootstrapDemoUser:
    def test_creates_demo_user_in_its_own_organization(self, repo, auth_service):
        auth_service.bootstrap_demo_user("demo-password")

        with repo.SessionLocal() as session:
            demo_user = session.query(User).filter(User.email == DEMO_USER_EMAIL).one()
            assert demo_user.identity_type == "demo"
            org = EnterpriseRepository(repo.SessionLocal).get_or_create_organization(
                session, DEMO_ORGANIZATION_NAME
            )
            assert demo_user.organization_id == org.id
            assert org.slug == DEMO_ORGANIZATION_SLUG

    def test_demo_user_never_shares_organization_with_administrator(self, repo, auth_service):
        auth_service.bootstrap_administrator("admin@example.com", "admin-password")
        auth_service.bootstrap_demo_user("demo-password")

        with repo.SessionLocal() as session:
            admin = session.query(User).filter(User.email == "admin@example.com").one()
            demo = session.query(User).filter(User.email == DEMO_USER_EMAIL).one()
            assert admin.organization_id != demo.organization_id

    def test_second_call_never_recreates(self, repo, auth_service):
        auth_service.bootstrap_demo_user("first-password")
        auth_service.bootstrap_demo_user("second-password")

        with repo.SessionLocal() as session:
            assert session.query(User).filter(User.email == DEMO_USER_EMAIL).count() == 1

        assert (
            auth_service.authenticate(DEMO_ORGANIZATION_SLUG, DEMO_USER_EMAIL, "first-password")
            is not None
        )
        assert (
            auth_service.authenticate(DEMO_ORGANIZATION_SLUG, DEMO_USER_EMAIL, "second-password")
            is None
        )

    def test_demo_user_gets_the_viewer_role_even_when_pre_existing(self, repo, auth_service):
        """Wave 2 Sprint 5: without a role the demo user would 403 on every
        RBAC-protected Enterprise Domain route -- the role is (re-)ensured
        on every boot, including for demo users created before RBAC, and
        never duplicated."""
        from src.database.models import Role, UserRole

        auth_service.bootstrap_demo_user("demo-password")
        auth_service.bootstrap_demo_user("demo-password")  # second boot, idempotent

        with repo.SessionLocal() as session:
            demo = session.query(User).filter(User.email == DEMO_USER_EMAIL).one()
            role_ids = [
                user_role.role_id
                for user_role in session.query(UserRole).filter(UserRole.user_id == demo.id)
            ]
            assert len(role_ids) == 1
            assert session.get(Role, role_ids[0]).name == "viewer"


class TestLogout:
    def test_logout_acknowledges_without_raising(self, auth_service):
        # No server-side session store exists yet (TDS Section 15.2) --
        # logout is a no-op that must never raise.
        auth_service.logout(session_id="session-abc", user_id=1)
