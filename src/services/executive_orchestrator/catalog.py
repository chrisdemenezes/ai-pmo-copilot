"""The closed catalog of the 8 Advisor Identities (Domain Blueprint §2.1,
D-138; AR-17 §7 -- "hoje, exatamente oito") and the fixed, versioned
vocabulary the Selection Rule (§2.1, Technical Design) evaluates signals
against.

Nothing here is invented: `name` matches the exact string each
`AdvisorContract` implementation already exposes; `description` is a
one-line restatement of what each Advisor's own Advisor Specification (or,
for Risk Advisor -- which predates that convention -- its own docstring in
`src/agents/risk_advisor/agent.py`) already declares publicly. Changing
this catalog or its vocabulary is a governance event (Decision Log), never
a silent code edit (Technical Design §2.3).
"""
from src.services.executive_orchestrator.types import AdvisorIdentity

ADVISOR_IDENTITY_CATALOG: tuple[AdvisorIdentity, ...] = (
    AdvisorIdentity(
        name="risk_advisor",
        description="Sintetiza riscos já identificados de um projeto -- nunca cria ou infere um novo risco.",
    ),
    AdvisorIdentity(
        name="delivery_advisor",
        description="Sintetiza o estado de entrega de um projeto a partir de ações, riscos e histórico já existentes.",
    ),
    AdvisorIdentity(
        name="portfolio_advisor",
        description="Avalia equilíbrio, dependências e sobreposição entre os projetos de um Portfolio específico.",
    ),
    AdvisorIdentity(
        name="pmo_advisor",
        description="Relata se o processo de acompanhamento de status é seguido pelos projetos da organização -- nunca decide composição de portfólio.",
    ),
    AdvisorIdentity(
        name="executive_advisor",
        description="Síntese executiva do que exige atenção da liderança agora, combinando status e risco, sem referência a estratégia declarada.",
    ),
    AdvisorIdentity(
        name="strategy_advisor",
        description="Responde se a execução continua alinhada com a estratégia declarada de Portfolio/Program/Project -- nunca 'o que exige atenção agora'.",
    ),
    AdvisorIdentity(
        name="document_advisor",
        description="Responde perguntas pontuais sobre o conteúdo de documentos já indexados, citando document_id/chunk_id reais.",
    ),
    AdvisorIdentity(
        name="governance_advisor",
        description="Responde perguntas de conformidade/governança sobre documentos já indexados, classificando institucionalmente a resposta.",
    ),
)

# Fixed, versioned vocabulary for implicit signal matching (Technical Design
# §2.1.2) -- lowercase terms only, matched as substrings of the question
# text. Overlap between Advisors is expected and legitimate (more than one
# Advisor may be relevant to the same question); it is never resolved here.
VOCABULARY: dict[str, frozenset[str]] = {
    "risk_advisor": frozenset({"risco", "riscos", "mitigação", "ameaça", "escalação"}),
    "delivery_advisor": frozenset({"entrega", "status", "andamento", "progresso"}),
    "portfolio_advisor": frozenset({"portfólio", "portfolio", "equilíbrio", "sobreposição"}),
    "pmo_advisor": frozenset({"pmo", "processo de acompanhamento", "acompanhamento"}),
    "executive_advisor": frozenset({"liderança", "atenção da liderança", "executivo"}),
    "strategy_advisor": frozenset({"estratégia", "estratégico", "alinhamento", "objetivo declarado"}),
    "document_advisor": frozenset({"documento", "documentos", "runbook"}),
    "governance_advisor": frozenset({"governança", "conformidade", "política"}),
}

# The one structural precondition among the 8 Advisor Identities: the
# Portfolio Advisor's own existing HTTP contract already requires a
# `portfolio_id` (`PortfolioAdvisorRequest.portfolio_id`) -- without one, it
# cannot be invoked at all (Technical Design §1.1: "scope organizacional
# explícito"). Folded into Selection, never into Execution, so every
# Advisor Identity that reaches Execution is always fully provisionable.
ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID: frozenset[str] = frozenset({"portfolio_advisor"})

# Scope eligibility (Founder Decision -- Explicit Scope / Decision Support,
# TECHNICAL-DESIGN-DECISION-SUPPORT.md §6.2, approved without reservation):
# of the 8 Advisor Identities, only 3 actually consume `OrchestrationScope`
# in `provisioning.py` (risk_advisor/delivery_advisor filter by
# `project_name`; portfolio_advisor requires `portfolio_id`) -- the other 5
# are unconditionally organization-scoped by their own Wave 5 design
# (`PMOEvidenceAssembler`/`ExecutiveEvidenceAssembler`/
# `StrategyEvidenceAssembler`.assemble(organization_id) and
# `gather_rag_context(organization_id, ...)` for Document/Governance never
# receive a scope parameter at all). This table is the single source of
# truth for which `scope.type` ("project"/"portfolio"/"organization") each
# Advisor Identity may be selected under, so that none ever produces
# evidence broader than the scope explicitly declared by the caller.
# Nothing here changes what evidence an Advisor gathers -- only whether it
# is eligible for Selection under a given scope.
ADVISOR_ELIGIBLE_SCOPES: dict[str, frozenset[str]] = {
    "risk_advisor": frozenset({"project", "organization"}),
    "delivery_advisor": frozenset({"project", "organization"}),
    # "organization" is included per the Founder's own eligibility table
    # (Founder Decision -- Explicit Scope / Decision Support §3: "todos os
    # 8 Enterprise Advisors" under scope=organization) -- but Portfolio
    # Advisor is never actually *selected* under scope=organization in
    # practice, because the older, untouched structural precondition
    # (`ADVISOR_NAMES_REQUIRING_PORTFOLIO_ID`, D-143) independently
    # requires a `portfolio_id`, never present under scope=organization.
    # This table only says scope *type* organization does not, by itself,
    # exclude Portfolio Advisor -- it never grants it a new organization-
    # wide evidence-gathering mode (no Advisor is altered, Founder §3/§6).
    "portfolio_advisor": frozenset({"portfolio", "organization"}),
    "pmo_advisor": frozenset({"organization"}),
    "executive_advisor": frozenset({"organization"}),
    "strategy_advisor": frozenset({"organization"}),
    "document_advisor": frozenset({"organization"}),
    "governance_advisor": frozenset({"organization"}),
}
