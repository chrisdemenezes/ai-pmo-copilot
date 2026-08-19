# Technical Design — Epic W3-2: Digital PMO Intelligence Foundation

**Base:** `DOMAIN-BLUEPRINT-W3-2-Digital-PMO-Intelligence-Foundation.md` (aprovado), `AR-3-W3-2-DIGITAL-PMO-FOUNDATION-REVIEW.md` (aprovado sem ressalvas).
**Status:** resolve os contratos públicos do Blueprint em código concreto. Nenhuma implementação ainda — segue imediatamente após este documento, sem nova autorização (nenhum conflito arquitetural encontrado na Revisão).

---

## 1. Novo pacote

```
src/services/ai_foundation/
  __init__.py
  types.py                # Evidence, SessionContext, Recommendation, Explanation
  context_engine.py       # AIContextEngine
  recommendation_engine.py# RecommendationEngine
  explanation_engine.py   # ExplanationEngine
  prompt_composer.py      # render_analyst_prompt
  audit_integration.py    # AIFoundationAudit
  observability.py        # ObservabilityRecorder, TokenUsage
  prompts/
    analyst_preamble.md   # preâmbulo institucional único, prependado a todo prompt de Analyst
```

Local escolhido: `src/services/` já é a pasta oficial de serviços de aplicação (`ProjectSummaryService`, `AdministrationService` já vivem lá) — um subpacote, não uma nova pasta de topo (CLAUDE.md: nunca criar arquitetura paralela).

## 2. `types.py`

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Evidence:
    source_analysis_id: int
    source_created_at: datetime
    kind: str
    summary: dict


@dataclass(frozen=True)
class SessionContext:
    organization_id: int
    user_id: int
    session_id: str
    project_name: str | None = None


@dataclass(frozen=True)
class Recommendation:
    answer: str
    cited_evidence: list[Evidence] = field(default_factory=list)


@dataclass(frozen=True)
class Explanation:
    recommendation: Recommendation
    rationale: str
```

`SessionContext` é construído em cada rota a partir do `RequestContext` já resolvido:
```python
session = SessionContext(
    organization_id=context.organization.organization_id,
    user_id=context.user.user_id,
    session_id=context.session.session_id,  # já existe em RequestContext
    project_name=request.project_name,
)
```

## 3. `context_engine.py`

```python
class AIContextEngine:
    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def gather(self, organization_id: int, project_name: str | None, kind: str) -> list[Evidence]:
        records = self._repository.list_analyses(
            organization_id=organization_id, project_name=project_name, kind=kind, limit=None,
        )
        evidence: list[Evidence] = []
        for record in records:
            model_output = (record.payload or {}).get("model_output")
            if not isinstance(model_output, dict) or not model_output.get("structured"):
                continue
            evidence.append(
                Evidence(
                    source_analysis_id=record.id,
                    source_created_at=record.created_at,
                    kind=kind,
                    summary=model_output,
                )
            )
        return evidence
```

Nota: para o caso do Risk Advisor, `summary` carrega o `model_output` inteiro de uma análise de risco (`{"risks": [...], "escalation_recommendation": ...}`), não um único risco — o Risk Advisor extrai os riscos individuais de dentro de `summary["risks"]` ao montar seu prompt, exatamente como faz hoje via `ProjectSummaryService.list_latest_risks`. Isso mantém `AIContextEngine` genuinamente agnóstico ao formato interno de cada `kind`, delegando a interpretação ao Analyst (Blueprint §6).

## 4. `recommendation_engine.py`

```python
class RecommendationEngine:
    NO_EVIDENCE_ANSWER = "Nenhuma evidência identificada ainda para este projeto."

    @staticmethod
    def no_evidence() -> Recommendation:
        return Recommendation(answer=RecommendationEngine.NO_EVIDENCE_ANSWER, cited_evidence=[])

    @staticmethod
    def build(answer: str, cited_ids: list[int], evidence: list[Evidence]) -> Recommendation:
        by_id = {item.source_analysis_id: item for item in evidence}
        cited = [by_id[i] for i in cited_ids if i in by_id]  # nunca aceita id inventado
        return Recommendation(answer=answer, cited_evidence=cited)
