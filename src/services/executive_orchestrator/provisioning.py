"""Per-Advisor evidence provisioning (Technical Design §3, row
"`AdvisorFramework.run()`": "incluindo a montagem de evidência
(`gather_context`/`gather_rag_context`) que hoje já precede cada chamada em
cada rota"). Reuses, verbatim, the exact same `gather_context()`/
`gather_rag_context()`/`EvidenceAssembler`/`no_evidence_answer` already in
production in each `ask_*_advisor` route (`src/api/routes/intelligence.py`)
-- never a new evidence-access path, never a different `kind=`/assembler
than the one each Advisor's own route already uses.

Never calls `AIContextEngine`/any repository directly -- always through
`AdvisorFramework.gather_context()`/`gather_rag_context()` (the same
sanctioned intermediary every route already uses) or through the same
`EvidenceAssembler` classes each Advisor's own route already instantiates.
"""
from dataclasses import dataclass

from src.agents.delivery_advisor.agent import DeliveryAdvisorAgent
from src.agents.document_advisor.agent import DocumentAdvisorAgent
from src.agents.executive_advisor.agent import ExecutiveAdvisorAgent
from src.agents.executive_advisor.evidence_assembler import ExecutiveEvidenceAssembler
from src.agents.governance_advisor.agent import GovernanceAdvisorAgent
from src.agents.pmo_advisor.agent import PMOAdvisorAgent
from src.agents.pmo_advisor.evidence_assembler import PMOEvidenceAssembler
from src.agents.portfolio_advisor.agent import PortfolioAdvisorAgent
from src.agents.portfolio_advisor.evidence_assembler import PortfolioEvidenceAssembler
from src.agents.risk_advisor.agent import RiskAdvisorAgent
from src.agents.strategy_advisor.agent import StrategyAdvisorAgent
from src.agents.strategy_advisor.evidence_assembler import StrategyEvidenceAssembler
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.advisor_framework.types import AdvisorContract
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.domain_service import DomainService
from src.services.executive_orchestrator.selection_rule import OrchestrationScope
from src.services.knowledge_platform.rag_pipeline import RagContext


@dataclass(frozen=True)
class ProvisionedAdvisor:
    agent: AdvisorContract
    evidence: list[Evidence]
    rag_context: RagContext | None
    no_evidence_answer: str


def provision(
    advisor_name: str,
    framework: AdvisorFramework,
    domain_service: DomainService,
    session: SessionContext,
    question: str,
    scope: OrchestrationScope,
) -> ProvisionedAdvisor:
    if advisor_name == "risk_advisor":
        evidence = framework.gather_context(session.organization_id, scope.project_name, kind="risk")
        return ProvisionedAdvisor(
            RiskAdvisorAgent(framework), evidence, None, "Nenhum risco identificado ainda para este projeto."
        )

    if advisor_name == "delivery_advisor":
        evidence = framework.gather_context(session.organization_id, scope.project_name, kind="status")
        return ProvisionedAdvisor(
            DeliveryAdvisorAgent(framework),
            evidence,
            None,
            "Nenhuma análise de status registrada ainda para este projeto.",
        )

    if advisor_name == "portfolio_advisor":
        # scope.portfolio_id is guaranteed not None here -- the Selection
        # Rule's structural precondition (catalog.ADVISOR_NAMES_REQUIRING_
        # PORTFOLIO_ID) never selects this Advisor otherwise.
        result = PortfolioEvidenceAssembler(domain_service, framework).assemble(
            session.organization_id, scope.portfolio_id
        )
        evidence = result.evidence if result is not None else []
        return ProvisionedAdvisor(
            PortfolioAdvisorAgent(framework),
            evidence,
            None,
            "Nenhuma análise de status registrada para os projetos deste portfólio.",
        )

    if advisor_name == "pmo_advisor":
        result = PMOEvidenceAssembler(domain_service, framework).assemble(session.organization_id)
        return ProvisionedAdvisor(
            PMOAdvisorAgent(framework),
            result.evidence,
            None,
            "Nenhuma análise de status registrada para os projetos desta organização.",
        )

    if advisor_name == "executive_advisor":
        result = ExecutiveEvidenceAssembler(domain_service, framework).assemble(session.organization_id)
        return ProvisionedAdvisor(
            ExecutiveAdvisorAgent(framework),
            result.evidence,
            None,
            "Nenhuma análise de status ou risco registrada para os projetos desta organização.",
        )

    if advisor_name == "strategy_advisor":
        result = StrategyEvidenceAssembler(domain_service, framework).assemble(session.organization_id)
        return ProvisionedAdvisor(
            StrategyAdvisorAgent(framework),
            result.evidence,
            None,
            "Nenhum objetivo declarado ou evidência de execução comparável registrada para esta organização.",
        )

    if advisor_name == "document_advisor":
        rag_context = framework.gather_rag_context(session.organization_id, question, top_k=5)
        evidence = framework.normalize_rag_evidence(rag_context)
        return ProvisionedAdvisor(
            DocumentAdvisorAgent(framework),
            evidence,
            rag_context,
            "Nenhum documento relevante foi encontrado para responder a esta pergunta.",
        )

    if advisor_name == "governance_advisor":
        rag_context = framework.gather_rag_context(session.organization_id, question, top_k=5)
        evidence = framework.normalize_rag_evidence(rag_context)
        return ProvisionedAdvisor(
            GovernanceAdvisorAgent(framework),
            evidence,
            rag_context,
            "[SEM EVIDÊNCIA]\nNenhuma referência de governança relevante foi encontrada para responder a esta pergunta.",
        )

    raise ValueError(f"Advisor Identity desconhecida: {advisor_name!r}")
