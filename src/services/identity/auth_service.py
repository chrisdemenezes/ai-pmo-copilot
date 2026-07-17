"""Identity Layer application service (TDS Epic 2).

AuthService depends on a CredentialVerifier by composition (injected), not
by inheritance -- Argon2/local is the only implementation in this epic; a
future SSO/OAuth/LDAP provider implements the same contract (interfaces.py)
without this class changing.
"""
import logging
import os

from sqlalchemy.orm import sessionmaker

from src.database.enterprise_repository import EnterpriseRepository
from src.database.project_identity import DEFAULT_ORGANIZATION_NAME, organization_slug
from src.services.identity.interfaces import CredentialVerifier
from src.services.identity.models import AuthenticatedUser, OrganizationIdentity

logger = logging.getLogger(__name__)

DEMO_ORGANIZATION_NAME = "Demo Organization"
DEMO_USER_EMAIL = "demo@stratech.local"

# Stable external identifiers for the two organizations this épico bootstraps
# (EO-015). Derived once from the display names via the same rule the 0004
# migration backfill and EnterpriseRepository creation paths use -- never
# recomputed for an existing row.
DEFAULT_ORGANIZATION_SLUG = organization_slug(DEFAULT_ORGANIZATION_NAME)
DEMO_ORGANIZATION_SLUG = organization_slug(DEMO_ORGANIZATION_NAME)


class AuthService:
    def __init__(
        self,
        session_factory: sessionmaker,
        credential_verifier: CredentialVerifier,
        enterprise_repository: EnterpriseRepository | None = None,
    ):
        self._session_factory = session_factory
        self._credentials = credential_verifier
        self._repo = enterprise_repository or EnterpriseRepository(session_factory)

    # -- Login ---------------------------------------------------------

    def authenticate(
        self, organization_slug: str, email: str, password: str
    ) -> tuple[AuthenticatedUser, OrganizationIdentity] | None:
        """Verify credentials scoped by organization + email + password
        (EO-015 Organizational Identity Scope Correction).

        The login contract is {organization, email, password} -- resolution
        is organization_slug + email, never a global email search, so the
        same email may exist validly in two different organizations without
        one ever authenticating in the other's context.

        Returns None on any failure (organization not found, user not
        found, wrong password) -- callers must not distinguish these cases
        in the HTTP response, to avoid revealing whether the organization or
        the user exists (TDS Section 7 / EO-015).
        """
        with self._session_factory() as session:
            org = self._repo.get_organization_by_slug(session, organization_slug)
            if org is None:
                logger.info("Login failed: organization not found slug=%s", organization_slug)
                return None

            user = self._repo.get_user_by_email(session, org.id, email)
            if user is None or user.password_hash is None:
                logger.info(
                    "Login failed: user not found organization_id=%s email=%s", org.id, email
                )
                return None

            if not self._credentials.verify(password, user.password_hash):
                logger.info("Login failed: bad password user_id=%s", user.id)
                return None

            if self._credentials.needs_rehash(user.password_hash):
                user.password_hash = self._credentials.hash(password)
                logger.info("Rehashed password on login user_id=%s", user.id)

            session.commit()

            authenticated_user = AuthenticatedUser(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                identity_type=user.identity_type,
            )
            organization = OrganizationIdentity(
                organization_id=org.id, name=org.name, slug=org.slug
            )
            logger.info(
                "Login succeeded user_id=%s organization_id=%s", user.id, org.id
            )
            return authenticated_user, organization

    # -- Logout ----------------------------------------------------------

    def logout(self, session_id: str, user_id: int) -> None:
        """No server-side session store exists yet (TDS Section 15.2) --
        this call only records the event. Its fixed contract is what lets a
        future epic add real server-side invalidation without a new
        endpoint or a BFF change."""
        logger.info("Logout acknowledged session_id=%s user_id=%s", session_id, user_id)

    # -- Bootstrap ---------------------------------------------------------

    def bootstrap_administrator(self, email: str, password: str) -> None:
        """Create the first Administrator on first boot. Transactional
        (user + role in one commit, TDS Section 12/AR-001 item 4). Never
        recreates or resets an existing user with this email (TDS Section
        13, Rev. 1)."""
        with self._session_factory() as session:
            org = self._repo.get_or_create_default_organization(session)
            existing = self._repo.get_user_by_email(session, org.id, email)
            if existing is not None:
                logger.info("Administrator bootstrap skipped -- already exists email=%s", email)
                return

            user = self._repo.create_user_in_session(
                session,
                organization_id=org.id,
                email=email,
                display_name="Administrator",
                password_hash=self._credentials.hash(password),
                identity_type="standard",
            )
            self._repo.assign_role_in_session(session, user.id, "organization_admin")
            session.commit()
            logger.info("Administrator bootstrapped user_id=%s", user.id)

    def bootstrap_demo_user(self, password: str) -> None:
        """Create the Demo Mode user in its own organization -- never the
        default organization, never reusing the Administrator (TDS Section
        16/AR-001 item 5). Idempotent, same guard as the Administrator."""
        with self._session_factory() as session:
            org = self._repo.get_or_create_organization(session, DEMO_ORGANIZATION_NAME)
            existing = self._repo.get_user_by_email(session, org.id, DEMO_USER_EMAIL)
            if existing is not None:
                logger.info("Demo user bootstrap skipped -- already exists")
                return

            self._repo.create_user_in_session(
                session,
                organization_id=org.id,
                email=DEMO_USER_EMAIL,
                display_name="Demo",
                password_hash=self._credentials.hash(password),
                identity_type="demo",
            )
            session.commit()
            logger.info("Demo user bootstrapped organization_id=%s", org.id)


def bootstrap_identities(auth_service: AuthService) -> None:
    """Entry point called once at backend startup (src/main.py). Reads
    environment variables directly so the caller doesn't need to know
    which bootstrap paths are configured."""
    admin_email = os.getenv("STRATECH_ADMIN_EMAIL")
    admin_password = os.getenv("STRATECH_ADMIN_PASSWORD")
    if admin_email and admin_password:
        auth_service.bootstrap_administrator(admin_email, admin_password)
    else:
        logger.info(
            "Administrator bootstrap skipped -- "
            "STRATECH_ADMIN_EMAIL/STRATECH_ADMIN_PASSWORD not set"
        )

    demo_password = os.getenv("WORKSPACE_PASSWORD")
    if demo_password:
        auth_service.bootstrap_demo_user(demo_password)
    else:
        logger.info("Demo user bootstrap skipped -- WORKSPACE_PASSWORD not set")


__all__ = [
    "AuthService",
    "bootstrap_identities",
    "DEFAULT_ORGANIZATION_NAME",
    "DEFAULT_ORGANIZATION_SLUG",
    "DEMO_ORGANIZATION_NAME",
    "DEMO_ORGANIZATION_SLUG",
    "DEMO_USER_EMAIL",
]
