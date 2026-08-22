"""Executive Advisor (Wave 5, 7th Advisor, third Classe B), per
`TECHNICAL-DESIGN-EXECUTIVE-ADVISOR.md`.

Proves, against the real `ExecutiveEvidenceAssembler`/`ExecutiveAdvisorAgent`
(never fake test doubles for the components under test), the end-to-end
chain: Organization -> Project -> two `AnalysisRecord`s (kind="status" +
kind="risk") -> `AdvisorFramework.run()` (byte-for-byte unchanged) ->
Executive Advisor -> LLM -> Response.

Covers the 13 mandatory scenarios (A-M) required by "Founder Decision --
Technical Design do Executive Advisor" (item 5), using real PostgreSQL and
real `DomainService` (Wave 2).
"""
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.agents.executive_advisor.agent import ExecutiveAdvisorAgent
from src.agents.executive_advisor.evidence_assembler import ExecutiveEvidenceAssembler
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
        raise AssertionError("Executive Advisor must never consult RAG -- status/risk only")


@pytest.fixture()
def repo():
    with temp_database_url("executive_advisor") as database_url:
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


def _save_risk_at(repo, org_id: int, project_name: str, description: str, created_at: datetime) -> int:
    return _save_analysis_at(
        repo,
        org_id,
        project_name,
        "risk",
        {
            "structured": True,
            "risks": [{"description": description, "probability": "medium", "impact": "high", "mitigation": "m"}],
            "escalation_recommendation": None,
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


class TestScenarioA_StatusERisco:
    def test_project_with_status_and_risk(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_risk_at(repo, org_id, "Aurora", "atraso de fornecedor", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.projects_with_status_and_risk == 1
        assert len(result.evidence) == 2
        assert {item.metadata["kind"] for item in result.evidence} == {"status", "risk"}


class TestScenarioB_SomenteStatus:
    def test_project_only_with_status(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.projects_with_status == 1
        assert result.projects_with_risk == 0
        assert result.projects_with_status_and_risk == 0
        assert len(result.evidence) == 1
        assert result.evidence[0].metadata["kind"] == "status"


class TestScenarioC_SomenteRisco:
    def test_project_only_with_risk(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_risk_at(repo, org_id, "Aurora", "atraso de fornecedor", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.projects_with_status == 0
        assert result.projects_with_risk == 1
        assert result.projects_with_status_and_risk == 0
        assert len(result.evidence) == 1
        assert result.evidence[0].metadata["kind"] == "risk"


class TestScenarioD_NenhumaEvidencia:
    def test_project_without_any_evidence(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)

        framework = _framework(repo, _ExplodingProvider())
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.total_projects == 1
        assert result.projects_without_any_evidence == 1
        assert result.evidence == []


class TestScenarioE_CoberturaCompleta:
    def test_all_projects_contribute_at_least_one_source(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        aurora = _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        boreal = _create_project(domain_service, org_id, program_id, "Boreal", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_risk_at(repo, org_id, "Boreal", "risco de escopo", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.total_projects == 2
        assert result.projects_without_any_evidence == 0
        project_ids = {item.metadata["project_id"] for item in result.evidence}
        assert project_ids == {aurora.id, boreal.id}


class TestScenarioF_CoberturaParcial:
    def test_some_projects_lack_all_evidence(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _create_project(domain_service, org_id, program_id, "Boreal", actor_id)
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        # Boreal contributes nothing.

        framework = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.total_projects == 2
        assert result.projects_without_any_evidence == 1
        # Synthesis is still permitted -- caller decides via framework.run(),
        # never gated here (that gate only triggers on total absence, G).


class TestScenarioG_AusenciaTotal:
    def test_no_evidence_at_all_means_no_llm_call(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)

        framework = _framework(repo, _ExplodingProvider())
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)
        assert result.evidence == []

        agent = ExecutiveAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "O que exige atencao da lideranca agora?",
            result.evidence,
            no_evidence_answer="Nenhuma análise de status ou risco registrada para os projetos desta organização.",
        )

        assert explanation.recommendation.answer == (
            "Nenhuma análise de status ou risco registrada para os projetos desta organização."
        )
        assert explanation.recommendation.cited_evidence == []

    def test_organizational_learnings_never_substitute_for_missing_status_or_risk_evidence(
        self, repo, domain_service
    ):
        """Package M (V1 Product & Capability Completion): 3+ projects
        sharing a recurring action item are real Organizational Learnings
        (gathered separately by `ExecutiveAdvisorAgent.advise()` as
        supporting context), but the Evidence Gate keys exclusively on
        status/risk analyses -- exactly as before Package M existed. The
        LLM must still never be called."""
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        for project_name in ["Aurora", "Boreal", "Cedro"]:
            _create_project(domain_service, org_id, program_id, project_name, actor_id)
            _save_analysis_at(
                repo,
                org_id,
                project_name,
                "meeting",
                {
                    "structured": True,
                    "summary": "x",
                    "decisions": [],
                    "action_items": [{"description": "Mesma acao pendente recorrente"}],
                    "issues": [],
                    "dependencies": [],
                },
                NOW,
            )

        framework = _framework(repo, _ExplodingProvider())
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)
        assert result.evidence == []

        agent = ExecutiveAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "O que exige atencao da lideranca agora?",
            result.evidence,
            no_evidence_answer="Nenhuma análise de status ou risco registrada para os projetos desta organização.",
        )

        assert explanation.recommendation.answer == (
            "Nenhuma análise de status ou risco registrada para os projetos desta organização."
        )
        assert explanation.recommendation.cited_evidence == []


class TestTD017ExecutiveSignalsIntegration:
    """TD-017 (V1 Post-Completion Technical Closure): Executive Signals as
    supporting context, same discipline already proven for Organizational
    Learnings (Package M)."""

    def test_executive_signals_never_substitute_for_missing_status_or_risk_evidence(
        self, repo, domain_service
    ):
        """Even when a Project has a real, signal-producing EVM history
        (baseline + 2 snapshots showing a genuine CPI deterioration), the
        Evidence Gate keys exclusively on status/risk analyses -- exactly as
        before TD-017 existed. The LLM must still never be called."""
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        project = domain_service.create_project(
            org_id, program_id, "Aurora", actor_id, correlation_id=CORRELATION_ID
        )
        repo.performance.create_baseline(
            org_id,
            project.id,
            Decimal("100000.00"),
            [(date(2026, 1, 1), Decimal(0)), (date(2026, 2, 1), Decimal(50))],
        )
        repo.performance.capture_snapshot(org_id, project.id, date(2026, 1, 1), Decimal("100000.00"), 100)
        repo.performance.capture_snapshot(org_id, project.id, date(2026, 2, 1), Decimal("100000.00"), 50)

        framework = _framework(repo, _ExplodingProvider())
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)
        assert result.evidence == []

        agent = ExecutiveAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "O que exige atencao da lideranca agora?",
            result.evidence,
            no_evidence_answer="Nenhuma análise de status ou risco registrada para os projetos desta organização.",
        )

        assert explanation.recommendation.answer == (
            "Nenhuma análise de status ou risco registrada para os projetos desta organização."
        )
        assert explanation.recommendation.cited_evidence == []

    def test_executive_signal_appears_in_prompt_as_supporting_context_when_evidence_exists(
        self, repo, domain_service
    ):
        """Positive path: real status evidence exists (Evidence Gate opens),
        and a real Executive Signal is rendered into the prompt as
        `$analytics_context` -- never citable, never the sole basis, exactly
        the same discipline as `$learnings_json`."""
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        project = domain_service.create_project(
            org_id, program_id, "Aurora", actor_id, correlation_id=CORRELATION_ID
        )
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        repo.performance.create_baseline(
            org_id,
            project.id,
            Decimal("100000.00"),
            [(date(2026, 1, 1), Decimal(0)), (date(2026, 2, 1), Decimal(50))],
        )
        repo.performance.capture_snapshot(org_id, project.id, date(2026, 1, 1), Decimal("100000.00"), 100)
        repo.performance.capture_snapshot(org_id, project.id, date(2026, 2, 1), Decimal("100000.00"), 50)

        recording_provider = _ScriptedProvider("ok", [])
        framework = _framework(repo, recording_provider)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)
        assert result.evidence != []

        with patch.object(
            recording_provider, "generate", wraps=recording_provider.generate
        ) as generate_spy:
            agent = ExecutiveAdvisorAgent(framework)
            framework.run(agent, _session(repo, org_id), "O que exige atencao agora?", result.evidence)

        sent_prompt = generate_spy.call_args[0][0]
        analytics_sent = json.loads(
            sent_prompt.split("of your own:\n", 1)[1].split("\n\nRespond", 1)[0]
        )
        assert analytics_sent[0]["scope"] == "Aurora"
        assert analytics_sent[0]["signal_type"] == "cost_performance_deteriorating"


class TestScenarioH_DuasCitacoesMesmoProjectKindsDiferentes:
    def test_two_citations_of_the_same_project_with_different_kinds_remain_distinguishable(
        self, repo, domain_service
    ):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        status_id = _save_status_at(repo, org_id, "Aurora", "red", NOW - timedelta(days=1))
        risk_id = _save_risk_at(repo, org_id, "Aurora", "atraso critico", NOW - timedelta(days=1))

        framework_for_assembly = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework_for_assembly)
        result = assembler.assemble(org_id)
        assert len(result.evidence) == 2

        provider = _ScriptedProvider(
            answer="Aurora esta red e com risco critico, exige decisao agora.",
            cited_analysis_ids=[status_id, risk_id],
        )
        framework = _framework(repo, provider)
        agent = ExecutiveAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "O que exige decisao agora?", result.evidence)

        cited = {(e.source_id, e.metadata["kind"]) for e in explanation.recommendation.cited_evidence}
        assert cited == {(status_id, "status"), (risk_id, "risk")}
        assert len(explanation.recommendation.cited_evidence) == 2


class TestScenarioI_FiltroDeCitacoesEfetivamenteUtilizadas:
    def test_cited_evidence_contains_only_what_the_model_actually_cited(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _create_project(domain_service, org_id, program_id, "Boreal", actor_id)
        status_aurora = _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_status_at(repo, org_id, "Boreal", "green", NOW - timedelta(days=1))

        assembler = ExecutiveEvidenceAssembler(domain_service, _framework(repo, None))
        result = assembler.assemble(org_id)
        assert len(result.evidence) == 2

        provider = _ScriptedProvider(answer="Aurora esta green.", cited_analysis_ids=[status_aurora])
        framework = _framework(repo, provider)
        agent = ExecutiveAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "Como esta Aurora?", result.evidence)

        assert len(explanation.recommendation.cited_evidence) == 1
        assert explanation.recommendation.cited_evidence[0].source_id == status_aurora


class TestScenarioJ_IsolamentoOrganizacional:
    def test_projects_of_another_organization_never_leak_in(self, repo, domain_service):
        org_a, program_a = _org_with_project(domain_service, repo, "Org A")
        org_b, program_b = _org_with_project(domain_service, repo, "Org B")
        actor_a = repo.enterprise.create_user(org_a, "a2@example.com", "Actor2")
        actor_b = repo.enterprise.create_user(org_b, "b2@example.com", "Actor2B")
        _create_project(domain_service, org_a, program_a, "Aurora", actor_a)
        _create_project(domain_service, org_b, program_b, "Nebula", actor_b)
        _save_status_at(repo, org_a, "Aurora", "green", NOW - timedelta(days=1))
        _save_risk_at(repo, org_b, "Nebula", "risco b", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_a)

        assert result.total_projects == 1
        assert [item.metadata["project_name"] for item in result.evidence] == ["Aurora"]


class TestScenarioK_AusenciaDeRankingEmCodigo:
    def test_evidence_order_never_reflects_priority(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _create_project(domain_service, org_id, program_id, "Boreal", actor_id)
        status_boreal = _save_status_at(repo, org_id, "Boreal", "red", NOW - timedelta(days=1))
        status_aurora = _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        assembler = ExecutiveEvidenceAssembler(domain_service, _framework(repo, None))
        result = assembler.assemble(org_id)

        # The model can cite the LAST-composed project's evidence even
        # though it appears later in `result.evidence` -- filtering by
        # RecommendationEngine.build() is position-independent, proving no
        # code-level ranking or reordering ever happens.
        last_evidence = result.evidence[-1]
        provider = _ScriptedProvider(answer="ok", cited_analysis_ids=[last_evidence.source_id])
        framework = _framework(repo, provider)
        agent = ExecutiveAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "?", result.evidence)

        assert len(explanation.recommendation.cited_evidence) == 1
        assert explanation.recommendation.cited_evidence[0].source_id == last_evidence.source_id
        assert {status_boreal, status_aurora} == {item.source_id for item in result.evidence}


class TestScenarioL_AusenciaDeTendenciaHistorica:
    def test_only_the_most_recent_record_of_each_kind_reaches_the_evidence(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        _save_status_at(repo, org_id, "Aurora", "red", NOW - timedelta(days=10))
        newest_status = _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        assembler = ExecutiveEvidenceAssembler(domain_service, _framework(repo, None))
        result = assembler.assemble(org_id)

        status_items = [item for item in result.evidence if item.metadata["kind"] == "status"]
        assert len(status_items) == 1
        assert status_items[0].source_id == newest_status


class TestScenarioM_NenhumaChamadaAoLlmSemEvidencia:
    def test_no_llm_call_when_evidence_is_empty(self, repo, domain_service):
        org_id, _program_id = _org_with_project(domain_service, repo)
        # No projects at all -- organization is entirely empty.

        framework = _framework(repo, _ExplodingProvider())
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)
        assert result.evidence == []

        agent = ExecutiveAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "O que exige atencao agora?",
            result.evidence,
            no_evidence_answer="Nenhuma análise de status ou risco registrada para os projetos desta organização.",
        )
        assert explanation.recommendation.cited_evidence == []


class TestNoSecondSource:
    def test_meeting_analyses_never_contribute_evidence(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)
        status_id = _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_analysis_at(
            repo, org_id, "Aurora", "meeting",
            {"structured": True, "summary": "s", "decisions": [], "action_items": [], "issues": [], "dependencies": []},
            NOW - timedelta(days=1),
        )

        framework = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
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
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        agent = ExecutiveAdvisorAgent(framework)
        framework.run(agent, _session(repo, org_id), "Como esta Aurora?", result.evidence)
        # No AssertionError raised -> RAG was never touched.


class TestCoverageInvariants:
    def test_coverage_invariants_hold_across_a_mixed_organization(self, repo, domain_service):
        org_id, program_id = _org_with_project(domain_service, repo)
        actor_id = repo.enterprise.create_user(org_id, "a2@example.com", "Actor2")
        _create_project(domain_service, org_id, program_id, "Aurora", actor_id)  # status + risk
        _create_project(domain_service, org_id, program_id, "Boreal", actor_id)  # status only
        _create_project(domain_service, org_id, program_id, "Castor", actor_id)  # nothing
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))
        _save_risk_at(repo, org_id, "Aurora", "risco a", NOW - timedelta(days=1))
        _save_status_at(repo, org_id, "Boreal", "yellow", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = ExecutiveEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.total_projects == 3
        assert result.projects_with_status == 2
        assert result.projects_without_status == 1
        assert result.projects_with_risk == 1
        assert result.projects_without_risk == 2
        assert result.projects_with_status_and_risk == 1
        assert result.projects_without_any_evidence == 1
        assert result.projects_with_status + result.projects_without_status == result.total_projects
        assert result.projects_with_risk + result.projects_without_risk == result.total_projects
        assert result.projects_without_any_evidence == (
            result.total_projects
            - result.projects_with_status
            - result.projects_with_risk
            + result.projects_with_status_and_risk
        )
