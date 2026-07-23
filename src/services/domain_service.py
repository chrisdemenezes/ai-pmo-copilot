"""Application layer for the Enterprise Domain API (Wave 2, Sprint 2).

Same split already used by `ProjectSummaryService`: routes stay thin
adapters, this service holds the one non-trivial rule the repository
itself doesn't enforce -- that a child (Program under a Portfolio, Project
under a Program) is only reachable through a parent that belongs to the
caller's organization. Returning `None` here (never raising) lets every
route in `src/api/routes/portfolio.py`/`program.py`/`project_delivery.py`
map "not found" and "not yours" to the same 404, so no route ever leaks
whether an id merely doesn't exist or belongs to someone else.

Sprint 4 (Enterprise Administration): every `create_*` records an audit
entry via `AdministrationRepository.record_audit` -- Épico 5's "Auditoria
de mutações" applied retroactively to this Bounded Context's writes, not
just to the new Administration endpoints themselves.

Wave 1 (Event Foundation, closed retrospectively per D-048): every
`create_*` also emits an event via `EventEmitter`, immediately after the
write succeeds -- the seam `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §5
described, so promoting `NoOpEventEmitter` to a real emitter later changes
zero call sites here. `create_program`/`create_project` always create
already linked to their parent (there is no separate re-parenting route),
so each emits both its `.created` event and the corresponding
`.linked_to_*` event from the same Event Map (§5.9).
"""
import logging

from src.database.models import Portfolio, Program, Project
from src.database.repository import AnalysisRepository
from src.services.events.interfaces import EventEmitter

logger = logging.getLogger(__name__)


class DomainService:
    def __init__(self, repository: AnalysisRepository, emitter: EventEmitter) -> None:
        self._repository = repository
        self._emitter = emitter

    # -- Portfolios ----------------------------------------------------

    def list_portfolios(self, organization_id: int) -> list[Portfolio]:
        return self._repository.domain.list_portfolios_by_organization(organization_id)

    def get_portfolio(self, portfolio_id: int, organization_id: int) -> Portfolio | None:
        return self._repository.domain.get_portfolio(portfolio_id, organization_id)

    def create_portfolio(
        self, organization_id: int, name: str, code: str, actor_user_id: int, **fields
    ) -> Portfolio:
        portfolio_id = self._repository.domain.create_portfolio(
            organization_id, name, code, **fields
        )
        self._repository.administration.record_audit(
            organization_id, actor_user_id, "portfolio.created", "portfolio", portfolio_id
        )
        self._emitter.emit("portfolio.created", {"portfolio_id": portfolio_id}, organization_id)
        return self._repository.domain.get_portfolio(portfolio_id, organization_id)

    # -- Programs --------------------------------------------------------

    def list_programs(
        self, organization_id: int, portfolio_id: int | None = None
    ) -> list[Program] | None:
        """Returns None (not an empty list) when a portfolio_id filter is
        given but doesn't resolve within this organization -- the route
        maps that to 404, distinct from "resolves, but has zero Programs"."""
        if portfolio_id is None:
            return self._repository.domain.list_programs_by_organization(organization_id)
        if self.get_portfolio(portfolio_id, organization_id) is None:
            return None
        return self._repository.domain.list_programs_by_portfolio(portfolio_id)

    def get_program(self, program_id: int, organization_id: int) -> Program | None:
        return self._repository.domain.get_program(program_id, organization_id)

    def create_program(
        self,
        organization_id: int,
        portfolio_id: int,
        name: str,
        code: str,
        actor_user_id: int,
        **fields,
    ) -> Program | None:
        """None means the portfolio doesn't exist or isn't this
        organization's -- the route maps that to 404, never creating a
        Program under a Portfolio the caller can't already see."""
        if self.get_portfolio(portfolio_id, organization_id) is None:
            return None
        program_id = self._repository.domain.create_program(portfolio_id, name, code, **fields)
        self._repository.administration.record_audit(
            organization_id, actor_user_id, "program.created", "program", program_id
        )
        payload = {"program_id": program_id, "portfolio_id": portfolio_id}
        self._emitter.emit("program.created", payload, organization_id)
        self._emitter.emit("program.linked_to_portfolio", payload, organization_id)
        return self._repository.domain.get_program(program_id, organization_id)

    # -- Projects (domain fields on the Épico-1 `projects` table) --------

    def list_projects(
        self, organization_id: int, program_id: int | None = None
    ) -> list[Project] | None:
        if program_id is None:
            return self._repository.domain.list_projects_by_organization(organization_id)
        if self.get_program(program_id, organization_id) is None:
            return None
        return self._repository.domain.list_projects_by_program(program_id)

    def get_project(self, project_id: int, organization_id: int) -> Project | None:
        return self._repository.domain.get_project(project_id, organization_id)

    def create_project(
        self, organization_id: int, program_id: int, name: str, actor_user_id: int, **fields
    ) -> Project | None:
        """None means the program doesn't exist or isn't this
        organization's -- same not-found-not-yours discipline as
        create_program()."""
        if self.get_program(program_id, organization_id) is None:
            return None
        project_id = self._repository.domain.create_project_with_domain(
            organization_id, program_id, name, **fields
        )
        self._repository.administration.record_audit(
            organization_id, actor_user_id, "project_delivery.created", "project", project_id
        )
        payload = {"project_id": project_id, "program_id": program_id}
        self._emitter.emit("project_delivery.created", payload, organization_id)
        self._emitter.emit("project_delivery.linked_to_program", payload, organization_id)
        return self._repository.domain.get_project(project_id, organization_id)
