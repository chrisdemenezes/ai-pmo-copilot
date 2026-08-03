"""Governance Advisor HTTP route (Wave 5), per
`TECHNICAL-DESIGN-GOVERNANCE-ADVISOR.md` §5.

Same rigor already established for `/document-advisor/ask`
(`test_document_advisor_api.py`) -- real Postgres, real migration-seeded
permissions, real institutional headers, real `KnowledgeRepository` for
ingestion.
"""
import json
import os
import subprocess
import sys

import pytest

from fastapi.testclient import TestClient

from src.api import authorization as authorization_module
from src.api import dependencies as dependencies_module
from src.api.routes import intelligence
from src.database.repository import AnalysisRepository
from src.main import app
from src.services.authorization.checker import SqlPermissionChecker
from src.services.events.dispatcher import EventDispatcher
from src.services.events.in_process_publisher import InProcessEventPublisher
from src.services.knowledge_platform.embedding_provider import MockEmbeddingProvider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.vector_repository import PgVectorRepository

from tests.db import temp_database_url

CORRELATION_ID = "test-correlation-id"


def _alembic(env, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result


def _headers(organization_id: int, user_id: int) -> dict:
    return {
        "X-Stratech-User-Id": str(user_id),
        "X-Stratech-Organization-Id": str(organization_id),
        "X-Stratech-Session-Id": "session-1",
    }


def _actor(repo, organization_id: int, role: str = "organization_admin") -> int:
    user_id = repo.enterprise.create_user(organization_id, f"{role}@example.com", "Actor")
    with repo.SessionLocal() as session:
        repo.enterprise.assign_role_in_session(session, user_id, role)
        session.commit()
    return user_id


class FakePromptRegistry:
    def get(self, agent_name, prompt_name):
        assert agent_name == "governance_advisor"
        assert prompt_name == "advise"
        return "Question: $question\nChunks: $chunks_json"


class FakeProvider:
    def generate(self, prompt):
        return "not json at all"


@pytest.fixture()
def client():
    with temp_database_url("governance_advisor_api") as database_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        _alembic(env, "upgrade", "head")

        repo = AnalysisRepository(database_url=database_url)
        dispatcher = EventDispatcher(repo.SessionLocal)
        event_publisher = InProcessEventPublisher(repo.SessionLocal, dispatcher)
        vector_repository = PgVectorRepository(repo.SessionLocal)
        knowledge_repository = KnowledgeRepository(
            repo.SessionLocal, MockEmbeddingProvider(), vector_repository, event_publisher
        )

        app.dependency_overrides[intelligence.build_prompt_registry] = lambda: FakePromptRegistry()
        app.dependency_overrides[intelligence.build_provider] = lambda: FakeProvider()
        app.dependency_overrides[intelligence.build_repository] = lambda: repo
        app.dependency_overrides[dependencies_module.build_event_publisher] = lambda: event_publisher
        app.dependency_overrides[authorization_module.build_permission_checker] = (
            lambda: SqlPermissionChecker(repo.SessionLocal)
        )
        yield TestClient(app), repo, knowledge_repository
        app.dependency_overrides.pop(intelligence.build_prompt_registry, None)
        app.dependency_overrides.pop(intelligence.build_provider, None)
        app.dependency_overrides.pop(intelligence.build_repository, None)
        app.dependency_overrides.pop(dependencies_module.build_event_publisher, None)
        app.dependency_overrides.pop(authorization_module.build_permission_checker, None)


class TestNoEvidence:
    def test_returns_sem_evidencia_without_calling_the_llm_when_nothing_is_indexed(self, client):
        test_client, repo, _knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("LLM must not be called when there is no indexed evidence")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe alguma decisao sobre X?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["classification"] == "SEM EVIDÊNCIA"
        assert body["answer"] == "Nenhuma referência de governança relevante foi encontrada para responder a esta pergunta."
        assert body["cited_chunks"] == []


class TestRealCitationAndClassification:
    def test_answers_with_a_real_citation_and_conforme_classification(self, client):
        test_client, repo, knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        document = knowledge_repository.ingest(
            org_id, "decision-log-fragment.md", "D-050: knowledge.write e concedido a organization_admin, pmo e project_manager."
        )
        knowledge_repository.index(document.id, CORRELATION_ID)

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {
                        "answer": "[CONFORME]\nknowledge.write e concedido a organization_admin, pmo e project_manager, per D-050.",
                        "cited_analysis_ids": [1],
                    }
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Quem recebe knowledge.write?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["classification"] == "CONFORME"
        assert body["answer"] == "knowledge.write e concedido a organization_admin, pmo e project_manager, per D-050."
        assert body["cited_chunks"] == [
            {"document_id": document.id, "chunk_id": 1, "source_label": f"Document {document.id} / Chunk 1"}
        ]

    def test_discards_a_citation_the_model_invented(self, client):
        test_client, repo, knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        document = knowledge_repository.ingest(org_id, "decision-log-fragment.md", "D-050: regra institucional documentada")
        knowledge_repository.index(document.id, CORRELATION_ID)

        class AdvisorProvider:
            def generate(self, prompt):
                return json.dumps(
                    {"answer": "[CONFORME]\nA regra esta documentada em D-050.", "cited_analysis_ids": [1, 999999]}
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: AdvisorProvider()

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe uma regra documentada?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["cited_chunks"]) == 1
        assert body["cited_chunks"][0]["chunk_id"] == 1

    def test_unformatted_answer_falls_back_to_nao_classificado(self, client):
        test_client, repo, knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        document = knowledge_repository.ingest(org_id, "decision-log-fragment.md", "D-050: regra institucional documentada")
        knowledge_repository.index(document.id, CORRELATION_ID)

        class MalformedProvider:
            def generate(self, prompt):
                # No classification prefix on the first line -- must never
                # be silently guessed as one of the 5 official labels.
                return json.dumps({"answer": "A regra esta documentada.", "cited_analysis_ids": [1]})

        app.dependency_overrides[intelligence.build_provider] = lambda: MalformedProvider()

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe uma regra documentada?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["classification"] == "NÃO CLASSIFICADO"
        assert body["answer"] == "A regra esta documentada."


class TestRbac:
    def test_user_with_no_role_is_denied(self, client):
        test_client, repo, _knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = repo.enterprise.create_user(org_id, "norole@example.com", "No Role")

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "missing permission: knowledge.read"

    def test_viewer_can_ask(self, client):
        test_client, repo, _knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        viewer_id = _actor(repo, org_id, "viewer")

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, viewer_id),
            json={"question": "Alguma pergunta?"},
        )

        assert response.status_code == 200


