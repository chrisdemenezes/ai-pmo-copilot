"""Strategy Advisor (Wave 5, fourth Classe B Advisor, eighth and last
Advisor of the Wave), per `TECHNICAL-DESIGN-STRATEGY-ADVISOR.md`.

Proves, against the real `StrategyEvidenceAssembler`/`StrategyAdvisorAgent`
(never fake test doubles for the components under test), the end-to-end
chain: Organization -> Portfolio/Program/Project (declared objectives) +
`AnalysisRecord`s (kind="status"/"risk") -> `AdvisorFramework.run()`
(byte-for-byte unchanged) -> Strategy Advisor -> LLM -> Response, using
real PostgreSQL and real `DomainService` (Wave 2).

Covers scenarios H-N, P, Q, T, U (§12/§12.1) -- most critically P, the
end-to-end citation test that would have caught the harmonized bug (D-129):
a `declared_strategy` citation only resolves correctly if the synthetic
`source_id` genuinely round-trips through `RecommendationEngine.build()`.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.agents.strategy_advisor.agent import StrategyAdvisorAgent
from src.agents.strategy_advisor.evidence_assembler import (
    StrategyEvidenceAssembler,
    _synthetic_source_id,
)
from src.api.routes.intelligence import _strategy_cited_evidence
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
        raise AssertionError("Strategy Advisor must never consult RAG this Epic -- declared strategy + status/risk only")


@pytest.fixture()
def repo():
    with temp_database_url("strategy_advisor") as database_url:
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
        kind=kind, payload={"model_output": model_output}, organization_id=org_id, project_name=project_name
    )
    with repo.SessionLocal() as session:
        record = session.get(AnalysisRecord, analysis_id)
        record.created_at = created_at
        session.commit()
    return analysis_id


def _save_status_at(repo, org_id, project_name, health_status, created_at) -> int:
    return _save_analysis_at(
        repo, org_id, project_name, "status",
        {"structured": True, "health_status": health_status, "key_findings": [], "recommendations": []},
        created_at,
    )


def _save_risk_at(repo, org_id, project_name, description, created_at) -> int:
    return _save_analysis_at(
        repo, org_id, project_name, "risk",
        {"structured": True, "risks": [{"description": description, "probability": "medium", "impact": "high", "mitigation": "m"}], "escalation_recommendation": None},
        created_at,
    )


def _org(repo, name="Org A") -> int:
    return repo.enterprise.create_organization(name)


def _actor(repo, org_id) -> int:
    return repo.enterprise.create_user(org_id, f"actor-{org_id}@example.com", "Actor")


def _portfolio(domain_service, org_id, actor_id, code, objective=None):
    return domain_service.create_portfolio(
        org_id, f"Portfolio {code}", code, actor_id, correlation_id=CORRELATION_ID, strategic_objective=objective
    )


def _program(domain_service, org_id, actor_id, portfolio_id, code, objective=None):
    return domain_service.create_program(
        org_id, portfolio_id, f"Program {code}", code, actor_id, correlation_id=CORRELATION_ID, objective=objective
    )


def _project(domain_service, org_id, actor_id, program_id, name, objective=None):
    return domain_service.create_project(
        org_id, program_id, name, actor_id, correlation_id=CORRELATION_ID, objective=objective
    )


class TestScenarioH_AusenciaTotal:
    def test_no_evidence_at_all_means_no_llm_call(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A")
        program = _program(domain_service, org_id, actor_id, portfolio.id, "PRG-A")
        _project(domain_service, org_id, actor_id, program.id, "Aurora")
        # No declared objectives anywhere, no execution evidence.

        framework = _framework(repo, _ExplodingProvider())
        assembler = StrategyEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)
        assert result.evidence == []

        agent = StrategyAdvisorAgent(framework)
        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "A execucao continua alinhada com a estrategia?",
            result.evidence,
            no_evidence_answer="Nenhum objetivo declarado ou evidência de execução comparável registrada para esta organização.",
        )

        assert explanation.recommendation.answer == (
            "Nenhum objetivo declarado ou evidência de execução comparável registrada para esta organização."
        )
        assert explanation.recommendation.cited_evidence == []


class TestScenarioI_CoberturaParcial:
    def test_partial_coverage_still_permits_synthesis(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A")
        program = _program(domain_service, org_id, actor_id, portfolio.id, "PRG-A")
        _project(domain_service, org_id, actor_id, program.id, "Aurora", objective="Migrar workloads")
        _project(domain_service, org_id, actor_id, program.id, "Boreal")  # no objective, no execution

        framework = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        assert result.projects_with_strategy_without_execution == 1
        assert len(result.evidence) == 1  # only Aurora's declared_strategy


class TestScenarioJ_ColisaoPotencial:
    def test_synthetic_and_real_ids_coexist_without_collision(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A", objective="Expandir para APAC")
        program = _program(domain_service, org_id, actor_id, portfolio.id, "PRG-A")
        _project(domain_service, org_id, actor_id, program.id, "Aurora")
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        source_ids = [item.source_id for item in result.evidence]
        assert len(source_ids) == len(set(source_ids))  # every source_id is unique
        assert any(sid < 0 for sid in source_ids)  # synthetic declared_strategy token
        assert any(sid > 0 for sid in source_ids)  # real AnalysisRecord.id


class TestScenarioK_PropriedadeDeRoundTrip:
    def test_synthetic_source_id_is_stable_and_deterministic_for_real_ids(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A", objective="Expandir para APAC")

        framework = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        declared = result.evidence[0]
        assert declared.source_id == _synthetic_source_id("portfolio", portfolio.id)


class TestScenarioL_AusenciaDeVazamentoNoMapper:
    def test_synthetic_source_id_never_reaches_strategy_cited_evidence(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A", objective="Expandir para APAC")

        framework = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        cited = _strategy_cited_evidence(result.evidence[0])
        assert cited.source_id == portfolio.id
        assert cited.source_id != result.evidence[0].source_id
        assert cited.created_at is None


class TestScenarioM_DuasCitacoesMesmaUnidadeKindsDiferentes:
    def test_declared_strategy_and_status_of_same_project_remain_distinguishable(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A")
        program = _program(domain_service, org_id, actor_id, portfolio.id, "PRG-A")
        project = _project(domain_service, org_id, actor_id, program.id, "Aurora", objective="Migrar workloads")
        status_id = _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        framework_for_assembly = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework_for_assembly)
        result = assembler.assemble(org_id)
        assert len(result.evidence) == 2

        declared_source_id = _synthetic_source_id("project", project.id)
        provider = _ScriptedProvider(
            answer="Aurora esta alinhada e com status verde.",
            cited_analysis_ids=[declared_source_id, status_id],
        )
        framework = _framework(repo, provider)
        agent = StrategyAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "Aurora esta alinhada?", result.evidence)

        cited_kinds = {(e.source_id, e.metadata["kind"]) for e in explanation.recommendation.cited_evidence}
        assert cited_kinds == {(declared_source_id, "declared_strategy"), (status_id, "status")}


class TestScenarioN_IsolamentoOrganizacional:
    def test_other_organizations_never_leak_in(self, repo, domain_service):
        org_a = _org(repo, "Org A")
        org_b = _org(repo, "Org B")
        actor_a = _actor(repo, org_a)
        actor_b = _actor(repo, org_b)
        portfolio_a = _portfolio(domain_service, org_a, actor_a, "PF-A", objective="Objetivo A")
        portfolio_b = _portfolio(domain_service, org_b, actor_b, "PF-B", objective="Objetivo B")

        framework = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_a)

        assert result.portfolios_total == 1
        assert result.evidence[0].metadata["real_entity_id"] == portfolio_a.id
        assert all(e.metadata["real_entity_id"] != portfolio_b.id for e in result.evidence)


class TestScenarioP_CitacaoRealDeDeclaredStrategyPontaAPonta:
    def test_declared_strategy_citation_resolves_end_to_end(self, repo, domain_service):
        # The exact scenario that would have caught the original harmonized
        # bug: the model cites the synthetic source_id it was given, and
        # RecommendationEngine.build() (byte-for-byte unchanged) must
        # correctly resolve it back to the declared_strategy Evidence item.
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A", objective="Expandir para APAC")

        framework_for_assembly = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework_for_assembly)
        result = assembler.assemble(org_id)
        assert len(result.evidence) == 1
        declared = result.evidence[0]

        provider = _ScriptedProvider(
            answer="O Portfolio Atlas declara expansao para APAC.",
            cited_analysis_ids=[declared.source_id],
        )
        framework = _framework(repo, provider)
        agent = StrategyAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "Qual a estrategia do portfolio?", result.evidence)

        assert len(explanation.recommendation.cited_evidence) == 1
        resolved = explanation.recommendation.cited_evidence[0]
        assert resolved.source_id == declared.source_id
        assert resolved.metadata["real_entity_id"] == portfolio.id
        assert resolved.metadata["kind"] == "declared_strategy"


class TestScenarioQ_ConversaoDoTokenSinteticoParaIdentidadeReal:
    def test_mapper_converts_synthetic_token_to_real_identity(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A", objective="Expandir para APAC")

        framework_for_assembly = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework_for_assembly)
        result = assembler.assemble(org_id)
        declared = result.evidence[0]

        provider = _ScriptedProvider(answer="ok", cited_analysis_ids=[declared.source_id])
        framework = _framework(repo, provider)
        agent = StrategyAdvisorAgent(framework)
        explanation = framework.run(agent, _session(repo, org_id), "?", result.evidence)

        cited = _strategy_cited_evidence(explanation.recommendation.cited_evidence[0])
        assert cited.entity_id == portfolio.id
        assert cited.source_id == portfolio.id
        assert cited.level == "portfolio"
        assert cited.created_at is None


class TestScenarioT_EstrategiaEExecucaoCitadasSimultaneamente:
    def test_declared_strategy_and_execution_cited_in_the_same_call_without_collision(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A")
        program = _program(domain_service, org_id, actor_id, portfolio.id, "PRG-A")
        project = _project(domain_service, org_id, actor_id, program.id, "Aurora", objective="Migrar workloads")
        risk_id = _save_risk_at(repo, org_id, "Aurora", "atraso de fornecedor", NOW - timedelta(days=1))

        framework_for_assembly = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework_for_assembly)
        result = assembler.assemble(org_id)
        assert len(result.evidence) == 2

        declared_source_id = _synthetic_source_id("project", project.id)
        provider = _ScriptedProvider(
            answer="Aurora esta alinhada, mas ha um risco de fornecedor.",
            cited_analysis_ids=[declared_source_id, risk_id],
        )
        framework = _framework(repo, provider)
        agent = StrategyAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "?", result.evidence)

        assert len(explanation.recommendation.cited_evidence) == 2
        cited_ids = {e.source_id for e in explanation.recommendation.cited_evidence}
        assert cited_ids == {declared_source_id, risk_id}


class TestScenarioU_DescarteDeTokenInventado:
    def test_a_synthetic_id_never_emitted_by_the_assembler_is_never_cited(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        _portfolio(domain_service, org_id, actor_id, "PF-A", objective="Expandir para APAC")

        framework_for_assembly = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework_for_assembly)
        result = assembler.assemble(org_id)
        declared = result.evidence[0]

        never_emitted = _synthetic_source_id("project", 999_999)
        provider = _ScriptedProvider(answer="ok", cited_analysis_ids=[declared.source_id, never_emitted])
        framework = _framework(repo, provider)
        agent = StrategyAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "?", result.evidence)

        cited_ids = {e.source_id for e in explanation.recommendation.cited_evidence}
        assert cited_ids == {declared.source_id}  # invented token silently discarded


class TestCoverageInvariants:
    def test_coverage_invariants_hold_across_a_mixed_organization(self, repo, domain_service):
        org_id = _org(repo)
        actor_id = _actor(repo, org_id)
        portfolio = _portfolio(domain_service, org_id, actor_id, "PF-A", objective="Expandir para APAC")
        program = _program(domain_service, org_id, actor_id, portfolio.id, "PRG-A", objective="Consolidar dados")
        _project(domain_service, org_id, actor_id, program.id, "Aurora", objective="Migrar workloads")
        _project(domain_service, org_id, actor_id, program.id, "Boreal")
        _save_status_at(repo, org_id, "Aurora", "green", NOW - timedelta(days=1))

        framework = _framework(repo, None)
        assembler = StrategyEvidenceAssembler(domain_service, framework)
        result = assembler.assemble(org_id)

        for prefix in ("portfolios", "programs", "projects"):
            total = getattr(result, f"{prefix}_total")
            with_ds = getattr(result, f"{prefix}_with_declared_strategy")
            without_ds = getattr(result, f"{prefix}_without_declared_strategy")
            comparable = getattr(result, f"{prefix}_comparable")
            with_exec = getattr(result, f"{prefix}_with_execution_evidence")
            with_ds_without_exec = getattr(result, f"{prefix}_with_strategy_without_execution")
            assert with_ds + without_ds == total
            assert comparable + with_ds_without_exec == with_ds
            assert comparable <= min(with_ds, with_exec)
