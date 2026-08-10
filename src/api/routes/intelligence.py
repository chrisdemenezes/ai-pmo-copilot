"""Intelligence API -- meeting/risk/status analysis + read endpoints.

RBAC + organization scope (Security Hardening Gate, C-1/C-2; Repository
Audit Wave 3): every route below carries `Depends(require_permission(
"intelligence.read"|"intelligence.write"))`, inserted after
`get_request_context`, the same seam every other Enterprise Domain route
module uses (`portfolio.py`, `program.py`, `project_delivery.py`,
`administration.py`). Every read/write is scoped by
`context.organization.organization_id`, never a client-supplied value.
"""
import logging
from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi import APIRouter, Depends, HTTPException

from src.agents.delivery_advisor.agent import DeliveryAdvisorAgent
from src.agents.document_advisor.agent import DocumentAdvisorAgent
from src.agents.executive_advisor.agent import ExecutiveAdvisorAgent
from src.agents.executive_advisor.evidence_assembler import (
    ExecutiveAssemblyResult,
    ExecutiveEvidenceAssembler,
)
from src.agents.governance_advisor.agent import GovernanceAdvisorAgent
from src.agents.pmo_advisor.agent import PMOAdvisorAgent
from src.agents.pmo_advisor.evidence_assembler import (
    PMOAssemblyResult,
    PMOEvidenceAssembler,
)
from src.agents.strategy_advisor.agent import StrategyAdvisorAgent
from src.agents.strategy_advisor.evidence_assembler import (
    StrategyAssemblyResult,
    StrategyEvidenceAssembler,
)
from src.agents.portfolio_advisor.agent import PortfolioAdvisorAgent
from src.agents.portfolio_advisor.evidence_assembler import (
    PortfolioAssemblyResult,
    PortfolioEvidenceAssembler,
)
from src.agents.meeting_intelligence.agent import MeetingIntelligenceAgent
from src.agents.project_status.agent import ProjectStatusAgent
from src.agents.risk_advisor.agent import RiskAdvisorAgent
from src.agents.risk_review.agent import RiskReviewAgent
from src.api.authorization import require_permission
from src.api.dependencies import build_event_publisher, build_repository
from src.api.routes.portfolio import build_domain_service
from src.api.identity_context import get_request_context
from src.api.rate_limiter import enforce_rate_limit
from src.api.security import verify_api_key
from src.database.enterprise_repository import (
    AmbiguousProjectNameError,
    ProjectNotFoundError,
    ProjectReferenceMismatchError,
)
from src.llm.providers.base import LLMProvider
from src.llm.providers.factory import get_provider
from src.prompts.registry import PromptRegistry
from src.database.repository import AnalysisRepository, analysis_display_name
from src.services.advisor_framework.framework import AdvisorFramework
from src.services.advisor_framework.types import AdvisorExecutionError
from src.services.domain_service import DomainService
from src.services.ai_foundation.types import Evidence, SessionContext
from src.services.events.interfaces import EventPublisher
from src.services.executive_orchestrator.catalog import ADVISOR_IDENTITY_CATALOG
from src.services.executive_orchestrator.orchestrator import ExecutiveOrchestrator
from src.services.executive_orchestrator.selection_rule import OrchestrationScope, SelectionSignals
from src.services.executive_orchestrator.types import Capability
from src.services.identity.models import RequestContext
from src.services.knowledge_platform.embedding_provider import get_embedding_provider
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.rag_pipeline import RagPipeline
from src.services.knowledge_platform.vector_repository import PgVectorRepository
from src.services.project_summary_service import ProjectSummaryService

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


def _ensure_has_content(value: str) -> str:
    if not value.strip():
        raise ValueError("must contain non-whitespace content")
    return value


class MeetingAnalysisRequest(BaseModel):
    transcript: str = Field(..., min_length=10, max_length=20000)
    project_name: str | None = None

    _validate_transcript = field_validator("transcript")(_ensure_has_content)


class RiskAnalysisRequest(BaseModel):
    project_context: str = Field(..., min_length=10, max_length=20000)
    project_name: str | None = None

    _validate_project_context = field_validator("project_context")(_ensure_has_content)


class ProjectStatusRequest(BaseModel):
    project_context: str = Field(..., min_length=10, max_length=20000)
    project_name: str | None = None

    _validate_project_context = field_validator("project_context")(_ensure_has_content)


class AnalysisSummary(BaseModel):
    id: int
    kind: str
    # Display attribute derived from Project.name via project_id (TD-008 Fase
    # 3b, Etapa 4a); project_id is the identity key. Built explicitly by the
    # routes (not `from_attributes`) so the display never reads the legacy
    # analysis_records.project_name column.
    project_id: int | None = None
    project_name: str | None
    created_at: datetime


class AnalysisDetail(AnalysisSummary):
    payload: dict


class ProjectSummaryResponse(BaseModel):
    project_name: str
    project_id: int | None = None
    total_analyses: int
    open_risks: int
    pending_action_items: int
    latest_health_status: str | None


class ActionItemResponse(BaseModel):
    project_id: int | None = None
    project_name: str | None
    description: str
    # due_date stays a plain string, never parsed to a date here -- it's
    # free text extracted by the AI (FS-007 §11); the frontend treats an
    # unparseable value as "sem prazo" instead of the API rejecting it.
    owner: str | None
    due_date: str | None
    source_analysis_id: int
    source_created_at: datetime


class LatestRiskItemResponse(BaseModel):
    project_id: int | None = None
    project_name: str | None
    description: str
    probability: str | None
    impact: str | None
    mitigation: str | None
    escalation_recommendation: str | None
    source_analysis_id: int
    source_created_at: datetime


class RiskAdvisorRequest(BaseModel):
    project_name: str
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class CitedAnalysis(BaseModel):
    source_analysis_id: int
    source_created_at: datetime


class RiskAdvisorResponse(BaseModel):
    answer: str
    cited_analyses: list[CitedAnalysis]


class DeliveryAdvisorRequest(BaseModel):
    project_name: str
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class DeliveryAdvisorResponse(BaseModel):
    answer: str
    cited_analyses: list[CitedAnalysis]  # reaproveitado do Risk Advisor -- mesmo shape exato


