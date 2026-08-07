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
