"""Write-side repository for the Enterprise Foundation entities.

Épico 1 scope: structural creation plus the cross-tenant guards the schema
alone cannot express. All writes to organizations/users/projects/memberships
must go through here so an invalid cross-organization link can never be
persisted (Founder directive, Release 0.1 opening).
"""
import logging

from sqlalchemy.orm import Session, sessionmaker

from src.database.models import (
    Organization,
    Project,
    Role,
    User,
    UserProjectMembership,
    UserRole,
)
from src.database.project_identity import (
    DEFAULT_ORGANIZATION_NAME,
    FALLBACK_PROJECT_NAME,
    normalize_project_name,
    organization_slug,
)

logger = logging.getLogger(__name__)


class CrossTenantViolationError(Exception):
    """A write tried to link entities that belong to different organizations."""


class EmailConflictError(Exception):
    """A user create/update collided with an existing email in the same
    organization (case-insensitive -- User Management, Wave 2)."""


class LastActiveAdminError(Exception):
    """An operation would leave an organization with zero active
    `organization_admin` users (User Management, Wave 2)."""


class SelfDeactivationError(Exception):
    """An actor tried to deactivate their own user account (User
    Management, Wave 2)."""


class ProjectNotFoundError(Exception):
    """A project reference (id or name) did not resolve to a Project in the
    caller's organization (TD-008 Phase 3b, dual-key resolution). A
    cross-organization id resolves here too -- an id that exists in another
    organization is reported as not-found, never confirmed, matching the
    404 convention already used across the Enterprise Domain API."""


class AmbiguousProjectNameError(Exception):
    """A project name resolved to more than one Project in the organization
    (TD-008 Phase 3b). Name is not a safe key precisely because of this --
    the migration to project_id exists to remove the ambiguity; while both
    keys coexist, an ambiguous name is rejected explicitly instead of
    silently picking one."""


class ProjectReferenceMismatchError(Exception):
    """Both project_id and project_name were supplied and they point to
    different Projects (TD-008 Phase 3b dual-key contract, Founder
    requirement). Rejected explicitly -- never silently resolved to one."""