class PortfolioAdvisorRequest(BaseModel):
    portfolio_id: int
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class CitedProject(BaseModel):
    project_id: int
    project_name: str
    source_analysis_id: int
    source_created_at: datetime


class PortfolioAdvisorResponse(BaseModel):
    answer: str
    total_projects: int
    projects_with_evidence: int
    projects_without_evidence: int
    cited_projects: list[CitedProject]


class PMOAdvisorRequest(BaseModel):
    # No project_id/portfolio_id -- the PMO Advisor's scope is always the
    # organization of the authenticated session (D-114), never a
    # caller-supplied identifier. Same shape as DocumentAdvisorRequest.
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class PMOAdvisorResponse(BaseModel):
    answer: str
    total_projects: int
    projects_with_status: int
    projects_without_status: int
    projects_stale: int
    projects_current: int
    # CitedProject reused as-is (D-116 SS5.3): source_analysis_id already
    # makes every citation unambiguously traceable to one AnalysisRecord,
    # even when the same project_id appears more than once because
    # multiple records of that Project were cited.
    cited_projects: list[CitedProject]


class ExecutiveAdvisorRequest(BaseModel):
    # No project_id/portfolio_id -- same reasoning as PMOAdvisorRequest: the
    # Executive Advisor's scope is always the organization of the
    # authenticated session (Domain Blueprint §4, AR-14).
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class ExecutiveCitedEvidence(BaseModel):
    # New, isolated model (AR-14 §2/Technical Design §4.2) -- CitedProject
    # is never touched, remains serving Portfolio/PMO Advisor unchanged.
    # "kind" distinguishes "status" from "risk" citations of the same
    # project, something CitedProject cannot express.
    project_id: int
    project_name: str
    source_analysis_id: int
    kind: str
    created_at: datetime


class ExecutiveAdvisorResponse(BaseModel):
    answer: str
    total_projects: int
    projects_with_status: int
    projects_without_status: int
    projects_with_risk: int
    projects_without_risk: int
    projects_with_status_and_risk: int
    projects_without_any_evidence: int
    cited_evidence: list[ExecutiveCitedEvidence]


class StrategyAdvisorRequest(BaseModel):
    # No project_id/portfolio_id -- same reasoning as PMOAdvisorRequest/
    # ExecutiveAdvisorRequest: the Strategy Advisor's scope is always the
    # organization of the authenticated session (Domain Blueprint §4).
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class StrategyCitedEvidence(BaseModel):
    # New, isolated model (AR-15 §6.3/Technical Design §5) -- CitedProject/
    # ExecutiveCitedEvidence are never touched. "level" and the third
    # "kind" value ("declared_strategy") are the two extensions neither
    # existing model can express. entity_id/source_id always carry the
    # real domain identity here -- the synthetic Evidence.source_id used
    # internally to correlate citations (Technical Design §3/§10.2) never
    # reaches this model (Technical Design §4.3).
    level: str
    entity_id: int
    entity_name: str
    kind: str
    source_id: int
    created_at: datetime | None


class StrategyAdvisorResponse(BaseModel):
    answer: str
    portfolios_total: int
    portfolios_with_declared_strategy: int
    portfolios_without_declared_strategy: int
    portfolios_with_execution_evidence: int
    portfolios_comparable: int
    portfolios_with_strategy_without_execution: int
    programs_total: int
    programs_with_declared_strategy: int
    programs_without_declared_strategy: int
    programs_with_execution_evidence: int
    programs_comparable: int
    programs_with_strategy_without_execution: int
    projects_total: int
    projects_with_declared_strategy: int
    projects_without_declared_strategy: int
    projects_with_execution_evidence: int
    projects_comparable: int
    projects_with_strategy_without_execution: int
    cited_evidence: list[StrategyCitedEvidence]


class DocumentAdvisorRequest(BaseModel):
    # No project_name/project_id: KnowledgeRepository.search() (and, by
    # extension, RagPipeline.retrieve()) filters exclusively by
    # organization_id -- never project_id -- confirmed by direct code
    # reading (Technical Design §6). Unlike the Risk Advisor, this Advisor
    # never calls gather_context(), so there is no project scope to receive.
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


class CitedChunk(BaseModel):
    document_id: int
    chunk_id: int
    source_label: str


class DocumentAdvisorResponse(BaseModel):
    answer: str
    cited_chunks: list[CitedChunk]


class GovernanceAdvisorRequest(BaseModel):
    # Same absence of project_name/project_id as DocumentAdvisorRequest --
    # RAG search() filters exclusively by organization_id.
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)


_GOVERNANCE_CLASSIFICATIONS = ("CONFORME", "INCONSISTENTE", "DESATUALIZADO", "CONFLITANTE", "SEM EVIDÊNCIA")
_GOVERNANCE_UNCLASSIFIED = "NÃO CLASSIFICADO"


class GovernanceAdvisorResponse(BaseModel):
    answer: str
    classification: str
    cited_chunks: list[CitedChunk]


def _parse_governance_classification(answer: str) -> tuple[str, str]:
    """HTTP-layer only (Technical Design §4/§5, Founder Decision — AR-10):
    the classification is transmitted exclusively via the first line of
    `answer` -- never a field threaded through `AdvisorFramework.run()`/
    `Recommendation`/`Explanation`, all of which remain untouched. The
    first line must contain nothing but one of the 5 official bracketed
    labels; anything else yields the explicit `NÃO CLASSIFICADO` sentinel,
    never a guessed/invented classification."""
    first_line, _, rest = answer.partition("\n")
    for label in _GOVERNANCE_CLASSIFICATIONS:
        if first_line.strip() == f"[{label}]":
            return label, rest.strip()
    return _GOVERNANCE_UNCLASSIFIED, answer


def build_prompt_registry() -> PromptRegistry:
    return PromptRegistry(base_path="src/agents")


def build_orchestrator_prompt_registry() -> PromptRegistry:
    # Distinct from build_prompt_registry() above: synthesize() (Executive
    # Orchestrator, D-145) requires base_path="src/services", never
    # "src/agents" -- preserves the closed 8-Advisor catalog (Vision,
    # Princípio 8; TECHNICAL-DESIGN-DECISION-SUPPORT.md §2).
    return PromptRegistry(base_path="src/services")