```

## 5. `explanation_engine.py`

```python
class ExplanationEngine:
    RATIONALE_TEMPLATE = (
        "Síntese informativa baseada em {count} evidência(s) já registrada(s) -- "
        "não é uma decisão automática (ADR-V2-007)."
    )

    @staticmethod
    def explain(recommendation: Recommendation) -> Explanation:
        rationale = ExplanationEngine.RATIONALE_TEMPLATE.format(
            count=len(recommendation.cited_evidence)
        )
        return Explanation(recommendation=recommendation, rationale=rationale)
```

## 6. `prompt_composer.py`

```python
def render_analyst_prompt(
    prompt_registry: PromptRegistry, agent_name: str, prompt_name: str, **variables: str
) -> str:
    preamble_path = Path(__file__).parent / "prompts" / "analyst_preamble.md"
    preamble = preamble_path.read_text(encoding="utf-8")
    template = prompt_registry.get(agent_name, prompt_name)
    return Template(f"{preamble}\n\n{template}").safe_substitute(**variables)
```

`prompts/analyst_preamble.md` (novo, único, compartilhado):
```
You are part of the STRATECH Digital PMO Intelligence Foundation.

STRATECH is an Executive Decision Operating System, not a chatbot and not an
autonomous agent. You operate as a Digital PMO: you synthesize institutional
data already collected, you never decide anything, and you never invent
information beyond what is provided below. Executives always make the final
decision.
```

`PromptRegistry.get()` permanece exatamente como está — `render_analyst_prompt` só compõe por cima dela.

## 7. `audit_integration.py`

```python
class AIFoundationAudit:
    @staticmethod
    def record_question(
        repository: AnalysisRepository, session: SessionContext, analyst_name: str, question: str
    ) -> None:
        repository.administration.record_audit(
            session.organization_id,
            session.user_id,
            f"{analyst_name}.question_asked",
            "project",
            None,
            {"project_name": session.project_name, "question": question},
        )
```

Mesma ação e mesmo payload que `ask_risk_advisor` já grava hoje (`risk_advisor.question_asked`) — nenhuma mudança de comportamento observável, apenas centralização.

## 8. `observability.py`

```python
@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int


class ObservabilityRecorder:
    @staticmethod
    def record_call(analyst_name: str, session: SessionContext, fn: Callable[[], str]) -> str:
        started = time.monotonic()
        result = fn()
        elapsed_ms = round((time.monotonic() - started) * 1000, 1)
        usage = getattr(fn, "__self__", None)  # ver nota abaixo
        logger.info(
            "AI Foundation call analyst=%s organization_id=%s latency_ms=%s",
            analyst_name, session.organization_id, elapsed_ms,
        )
        return result
```

Correção de desenho em relação ao Blueprint (achado durante a Technical Design, não uma mudança de escopo): `fn` é `lambda: provider.generate(prompt)` -- um closure sem acesso direto ao provider para ler `last_usage` depois da chamada. `ObservabilityRecorder.record_call` recebe o `provider` explicitamente, não um `Callable` opaco:

```python
class ObservabilityRecorder:
    @staticmethod
    def record_call(analyst_name: str, session: SessionContext, provider: LLMProvider, prompt: str) -> str:
        started = time.monotonic()
        result = provider.generate(prompt)
        elapsed_ms = round((time.monotonic() - started) * 1000, 1)
        usage = getattr(provider, "last_usage", None)
        logger.info(
            "AI Foundation call analyst=%s organization_id=%s latency_ms=%s input_tokens=%s output_tokens=%s",
            analyst_name,
            session.organization_id,
            elapsed_ms,
            usage.input_tokens if usage else None,
            usage.output_tokens if usage else None,
        )
        return result
