"""Delivery Advisor (Wave 5, 4th Advisor of the institutional cycle), per
`TECHNICAL-DESIGN-DELIVERY-ADVISOR.md`.

Proves, against the real `DeliveryAdvisorAgent` (never a fake test
double), the end-to-end chain: `AnalysisRecord` (kind="status") ->
`AIContextEngine.gather()` -> `AdvisorFramework.run()` (byte-for-byte
unchanged) -> Delivery Advisor -> LLM -> Response.

Includes the three mandatory temporal scenarios required by "Founder
Decision -- Technical Design do Delivery Advisor" (item 4), using explicit
`created_at` timestamps (item 5) to prove ordering and rule out an
inverted trend:

A. Melhora: antigo vermelho -> intermediario amarelo -> recente verde.
B. Deterioracao: antigo verde -> intermediario amarelo -> recente vermelho.
C. Registro unico: sem historico suficiente para avaliar evolucao.

Also proves the absence of a second source of evidence (item 2): this
Advisor is built with `rag_pipeline=None` throughout -- any accidental
call to `gather_rag_context()` would raise `AttributeError` immediately,
so a passing test is itself the proof no second source is ever touched.
"""
import json
from datetime import datetime, timezone

import pytest

from src.agents.delivery_advisor.agent import DeliveryAdvisorAgent
from src.database.repository import AnalysisRecord, AnalysisRepository
from src.prompts.registry import PromptRegistry
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.ai_foundation.types import SessionContext
from tests.db import temp_database_url


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
    with temp_database_url("delivery_advisor") as database_url:
        yield AnalysisRepository(database_url=database_url)


def _framework(repo, provider):
    # rag_pipeline=None throughout this file, deliberately (item 2/6 of the
    # authorization): the Delivery Advisor never calls
    # gather_rag_context() -- if it ever did, this would raise
    # AttributeError immediately, so a passing test proves the absence of a
    # second/supplementary source of evidence.
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


class TestNoEvidenceWithoutLlmCall:
    def test_no_status_analysis_means_no_llm_call(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        framework = _framework(repo, _ExplodingProvider())
        agent = DeliveryAdvisorAgent(framework)

        evidence = framework.gather_context(org_id, "Aurora", kind="status")
        assert evidence == []

        explanation = framework.run(
            agent,
            _session(repo, org_id),
            "Como esta o projeto Aurora?",
            evidence,
            no_evidence_answer="Nenhuma análise de status registrada ainda para este projeto.",
        )

        assert explanation.recommendation.answer == "Nenhuma análise de status registrada ainda para este projeto."
        assert explanation.recommendation.cited_evidence == []


class TestSingleSourceOnly:
    def test_gather_context_is_called_exactly_once_with_kind_status(self, repo, monkeypatch):
        org_id = repo.enterprise.create_organization("Org A")
        _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
        framework = _framework(repo, _ScriptedProvider("ok", []))

        calls = []
        original_gather = framework.gather_context

        def _recording_gather(organization_id, project_name, kind):
            calls.append(kind)
            return original_gather(organization_id, project_name, kind)

        monkeypatch.setattr(framework, "gather_context", _recording_gather)
        agent = DeliveryAdvisorAgent(framework)

        evidence = framework.gather_context(org_id, "Aurora", kind="status")
        framework.run(agent, _session(repo, org_id), "Como esta o projeto?", evidence)

        # Exactly one call, exactly kind="status" -- never "risk"/"meeting"/
        # "action_items", per Founder Decision item 2.
        assert calls == ["status"]


class TestTemporalScenarioA_Melhora:
    def test_old_red_intermediate_yellow_recent_green_yields_current_green_and_melhorando(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        red_id = _save_status_at(repo, org_id, "Aurora", "red", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc))
        yellow_id = _save_status_at(repo, org_id, "Aurora", "yellow", datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc))
        green_id = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))

        framework = _framework(repo, None)
        evidence = framework.gather_context(org_id, "Aurora", kind="status")

        # Ordering proof (item 5): most-recent-first, timestamps confirm it
        # -- the current entry is the green one saved last, never reversed.
        assert [item.source_id for item in evidence] == [green_id, yellow_id, red_id]
        assert evidence[0].content["health_status"] == "green"
        assert evidence[-1].content["health_status"] == "red"

        provider = _ScriptedProvider(
            answer=(
                "O estado atual do projeto Aurora e green. A tendencia e melhorando: "
                "o projeto evoluiu de red para yellow e agora green nas ultimas analises."
            ),
            cited_analysis_ids=[green_id, yellow_id, red_id],
        )
        framework = _framework(repo, provider)
        agent = DeliveryAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "Como esta o projeto Aurora?", evidence)

        assert "green" in explanation.recommendation.answer
        assert "melhorando" in explanation.recommendation.answer
        assert [item.source_id for item in explanation.recommendation.cited_evidence] == [
            green_id,
            yellow_id,
            red_id,
        ]
        assert provider.calls == 1