def build_provider() -> LLMProvider:
    return get_provider()


def build_knowledge_repository(
    repository: AnalysisRepository = Depends(build_repository),
    publisher: EventPublisher = Depends(build_event_publisher),
) -> KnowledgeRepository:
    vector_repository = PgVectorRepository(repository.SessionLocal)
    return KnowledgeRepository(
        repository.SessionLocal, get_embedding_provider(), vector_repository, publisher
    )


def build_rag_pipeline(
    knowledge_repository: KnowledgeRepository = Depends(build_knowledge_repository),
) -> RagPipeline:
    return RagPipeline(knowledge_repository)


def build_project_summary_service(
    repository: AnalysisRepository = Depends(build_repository),
) -> ProjectSummaryService:
    return ProjectSummaryService(repository=repository)


def resolve_project_scope(
    repository: AnalysisRepository,
    organization_id: int,
    project_id: int | None,
    project_name: str | None,
) -> tuple[int | None, str | None]:
    """Dual-key boundary check (TD-008 Phase 3b, Etapa 1). Returns the
    `(project_id, project_name)` pair the caller should filter by -- at most
    one is non-None. Maps the resolver's domain errors to HTTP:
    - not found by id / cross-organization -> 404 (never confirm a foreign id);
    - ambiguous name                       -> 409 (never silently pick one);
    - id/name divergence                   -> 409.

    Additive-by-design rules that keep this a zero-regression change:
    - neither given -> (None, None): portfolio scope, unchanged.
    - id given (with or without name) -> full validation, filter by the
      resolved id (exact -- the migration's whole point).
    - name only:
        * resolves uniquely -> filter by its id (identical results to the
          legacy name filter for a unique name, but now exact);
        * ambiguous (>1 match) -> 409 (the one behavior we tighten, per the
          Founder's 'não permitir resolução ambígua por nome');
        * no Project row at all (never analyzed) -> preserve the legacy
          empty-list behavior by filtering on the raw name (a genuinely
          nonexistent project simply has no analyses).
    """
    has_name = project_name is not None and project_name.strip() != ""
    if project_id is None and not has_name:
        return (None, None)

    try:
        project = repository.enterprise.resolve_project_reference(
            organization_id, project_id=project_id, project_name=project_name
        )
        return (project.id, None) if project is not None else (None, None)
    except ProjectNotFoundError as exc:
        # An id that doesn't resolve is always a hard 404 (incl. cross-org).
        # A NAME that doesn't resolve, with no id supplied, is the legacy
        # "never-analyzed project" case -> keep filtering by the raw name
        # (empty result), never a 404, to stay additive.
        if project_id is None:
            return (None, project_name)
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except AmbiguousProjectNameError as exc:
        raise HTTPException(
            status_code=409, detail="Project name is ambiguous; use project_id"
        ) from exc
    except ProjectReferenceMismatchError as exc:
        raise HTTPException(
            status_code=409,
            detail="project_id and project_name refer to different projects",
        ) from exc


@router.post("/meetings/analyze")
def analyze_meeting(
    request: MeetingAnalysisRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.write")),
):
    organization_id = context.organization.organization_id
    logger.info(
        "Analyzing meeting organization_id=%s project_name=%s", organization_id, request.project_name
    )
    agent = MeetingIntelligenceAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(transcript=request.transcript, project_name=request.project_name)
    analysis_id = repository.save_analysis(
        kind="meeting",
        payload=result,
        organization_id=organization_id,
        project_name=request.project_name,
    )
    repository.administration.record_audit(
        organization_id,
        context.user.user_id,
        "analysis.meeting_created",
        "analysis",
        analysis_id,
        {"project_name": request.project_name},
    )
    return result


@router.post("/risks/analyze")
def analyze_risk(
    request: RiskAnalysisRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.write")),
):
    organization_id = context.organization.organization_id
    logger.info(
        "Analyzing risk organization_id=%s project_name=%s", organization_id, request.project_name
    )
    agent = RiskReviewAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(project_context=request.project_context, project_name=request.project_name)
    analysis_id = repository.save_analysis(
        kind="risk",
        payload=result,
        organization_id=organization_id,
        project_name=request.project_name,
    )
    repository.administration.record_audit(
        organization_id,
        context.user.user_id,
        "analysis.risk_created",
        "analysis",
        analysis_id,
        {"project_name": request.project_name},
    )
    return result


