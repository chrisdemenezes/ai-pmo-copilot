"""Enterprise Advisor Framework (Wave 3 Fase 3) -- proves the Framework's
contracts and infrastructure in isolation, against a minimal test double
(`_FakeAdvisor`), never the real `RiskAdvisorAgent` (which is migrated
only in Fase 4, per the Founder's validation condition). Runs on real
PostgreSQL (`tests/db.py`).
"""
import pytest

from src.database.repository import AnalysisRepository
from src.llm.providers.mock_provider import MockLLMProvider
from src.prompts.registry import PromptRegistry
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.advisor_framework.types import AdvisorExecutionError
from src.services.ai_foundation.types import SessionContext
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.rag_pipeline import RagPipeline
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


class _FakeAdvisor:
    """Minimal `AdvisorContract` test double -- never the real
    `RiskAdvisorAgent`, which stays untouched in this Fase."""

    name = "fake_advisor"

    def __init__(self, response: dict | None = None):
        self.response = response if response is not None else {
            "structured": True,
            "answer": "synthesized answer",
            "cited_analysis_ids": [],
        }
        self.called_with = None

    def advise(self, session, question, evidence, rag_context=None):
        self.called_with = (session, question, evidence, rag_context)
        return self.response


@pytest.fixture()
def repo():
    with temp_database_url("advisor_framework") as database_url:
        yield AnalysisRepository(database_url=database_url)


@pytest.fixture()
def knowledge_repository(repo):
    vector_repository = PgVectorRepository(repo.SessionLocal)
    event_publisher = InProcessEventPublisher(repo.SessionLocal, EventDispatcher(repo.SessionLocal))
    return KnowledgeRepository(repo.SessionLocal, MockEmbeddingProvider(), vector_repository, event_publisher)


@pytest.fixture()
def framework(repo, knowledge_repository):
    return AdvisorFramework(
        repository=repo,
        prompt_registry=PromptRegistry(base_path="src/agents"),
        llm_provider=MockLLMProvider(response="mock advisor output"),
        rag_pipeline=RagPipeline(knowledge_repository),
    )


def _session(repo, org_id: int) -> SessionContext:
    user_id = repo.enterprise.create_user(org_id, "founder@stratech.example", "Founder")
    return SessionContext(
        organization_id=org_id, user_id=user_id, session_id="s-1", project_name="Aurora"
    )


class TestRunAuditsUnconditionally:
    def test_audits_even_with_no_evidence(self, repo, framework):
        org_id = repo.enterprise.create_organization("Org A")
        advisor = _FakeAdvisor()

        framework.run(advisor, _session(repo, org_id), "any question?", evidence=[])

        logs = repo.administration.list_audit_log(org_id)
        assert any(log.action == "fake_advisor.question_asked" for log in logs)

    def test_audits_with_evidence(self, repo, framework):
        org_id = repo.enterprise.create_organization("Org A")
        analysis_id = repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        evidence = framework.gather_context(org_id, "Aurora", kind="risk")
        assert len(evidence) == 1
        assert evidence[0].source_analysis_id == analysis_id

        framework.run(_FakeAdvisor(), _session(repo, org_id), "any question?", evidence=evidence)

        logs = repo.administration.list_audit_log(org_id)
        assert any(log.action == "fake_advisor.question_asked" for log in logs)


class TestRunNoEvidence:
    def test_returns_no_evidence_without_calling_the_advisor(self, repo, framework):
        org_id = repo.enterprise.create_organization("Org A")
        advisor = _FakeAdvisor()

        explanation = framework.run(advisor, _session(repo, org_id), "any question?", evidence=[])

        assert advisor.called_with is None
        assert explanation.recommendation.cited_evidence == []


class TestRunWithEvidence:
    def test_builds_a_grounded_recommendation(self, repo, framework):
        org_id = repo.enterprise.create_organization("Org A")
        repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        evidence = framework.gather_context(org_id, "Aurora", kind="risk")
        analysis_id = evidence[0].source_analysis_id

        advisor = _FakeAdvisor(
            response={
                "structured": True,
                "answer": "here is the synthesis",
                "cited_analysis_ids": [analysis_id, 999999],  # 999999 never in evidence
            }
        )
        explanation = framework.run(advisor, _session(repo, org_id), "what are the risks?", evidence)

        assert explanation.recommendation.answer == "here is the synthesis"
        # Only the real, present citation survives -- never an invented one.
        assert [e.source_analysis_id for e in explanation.recommendation.cited_evidence] == [analysis_id]

    def test_raises_for_malformed_advisor_output(self, repo, framework):
        org_id = repo.enterprise.create_organization("Org A")
        repo.save_analysis(
            kind="risk",
            payload={"model_output": {"structured": True, "risks": []}},
            organization_id=org_id,
            project_name="Aurora",
        )
        evidence = framework.gather_context(org_id, "Aurora", kind="risk")

        advisor = _FakeAdvisor(response={"structured": False, "raw_output": "not json"})
        with pytest.raises(AdvisorExecutionError):
            framework.run(advisor, _session(repo, org_id), "what are the risks?", evidence)


class TestControlledRagAccess:
    def test_gather_rag_context_delegates_to_rag_pipeline(
        self, repo, knowledge_repository, framework
    ):
        org_id = repo.enterprise.create_organization("Org A")
        document = knowledge_repository.ingest(org_id, "runbook.md", "the rollback procedure is documented here")
        knowledge_repository.index(document.id, CORRELATION_ID)

        context = framework.gather_rag_context(org_id, "rollback procedure", top_k=3)

        assert len(context.chunks) == 1
        assert context.chunks[0].document_id == document.id
        assert context.chunk_ids == {context.chunks[0].chunk_id}


class TestControlledLlmAccess:
    def test_call_llm_delegates_to_the_provider(self, repo, framework):
        org_id = repo.enterprise.create_organization("Org A")
        output = framework.call_llm("fake_advisor", _session(repo, org_id), "any prompt")
        assert output == "mock advisor output"

    def test_render_prompt_composes_the_shared_preamble(self, framework):
        prompt = framework.render_prompt(
            "risk_advisor", "advise", question="what is the risk?", risks_json="[]"
        )
        assert "STRATECH Digital PMO Intelligence Foundation" in prompt  # shared preamble
        assert "what is the risk?" in prompt  # advisor's own template, substituted