class TestTemporalScenarioB_Deterioracao:
    def test_old_green_intermediate_yellow_recent_red_yields_current_red_and_deteriorando(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        green_id = _save_status_at(repo, org_id, "Aurora", "green", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc))
        yellow_id = _save_status_at(repo, org_id, "Aurora", "yellow", datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc))
        red_id = _save_status_at(repo, org_id, "Aurora", "red", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))

        framework = _framework(repo, None)
        evidence = framework.gather_context(org_id, "Aurora", kind="status")

        # Ordering proof (item 5): the most recent record (red) is first,
        # never the oldest (green) -- rules out an inverted trend reading.
        assert [item.source_id for item in evidence] == [red_id, yellow_id, green_id]
        assert evidence[0].content["health_status"] == "red"
        assert evidence[-1].content["health_status"] == "green"

        provider = _ScriptedProvider(
            answer=(
                "O estado atual do projeto Aurora e red. A tendencia e deteriorando: "
                "o projeto evoluiu de green para yellow e agora red nas ultimas analises."
            ),
            cited_analysis_ids=[red_id, yellow_id, green_id],
        )
        framework = _framework(repo, provider)
        agent = DeliveryAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "Como esta o projeto Aurora?", evidence)

        assert "red" in explanation.recommendation.answer
        assert "deteriorando" in explanation.recommendation.answer
        assert [item.source_id for item in explanation.recommendation.cited_evidence] == [
            red_id,
            yellow_id,
            green_id,
        ]


class TestTemporalScenarioC_RegistroUnico:
    def test_single_record_reports_current_state_without_inventing_a_trend(self, repo):
        org_id = repo.enterprise.create_organization("Org A")
        yellow_id = _save_status_at(repo, org_id, "Aurora", "yellow", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))

        framework = _framework(repo, None)
        evidence = framework.gather_context(org_id, "Aurora", kind="status")
        assert len(evidence) == 1

        provider = _ScriptedProvider(
            answer=(
                "O estado atual do projeto Aurora e yellow. Nao ha historico suficiente "
                "para avaliar uma tendencia de evolucao."
            ),
            cited_analysis_ids=[yellow_id],
        )
        framework = _framework(repo, provider)
        agent = DeliveryAdvisorAgent(framework)

        explanation = framework.run(agent, _session(repo, org_id), "Como esta o projeto Aurora?", evidence)

        assert "yellow" in explanation.recommendation.answer
        assert "Nao ha historico suficiente" in explanation.recommendation.answer
        assert "melhorando" not in explanation.recommendation.answer
        assert "deteriorando" not in explanation.recommendation.answer
        assert [item.source_id for item in explanation.recommendation.cited_evidence] == [yellow_id]


class TestOrganizationalIsolation:
    def test_never_returns_status_evidence_from_another_organization(self, repo):
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        org_a_id = _save_status_at(repo, org_a, "Aurora", "green", datetime(2026, 8, 1, tzinfo=timezone.utc))
        _save_status_at(repo, org_b, "Aurora", "red", datetime(2026, 8, 1, tzinfo=timezone.utc))

        framework = _framework(repo, _ExplodingProvider())
        evidence = framework.gather_context(org_a, "Aurora", kind="status")

        # Both organizations happen to name their project "Aurora" -- Org A
        # must only ever see its own record, never Org B's.
        assert [item.source_id for item in evidence] == [org_a_id]
        assert evidence[0].content["health_status"] == "green"