@router.post("/projects/analyze")
def analyze_project_status(
    request: ProjectStatusRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.write")),
):
    organization_id = context.organization.organization_id
    logger.info(
        "Analyzing project status organization_id=%s project_name=%s",
        organization_id,
        request.project_name,
    )
    agent = ProjectStatusAgent(model_client=provider, prompt_registry=prompts)
    result = agent.analyze(project_context=request.project_context, project_name=request.project_name)
    analysis_id = repository.save_analysis(
        kind="status",
        payload=result,
        organization_id=organization_id,
        project_name=request.project_name,
    )
    repository.administration.record_audit(
        organization_id,
        context.user.user_id,
        "analysis.status_created",
        "analysis",
        analysis_id,
        {"project_name": request.project_name},
    )
    return result


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(
    project_name: str | None = None,
    project_id: int | None = None,
    kind: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    organization_id = context.organization.organization_id
    scope_id, scope_name = resolve_project_scope(
        repository, organization_id, project_id, project_name
    )
    logger.info(
        "Listing analyses organization_id=%s project_id=%s project_name=%s kind=%s created_from=%s created_to=%s limit=%d offset=%d",
        organization_id,
        scope_id,
        scope_name,
        kind,
        created_from,
        created_to,
        limit,
        offset,
    )
    # A specific project that was never analyzed (name resolved to no Project)
    # has no analyses -- return empty instead of falling through to portfolio
    # scope. `project_id` is now the ONLY scope key (TD-008 Fase 3b, Etapa 4a).
    if scope_id is None and scope_name is not None:
        return []
    records = repository.list_analyses(
        organization_id=organization_id,
        project_id=scope_id,
        kind=kind,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
    # Display name derives from Project.name via project_id -- never from the
    # legacy analysis_records.project_name column.
    return [
        AnalysisSummary(
            id=record.id,
            kind=record.kind,
            project_id=record.project_id,
            project_name=analysis_display_name(record),
            created_at=record.created_at,
        )
        for record in records
    ]


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(
    analysis_id: int,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    logger.info("Fetching analysis id=%s", analysis_id)
    record = repository.get_analysis(analysis_id, context.organization.organization_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # Display name from Project.name via project_id (TD-008 Fase 3b, Etapa 4a).
    return AnalysisDetail(
        id=record.id,
        kind=record.kind,
        project_id=record.project_id,
        project_name=analysis_display_name(record),
        created_at=record.created_at,
        payload=record.payload,
    )


@router.get("/action-items", response_model=list[ActionItemResponse])
def list_action_items(
    project_name: str | None = None,
    project_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # project_name/project_id are optional: present = Workspace view, absent
    # = portfolio view (FS-007 §2.2) -- same query-parameter design as
    # GET /analyses. project_id takes precedence (TD-008 Phase 3b, Etapa 1).
    organization_id = context.organization.organization_id
    scope_id, scope_name = resolve_project_scope(
        repository, organization_id, project_id, project_name
    )
    logger.info("Listing action items project_id=%s project_name=%s", scope_id, scope_name)
    return service.list_action_items(
        organization_id=organization_id, project_name=scope_name, project_id=scope_id
    )


@router.get("/risks/latest", response_model=list[LatestRiskItemResponse])
def list_latest_risks(
    project_name: str | None = None,
    project_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Same query-parameter design as GET /action-items: project_name/id
    # present = Workspace scope, absent = portfolio scope. Decision
    # Center's single new backend investment (FS-008 §3.1) -- reused by
    # any future Capability needing the latest risk analysis per project.
    organization_id = context.organization.organization_id
    scope_id, scope_name = resolve_project_scope(
        repository, organization_id, project_id, project_name
    )
    logger.info("Listing latest risks project_id=%s project_name=%s", scope_id, scope_name)
    return service.list_latest_risks(
        organization_id=organization_id, project_name=scope_name, project_id=scope_id
    )


@router.get("/projects/summary", response_model=ProjectSummaryResponse)
def get_project_summary(
    project_name: str | None = None,
    project_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    repository: AnalysisRepository = Depends(build_repository),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # project_name is a query parameter, not a path segment -- Starlette's
    # default path converter cannot capture a literal "/" in a {name}
    # segment (the ASGI server decodes %2F before route matching, so no
    # client-side encoding can work around it). Query parameters don't have
    # this restriction, matching the already-working GET /analyses design.
    # project_id takes precedence when supplied (TD-008 Phase 3b, Etapa 1).
    organization_id = context.organization.organization_id
    if project_id is None and (project_name is None or project_name.strip() == ""):
        raise HTTPException(
            status_code=422, detail="project_name or project_id is required"
        )
    scope_id, scope_name = resolve_project_scope(
        repository, organization_id, project_id, project_name
    )
    logger.info("Summarizing project_id=%s project_name=%s", scope_id, scope_name)
    # display_name echoes the name the caller informed for a never-analyzed /
    # empty project; when the project has analyses, summarize derives the
    # display name from Project.name (TD-008 Fase 3b, Etapa 4a).
    return service.summarize(
        organization_id=organization_id,
        project_name=scope_name,
        project_id=scope_id,
        display_name=project_name,
    )


@router.get("/portfolio/summary", response_model=list[ProjectSummaryResponse])
def get_portfolio_summary(
    context: RequestContext = Depends(get_request_context),
    service: ProjectSummaryService = Depends(build_project_summary_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    logger.info("Summarizing portfolio")
    return service.summarize_portfolio(organization_id=context.organization.organization_id)


@router.post("/risk-advisor/ask", response_model=RiskAdvisorResponse)
def ask_risk_advisor(
    request: RiskAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    # Read-only: reuses the same permission protecting GET /risks/latest,
    # its own data source (Technical Design §2 -- no dedicated permission,
    # this agent never creates/edits/triggers an analysis).
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Wave 3 Fase 4: migrated onto AdvisorFramework -- see
    # docs/architecture/TECHNICAL-DESIGN-RISK-ADVISOR-MIGRATION-FASE4.md.
    # Risk Advisor -> Advisor Framework -> Gather Context -> RagPipeline ->
    # KnowledgeRepository -> traceable context -> LLMProvider -> Response ->
    # Audit -- the full chain the Founder mandated be exercised end to end.
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
        project_name=request.project_name,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)

    evidence = framework.gather_context(session.organization_id, session.project_name, kind="risk")
    rag_context = framework.gather_rag_context(session.organization_id, request.question, top_k=5)
    logger.info(
        "Risk Advisor question organization_id=%s project_name=%s rag_chunk_ids=%s",
        session.organization_id,
        session.project_name,
        sorted(rag_context.chunk_ids),
    )

    agent = RiskAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            evidence,
            rag_context=rag_context,
            no_evidence_answer="Nenhum risco identificado ainda para este projeto.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _risk_advisor_response(explanation)


def _risk_advisor_response(explanation) -> RiskAdvisorResponse:
    return RiskAdvisorResponse(
        answer=explanation.recommendation.answer,
        cited_analyses=[
            CitedAnalysis(
                source_analysis_id=item.source_id,
                source_created_at=item.metadata["created_at"],
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )


@router.post("/delivery-advisor/ask", response_model=DeliveryAdvisorResponse)
def ask_delivery_advisor(
    request: DeliveryAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    # Read-only, same permission already protecting the Risk Advisor -- this
    # agent never creates/edits/triggers an analysis.
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Classe A, single source of evidence (AR-8 §4.2/D-104, reconfirmed
    # Technical Design item 2): exactly one call to gather_context(),
    # kind="status" -- never risk/meeting/action_items, never RAG.
    # gather_rag_context() is deliberately never called by this route.
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
        project_name=request.project_name,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)

    evidence = framework.gather_context(session.organization_id, session.project_name, kind="status")

    agent = DeliveryAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            evidence,
            no_evidence_answer="Nenhuma análise de status registrada ainda para este projeto.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _delivery_advisor_response(explanation)


def _delivery_advisor_response(explanation) -> DeliveryAdvisorResponse:
    return DeliveryAdvisorResponse(
        answer=explanation.recommendation.answer,
        cited_analyses=[
            CitedAnalysis(
                source_analysis_id=item.source_id,
                source_created_at=item.metadata["created_at"],
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )


@router.post("/portfolio-advisor/ask", response_model=PortfolioAdvisorResponse)
def ask_portfolio_advisor(
    request: PortfolioAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    domain_service: DomainService = Depends(build_domain_service),
    # Read-only, same permission already protecting Risk/Delivery Advisor --
    # this agent never creates/edits/triggers an analysis.
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Classe B, first of its kind (AR-8 §4.2/D-104): composition of N
    # independent gather_context(kind="status") calls, one per Project of
    # the Portfolio, happens entirely inside PortfolioEvidenceAssembler --
    # never inside AdvisorFramework/AIContextEngine.
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)
    assembler = PortfolioEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(session.organization_id, request.portfolio_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    agent = PortfolioAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            result.evidence,
            no_evidence_answer="Nenhuma análise de status registrada para os projetos deste portfólio.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _portfolio_advisor_response(explanation, result)


def _portfolio_advisor_response(
    explanation, result: PortfolioAssemblyResult
) -> PortfolioAdvisorResponse:
    return PortfolioAdvisorResponse(
        answer=explanation.recommendation.answer,
        total_projects=result.total_projects,
        projects_with_evidence=result.projects_with_evidence,
        projects_without_evidence=result.total_projects - result.projects_with_evidence,
        cited_projects=[
            CitedProject(
                project_id=item.metadata["project_id"],
                project_name=item.metadata["project_name"],
                source_analysis_id=item.source_id,
                source_created_at=item.metadata["created_at"],
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )


@router.post("/pmo-advisor/ask", response_model=PMOAdvisorResponse)
def ask_pmo_advisor(
    request: PMOAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    domain_service: DomainService = Depends(build_domain_service),
    # Read-only, same permission already protecting Risk/Delivery/Portfolio
    # Advisor -- this agent never creates/edits/triggers an analysis.
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Classe B, second of its kind (AR-8 §4.2/D-104), organizational scope
    # (D-114): composition of N independent gather_context(kind="status")
    # calls, one per Project of the organization, happens entirely inside
    # PMOEvidenceAssembler -- never inside AdvisorFramework/AIContextEngine.
    # Unlike the Portfolio Advisor, there is no caller-supplied id that can
    # fail to resolve, so there is no 404 case here (D-116 §3.4).
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)
    assembler = PMOEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(session.organization_id)

    agent = PMOAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            result.evidence,
            no_evidence_answer="Nenhuma análise de status registrada para os projetos desta organização.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _pmo_advisor_response(explanation, result)


def _pmo_advisor_response(explanation, result: PMOAssemblyResult) -> PMOAdvisorResponse:
    return PMOAdvisorResponse(
        answer=explanation.recommendation.answer,
        total_projects=result.total_projects,
        projects_with_status=result.projects_with_status,
        projects_without_status=result.projects_without_status,
        projects_stale=result.projects_stale,
        projects_current=result.projects_current,
        cited_projects=[
            CitedProject(
                project_id=item.metadata["project_id"],
                project_name=item.metadata["project_name"],
                source_analysis_id=item.source_id,
                source_created_at=item.metadata["created_at"],
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )


@router.post("/executive-advisor/ask", response_model=ExecutiveAdvisorResponse)
def ask_executive_advisor(
    request: ExecutiveAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    domain_service: DomainService = Depends(build_domain_service),
    # Read-only, same permission already protecting Risk/Delivery/Portfolio/
    # PMO Advisor -- this agent never creates/edits/triggers an analysis.
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Classe B, third of its kind (AR-8 §4.2/D-104), organizational scope
    # (Domain Blueprint §4): composition of two independent gather_context()
    # calls per Project ("status" + "risk") happens entirely inside
    # ExecutiveEvidenceAssembler -- never inside AdvisorFramework/
    # AIContextEngine, never gather_context_many() (D-120 §8). Same as the
    # PMO Advisor, organizational scope always resolves via the session, so
    # there is no 404 case here.
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)
    assembler = ExecutiveEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(session.organization_id)

    agent = ExecutiveAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            result.evidence,
            no_evidence_answer="Nenhuma análise de status ou risco registrada para os projetos desta organização.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _executive_advisor_response(explanation, result)


def _executive_advisor_response(
    explanation, result: ExecutiveAssemblyResult
) -> ExecutiveAdvisorResponse:
    return ExecutiveAdvisorResponse(
        answer=explanation.recommendation.answer,
        total_projects=result.total_projects,
        projects_with_status=result.projects_with_status,
        projects_without_status=result.projects_without_status,
        projects_with_risk=result.projects_with_risk,
        projects_without_risk=result.projects_without_risk,
        projects_with_status_and_risk=result.projects_with_status_and_risk,
        projects_without_any_evidence=result.projects_without_any_evidence,
        cited_evidence=[
            ExecutiveCitedEvidence(
                project_id=item.metadata["project_id"],
                project_name=item.metadata["project_name"],
                source_analysis_id=item.source_id,
                kind=item.metadata["kind"],
                created_at=item.metadata["created_at"],
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )


@router.post("/strategy-advisor/ask", response_model=StrategyAdvisorResponse)
def ask_strategy_advisor(
    request: StrategyAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    domain_service: DomainService = Depends(build_domain_service),
    # Read-only, same permission already protecting Risk/Delivery/Portfolio/
    # PMO/Executive Advisor -- this agent never creates/edits/triggers an
    # analysis, never creates/alters strategy.
    _permission: None = Depends(require_permission("intelligence.read")),
):
    # Classe B, fourth of its kind, eighth and last Advisor of Wave 5
    # (Advisor Specification/Domain Blueprint/AR-15/Technical Design):
    # composition of declared strategy (Portfolio/Program/Project's own
    # objective field) plus execution evidence (kind="status"/"risk",
    # aggregated per unit from the same per-Project gather_context() calls)
    # happens entirely inside StrategyEvidenceAssembler -- never inside
    # AdvisorFramework/AIContextEngine. Organizational scope always
    # resolves via the session, so there is no 404 case here.
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)
    assembler = StrategyEvidenceAssembler(domain_service, framework)

    result = assembler.assemble(session.organization_id)

    agent = StrategyAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            result.evidence,
            no_evidence_answer="Nenhum objetivo declarado ou evidência de execução comparável registrada para esta organização.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _strategy_advisor_response(explanation, result)


def _strategy_advisor_response(
    explanation, result: StrategyAssemblyResult
) -> StrategyAdvisorResponse:
    return StrategyAdvisorResponse(
        answer=explanation.recommendation.answer,
        portfolios_total=result.portfolios_total,
        portfolios_with_declared_strategy=result.portfolios_with_declared_strategy,
        portfolios_without_declared_strategy=result.portfolios_without_declared_strategy,
        portfolios_with_execution_evidence=result.portfolios_with_execution_evidence,
        portfolios_comparable=result.portfolios_comparable,
        portfolios_with_strategy_without_execution=result.portfolios_with_strategy_without_execution,
        programs_total=result.programs_total,
        programs_with_declared_strategy=result.programs_with_declared_strategy,
        programs_without_declared_strategy=result.programs_without_declared_strategy,
        programs_with_execution_evidence=result.programs_with_execution_evidence,
        programs_comparable=result.programs_comparable,
        programs_with_strategy_without_execution=result.programs_with_strategy_without_execution,
        projects_total=result.projects_total,
        projects_with_declared_strategy=result.projects_with_declared_strategy,
        projects_without_declared_strategy=result.projects_without_declared_strategy,
        projects_with_execution_evidence=result.projects_with_execution_evidence,
        projects_comparable=result.projects_comparable,
        projects_with_strategy_without_execution=result.projects_with_strategy_without_execution,
        cited_evidence=[_strategy_cited_evidence(item) for item in explanation.recommendation.cited_evidence],
    )


def _strategy_cited_evidence(item: Evidence) -> StrategyCitedEvidence:
    # Technical Design §4.3 -- the synthetic Evidence.source_id (used only
    # internally by RecommendationEngine.build() to correlate citations,
    # §10.2) is read HERE exactly once, only to be discarded: for
    # kind="declared_strategy" the real identity always comes from
    # metadata["real_entity_id"], never item.source_id.
    kind = item.metadata["kind"]
    if kind == "declared_strategy":
        source_id = item.metadata["real_entity_id"]
        created_at = None
    else:
        source_id = item.source_id
        created_at = item.metadata["created_at"]
    return StrategyCitedEvidence(
        level=item.metadata["level"],
        entity_id=item.metadata["real_entity_id"],
        entity_name=item.metadata["entity_name"],
        kind=kind,
        source_id=source_id,
        created_at=created_at,
    )


@router.post("/document-advisor/ask", response_model=DocumentAdvisorResponse)
def ask_document_advisor(
    request: DocumentAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    # Read-only: reuses knowledge.read (already granted since W5-0), the
    # permission that already protects reading indexed documents -- this
    # Advisor never creates/edits a document (Technical Design §7).
    _permission: None = Depends(require_permission("knowledge.read")),
):
    # Epic W5-1 (Document Advisor) -- see
    # docs/architecture/TECHNICAL-DESIGN-DOCUMENT-ADVISOR.md.
    # Knowledge Platform -> RAG Pipeline -> normalize_rag_evidence() ->
    # AdvisorFramework.run() -> Document Advisor -> LLM -> resposta
    # fundamentada, citando document_id/chunk_id reais.
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)

    rag_context = framework.gather_rag_context(session.organization_id, request.question, top_k=5)
    evidence = framework.normalize_rag_evidence(rag_context)
    logger.info(
        "Document Advisor question organization_id=%s rag_chunk_ids=%s",
        session.organization_id,
        sorted(rag_context.chunk_ids),
    )

    agent = DocumentAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            evidence,
            rag_context=rag_context,
            no_evidence_answer="Nenhum documento relevante foi encontrado para responder a esta pergunta.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _document_advisor_response(explanation)


def _document_advisor_response(explanation) -> DocumentAdvisorResponse:
    return DocumentAdvisorResponse(
        answer=explanation.recommendation.answer,
        cited_chunks=[
            CitedChunk(
                document_id=item.metadata["document_id"],
                chunk_id=item.source_id,
                source_label=item.source_label,
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )


@router.post("/governance-advisor/ask", response_model=GovernanceAdvisorResponse)
def ask_governance_advisor(
    request: GovernanceAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    # Read-only: reuses knowledge.read, same justification as the Document
    # Advisor (Technical Design §6) -- never creates/edits a document.
    _permission: None = Depends(require_permission("knowledge.read")),
):
    # Epic seguinte da Wave 5 (Governance Advisor) -- see
    # docs/architecture/TECHNICAL-DESIGN-GOVERNANCE-ADVISOR.md.
    # Knowledge Platform -> RAG Pipeline -> normalize_rag_evidence() ->
    # AdvisorFramework.run() (byte-for-byte unchanged) -> Governance Advisor
    # -> LLM -> resposta fundamentada, com classificação institucional
    # (§4/§5 do Technical Design) extraída aqui, na rota, nunca no Framework.
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)

    rag_context = framework.gather_rag_context(session.organization_id, request.question, top_k=5)
    evidence = framework.normalize_rag_evidence(rag_context)
    logger.info(
        "Governance Advisor question organization_id=%s rag_chunk_ids=%s",
        session.organization_id,
        sorted(rag_context.chunk_ids),
    )

    agent = GovernanceAdvisorAgent(framework)
    try:
        explanation = framework.run(
            agent,
            session,
            request.question,
            evidence,
            rag_context=rag_context,
            no_evidence_answer="[SEM EVIDÊNCIA]\nNenhuma referência de governança relevante foi encontrada para responder a esta pergunta.",
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _governance_advisor_response(explanation)


def _governance_advisor_response(explanation) -> GovernanceAdvisorResponse:
    classification, answer = _parse_governance_classification(explanation.recommendation.answer)
    return GovernanceAdvisorResponse(
        answer=answer,
        classification=classification,
        cited_chunks=[
            CitedChunk(
                document_id=item.metadata["document_id"],
                chunk_id=item.source_id,
                source_label=item.source_label,
            )
            for item in explanation.recommendation.cited_evidence
        ],
    )


# -- Decision Support -- first production consumer of the Executive
# Orchestrator (D-147/D-152; TECHNICAL-DESIGN-DECISION-SUPPORT.md) --------


class ExplicitScope(BaseModel):
    """Executive Intelligence Explicit Scope (Founder Decision --
    Eliminação do Risco de Escopo Implícito; Vision, Princípio 13): a scope
    is always one of exactly three declared types, never inferred from
    absence. `organization` is a valid, intentional scope -- never an
    implicit fallback from an omitted `project_id`/`portfolio_id`. Shared,
    unchanged, by every Executive Intelligence Capability that requires a
    scope (Decision Support, Executive Narrative) -- never duplicated
    (Technical Design -- Executive Narrative, §5.2)."""

    type: Literal["project", "portfolio", "organization"]
    project_id: int | None = None
    portfolio_id: int | None = None

    @model_validator(mode="after")
    def _validate_combination(self) -> "ExplicitScope":
        if self.type == "project":
            if self.project_id is None:
                raise ValueError("project_id is required when scope.type is 'project'")
            if self.portfolio_id is not None:
                raise ValueError("portfolio_id must not be set when scope.type is 'project'")
        elif self.type == "portfolio":
            if self.portfolio_id is None:
                raise ValueError("portfolio_id is required when scope.type is 'portfolio'")
            if self.project_id is not None:
                raise ValueError("project_id must not be set when scope.type is 'portfolio'")
        else:  # organization
            if self.project_id is not None or self.portfolio_id is not None:
                raise ValueError(
                    "project_id/portfolio_id must not be set when scope.type is 'organization'"
                )
        return self


class DecisionSupportRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    # No default -- absence of `scope` is a 422 (Pydantic: required field),
    # never interpreted as organization scope (Technical Design §3).
    scope: ExplicitScope

    _validate_question = field_validator("question")(_ensure_has_content)


class ExecutiveIntelligenceCitation(BaseModel):
    """Shared by every Executive Intelligence Capability's response --
    identical shape for Decision Support and Executive Narrative, never
    duplicated."""

    advisor_name: str
    source_type: str
    source_id: int
    source_label: str


class ExecutiveIntelligenceAdvisorExecution(BaseModel):
    advisor_name: str
    had_evidence: bool


class ExecutiveIntelligenceCorrelation(BaseModel):
    advisor_names: tuple[str, str]
    is_structural_pair: bool


class ExecutiveIntelligenceCompositionTrace(BaseModel):
    selection_signals: list[str]
    selected_advisor_names: list[str]
    advisors_used: list[ExecutiveIntelligenceAdvisorExecution]
    correlations: list[ExecutiveIntelligenceCorrelation]
    synthesis_source_advisor_names: list[str] | None


class DecisionSupportResponse(BaseModel):
    capability: str
    insufficient_basis: bool
    insufficient_basis_reason: str | None
    answer: str | None
    advisors_used: list[str]
    citations: list[ExecutiveIntelligenceCitation]
    composition_trace: ExecutiveIntelligenceCompositionTrace


class ExecutiveNarrativeRequest(BaseModel):
    """Never accepts `question` or any free text (Technical Design --
    Executive Narrative, §2/§5.2) -- the only input is an explicitly
    declared scope."""

    scope: ExplicitScope


class ExecutiveNarrativeResponse(BaseModel):
    capability: str
    scope: ExplicitScope
    insufficient_basis: bool
    insufficient_basis_reason: str | None
    narrative: str | None
    advisors_used: list[str]
    citations: list[ExecutiveIntelligenceCitation]
    composition_trace: ExecutiveIntelligenceCompositionTrace


# Fixed internal prompt for Executive Narrative -- never user-configurable,
# never exposed in the contract (Technical Design §6): a single synthesis-
# eliciting text passed identically to every selected Advisor and to
# synthesize(), exactly the way `request.question` already is for Decision
# Support -- no change to either signature.
EXECUTIVE_NARRATIVE_PROMPT = (
    "Produza uma síntese executiva do estado atual deste escopo, cobrindo riscos, "
    "entrega e quaisquer sinais relevantes segundo a evidência disponível."
)


def resolve_decision_support_scope(
    scope: ExplicitScope,
    organization_id: int,
    domain_service: DomainService,
) -> OrchestrationScope:
    """Boundary-only identity resolution + organizational ownership check
    (Founder Decision -- Explicit Scope; Technical Design §5/§8) -- never a
    domain decision, purely translates an already-validated `scope` into
    the `OrchestrationScope` the Executive Orchestrator already accepts,
    itself unchanged (Technical Design §6.1, Decisão A). `project_id`/
    `portfolio_id` given but belonging to another organization is reported
    as not-found, never confirmed as existing elsewhere -- the same
    `DomainService.get_project()`/`get_portfolio()` already used by
    `ExecutiveEvidenceAssembler`/`PortfolioEvidenceAssembler`."""
    if scope.type == "project":
        project = domain_service.get_project(scope.project_id, organization_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return OrchestrationScope(project_name=project.name)
    if scope.type == "portfolio":
        portfolio = domain_service.get_portfolio(scope.portfolio_id, organization_id)
        if portfolio is None:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return OrchestrationScope(portfolio_id=portfolio.id)
    return OrchestrationScope()


@router.post("/decision-support/ask", response_model=DecisionSupportResponse)
def ask_decision_support(
    request: DecisionSupportRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    orchestrator_prompts: PromptRegistry = Depends(build_orchestrator_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    domain_service: DomainService = Depends(build_domain_service),
    # Read-only, same permission already protecting all 8 Advisors --
    # Decision Support never creates/edits/triggers an analysis, never
    # persists anything.
    _permission: None = Depends(require_permission("intelligence.read")),
) -> DecisionSupportResponse:
    # First production consumer of the Executive Orchestrator (D-147),
    # first functional Wave 6 Capability (AR-17 §2: Seleção -> Execução ->
    # Correlação -> Síntese). A thin adapter (Technical Design §2): never
    # selects Advisors, never correlates, never synthesizes, never accesses
    # evidence/Domain/Knowledge Platform directly -- all of that stays
    # exclusively inside ExecutiveOrchestrator/AdvisorFramework/the 8
    # Advisors, all preserved unchanged. Explicit Scope (Founder Decision
    # -- Eliminação do Risco de Escopo Implícito; Vision, Princípio 13)
    # resolved and validated (ownership confirmed, 404 on cross-tenant)
    # before ExecutiveOrchestrator.run() is ever invoked.
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    scope = resolve_decision_support_scope(request.scope, session.organization_id, domain_service)

    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)
    orchestrator = ExecutiveOrchestrator(framework, domain_service, provider, orchestrator_prompts)
    signals = SelectionSignals(question=request.question, scope=scope)

    try:
        result = orchestrator.run(Capability.DECISION_SUPPORT, session, request.question, signals)
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _decision_support_response(result)


def _decision_support_response(result) -> DecisionSupportResponse:
    trace = result.composition_trace
    citations = [
        ExecutiveIntelligenceCitation(
            advisor_name=item.advisor_name,
            source_type=evidence.source_type,
            source_id=evidence.source_id,
            source_label=evidence.source_label,
        )
        for item in result.explanations
        for evidence in item.explanation.recommendation.cited_evidence
    ]
    return DecisionSupportResponse(
        capability=result.capability.value,
        insufficient_basis=result.is_insufficient_basis,
        insufficient_basis_reason=(
            result.insufficient_basis_reason.value if result.insufficient_basis_reason else None
        ),
        answer=result.synthesis,
        advisors_used=[identity.name for identity in result.advisor_identities],
        citations=citations,
        composition_trace=ExecutiveIntelligenceCompositionTrace(
            selection_signals=list(trace.selection.signals),
            selected_advisor_names=list(trace.selection.selected_advisor_names),
            advisors_used=[
                ExecutiveIntelligenceAdvisorExecution(
                    advisor_name=entry.advisor_name, had_evidence=entry.had_evidence
                )
                for entry in trace.executions
            ],
            correlations=[
                ExecutiveIntelligenceCorrelation(
                    advisor_names=entry.advisor_names, is_structural_pair=entry.is_structural_pair
                )
                for entry in trace.correlations
            ],
            synthesis_source_advisor_names=(
                list(trace.synthesis.source_advisor_names) if trace.synthesis else None
            ),
        ),
    )


@router.post("/executive-narrative/generate", response_model=ExecutiveNarrativeResponse)
def generate_executive_narrative(
    request: ExecutiveNarrativeRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    orchestrator_prompts: PromptRegistry = Depends(build_orchestrator_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    domain_service: DomainService = Depends(build_domain_service),
    # Read-only, same permission already protecting Decision Support and all
    # 8 Advisors -- Executive Narrative never creates/edits/triggers an
    # analysis, never persists anything.
    _permission: None = Depends(require_permission("intelligence.read")),
) -> ExecutiveNarrativeResponse:
    # Second production consumer of the Executive Orchestrator (Technical
    # Design -- Executive Narrative). A thin adapter, same shape as
    # ask_decision_support: never selects Advisors, never correlates, never
    # synthesizes, never accesses evidence/Domain/Knowledge Platform
    # directly. Explicit Scope resolved/validated before
    # ExecutiveOrchestrator.run() is ever invoked. Unlike Decision Support,
    # no free-text question is ever accepted -- `explicit` is populated with
    # every Advisor Identity in the catalog, so the scope-eligibility table
    # already approved for Decision Support (`ADVISOR_ELIGIBLE_SCOPES`,
    # `catalog.py`, unmodified) does the entire selection, never lexical
    # matching against user text (Technical Design §4).
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    scope = resolve_decision_support_scope(request.scope, session.organization_id, domain_service)

    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)
    orchestrator = ExecutiveOrchestrator(framework, domain_service, provider, orchestrator_prompts)
    signals = SelectionSignals(
        explicit=frozenset(identity.name for identity in ADVISOR_IDENTITY_CATALOG),
        scope=scope,
    )

    try:
        result = orchestrator.run(
            Capability.EXECUTIVE_NARRATIVE, session, EXECUTIVE_NARRATIVE_PROMPT, signals
        )
    except AdvisorExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _executive_narrative_response(result, request.scope)


def _executive_narrative_response(result, scope: ExplicitScope) -> ExecutiveNarrativeResponse:
    trace = result.composition_trace
    citations = [
        ExecutiveIntelligenceCitation(
            advisor_name=item.advisor_name,
            source_type=evidence.source_type,
            source_id=evidence.source_id,
            source_label=evidence.source_label,
        )
        for item in result.explanations
        for evidence in item.explanation.recommendation.cited_evidence
    ]
    return ExecutiveNarrativeResponse(
        capability=result.capability.value,
        scope=scope,
        insufficient_basis=result.is_insufficient_basis,
        insufficient_basis_reason=(
            result.insufficient_basis_reason.value if result.insufficient_basis_reason else None
        ),
        narrative=result.synthesis,
        advisors_used=[identity.name for identity in result.advisor_identities],
        citations=citations,
        composition_trace=ExecutiveIntelligenceCompositionTrace(
            selection_signals=list(trace.selection.signals),
            selected_advisor_names=list(trace.selection.selected_advisor_names),
            advisors_used=[
                ExecutiveIntelligenceAdvisorExecution(
                    advisor_name=entry.advisor_name, had_evidence=entry.had_evidence
                )
                for entry in trace.executions
            ],
            correlations=[
                ExecutiveIntelligenceCorrelation(
                    advisor_names=entry.advisor_names, is_structural_pair=entry.is_structural_pair
                )
                for entry in trace.correlations
            ],
            synthesis_source_advisor_names=(
                list(trace.synthesis.source_advisor_names) if trace.synthesis else None
            ),
        ),
    )
