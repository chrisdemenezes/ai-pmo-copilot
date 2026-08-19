from src.database.repository import AnalysisRepository
from src.services.ai_foundation.types import SessionContext


class AIFoundationAudit:
    """Standard audit trail for every Enterprise Analyst question -- the
    same action-naming convention and payload shape the Risk Advisor
    established manually (Security Hardening Gate, D-046), now codified
    once (Domain Blueprint §4.7). Never logs the model's answer."""

    @staticmethod
    def record_question(
        repository: AnalysisRepository,
        session: SessionContext,
        analyst_name: str,
        question: str,
    ) -> None:
        repository.administration.record_audit(
            session.organization_id,
            session.user_id,
            f"{analyst_name}.question_asked",
            "project",
            None,
            {"project_name": session.project_name, "question": question},
        )
