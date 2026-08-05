"""PMO Advisor (Wave 5, 6th Advisor, second Classe B), per
`TECHNICAL-DESIGN-PMO-ADVISOR.md`.

Proves, against the real `PMOEvidenceAssembler`/`PMOAdvisorAgent` (never
fake test doubles for the components under test), the end-to-end chain:
Organization -> Project -> `AnalysisRecord` (kind="status") ->
`AdvisorFramework.run()` (byte-for-byte unchanged) -> PMO Advisor -> LLM ->
Response.

Covers the 13 mandatory scenarios (A-M) plus the additional proofs required
by "Founder Decision -- Technical Design do PMO Advisor" (item 8), using
real PostgreSQL and real `DomainService` (Wave 2).
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.agents.pmo_advisor.agent import PMOAdvisorAgent
from src.agents.pmo_advisor.evidence_assembler import PMOEvidenceAssembler
from src.database.repository import AnalysisRecord, AnalysisRepository
from src.prompts.registry import PromptRegistry
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import SessionContext
from src.services.domain_service import DomainService
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"
NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


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


class _ExplodingRagPipeline:
    def retrieve(self, organization_id, query, top_k=5):
        raise AssertionError("PMO Advisor must never consult RAG -- kind=status only")


@pytest.fixture()
def repo():
    with temp_database_url("pmo_advisor") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def domain_service(repo):
    return DomainService(repository=repo, publisher=_NoOpEventPublisher())


def _framework(repo, provider, rag_pipeline=None):
    if rag_pipeline is None:
        rag_pipeline = _ExplodingRagPipeline()
    return AdvisorFramework(
        repository=repo,
        prompt_registry=PromptRegistry(base_path="src/agents"),
        llm_provider=provider,
        rag_pipeline=rag_pipeline,
    )


def _session(repo, org_id: int) -> SessionContext:
    user_id = repo.enterprise.create_user(org_id, "founder@stratech.example", "Founder")
    return SessionContext(organization_id=org_id, user_id=user_id, session_id="s-1")


def _save_analysis_at(repo, org_id, project_name, kind, model_output, created_at) -> int:
    analysis_id = repo.save_analysis(
        kind=kind,
        payload={"model_output": model_output},
        organization_id=org_id,
        project_name=project_name,
    )
    with repo.SessionLocal() as session:
        record = session.get(AnalysisRecord, analysis_id)
        record.created_at = created_at
        session.commit()
    return analysis_id


def _save_status_at(repo, org_id: int, project_name: str, health_status: str, created_at: datetime) -> int:
    return _save_analysis_at(
        repo,
        org_id,
        project_name,
        "status",
        {
            "structured": True,
            "health_status": health_status,
            "key_findings": [f"finding-{health_status}"],
            "recommendations": [f"recommendation-{health_status}"],
        },
        created_at,
    )


def _org_with_project(domain_service, repo, name="Org A") -> tuple[int, int]:
    org_id = repo.enterprise.create_organization(name)
    actor_id = repo.enterprise.create_user(org_id, "actor@example.com", "Actor")
    portfolio = domain_service.create_portfolio(org_id, "Portfolio", "PF-A", actor_id, correlation_id=CORRELATION_ID)
    program = domain_service.create_program(org_id, portfolio.id, "Program", "PRG", actor_id, correlation_id=CORRELATION_ID)
    return org_id, program.id


def _create_project(domain_service, org_id, program_id, name, actor_id):
    return domain_service.create_project(org_id, program_id, name, actor_id, correlation_id=CORRELATION_ID)


class TestScenarioA_TrezeDiasCurrent:
    def test_thirteen_days_is_current(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=13))

        framework = _framework(repo, None)
        with patch("src.agents.pmo_advisor.evidence_assembler.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            assembler = PMOEvidenceAssembler(domain_service, framework)
            result = assembler.assemble(org_id)

        assert result.evidence[0].metadata["staleness_days"] == 13
        assert result.evidence[0].metadata["is_stale"] is False
        assert result.projects_current == 1
        assert result.projects_stale == 0


class TestScenarioB_QuatorzeDiasStale:
    def test_fourteen_days_is_stale(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=14))

        framework = _framework(repo, None)
        with patch("src.agents.pmo_advisor.evidence_assembler.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            assembler = PMOEvidenceAssembler(domain_service, framework)
            result = assembler.assemble(org_id)

        assert result.evidence[0].metadata["staleness_days"] == 14
        assert result.evidence[0].metadata["is_stale"] is True
        assert result.projects_stale == 1
        assert result.projects_current == 0


class TestScenarioC_QuinzeDiasStale:
    def test_fifteen_days_is_stale(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=15))

        framework = _framework(repo, None)
        with patch("src.agents.pmo_advisor.evidence_assembler.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            assembler = PMOEvidenceAssembler(domain_service, framework)
            result = assembler.assemble(org_id)

        assert result.evidence[0].metadata["staleness_days"] == 15
        assert result.evidence[0].metadata["is_stale"] is True


class TestScenarioD_ProjectSemStatus:
    def test_project_without_status_is_never_stale(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)

        framework = _framework(repo, _ExplodingProvider())
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.total_projects == 1
        assert result.projects_with_status == 0
        assert result.projects_without_status == 1
        assert result.projects_stale == 0
        assert result.projects_current == 0
        assert result.evidence == []


class TestScenarioE_MaisDeCincoRegistros:
    def test_project_with_more_than_five_records_is_capped_at_five(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        ids = []
        for i in range(7):
            ids.append(_save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=i)))

        framework = _framework(repo, None)
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert len(result.evidence) == 5
        # ids was built from newest (offset 0 days) to oldest (offset 6
        # days) -- AnalysisRepository.list_analyses() already returns that
        # same newest-first order, so the cap keeps exactly the first 5.
        assert [item.source_id for item in result.evidence] == ids[:5]


class TestScenarioF_MenosDeCincoRegistros:
    def test_project_with_fewer_than_five_records_applies_no_cut(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_status_at(repo, org_id, "Aurora", "red", NOW - timedelta(days=2))
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert len(result.evidence) == 2


class TestScenarioG_CoberturaCompleta:
    def test_all_projects_have_status(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        aurora = _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        boreal = _create_project(domain_service, org_id, program_id, "Boreal", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_status_at(repo, org_id, "Boreal", "red", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.total_projects == 2
        assert result.projects_with_status == 2
        assert result.projects_without_status == 0
        project_ids = {item.metadata["project_id"] for item in result.evidence}
        assert project_ids == {aurora.id, boreal.id}


class TestScenarioH_CoberturaParcial:
    def test_some_projects_lack_status(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _create_project(domain_service, org_id, program_id, "Boreal", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.total_projects == 2
        assert result.projects_with_status == 1
        assert result.projects_without_status == 1


class TestScenarioI_CoberturaZero:
    def test_no_status_at_all_means_no_llm_call(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)

        framework = _framework(repo, _ExplodingProvider())
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)
        assert result.evidence == []

        agent = PMOAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "Ha algum padrao de atraso?",
            result.evidence,
            no_evidence_answer="Nenhuma análise de status registrada para os projetos desta organização.",
        )

        assert explanation.recommendation.answer == "Nenhuma análise de status registrada para os projetos desta organização."
        assert explanation.recommendation.cited_evidence == []


class TestScenarioJ_InvariantesDeContagem:
    def test_coverage_invariants_hold_across_a_mixed_organization(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)  # current
        _create_project(domain_service, org_id, program_id, "Boreal", actor_id)  # stale
        _create_project(domain_service, org_id, program_id, "Castor", actor_id)  # no status
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_status_at(repo, org_id, "Boreal", "red", NOW - timedelta(days=20))

        framework = _framework(repo, None)
        with patch("src.agents.pmo_advisor.evidence_assembler.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            assembler = PMOEvidenceAssembler(domain_service, framework)
            result = assembler.assemble(org_id)

        assert result.total_projects == 3
        assert result.projects_with_status + result.projects_without_status == result.total_projects
        assert result.projects_stale + result.projects_current == result.projects_with_status
        assert result.projects_without_status == 1
        assert result.projects_stale == 1
        assert result.projects_current == 1


class TestScenarioK_IsolamentoOrganizacional:
    def test_projects_of_another_organization_never_leak_in(self, repo, domain_service):
        org_a, program_a = _org_with_project(domain_service, repo, "Org A")
        org_b, program_b = _org_with_project(domain_service, repo, "Org B")
        actor_a = repo.enterprise.create_user(org_a, "a2@example.com", "Actor2")
        actor_b = repo.enterprise.create_user(org_b, "b2@example.com", "Actor2B")
        _create_project(domain_service, org_a, program_a, "Aurora", actor_a)
        _create_project(domain_service, org_b, program_b, "Nebula", actor_b)
        _save_status_at(repo, org_a, "Aurora", "green", NOW - timedelta(days=1))
        _save_status_at(repo, org_b, "Nebula", "red", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_a)

        assert result.total_projects == 1
        assert [item.metadata["project_name"] for item in result.evidence] == ["Aurora"]


class TestScenarioL_NenhumaChamadaAoLlmSemEvidencia:
    def test_no_llm_call_when_evidence_is_empty(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        # No projects at all -- organization is entirely empty.

        framework = _framework(repo, _ExplodingProvider())
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)
        assert result.evidence == []

        agent = PMOAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "Ha algum padrao de atraso?",
            result.evidence,
            no_evidence_answer="Nenhuma análise de status registrada para os projetos desta organização.",
        )
        assert explanation.recommendation.cited_evidence == []


class TestScenarioM_RastreabilidadeAteProjectEAnalysisRecord:
    def test_repeated_citations_of_the_same_project_remain_distinguishable(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        id_old = _save_status_at(repo, org_id, "Aurora", "red", NOW - timedelta(days=5))
        id_new = _save_status_at(repo, org_id, "Aurora", "yellow", NOW - timedelta(days=1))

        framework_for_assembly = _framework(repo, None)
        assembler = PMOEvidenceAssembler(domain_service, framework_for_assembly)
        result = assembler.assemble(org_id)
        assert len(result.evidence) == 2

        # Model deliberately cites BOTH records of the same Project.
        provider = _ScriptedProvider(
            answer="Aurora oscilou de red para yellow.", cited_analysis_ids=[id_old, id_new]
        )
        framework = _framework(repo, provider)
        agent = PMOAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "Como Aurora evoluiu?", result.evidence)

        cited_ids = [e.source_id for e in explanation.recommendation.cited_evidence]
        # Both citations survive, each unambiguously traceable to its own
        # AnalysisRecord id -- never collapsed into one.
        assert sorted(cited_ids) == sorted([id_old, id_new])
        assert len(set(cited_ids)) == 2


class TestSingleReferenceTimeCapture:
    def test_reference_time_is_captured_exactly_once_per_assemble_call(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _create_project(domain_service, org_id, program_id, "Boreal", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_status_at(repo, org_id, "Boreal", "red", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        with patch("src.agents.pmo_advisor.evidence_assembler.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            assembler = PMOEvidenceAssembler(domain_service, framework)
            assembler.assemble(org_id)

            assert mock_dt.now.call_count == 1


class TestNoSecondSource:
    def test_meeting_and_risk_analyses_never_contribute_evidence(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        status_id = _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_analysis_at(
            repo, org_id, "Aurora", "meeting",
            {"structured": True, "summary": "s", "decisions": [], "action_items": [], "issues": [], "dependencies": []},
            NOW - timedelta(days=1),
        )
        _save_analysis_at(
            repo, org_id, "Aurora", "risk",
            {"structured": True, "risks": [], "escalation_recommendation": None},
            NOW - timedelta(days=1),
        )

        framework = _framework(repo, None)
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert len(result.evidence) == 1
        assert result.evidence[0].source_id == status_id
        assert result.evidence[0].metadata["kind"] == "status"

    def test_rag_is_never_consulted(self, repo, domain_service):
        # _framework() defaults to _ExplodingRagPipeline() -- any accidental
        # gather_rag_context() call anywhere in this flow raises immediately.
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        provider = _ScriptedProvider(answer="Aurora esta green.", cited_analysis_ids=[])
        framework = _framework(repo, provider)
        assembler = PMOEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        agent = PMOAdvisorAgent(framework)
        framework.run(agent, _session(repo, org_id), "Como esta Aurora?", result.evidence)
        # No AssertionError raised -> RAG was never touched.
