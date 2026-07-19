"""DomainRepository (Portfolio -> Program -> Project) -- org-scoped reads,
cross-tenant guards, and the Project unification recommended by
`DOMAIN-BLUEPRINT-PROJECT.md` (Opção A): Project domain fields live on the
same Épico-1 `projects` table, no `projects_delivery` table exists.
"""
import pytest

from src.database.enterprise_repository import CrossTenantViolationError
from src.database.repository import AnalysisRepository


@pytest.fixture()
def repo(tmp_path):
    return AnalysisRepository(database_url=f"sqlite:///{tmp_path / 'domain.db'}")


@pytest.fixture()
def two_orgs_with_portfolios(repo):
    org_a = repo.enterprise.create_organization("Organização A")
    org_b = repo.enterprise.create_organization("Organização B")
    portfolio_a = repo.domain.create_portfolio(org_a, "Portfólio A", "PF-A")
    portfolio_b = repo.domain.create_portfolio(org_b, "Portfólio B", "PF-B")
    program_a = repo.domain.create_program(portfolio_a, "Programa A", "PG-A")
    program_b = repo.domain.create_program(portfolio_b, "Programa B", "PG-B")
    return {
        "org_a": org_a,
        "org_b": org_b,
        "portfolio_a": portfolio_a,
        "portfolio_b": portfolio_b,
        "program_a": program_a,
        "program_b": program_b,
    }


class TestPortfolioSegregation:
    def test_portfolio_listing_is_scoped_by_organization(self, repo, two_orgs_with_portfolios):
        ctx = two_orgs_with_portfolios
        names_a = {p.name for p in repo.domain.list_portfolios_by_organization(ctx["org_a"])}
        names_b = {p.name for p in repo.domain.list_portfolios_by_organization(ctx["org_b"])}
        assert names_a == {"Portfólio A"}
        assert names_b == {"Portfólio B"}

    def test_portfolio_requires_existing_organization(self, repo):
        with pytest.raises(ValueError):
            repo.domain.create_portfolio(999999, "X", "PF-X")


class TestProgramSegregation:
    def test_program_listing_is_scoped_by_portfolio(self, repo, two_orgs_with_portfolios):
        ctx = two_orgs_with_portfolios
        programs_a = repo.domain.list_programs_by_portfolio(ctx["portfolio_a"])
        programs_b = repo.domain.list_programs_by_portfolio(ctx["portfolio_b"])
        assert {p.name for p in programs_a} == {"Programa A"}
        assert {p.name for p in programs_b} == {"Programa B"}

    def test_program_listing_is_scoped_by_organization_transitively(
        self, repo, two_orgs_with_portfolios
    ):
        ctx = two_orgs_with_portfolios
        names_a = {p.name for p in repo.domain.list_programs_by_organization(ctx["org_a"])}
        names_b = {p.name for p in repo.domain.list_programs_by_organization(ctx["org_b"])}
        assert names_a == {"Programa A"}
        assert names_b == {"Programa B"}

    def test_program_requires_existing_portfolio(self, repo):
        with pytest.raises(ValueError):
            repo.domain.create_program(999999, "X", "PG-X")


class TestProjectUnificationAndSegregation:
    def test_create_project_with_domain_links_to_program(self, repo, two_orgs_with_portfolios):
        ctx = two_orgs_with_portfolios
        project_id = repo.domain.create_project_with_domain(
            ctx["org_a"], ctx["program_a"], "Projeto A", code="PJ-A", health="green"
        )
        projects = repo.domain.list_projects_by_program(ctx["program_a"])
        assert len(projects) == 1
        assert projects[0].id == project_id
        assert projects[0].code == "PJ-A"
        assert projects[0].health == "green"

    def test_create_project_refuses_cross_tenant_program(self, repo, two_orgs_with_portfolios):
        ctx = two_orgs_with_portfolios
        with pytest.raises(CrossTenantViolationError):
            repo.domain.create_project_with_domain(ctx["org_a"], ctx["program_b"], "X")

    def test_create_project_requires_existing_organization_and_program(
        self, repo, two_orgs_with_portfolios
    ):
        ctx = two_orgs_with_portfolios
        with pytest.raises(ValueError):
            repo.domain.create_project_with_domain(999999, ctx["program_a"], "X")
        with pytest.raises(ValueError):
            repo.domain.create_project_with_domain(ctx["org_a"], 999999, "X")

    def test_attach_project_requires_existing_entities(self, repo, two_orgs_with_portfolios):
        ctx = two_orgs_with_portfolios
        legacy_project_id = repo.enterprise.create_project(ctx["org_a"], "Projeto Legado")
        with pytest.raises(ValueError):
            repo.domain.attach_project_to_program(999999, ctx["program_a"])
        with pytest.raises(ValueError):
            repo.domain.attach_project_to_program(legacy_project_id, 999999)

    def test_attach_project_to_program_unifies_a_legacy_project(
        self, repo, two_orgs_with_portfolios
    ):
        """Fase 2 of DOMAIN-BLUEPRINT-PROJECT.md: an existing (legacy)
        Épico-1 Project gains a program_id and domain fields in place --
        no second "Project" row, no projects_delivery table."""
        ctx = two_orgs_with_portfolios
        legacy_project_id = repo.enterprise.create_project(ctx["org_a"], "Projeto Legado")

        repo.domain.attach_project_to_program(
            legacy_project_id, ctx["program_a"], code="PJ-LEGACY", status="Ativo"
        )

        projects = repo.domain.list_projects_by_program(ctx["program_a"])
        assert len(projects) == 1
        assert projects[0].id == legacy_project_id
        assert projects[0].code == "PJ-LEGACY"
        assert projects[0].name == "Projeto Legado"  # untouched

    def test_attach_project_refuses_cross_tenant_link(self, repo, two_orgs_with_portfolios):
        ctx = two_orgs_with_portfolios
        project_b = repo.enterprise.create_project(ctx["org_b"], "Projeto B")
        with pytest.raises(CrossTenantViolationError):
            repo.domain.attach_project_to_program(project_b, ctx["program_a"])

    def test_project_listing_is_scoped_by_program(self, repo, two_orgs_with_portfolios):
        ctx = two_orgs_with_portfolios
        repo.domain.create_project_with_domain(ctx["org_a"], ctx["program_a"], "Projeto A1")
        repo.domain.create_project_with_domain(ctx["org_b"], ctx["program_b"], "Projeto B1")
        names_a = {p.name for p in repo.domain.list_projects_by_program(ctx["program_a"])}
        names_b = {p.name for p in repo.domain.list_projects_by_program(ctx["program_b"])}
        assert names_a == {"Projeto A1"}
        assert names_b == {"Projeto B1"}
