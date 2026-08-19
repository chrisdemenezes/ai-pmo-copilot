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
`create_*` also publishes an event via `EventPublisher`, immediately
after the write succeeds. Wave 4 (Enterprise Operations, Epic W4-1,
D-076) promoted the seam from `EventEmitter`/`NoOpEventEmitter` to
`EventPublisher`/`InProcessEventPublisher` -- same call position, same 5
`event_type` values, now envelope-wrapped with full observability
(Event ID/Correlation ID/Timestamp/Tenant/Origin/Payload Version).
`correlation_id` is never minted here -- it is the same identifier
`RequestIDMiddleware` already generates once per request
(`RequestContext.request_id`), passed down by the calling route; this
service never creates a new one. `create_program`/`create_project`
always create already linked to their parent (there is no separate
re-parenting route), so each publishes both its `.created` event and the
corresponding `.linked_to_*` event from the same Event Map (§5.9).
"""
import logging

from src.database.models import Portfolio, Program, Project
from src.database.repository import AnalysisRepository
from src.services.events.interfaces import EventPublisher

logger = logging.getLogger(__name__)


class DomainService:
    def __init__(self, repository: AnalysisRepository, publisher: EventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    # -- Portfolios ----------------------------------------------------

    def list_portfolios(self, organization_id: int) -> list[Portfolio]:
        return self._repository.domain.list_portfolios_by_organization(organization_id)

    def get_portfolio(self, portfolio_id: int, organization_id: int) -> Portfolio | None:
        return self._repository.domain.get_portfolio(portfolio_id, organization_id)

    def create_portfolio(
        self,
        organization_id: int,
        name: str,
        code: str,
        actor_user_id: int,
        correlation_id: str,
        **fields,
    ) -> Portfolio:
        portfolio_id = self._repository.domain.create_portfolio(
            organization_id, name, code, **fields
        )
        self._repository.administration.record_audit(
            organization_id, actor_user_id, "portfolio.created", "portfolio", portfolio_id
        )
        self._publisher.publish(
            "portfolio.created",
            {"portfolio_id": portfolio_id},
            organization_id,
            correlation_id=correlation_id,
            origin="domain_service",
        )
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
        correlation_id: str,
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
        self._publisher.publish(
            "program.created", payload, organization_id, correlation_id=correlation_id, origin="domain_service"
        )
        self._publisher.publish(
            "program.linked_to_portfolio",
            payload,
            organization_id,
            correlation_id=correlation_id,
            origin="domain_service",
        )
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
        self,
        organization_id: int,
        program_id: int,
        name: str,
        actor_user_id: int,
        correlation_id: str,
        **fields,
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
        self._publisher.publish(
            "project_delivery.created",
            payload,
            organization_id,
            correlation_id=correlation_id,
            origin="domain_service",
        )
        self._publisher.publish(
            "project_delivery.linked_to_program",
            payload,
            organization_id,
            correlation_id=correlation_id,
            origin="domain_service",
        )
        return self._repository.domain.get_project(project_id, organization_id)
