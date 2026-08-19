# Technical Design — Portfolio Advisor (etapa 4 de 6)

**Autorização:** "Founder Decision — AR-12 Portfolio Advisor" (veredito **APPROVED — GO para o Technical Design**), oficializando: (1) cada Project contribui exatamente uma `Evidence` (`evidence[0]`, per `created_at` DESC), e o `PortfolioEvidenceAssembler` não pode interpretar conteúdo, comparar `health_status`, calcular tendência, atribuir pesos, ou selecionar registros por regra adicional; (2) a distinção Delivery Advisor (histórico completo, trajetória) vs. Portfolio Advisor (estado atual, comparação transversal) permanece; (3) a ordem Programs→Projects é incidental — o prompt deve instruir explicitamente que as evidências formam um conjunto, sem prioridade por posição; (4) o modelo de resposta deve informar total de Projects, Projects com evidência, Projects sem evidência, e limitações quando a cobertura for parcial — nunca generalizar; (5) rastreabilidade mínima por `Evidence.metadata` (`portfolio_id`/`program_id`/`project_id`/`project_name`/`source_id`/`created_at`), nenhuma alteração ao contrato `Evidence`; (6) limites funcionais — o Advisor avalia apenas estado consolidado atual, distribuição de saúde, concentração de criticidade, Projects que exigem atenção, cobertura de evidências — nunca tendência histórica consolidada do Portfolio; (7) gatilho de performance mantido (>20 chamadas sequenciais ou p95 > 3s), nenhuma otimização antecipada; (8) preservar integralmente `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline/`RecommendationEngine`/`ExplanationEngine`. Nenhum código escrito nesta etapa.

---

## Executive Summary

O Portfolio Advisor reutiliza integralmente o `AdvisorFramework` — `gather_context()` chamado N vezes (uma por Project), `run()` chamado exatamente 1 vez, byte-for-byte como qualquer outro Advisor. O único componente estrutural novo é o `PortfolioEvidenceAssembler` (definido em D-109, confirmado em AR-12): resolve o Portfolio org-scoped via `DomainService`, lista Programs/Projects (Wave 2, já em produção), solicita a evidência de status mais recente de cada Project via `AdvisorFramework.gather_context()`, seleciona mecanicamente `evidence[0]` (nunca interpreta), enriquece `Evidence.metadata` com `portfolio_id`/`program_id`/`project_id`/`project_name` (campo já genérico, nenhuma mudança ao contrato `Evidence`), e devolve tanto a evidência consolidada quanto as contagens de cobertura (`total_projects`/`projects_with_evidence`) — nunca calculadas pelo LLM, sempre pelo próprio Assembler, por contagem estrutural. O `PortfolioAdvisorResponse` expõe essas contagens como campos estruturados, permitindo ao cliente (e ao Founder) verificar a cobertura sem depender da honestidade da narrativa do modelo — o prompt reforça a mesma disciplina em texto, mas os números não vêm do LLM. Recomendação ao final: **GO para a implementação.**

---

## 1. Reuso integral do `AdvisorFramework`/`AIContextEngine` (confirmado, zero mudança)

Idêntico ao já confirmado para Delivery Advisor (D-106 §1) — reafirmado aqui, não redecidido:

- `AdvisorFramework(repository, prompts, provider, rag_pipeline)` — construção idêntica.
- `gather_context(organization_id, project_name, kind="status")` — já existente, chamado N vezes (uma por Project resolvido pelo Assembler), zero mudança de assinatura.
- `run()` — **byte-for-byte inalterado**, chamado exatamente 1 vez com a `evidence` já consolidada.
- `DomainService.get_portfolio()`/`list_programs()`/`list_projects()` (Wave 2) — já existentes, já org-scoped, reutilizados sem extensão.

**Confirmação explícita per diretriz 8:** nenhuma lógica de resolução de portfólio, nenhuma lógica de seleção de evidência mais recente, nenhuma lógica de contagem de cobertura toca `AdvisorFramework`, `AIContextEngine`, Workflow Runtime, Event Pipeline, `RecommendationEngine` ou `ExplanationEngine`. Todo o comportamento novo desta Epic vive em três lugares: o `PortfolioEvidenceAssembler` (composição estrutural, §2), o prompt do `PortfolioAdvisorAgent` (interpretação de domínio, §5), e a rota HTTP (composição de resposta, §6) — nunca no Framework.

---

## 2. `PortfolioEvidenceAssembler` — contrato definitivo

```python
@dataclass(frozen=True)
class PortfolioAssemblyResult:
    evidence: list[Evidence]
    total_projects: int
    projects_with_evidence: int


class PortfolioEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        self._domain_service = domain_service
        self._framework = framework

    def assemble(self, organization_id: int, portfolio_id: int) -> PortfolioAssemblyResult | None:
        portfolio = self._domain_service.get_portfolio(portfolio_id, organization_id)
        if portfolio is None:
            return None  # não existe ou não é desta organização -- rota mapeia para 404

        programs = self._domain_service.list_programs(organization_id, portfolio_id) or []

        evidence: list[Evidence] = []
        total_projects = 0
        projects_with_evidence = 0

        for program in programs:
            projects = self._domain_service.list_projects(organization_id, program.id) or []
            for project in projects:
                total_projects += 1
                project_evidence = self._framework.gather_context(
                    organization_id, project.name, kind="status"
                )
                if not project_evidence:
                    continue  # Project sem AnalysisRecord de status -- não é erro (§7 do Domain Blueprint)

                # Seleção puramente mecânica -- evidence[0] já é garantido ser
                # o mais recente por AnalysisRepository.list_analyses()
                # (created_at DESC, confirmado em AR-11/AR-12). NENHUMA leitura
                # de content, NENHUMA comparação de health_status, NENHUM
                # cálculo, NENHUM peso -- exatamente per diretriz 1 desta
                # autorização.
                most_recent = project_evidence[0]
                evidence.append(
                    Evidence(
                        source_type=most_recent.source_type,
                        source_id=most_recent.source_id,
                        source_label=most_recent.source_label,
                        content=most_recent.content,
                        metadata={
                            **most_recent.metadata,  # created_at, kind -- já existentes
                            "portfolio_id": portfolio.id,
                            "program_id": program.id,
                            "project_id": project.id,
                            "project_name": project.name,
                        },
                    )
                )
                projects_with_evidence += 1

        return PortfolioAssemblyResult(
            evidence=evidence,
            total_projects=total_projects,
            projects_with_evidence=projects_with_evidence,
        )
```

**Confirmação literal das 5 proibições da diretriz 1:** este código nunca lê `content` (não interpreta); nunca compara `health_status` entre itens; nunca calcula tendência (nenhum laço compara dois `Evidence` entre si); nunca atribui peso (cada Project contribui exatamente um item, sem ponderação); nunca seleciona por regra além de "primeiro da lista já ordenada" (nenhum `if`/critério adicional decide qual registro usar).

---

## 3. Fluxo completo

```
Cliente (pergunta em linguagem natural sobre composição/equilíbrio de um portfólio)
  │
  ▼
POST /portfolio-advisor/ask   (src/api/routes/intelligence.py, novo)
  │  RBAC: require_permission("intelligence.read")  -- mesma permissão do
  │  Risk/Delivery Advisor, nenhuma migração nova (definitivo nesta etapa)
  ▼
SessionContext(organization_id, user_id, session_id)  -- sem project_name,
  │  mesma razão do Document/Governance Advisor: escopo é o portfolio_id,
  │  não um único projeto
  ▼
AdvisorFramework(repository, prompts, provider, rag_pipeline)  -- idêntico
DomainService(repository, event_publisher)  -- já existente, Wave 2
PortfolioEvidenceAssembler(domain_service, framework)  -- novo, §2
  │
  ▼
result = assembler.assemble(organization_id, portfolio_id)
  │
  ├─ result is None  →  HTTPException(404)  -- Portfolio não existe ou não
  │      é desta organização (mesmo portão 404-not-403 já estrutural)
  │
  ▼ (result não é None)
agent = PortfolioAdvisorAgent(framework)
framework.run(agent, session, question, result.evidence,
               no_evidence_answer="Nenhuma análise de status registrada para os projetos deste portfólio.")
  │
  ├─ AIFoundationAudit.record_question(...)          -- inalterado
  ├─ if not evidence: RecommendationEngine.no_evidence(...)  -- inalterado,
  │     cobre Portfolio sem Programs/Projects, ou nenhum Project com status
  ├─ PortfolioAdvisorAgent.advise(...)   -- único componente de interpretação (§5)
  ├─ RecommendationEngine.build(answer, cited_analysis_ids, evidence)  -- inalterado
  └─ ExplanationEngine.explain(recommendation)  -- inalterado
  ▼
_portfolio_advisor_response(explanation, result)   -- novo, apenas na rota (§6)
  ▼
PortfolioAdvisorResponse{answer, total_projects, projects_with_evidence,
                          projects_without_evidence, cited_projects: [...]}
