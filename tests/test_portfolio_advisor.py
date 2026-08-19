"""Portfolio Advisor (Wave 5, 5th Advisor, first Classe B), per
`TECHNICAL-DESIGN-PORTFOLIO-ADVISOR.md`.

Proves, against the real `PortfolioEvidenceAssembler`/`PortfolioAdvisorAgent`
(never fake test doubles for the components under test), the end-to-end
chain: Portfolio -> Program -> Project -> `AnalysisRecord` (kind="status")
-> `AdvisorFramework.run()` (byte-for-byte unchanged) -> Portfolio Advisor
-> LLM -> Response.

Covers the 11 mandatory scenarios (A-K) required by "Founder Decision --
Technical Design do Portfolio Advisor" (item 6), using real PostgreSQL and
real `DomainService` (Wave 2).
"""
import json
from datetime import datetime, timezone

import pytest

from src.agents.portfolio_advisor.agent import PortfolioAdvisorAgent
from src.agents.portfolio_advisor.evidence_assembler import PortfolioEvidenceAssembler
from src.database.repository import AnalysisRecord, AnalysisRepository
from src.prompts.registry import PromptRegistry
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.recommendation_engine import RecommendationEngine
from src.services.ai_foundation.types import SessionContext
from src.services.domain_service import DomainService
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


class _NoOpEventPublisher:
    def publish(self, event_type, payload, organization_id, correlation_id, origin):
        return None


class _ScriptedProvider:
    def __init__(self, answer: str, cited_analysis_ids: list[int]):
        self.answer = answer
        self.cited_analysis_ids = cited_analysis_ids
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return json.dumps({"answer": self.answer, "cited_analysis_ids": self.cited_analysis_ids})


class _ExplodingProvider:
    def generate(self, prompt: str) -> str:
        raise AssertionError("LLM must not be called when there is nothing to synthesize")


@pytest.fixture()
def repo():
    with temp_database_url("portfolio_advisor") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def domain_service(repo):
    return DomainService(repository=repo, publisher=_NoOpEventPublisher())


def _framework(repo, provider):
    # rag_pipeline=None throughout this file, deliberately: the Portfolio
    # Advisor never consults RAG. Any accidental call would raise
    # AttributeError immediately, so a passing test proves its absence.
    return AdvisorFramework(
        repository=repo,
        prompt_registry=PromptRegistry(base_path="src/agents"),
        llm_provider=provider,
        rag_pipeline=None,
    )


def _session(repo, org_id: int) -> SessionContext:
    user_id = repo.enterprise.create_user(org_id, "founder@stratech.example", "Founder")
    return SessionContext(organization_id=org_id, user_id=user_id, session_id="s-1")


def _save_status_at(repo, org_id: int, project_name: str, health_status: str, created_at: datetime) -> int:
    analysis_id = repo.save_analysis(
        kind="status",
        payload={
            "model_output": {
                "structured": True,
                "health_status": health_status,
                "key_findings": [f"finding-{health_status}"],
                "recommendations": [f"recommendation-{health_status}"],
            }
        },
        organization_id=org_id,
        project_name=project_name,
    )
    with repo.SessionLocal() as session:
        record = session.get(AnalysisRecord, analysis_id)
        record.created_at = created_at
        session.commit()
    return analysis_id


def _build_portfolio(domain_service, org_id: int, actor_id: int, code: str = "PF-A"):
    portfolio = domain_service.create_portfolio(org_id, "Cloud Modernization", code, actor_id, correlation_id=CORRELATION_ID)
    program = domain_service.create_program(org_id, portfolio.id, "Infra", "INFRA", actor_id, correlation_id=CORRELATION_ID)
    return portfolio, program


def _create_project(domain_service, org_id: int, program_id: int, name: str, actor_id: int):
    return domain_service.create_project(org_id, program_id, name, actor_id, correlation_id=CORRELATION_ID)