```

## 9. `ProductionLLMProvider` — extensão aditiva

```python
@dataclass
class ProductionLLMProvider:
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 1200
    env_var: str = "ANTHROPIC_API_KEY"
    last_usage: TokenUsage | None = field(default=None, init=False, repr=False)

    def generate(self, prompt: str) -> str:
        ...
        message = client.messages.create(...)
        self.last_usage = TokenUsage(
            input_tokens=message.usage.input_tokens, output_tokens=message.usage.output_tokens,
        )
        return "\n".join(...)
```

`MockLLMProvider` não implementa `last_usage` — `getattr(provider, "last_usage", None)` em `ObservabilityRecorder` trata a ausência como "sem dado de custo disponível", nunca como erro. `LLMProvider` Protocol (`generate(self, prompt: str) -> str`) permanece **inalterado** — `last_usage` é um detalhe de implementação de `ProductionLLMProvider`, não parte do contrato estrutural.

## 10. Migração do Risk Advisor (`ask_risk_advisor`)

```python
@router.post("/risk-advisor/ask", response_model=RiskAdvisorResponse)
def ask_risk_advisor(
    request: RiskAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
        project_name=request.project_name,
    )
    context_engine = AIContextEngine(repository)
    evidence = context_engine.gather(session.organization_id, session.project_name, kind="risk")

    AIFoundationAudit.record_question(repository, session, "risk_advisor", request.question)

    if not evidence:
        explanation = ExplanationEngine.explain(RecommendationEngine.no_evidence())
        return _to_response(explanation)

    agent = RiskAdvisorAgent(model_client=provider, prompt_registry=prompts)
    result = agent.advise(question=request.question, evidence=evidence)
    model_output = result["model_output"]
    if not model_output.get("structured") or not isinstance(model_output.get("answer"), str):
        raise HTTPException(status_code=502, detail="Risk Advisor returned an invalid response")

    recommendation = RecommendationEngine.build(
        model_output["answer"], model_output.get("cited_analysis_ids") or [], evidence,
    )
    explanation = ExplanationEngine.explain(recommendation)
    return _to_response(explanation)


def _to_response(explanation: Explanation) -> RiskAdvisorResponse:
    return RiskAdvisorResponse(
        answer=explanation.recommendation.answer,
        cited_analyses=[
            CitedAnalysis(source_analysis_id=e.source_analysis_id, source_created_at=e.source_created_at)
            for e in explanation.recommendation.cited_evidence
        ],
    )
```

`RiskAdvisorAgent.advise` muda de assinatura (`risks: list[dict]` → `evidence: list[Evidence]`), extraindo `risks`/`escalation_recommendation` de `evidence[i].summary` ao montar `risks_json`, e chamando `render_analyst_prompt` (Foundation) em vez de `prompt_registry.get` direto, e `ObservabilityRecorder.record_call` em vez de `model_client.generate` direto. **Contrato HTTP (`RiskAdvisorRequest`/`RiskAdvisorResponse`) inalterado** — nenhuma migração de BFF/frontend necessária.

## 11. Plano de testes

- **Unitários** (`tests/test_ai_foundation/`): um arquivo por componente -- `test_context_engine.py`, `test_recommendation_engine.py` (inclui o caso de id inventado sendo descartado), `test_explanation_engine.py`, `test_prompt_composer.py`, `test_audit_integration.py`, `test_observability.py` (latência + tokens capturados, e ausência de `last_usage` tratada), `test_production_llm_provider_usage.py`.
- **Integração**: `tests/test_intelligence_api.py::TestRiskAdvisor` (já existente) roda inalterado contra a rota migrada -- prova que o contrato HTTP, RBAC, isolamento organizacional e auditoria continuam corretos após a refatoração.
- **E2E**: o teste Playwright já existente (`e2e/workspace.spec.ts` -- "Risk Advisor answers a question...") roda inalterado -- prova ponta-a-ponta que a migração não regrediu o comportamento visível ao usuário.

## 12. Fora de escopo (reafirmado do Blueprint §3)

Vector Store, pgvector, embeddings, RAG, Knowledge Platform, Executive Memory permanente, Multi-Agent Framework, planejamento/reflexão/auto-execução autônomos, agentes colaborativos, Model Registry, Provider Router, Prompt Versioning -- nenhum introduzido.