```

---

## 4. Contrato do `PortfolioAdvisorAgent` (nenhum contrato novo)

```python
class PortfolioAdvisorAgent:
    name = "portfolio_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(
        self,
        session: SessionContext,
        question: str,
        evidence: list[Evidence],
        rag_context: RagContext | None = None,
    ) -> dict:
        # `evidence` já chega composta pelo PortfolioEvidenceAssembler -- um
        # item por Project, já o mais recente. Este método NUNCA reordena,
        # NUNCA filtra, NUNCA pondera -- apenas serializa para JSON, mesma
        # disciplina de RiskAdvisorAgent/DeliveryAdvisorAgent.
        projects_json = json.dumps(
            [
                {
                    "project_id": item.metadata["project_id"],
                    "project_name": item.metadata["project_name"],
                    "program_id": item.metadata["program_id"],
                    "health_status": item.content.get("health_status"),
                    "key_findings": item.content.get("key_findings"),
                    "recommendations": item.content.get("recommendations"),
                    "source_analysis_id": item.source_id,
                    "source_created_at": str(item.metadata["created_at"]),
                }
                for item in evidence
            ],
            ensure_ascii=False,
        )
        final_prompt = self.framework.render_prompt(
            self.name, "advise", question=question, projects_json=projects_json
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
```

Mesma forma exata de `AdvisorContract`, mesmo `parse_structured_output` já usado por todo Advisor anterior.

---

## 5. Prompt — limites funcionais e ordem sem prioridade (per diretrizes 3 e 6)

### 5.1 Rascunho (`src/agents/portfolio_advisor/prompts/advise.md`, a ser criado na Implementação)

```
You are an AI PMO Copilot agent specialized in portfolio composition (balance, dependencies, overlap between projects and programs).

Answer strictly and exclusively based on the project snapshots provided below. Never invent a fact not present in this data, and never assume information about a project that has no snapshot in this list.

The project snapshots are a JSON array. Each item represents ONE project's CURRENT status only -- there is no historical sequence for any single project in this data, and you must never claim a project's trend improved, worsened, or stayed stable, because that information was not given to you.

The array is a SET, not a ranked list -- the order items appear in carries no importance or priority. Never treat a project mentioned first as more critical than one mentioned later; interpret the set as a whole, always naming each project by "project_name" when you discuss it.

You may evaluate: the portfolio's current consolidated state; the distribution of health across projects (how many green/yellow/red); concentration of criticality (which projects, named individually, are red or otherwise need attention); and which projects require attention. You must NOT claim a historical trend for the portfolio as a whole -- only a snapshot comparison across the projects given.

Question: $question

Project snapshots (JSON array, one current status per project -- order carries no meaning):
$projects_json

Respond with a single JSON object only, no extra text before or after it, using exactly this schema:
{
  "answer": "string",
  "cited_analysis_ids": [integer, ...]
}

"cited_analysis_ids" must list the "source_analysis_id" of every project snapshot your answer draws from -- name every project you cite, never summarize "several projects" without naming them.
```

Este texto é um rascunho de referência para a Implementação — a Technical Design autoriza sua estrutura e conteúdo, não fixa a redação final palavra por palavra.

### 5.2 Por que nenhum algoritmo é necessário para "neutralizar" a ordem (reafirmação de AR-12 §3)

O `PortfolioEvidenceAssembler` itera Programs/Projects na ordem que `list_programs_by_portfolio()`/`list_projects_by_program()` já devolvem (alfabética/por código, confirmado em AR-12 §3.1) — nenhuma mudança de ordenação é introduzida por este Technical Design. A garantia de "sem prioridade" é inteiramente textual (§5.1), nunca estrutural.

---

## 6. Rota HTTP e modelo de resposta (`src/api/routes/intelligence.py`)

```python
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


@router.post("/portfolio-advisor/ask", response_model=PortfolioAdvisorResponse)
def ask_portfolio_advisor(
    request: PortfolioAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    event_publisher: EventPublisher = Depends(build_event_publisher),
    _permission: None = Depends(require_permission("intelligence.read")),
):
    session = SessionContext(
        organization_id=context.organization.organization_id,
        user_id=context.user.user_id,
        session_id=context.session.session_id,
    )
    framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)
    domain_service = DomainService(repository, event_publisher)
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


