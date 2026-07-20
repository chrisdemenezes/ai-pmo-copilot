"""Write/read repository for the Enterprise Domain (Portfolio -> Program ->
Project), Wave 2 of the Enterprise Master Execution Program.

Same convention as `EnterpriseRepository` (Épico 1): one class, one method
group per entity, organization scoping enforced explicitly rather than
implicitly. `Project` here is the same Épico-1 `projects` table, extended
with domain fields (`DOMAIN-BLUEPRINT-PROJECT.md`, Opção A) -- there is no
separate `projects_delivery` table.

No Protocol abstraction introduced for this repository: `EnterpriseRepository`
itself has none, and there is no second implementation to abstract over yet
(YAGNI) -- Foundation Technical Design §2.4's Protocol sketch remains a
future option if one is ever needed, not a requirement today.
"""
import logging

from sqlalchemy.orm import sessionmaker

from src.database.enterprise_repository import CrossTenantViolationError
from src.database.models import Organization, Portfolio, Program, Project

logger = logging.getLogger(__name__)


class DomainRepository:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    # -- Portfolios ----------------------------------------------------

    def create_portfolio(self, organization_id: int, name: str, code: str, **fields) -> int:
        with self._session_factory() as session:
            if session.get(Organization, organization_id) is None:
                raise ValueError(f"Organization {organization_id} does not exist")
            portfolio = Portfolio(organization_id=organization_id, name=name, code=code, **fields)
            session.add(portfolio)
            session.commit()
            session.refresh(portfolio)
            logger.info(
                "Created portfolio id=%s organization_id=%s code=%s",
                portfolio.id,
                organization_id,
                code,
            )
            return portfolio.id

    def list_portfolios_by_organization(self, organization_id: int) -> list[Portfolio]:
        with self._session_factory() as session:
            portfolios = (
                session.query(Portfolio)
                .filter(Portfolio.organization_id == organization_id)
                .order_by(Portfolio.code)
                .all()
            )
            logger.info(
                "Listed %d portfolios organization_id=%s", len(portfolios), organization_id
            )
            return portfolios

    def get_portfolio(self, portfolio_id: int, organization_id: int) -> Portfolio | None:
        """Scoped by organization_id in the query itself, not checked after
        the fact -- a cross-organization id never distinguishes "not found"
        from "not yours" in the response (same 404 either way, no existence
        leak)."""
        with self._session_factory() as session:
            return (
                session.query(Portfolio)
                .filter(Portfolio.id == portfolio_id, Portfolio.organization_id == organization_id)
                .one_or_none()
            )

    # -- Programs --------------------------------------------------------

    def create_program(self, portfolio_id: int, name: str, code: str, **fields) -> int:
        with self._session_factory() as session:
            if session.get(Portfolio, portfolio_id) is None:
                raise ValueError(f"Portfolio {portfolio_id} does not exist")
            program = Program(portfolio_id=portfolio_id, name=name, code=code, **fields)
            session.add(program)
            session.commit()
            session.refresh(program)
            logger.info(
                "Created program id=%s portfolio_id=%s code=%s", program.id, portfolio_id, code
            )
            return program.id

    def list_programs_by_portfolio(self, portfolio_id: int) -> list[Program]:
        with self._session_factory() as session:
            programs = (
                session.query(Program)
                .filter(Program.portfolio_id == portfolio_id)
                .order_by(Program.code)
                .all()
            )
            logger.info("Listed %d programs portfolio_id=%s", len(programs), portfolio_id)
            return programs

    def list_programs_by_organization(self, organization_id: int) -> list[Program]:
        """Program has no organization_id column of its own -- scoped
        transitively through Portfolio (Foundation Technical Design §3.10)."""
        with self._session_factory() as session:
            programs = (
                session.query(Program)
                .join(Portfolio, Program.portfolio_id == Portfolio.id)
                .filter(Portfolio.organization_id == organization_id)
                .order_by(Program.code)
                .all()
            )
            logger.info(
                "Listed %d programs organization_id=%s", len(programs), organization_id
            )
            return programs

    def get_program(self, program_id: int, organization_id: int) -> Program | None:
        """Scoped transitively through Portfolio, same 404-not-403 discipline
        as get_portfolio()."""
        with self._session_factory() as session:
            return (
                session.query(Program)
                .join(Portfolio, Program.portfolio_id == Portfolio.id)
                .filter(Program.id == program_id, Portfolio.organization_id == organization_id)
                .one_or_none()
            )

    # -- Projects (domain fields on the Épico-1 `projects` table) --------

    def create_project_with_domain(
        self, organization_id: int, program_id: int, name: str, **domain_fields
    ) -> int:
        """Creates a brand-new Project already linked to a Program --
        distinct from `EnterpriseRepository.create_project()`, which creates
        an Épico-1 Project with no domain fields at all."""
        with self._session_factory() as session:
            if session.get(Organization, organization_id) is None:
                raise ValueError(f"Organization {organization_id} does not exist")
            program = session.get(Program, program_id)
            if program is None:
                raise ValueError(f"Program {program_id} does not exist")
            portfolio = session.get(Portfolio, program.portfolio_id)
            if portfolio is None or portfolio.organization_id != organization_id:
                logger.warning(
                    "Refused cross-tenant project creation organization_id=%s program_id=%s",
                    organization_id,
                    program_id,
                )
                raise CrossTenantViolationError(
                    "Program belongs to a different organization"
                )
            project = Project(
                organization_id=organization_id,
                name=name,
                program_id=program_id,
                **domain_fields,
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            logger.info(
                "Created project id=%s organization_id=%s program_id=%s",
                project.id,
                organization_id,
                program_id,
            )
            return project.id

    def attach_project_to_program(
        self, project_id: int, program_id: int, **domain_fields
    ) -> None:
        """Links an existing (e.g. legacy Épico-1) Project to a Program and
        sets its domain fields -- the migration path for TD-008 recommended
        by `DOMAIN-BLUEPRINT-PROJECT.md` §3, Fase 2."""
        with self._session_factory() as session:
            project = session.get(Project, project_id)
            program = session.get(Program, program_id)
            if project is None or program is None:
                raise ValueError("Project or Program does not exist")
            portfolio = session.get(Portfolio, program.portfolio_id)
            if portfolio is None or project.organization_id != portfolio.organization_id:
                logger.warning(
                    "Refused cross-tenant attach project=%s (org %s) program=%s",
                    project_id,
                    project.organization_id,
                    program_id,
                )
                raise CrossTenantViolationError(
                    "Project and Program belong to different organizations"
                )
            project.program_id = program_id
            for field, value in domain_fields.items():
                setattr(project, field, value)
            session.commit()
            logger.info("Attached project=%s to program=%s", project_id, program_id)

    def list_projects_by_program(self, program_id: int) -> list[Project]:
        with self._session_factory() as session:
            projects = (
                session.query(Project)
                .filter(Project.program_id == program_id)
                .order_by(Project.name)
                .all()
            )
            logger.info("Listed %d projects program_id=%s", len(projects), program_id)
            return projects

    def list_projects_by_organization(self, organization_id: int) -> list[Project]:
        """Only domain-linked Projects (program_id IS NOT NULL) -- a plain
        Épico-1 Project with no Program yet is not part of the Enterprise
        Domain API surface until it goes through
        `attach_project_to_program()` (TD-008, Fase 2)."""
        with self._session_factory() as session:
            projects = (
                session.query(Project)
                .filter(
                    Project.organization_id == organization_id,
                    Project.program_id.isnot(None),
                )
                .order_by(Project.name)
                .all()
            )
            logger.info(
                "Listed %d domain projects organization_id=%s", len(projects), organization_id
            )
            return projects

    def get_project(self, project_id: int, organization_id: int) -> Project | None:
        with self._session_factory() as session:
            return (
                session.query(Project)
                .filter(
                    Project.id == project_id,
                    Project.organization_id == organization_id,
                    Project.program_id.isnot(None),
                )
                .one_or_none()
            )