class TestScenarioA_CoberturaCompleta:
    def test_all_projects_have_evidence(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, program = _build_portfolio(domain_service, org_id, actor_id)
        aurora = _create_project(domain_service, org_id, program.id, "Aurora", actor_id)
        boreal = _create_project(domain_service, org_id, program.id, "Boreal", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
        _save_status_at(repo, org_id, "Boreal", "red", datetime(2026, 8, 1, tzinfo=timezone.utc))

        framework = _framework(repo, None)
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)

        assert result.total_projects == 2
        assert result.projects_with_evidence == 2
        assert len(result.evidence) == 2
        project_ids = {item.metadata["project_id"] for item in result.evidence}
        assert project_ids == {aurora.id, boreal.id}


class TestScenarioB_CoberturaParcial:
    def test_some_projects_lack_evidence(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, program = _build_portfolio(domain_service, org_id, actor_id)
        _create_project(domain_service, org_id, program.id, "Aurora", actor_id)
        _create_project(domain_service, org_id, program.id, "Boreal", actor_id)
        _create_project(domain_service, org_id, program.id, "Castor", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
        # Boreal and Castor never get a status AnalysisRecord.

        framework = _framework(repo, None)
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)

        assert result.total_projects == 3
        assert result.projects_with_evidence == 1
        assert len(result.evidence) == 1


class TestScenarioC_CoberturaZero:
    def test_no_project_has_a_status_analysis_means_no_llm_call(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, program = _build_portfolio(domain_service, org_id, actor_id)
        _create_project(domain_service, org_id, program.id, "Aurora", actor_id)

        framework = _framework(repo, _ExplodingProvider())
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)
        assert result.evidence == []

        agent = PortfolioAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "Como esta o portfolio?",
            result.evidence,
            no_evidence_answer="Nenhuma análise de status registrada para os projetos deste portfólio.",
        )

        assert explanation.recommendation.answer == "Nenhuma análise de status registrada para os projetos deste portfólio."
        assert explanation.recommendation.cited_evidence == []


class TestScenarioD_PortfolioSemProgramsOuProjects:
    def test_portfolio_without_programs(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio = domain_service.create_portfolio(org_id, "Empty Portfolio", "PF-EMPTY", actor_id, correlation_id=CORRELATION_ID)

        framework = _framework(repo, _ExplodingProvider())
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)

        assert result is not None
        assert result.evidence == []
        assert result.total_projects == 0
        assert result.projects_with_evidence == 0

    def test_portfolio_with_a_program_but_no_projects(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, _program = _build_portfolio(domain_service, org_id, actor_id)

        framework = _framework(repo, _ExplodingProvider())
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)

        assert result.evidence == []
        assert result.total_projects == 0


class TestScenarioE_PortfolioInexistente:
    def test_assemble_returns_none_for_a_nonexistent_portfolio_id(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")

        framework = _framework(repo, _ExplodingProvider())
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, 999999)

        assert result is None


class TestScenarioF_PortfolioDeOutraOrganizacao:
    def test_assemble_returns_none_when_portfolio_belongs_to_another_organization(self, repo, domain_service):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        actor_b = repo.enterprise.create_user(org_b, "actor@example.com", "Actor")
        portfolio_b = domain_service.create_portfolio(org_b, "Org B Portfolio", "PF-B", actor_b, correlation_id=CORRELATION_ID)

        framework = _framework(repo, _ExplodingProvider())
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_a, portfolio_b.id)

        assert result is None


class TestScenarioG_ApenasOStatusMaisRecente:
    def test_each_project_contributes_only_its_most_recent_status(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, program = _build_portfolio(domain_service, org_id, actor_id)
        _create_project(domain_service, org_id, program.id, "Aurora", actor_id)
        old_id = _save_status_at(repo, org_id, "Aurora", "red", datetime(2026, 7, 1, tzinfo=timezone.utc))
        recent_id = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))

        framework = _framework(repo, None)
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)

        assert len(result.evidence) == 1
        assert result.evidence[0].source_id == recent_id
        assert result.evidence[0].source_id != old_id
        assert result.evidence[0].content["health_status"] == "green"