def _portfolio_advisor_response(explanation, result: PortfolioAssemblyResult) -> PortfolioAdvisorResponse:
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
```

**Por que as contagens de cobertura nunca vêm do LLM (per diretriz 4):** `total_projects`/`projects_with_evidence`/`projects_without_evidence` são calculados inteiramente por `PortfolioEvidenceAssembler.assemble()` — contagem estrutural, nunca confiada à narrativa do modelo. O prompt (§5.1) também comunica a natureza de conjunto ao modelo para que sua prosa seja coerente com a cobertura real, mas o cliente da API nunca depende da honestidade do LLM para saber quantos projetos foram avaliados — mesma disciplina de "nunca confiar no LLM para fatos que o código já sabe com precisão" já aplicada em toda a plataforma.

---

## 7. RBAC — nenhuma migração nova

`intelligence.read` protege `POST /portfolio-advisor/ask`, exatamente como já faz para `/risk-advisor/ask` e `/delivery-advisor/ask` — mesma justificativa: síntese de leitura sobre análises já existentes, nunca cria/edita/dispara uma análise nova. Definitivo nesta etapa, per diretriz do Domain Blueprint reservando essa confirmação ao Technical Design.

---

## 8. Tratamento de cobertura parcial (per diretriz 4)

Quando `projects_with_evidence < total_projects` (cobertura parcial), a resposta HTTP expõe essa realidade estruturalmente (`projects_without_evidence > 0`), independentemente do que o texto de `answer` diga. O prompt (§5.1) reforça que o Advisor nunca deve generalizar para o portfólio inteiro quando parte dos projetos carece de evidência — mas a garantia **operacional** contra uma resposta enganosa é o campo estruturado, não a obediência do modelo ao texto do prompt. Nenhum caso de cobertura parcial é tratado como erro ou aciona `no_evidence()` — apenas o caso de `evidence` totalmente vazia (todos os Projects sem status, ou Portfolio sem Projects) aciona o portão anti-alucinação já estrutural.

---

## 9. Rastreabilidade — confirmação final dos 6 campos (per diretriz 5)

| Campo exigido | Onde vive | Como é garantido |
|---|---|---|
| `portfolio_id` | `Evidence.metadata["portfolio_id"]` | Adicionado pelo Assembler (§2) |
| `program_id` | `Evidence.metadata["program_id"]` | Adicionado pelo Assembler (§2) |
| `project_id` | `Evidence.metadata["project_id"]` | Adicionado pelo Assembler (§2) |
| `project_name` | `Evidence.metadata["project_name"]` | Adicionado pelo Assembler (§2) |
| `source_id` | `Evidence.source_id` (campo de topo, já existente) | **Já garantido pelo próprio contrato `Evidence`** — não precisa ser adicionado a `metadata`, pois já é um campo obrigatório de toda `Evidence`, para qualquer Advisor, desde AR-9 |
| `created_at` | `Evidence.metadata["created_at"]` | **Já preenchido por `AIContextEngine.gather()`** (zero mudança) — o Assembler apenas preserva via `**most_recent.metadata` no enriquecimento (§2) |

Nenhuma alteração ao contrato `Evidence` — os 6 campos são satisfeitos por uma combinação do que já existe (`source_id`, `metadata["created_at"]`) e do enriquecimento aditivo feito exclusivamente pelo Assembler (`portfolio_id`/`program_id`/`project_id`/`project_name`), confirmando a diretriz 5 sem exceção.

---

## 10. Limites funcionais (per diretriz 6, codificados no prompt, não em código)

**Permitido:** estado consolidado atual; distribuição de saúde (contagem green/yellow/red); concentração de criticidade (quais Projects, nomeados, estão red); Projects que exigem atenção; cobertura de evidências.

**Proibido nesta Epic:** tendência histórica consolidada do Portfolio — estruturalmente impossível de violar por acidente, porque cada Project contribui apenas seu estado atual (§2); nenhuma sequência temporal por projeto está presente em `projects_json` para o modelo interpretar como tendência.

---

## 11. Performance — gatilho mantido, nenhuma implementação (per diretriz 7)

Reafirmado de AR-12/Domain Blueprint, sem mudança: mais de 20 chamadas sequenciais a `gather_context()` por portfólio, ou p95 real de `POST /portfolio-advisor/ask` acima de 3 segundos, dispara uma Decision Proposal explícita de otimização — nenhuma API batch, paralelismo, cache, ou repository agregado implementado nesta Epic.

---

## 12. Testes planejados (plano, não implementação)

1. **Seleção mecânica de `evidence[0]` (diretriz 1):** Project com múltiplos `AnalysisRecord`s de status, timestamps explícitos → `PortfolioEvidenceAssembler` inclui apenas o mais recente na evidência consolidada.
2. **Ausência de interpretação/peso (diretriz 1):** dois Projects com `health_status` diferentes (`red`/`green`) → ambos entram na evidência com o mesmo tratamento estrutural, nenhuma ordenação por criticidade no Assembler (verificável por leitura de código + teste de ordem preservada).
3. **Portfolio inexistente/de outra organização:** `assemble()` retorna `None` → rota retorna 404.
4. **Portfolio sem Programs/Projects, ou todos os Projects sem status:** `evidence == []` → `no_evidence()` sem chamada ao LLM.
5. **Cobertura parcial:** portfólio com 5 Projects, 3 com status e 2 sem → `total_projects == 5`, `projects_with_evidence == 3`, `projects_without_evidence == 2`, resposta HTTP expõe os três números independentemente do texto de `answer`.
6. **Rastreabilidade completa:** `cited_projects` de cada item citado contém `project_id`/`project_name`/`source_analysis_id`/`source_created_at` reais.
7. **Ordem sem prioridade:** mesmo conjunto de Projects, ordem de composição trocada artificialmente no teste → resposta scriptada não muda de significado (teste de equivalência semântica, não de igualdade textual).
8. **Isolamento organizacional:** Portfolio de outra organização nunca resolvido, mesmo com `portfolio_id` correto.
9. **`AdvisorFramework`/`AIContextEngine`/`Recommendation`/`Explanation` inalterados:** confirmado por `git diff` vazio nesses arquivos ao final da implementação.

---

## 13. Riscos residuais

1. **Wording exato da instrução "conjunto, não lista ordenada" e dos limites funcionais no prompt** — mitigado pelos testes 2/7 (§12). Não bloqueante.
2. **Volume de `AnalysisRecord`s de status descartados por projeto (apenas o mais recente é usado)** — mesmo risco já aceito e justificado em AR-12 §2.4; histórico completo permanece consultável via Delivery Advisor.
3. **Gatilho de performance (§11)** — registrado, não uma decisão de otimização; nenhuma ação até ser cruzado por dado real.
4. **TD-015** — não incide neste Advisor (Classe B via `gather_context()` múltiplo, não `normalize_rag_evidence()`).

Nenhum risco bloqueia a implementação.

---

## 14. Estratégia incremental de implementação

1. **Passo 1 — `PortfolioEvidenceAssembler`:** novo componente (`src/agents/portfolio_advisor/evidence_assembler.py`), reutilizando `DomainService`/`AdvisorFramework.gather_context()` sem duplicação — testes unitários (§12.1-12.2, 12.5-12.6, com `DomainService`/`AdvisorFramework` reais ou dublês controlados).
2. **Passo 2 — `PortfolioAdvisorAgent` + prompt:** novo agente (`src/agents/portfolio_advisor/agent.py`), reaproveitando `parse_structured_output`/`render_analyst_prompt`/`ObservabilityRecorder` sem duplicação — testes unitários de serialização e prompt.
3. **Passo 3 — Rota + modelo de resposta:** `POST /portfolio-advisor/ask`, `PortfolioAdvisorRequest`/`PortfolioAdvisorResponse`/`CitedProject` — testes de integração via `AdvisorFramework`/`DomainService` reais (§12.3-12.4, 12.8).
4. **Passo 4 — Testes de ordem/cobertura + verificação final:** teste de equivalência sob reordenação (§12.7), suíte backend completa, `ruff`/`tsc`/`eslint`, confirmação de `AdvisorFramework`/`AIContextEngine`/`Recommendation`/`Explanation` inalterados via `git diff`, governança (Decision Log/CHANGELOG/Mission Control), Executive Evidence.

Cada passo é independentemente testável — nenhum passo depende de código do passo seguinte para validação isolada.

---

## 15. Recomendação GO/NO-GO para implementação

**GO.** Todos os pontos exigidos pela autorização do Founder foram resolvidos com evidência de código real: seleção de evidência puramente mecânica, sem interpretação/peso/comparação (§2); consistência com o Delivery Advisor reafirmada (AR-12, aplicada aqui sem redecisão); ordem sem prioridade garantida textualmente, nenhum algoritmo (§5.2); modelo de resposta com cobertura estrutural, nunca dependente do LLM (§6/§8); rastreabilidade completa dos 6 campos exigidos, sem alteração ao contrato `Evidence` (§9); limites funcionais codificados no prompt, estruturalmente impossíveis de violar por acidente (§10); gatilho de performance mantido, nenhuma otimização antecipada (§11); toda a infraestrutura compartilhada (`AdvisorFramework`, `AIContextEngine`, Workflow Runtime, Event Pipeline, `RecommendationEngine`, `ExplanationEngine`) preservada integralmente (§1). Nenhum risco residual (§13) bloqueia o início da implementação.

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de qualquer implementação.