class TestOrganizationalIsolation:
    def test_never_cites_a_governance_chunk_from_another_organization(self, client):
        test_client, repo, knowledge_repository = client
        org_a = repo.enterprise.create_organization("Org A")
        org_b = repo.enterprise.create_organization("Org B")
        user_a = _actor(repo, org_a, "organization_admin")
        document = knowledge_repository.ingest(org_b, "decision-log-fragment.md", "D-050: Org B confidential decision")
        knowledge_repository.index(document.id, CORRELATION_ID)

        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("must not synthesize over another organization's governance documents")

        app.dependency_overrides[intelligence.build_provider] = lambda: ExplodingProvider()

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_a, user_a),
            json={"question": "Existe alguma decisao registrada?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["classification"] == "SEM EVIDÊNCIA"
        assert body["cited_chunks"] == []


class TestMalformedResponse:
    def test_returns_502_for_a_malformed_advisor_response(self, client):
        test_client, repo, knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")
        document = knowledge_repository.ingest(org_id, "decision-log-fragment.md", "D-050: regra institucional documentada")
        knowledge_repository.index(document.id, CORRELATION_ID)

        class NotJsonProvider:
            def generate(self, prompt):
                return "not json at all"

        app.dependency_overrides[intelligence.build_provider] = lambda: NotJsonProvider()

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Existe uma regra documentada?"},
        )

        assert response.status_code == 502


class TestAuditTrail:
    def test_records_an_audit_entry_without_the_llm_answer(self, client):
        test_client, repo, _knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Alguma pergunta sobre governanca?"},
        )
        assert response.status_code == 200

        entries = repo.administration.list_audit_log(org_id)
        matching = [e for e in entries if e.action == "governance_advisor.question_asked"]
        assert len(matching) == 1
        assert matching[0].actor_user_id == user_id
        assert matching[0].organization_id == org_id
        assert matching[0].details["question"] == "Alguma pergunta sobre governanca?"
        assert "answer" not in matching[0].details


class TestMandatoryConflictEvidence:
    """Founder-mandated evidence (item 4): a real scenario where a
    Decision Log entry and a Technical Debt Register entry conflict,
    classified CONFLITANTE, citing both -- exercised here through the real
    HTTP route (RBAC, institutional headers, real ingestion), complementing
    the framework-level proof in `test_governance_advisor.py`."""

    def test_conflicting_documents_are_classified_conflitante_and_both_cited(self, client):
        test_client, repo, knowledge_repository = client
        org_id = repo.enterprise.create_organization("Org A")
        user_id = _actor(repo, org_id, "organization_admin")

        decision_log_doc = knowledge_repository.ingest(
            org_id,
            "decision-log-fragment.md",
            "D-050: A retencao de AuditLog e mantida indefinidamente, sem expiracao automatica.",
        )
        knowledge_repository.index(decision_log_doc.id, CORRELATION_ID)
        technical_debt_doc = knowledge_repository.ingest(
            org_id,
            "technical-debt-fragment.md",
            "TD-020: AuditLog expira automaticamente apos 90 dias, conforme politica de retencao implementada.",
        )
        knowledge_repository.index(technical_debt_doc.id, CORRELATION_ID)

        class ConflictProvider:
            def generate(self, prompt):
                return json.dumps(
                    {
                        "answer": (
                            "[CONFLITANTE]\n"
                            "O Decision Log (D-050) afirma retencao indefinida do AuditLog, enquanto o Technical "
                            "Debt Register (TD-020) afirma expiracao automatica apos 90 dias. Per a hierarquia "
                            "institucional (AR-10), o Decision Log tem precedencia."
                        ),
                        "cited_analysis_ids": [1, 2],
                    }
                )

        app.dependency_overrides[intelligence.build_provider] = lambda: ConflictProvider()

        response = test_client.post(
            "/api/governance-advisor/ask",
            headers=_headers(org_id, user_id),
            json={"question": "Qual a politica de retencao do AuditLog?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["classification"] == "CONFLITANTE"
        assert "precedencia" in body["answer"]
        cited_document_ids = {chunk["document_id"] for chunk in body["cited_chunks"]}
        assert cited_document_ids == {decision_log_doc.id, technical_debt_doc.id}