class EnterpriseRepository:
    """Operates inside sessions produced by the injected sessionmaker.

    Reuses the engine/session factory of the existing AnalysisRepository via
    dependency injection instead of creating a parallel engine.
    """

    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    # -- Organizations -----------------------------------------------------

    def create_organization(self, name: str) -> int:
        with self._session_factory() as session:
            org = Organization(name=name, slug=organization_slug(name))
            session.add(org)
            session.commit()
            session.refresh(org)
            logger.info("Created organization id=%s name=%s slug=%s", org.id, name, org.slug)
            return org.id

    def get_or_create_organization(self, session: Session, name: str) -> Organization:
        """Idempotent get-or-create for any named organization, in-session."""
        org = session.query(Organization).filter(Organization.name == name).one_or_none()
        if org is None:
            org = Organization(name=name, slug=organization_slug(name))
            session.add(org)
            session.flush()
            logger.info("Created organization id=%s name=%s slug=%s", org.id, name, org.slug)
        return org

    def get_or_create_default_organization(self, session: Session) -> Organization:
        """The single main organization of this installation (idempotent)."""
        return self.get_or_create_organization(session, DEFAULT_ORGANIZATION_NAME)

    def get_organization_by_slug(self, session: Session, slug: str) -> Organization | None:
        """Login's entry point into organization scoping (EO-015): the slug
        is the only organization identifier login ever accepts."""
        return session.query(Organization).filter(Organization.slug == slug).one_or_none()

    # -- Users -------------------------------------------------------------

    def get_user_by_email(
        self, session: Session, organization_id: int, email: str
    ) -> User | None:
        """In-session lookup scoped to one organization -- used by bootstrap
        (which always knows the target organization) so the query and any
        resulting write share one transaction (TDS Epic 2 Section 12)."""
        return (
            session.query(User)
            .filter(User.organization_id == organization_id, User.email == email)
            .one_or_none()
        )

    def create_user_in_session(
        self,
        session: Session,
        organization_id: int,
        email: str,
        display_name: str,
        password_hash: str,
        identity_type: str = "standard",
    ) -> User:
        user = User(
            organization_id=organization_id,
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            identity_type=identity_type,
        )
        session.add(user)
        session.flush()
        logger.info(
            "Created user id=%s organization_id=%s identity_type=%s",
            user.id,
            organization_id,
            identity_type,
        )
        return user

    def assign_role_in_session(self, session: Session, user_id: int, role_name: str) -> None:
        role = session.query(Role).filter(Role.name == role_name).one_or_none()
        if role is None:
            # Roles are normally seeded by migration 0002. An install that
            # only ran Base.metadata.create_all() (no alembic) would
            # otherwise fail here -- create it on demand so bootstrap never
            # depends on migrations having run.
            role = Role(name=role_name)
            session.add(role)
            session.flush()
            logger.warning(
                "Role '%s' did not exist and was created on demand "
                "(normally seeded by migration 0002 -- consider running "
                "`alembic upgrade head`)",
                role_name,
            )
        # Idempotent since Wave 2 Sprint 5: bootstrap now re-ensures roles on
        # every boot (demo user), so a second call must be a no-op, never a
        # duplicate-PK error on user_roles.
        already_has = (
            session.query(UserRole)
            .filter(UserRole.user_id == user_id, UserRole.role_id == role.id)
            .one_or_none()
        )
        if already_has is None:
            session.add(UserRole(user_id=user_id, role_id=role.id))
            logger.info("Assigned role=%s to user_id=%s", role_name, user_id)

    def create_user(self, organization_id: int, email: str, display_name: str) -> int:
        with self._session_factory() as session:
            if session.get(Organization, organization_id) is None:
                raise ValueError(f"Organization {organization_id} does not exist")
            user = User(
                organization_id=organization_id, email=email, display_name=display_name
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("Created user id=%s organization_id=%s", user.id, organization_id)
            return user.id

    # -- Projects ----------------------------------------------------------

    def create_project(self, organization_id: int, name: str) -> int:
        with self._session_factory() as session:
            if session.get(Organization, organization_id) is None:
                raise ValueError(f"Organization {organization_id} does not exist")
            project = Project(organization_id=organization_id, name=name)
            session.add(project)
            session.commit()
            session.refresh(project)
            logger.info(
                "Created project id=%s organization_id=%s", project.id, organization_id
            )
            return project.id

    def list_projects(self, organization_id: int) -> list[Project]:
        """Projects are always read through an organization scope."""
        with self._session_factory() as session:
            projects = (
                session.query(Project)
                .filter(Project.organization_id == organization_id)
                .order_by(Project.name)
                .all()
            )
            logger.info(
                "Listed %d projects organization_id=%s", len(projects), organization_id
            )
            return projects

    def get_or_create_project_for_name(
        self, session: Session, organization_id: int, raw_project_name: str | None
    ) -> Project:
        """Resolve a legacy free-text name to a real Project (deterministic),
        scoped to the caller's real organization (Security Hardening Gate,
        C-2) -- previously always resolved to the hardcoded default
        organization regardless of who called it, which meant every
        organization's analyses silently shared one Project namespace.

        Same rule as the 0002 migration: strip surrounding whitespace, no
        case folding, no similarity merging; empty/None maps to the fallback
        project. Runs inside the caller's session/transaction.
        """
        key = normalize_project_name(raw_project_name)
        name = key if key is not None else FALLBACK_PROJECT_NAME
        project = (
            session.query(Project)
            .filter(Project.organization_id == organization_id, Project.name == name)
            .one_or_none()
        )
        if project is None:
            project = Project(
                organization_id=organization_id,
                name=name,
                legacy_project_name=key,
            )
            session.add(project)
            session.flush()
            logger.info(
                "Created project id=%s organization_id=%s from legacy name=%r",
                project.id,
                organization_id,
                raw_project_name,
            )
        return project

    def resolve_project_reference(
        self,
        organization_id: int,
        project_id: int | None = None,
        project_name: str | None = None,
    ) -> Project | None:
        """Dual-key resolution (TD-008 Phase 3b, Etapa 1). Read-only -- never
        creates a Project (that stays with `get_or_create_project_for_name`
        on the analyze/write path).

        Contract (Founder requirements):
        - both None -> None (portfolio scope, no project filter).
        - project_id given -> must exist AND belong to `organization_id`,
          else ProjectNotFoundError (a cross-organization id is reported as
          not-found, never confirmed).
        - project_name given (no id) -> resolved within the organization;
          0 matches -> ProjectNotFoundError; >1 -> AmbiguousProjectNameError
          (name is not a safe key while duplicates can exist).
        - both given -> each resolved as above, then they must be the SAME
          Project, else ProjectReferenceMismatchError. Never silently picks
          one.
        """
        has_id = project_id is not None
        has_name = project_name is not None and project_name.strip() != ""
        if not has_id and not has_name:
            return None

        with self._session_factory() as session:
            by_id: Project | None = None
            if has_id:
                by_id = session.get(Project, project_id)
                if by_id is None or by_id.organization_id != organization_id:
                    raise ProjectNotFoundError(
                        f"Project id={project_id} not found in organization {organization_id}"
                    )

            by_name: Project | None = None
            if has_name:
                name = normalize_project_name(project_name)
                matches = (
                    session.query(Project)
                    .filter(
                        Project.organization_id == organization_id,
                        Project.name == name,
                    )
                    .all()
                )
                if len(matches) == 0:
                    raise ProjectNotFoundError(
                        f"Project name={project_name!r} not found in organization "
                        f"{organization_id}"
                    )
                if len(matches) > 1:
                    raise AmbiguousProjectNameError(
                        f"Project name={project_name!r} is ambiguous "
                        f"({len(matches)} matches) in organization {organization_id}"
                    )
                by_name = matches[0]

            if has_id and has_name and by_id.id != by_name.id:
                raise ProjectReferenceMismatchError(
                    f"project_id={project_id} and project_name={project_name!r} "
                    "refer to different projects"
                )

            return by_id or by_name

    # -- Memberships -------------------------------------------------------

    def add_project_member(
        self, user_id: int, project_id: int, role_in_project: str = "member"
    ) -> None:
        """Link a user to a project, refusing any cross-organization link."""
        with self._session_factory() as session:
            user = session.get(User, user_id)
            project = session.get(Project, project_id)
            if user is None or project is None:
                raise ValueError("User or project does not exist")
            if user.organization_id != project.organization_id:
                logger.warning(
                    "Refused cross-tenant membership user=%s (org %s) project=%s (org %s)",
                    user_id,
                    user.organization_id,
                    project_id,
                    project.organization_id,
                )
                raise CrossTenantViolationError(
                    "User and project belong to different organizations"
                )
            session.add(
                UserProjectMembership(
                    user_id=user_id, project_id=project_id, role_in_project=role_in_project
                )
            )
            session.commit()
            logger.info(
                "Added membership user=%s project=%s role=%s",
                user_id,
                project_id,
                role_in_project,
            )