class TestScenarioH_HistoricoNaoPesaMais:
    def test_a_project_with_many_records_contributes_the_same_single_evidence_as_one_with_a_single_record(
        self, repo, domain_service
    ):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, program = _build_portfolio(domain_service, org_id, actor_id)
        many = _create_project(domain_service, org_id, program.id, "Aurora", actor_id)
        single = _create_project(domain_service, org_id, program.id, "Boreal", actor_id)
        _save_status_at(repo, org_id, "Aurora", "red", datetime(2026, 7, 1, tzinfo=timezone.utc))
        _save_status_at(repo, org_id, "Aurora", "yellow", datetime(2026, 7, 20, tzinfo=timezone.utc))
        _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
        _save_status_at(repo, org_id, "Boreal", "yellow", datetime(2026, 8, 1, tzinfo=timezone.utc))

        framework = _framework(repo, None)
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)

        # Exactly one Evidence per project, regardless of history depth --
        # a 3-record project never outweighs a 1-record project.
        by_project = {item.metadata["project_id"]: item for item in result.evidence}
        assert set(by_project) == {many.id, single.id}
        assert len(result.evidence) == 2


class TestScenarioI_OrdemNaoImplicaPrioridade:
    def test_citation_filtering_is_position_independent(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, program = _build_portfolio(domain_service, org_id, actor_id)
        _create_project(domain_service, org_id, program.id, "Aurora", actor_id)
        _create_project(domain_service, org_id, program.id, "Boreal", actor_id)
        id_a = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
        id_b = _save_status_at(repo, org_id, "Boreal", "red", datetime(2026, 8, 1, tzinfo=timezone.utc))

        framework = _framework(repo, None)
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)

        forward = result.evidence
        reversed_order = list(reversed(result.evidence))

        # RecommendationEngine.build() filters citations purely by
        # source_id membership -- never by list position. Same cited_ids
        # against the evidence in either order must survive identically.
        rec_forward = RecommendationEngine.build("answer", [id_a, id_b], forward)
        rec_reversed = RecommendationEngine.build("answer", [id_a, id_b], reversed_order)

        assert {e.source_id for e in rec_forward.cited_evidence} == {id_a, id_b}
        assert {e.source_id for e in rec_reversed.cited_evidence} == {id_a, id_b}


class TestScenarioJ_CitedProjectsApenasOsCitados:
    def test_only_projects_the_model_actually_cited_are_returned(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, program = _build_portfolio(domain_service, org_id, actor_id)
        _create_project(domain_service, org_id, program.id, "Aurora", actor_id)
        _create_project(domain_service, org_id, program.id, "Boreal", actor_id)
        id_a = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
        _save_status_at(repo, org_id, "Boreal", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))

        framework_for_assembly = _framework(repo, None)
        assembler = PortfolioEvidenceAssembler(domain_service, framework_for_assembly)
        result = assembler.assemble(org_id, portfolio.id)
        assert len(result.evidence) == 2

        # Scripted model cites only Aurora, deliberately ignoring Boreal.
        provider = _ScriptedProvider(answer="Aurora esta green.", cited_analysis_ids=[id_a])
        framework = _framework(repo, provider)
        agent = PortfolioAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "Como esta Aurora?", result.evidence)

        assert [e.source_id for e in explanation.recommendation.cited_evidence] == [id_a]


class TestScenarioK_NenhumaChamadaAoLlmSemEvidencia:
    def test_no_llm_call_when_evidence_is_empty(self, repo, domain_service):
        org_id = repo.enterprise.create_organization("Org A")
        actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
        portfolio, _program = _build_portfolio(domain_service, org_id, actor_id)

        framework = _framework(repo, _ExplodingProvider())
        assembler = PortfolioEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id, portfolio.id)
        assert result.evidence == []

        agent = PortfolioAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "Como esta o portfolio?",
            result.evidence,
            no_evidence_answer="Nenhuma análise de status registrada para os projetos deste portfólio.",
        )
        assert explanation.recommendation.cited_evidence == []
