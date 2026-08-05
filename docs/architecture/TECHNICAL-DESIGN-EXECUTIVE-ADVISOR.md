# Technical Design — Executive Advisor

**Etapa 4 de 6** do ciclo institucional do Executive Advisor. Produzido sob autorização da Founder Decision que aprovou a AR-14 (`AR-14-EXECUTIVE-ADVISOR-ARCHITECTURE-REVIEW.md`) com **GO para o Technical Design**, oficializando o modelo de citação (`ExecutiveCitedEvidence`, isolado, `CitedProject` intocado), fontes exclusivas (`kind="status"` + `kind="risk"`, no máximo o mais recente de cada por Project), o `ExecutiveEvidenceAssembler` (responsabilidades e proibições explícitas), a cobertura estrutural (sete contagens), o tratamento de ausência/cobertura parcial, e a proibição permanente de ranking determinístico em código. Esta etapa detalha o contrato completo, sem escrever código.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Escopo organizacional, resolvido diretamente sobre os Projects da organização | Domain Blueprint (D-120) |
| Fontes exclusivas: `kind="status"` + `kind="risk"` — no máximo o mais recente de cada por Project; nunca histórico, `meeting`, `action_items`, RAG, documentos, respostas de outros Advisors | Advisor Specification + Domain Blueprint + AR-14 |
| `ProjectSummaryService` rejeitado como fonte; composição direta via `AnalysisRecord` | Domain Blueprint (D-120) |
| `gather_context_many()` rejeitado neste Epic; duas chamadas explícitas (`kind="status"`/`kind="risk"`) no `ExecutiveEvidenceAssembler` | Domain Blueprint (D-120) |
| `ExecutiveEvidenceAssembler` específico do pacote, não promovido a componente compartilhado | Domain Blueprint + AR-14 |
| Modelo de citação: `ExecutiveCitedEvidence` (`project_id`, `project_name`, `source_analysis_id`, `kind`, `created_at`), isolado — `CitedProject` intocado | AR-14 (D-121) |
| Cobertura estrutural: sete contagens | AR-14 (D-121) |
| Ausência total → `no_evidence()`, zero LLM; cobertura parcial → síntese permitida, limitação declarada | AR-14 (D-121) |
| Nenhum ranking determinístico em código | AR-14 (D-121) |

---

## 1. Executive Summary

Este Technical Design fecha o contrato de implementação do Executive Advisor sem introduzir nenhuma decisão nova de arquitetura — apenas formaliza, em nível de assinatura de função e estrutura de dados, o que a AR-14 já decidiu.

O componente central é `ExecutiveEvidenceAssembler` (`src/agents/executive_advisor/evidence_assembler.py`), terceiro componente de composição Classe B, estruturalmente distinto de `PortfolioEvidenceAssembler` e `PMOEvidenceAssembler`: para cada Project da organização, chama `framework.gather_context(kind="status")` **e** `framework.gather_context(kind="risk")` — duas chamadas explícitas e independentes — captura apenas `evidence[0]` de cada uma quando existir, e calcula as sete contagens de cobertura em uma única passada, sem nenhuma segunda iteração.

Cada `AnalysisRecord` selecionado (no máximo dois por Project — um status, um risco) vira um item de `Evidence` independente, mesmo mecanismo já usado por Delivery/PMO Advisor. `Evidence.metadata["kind"]` já vem preenchido por `AIContextEngine.gather()` — nenhuma mudança de contrato necessária para a rastreabilidade por `kind`.

O modelo de resposta (`ExecutiveAdvisorResponse`) expõe as sete contagens estruturais e uma lista de `ExecutiveCitedEvidence` — modelo novo, isolado, nunca reaproveitando `CitedProject`. `cited_evidence` só contém o que o LLM efetivamente citou, mesmo mecanismo de filtragem por `source_id` já usado em `RecommendationEngine.build()` desde o primeiro Advisor.

**Recomendação: GO para a implementação.**

---

## 2. Fluxo completo

```
POST /executive-advisor/ask
  { question: string }
        │
        ▼
require_permission("intelligence.read")   -- mesma RBAC de Delivery/Portfolio/PMO Advisor
        │
        ▼
ExecutiveEvidenceAssembler.assemble(organization_id)
  │
  ├─ DomainService.list_projects(organization_id)             -- Wave 2, já em produção
  │     (nunca None: escopo organizacional sempre resolve pela própria sessão)
  │
  └─ para cada Project:
        total_projects += 1
        status_evidence = framework.gather_context(org_id, project.name, kind="status")
        risk_evidence   = framework.gather_context(org_id, project.name, kind="risk")
            (AdvisorFramework/AIContextEngine inalterados -- duas chamadas explícitas)
        has_status = bool(status_evidence)
        has_risk   = bool(risk_evidence)
        se has_status: projects_with_status += 1; evidence.append(enrich(status_evidence[0], project))
        se has_risk:   projects_with_risk   += 1; evidence.append(enrich(risk_evidence[0], project))
        se has_status e has_risk: projects_with_status_and_risk += 1
        se not has_status e not has_risk: projects_without_any_evidence += 1
  retorna ExecutiveAssemblyResult(evidence, total_projects,
                                   projects_with_status, projects_without_status,
                                   projects_with_risk, projects_without_risk,
                                   projects_with_status_and_risk, projects_without_any_evidence)
        │
        ▼
ExecutiveAdvisorAgent(framework)
        │
        ▼
AdvisorFramework.run(agent, session, question, result.evidence,
                      no_evidence_answer="...")                 -- INALTERADO, mesmo portão anti-alucinação
        │
        ▼
_executive_advisor_response(explanation, result) → ExecutiveAdvisorResponse
```

Nenhum passo deste fluxo introduz uma chamada nova a `AdvisorFramework`/`AIContextEngine` além de `gather_context()`, já existente e já usado por todos os Advisors baseados em `AnalysisRecord`.

---

## 3. Contrato do `ExecutiveEvidenceAssembler`

### 3.1 Localização

`src/agents/executive_advisor/evidence_assembler.py` — exclusivo do pacote do Advisor, confirmando AR-14 §5: não promovido a componente compartilhado nesta etapa.

### 3.2 Estrutura de dados

```python
from dataclasses import dataclass
from src.services.ai_foundation.types import Evidence


@dataclass(frozen=True)
class ExecutiveAssemblyResult:
    evidence: list[Evidence]
    total_projects: int
    projects_with_status: int
    projects_without_status: int
    projects_with_risk: int
    projects_without_risk: int
    projects_with_status_and_risk: int
    projects_without_any_evidence: int
```

Mesma disciplina de `PortfolioAssemblyResult`/`PMOAssemblyResult`: `frozen=True`, todas as contagens já calculadas — a rota e o Agent nunca recalculam nada, apenas leem os campos.

### 3.3 Assinatura

```python
class ExecutiveEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        self._domain_service = domain_service
        self._framework = framework

    def assemble(self, organization_id: int) -> ExecutiveAssemblyResult:
        ...
```

Mesmo formato de `PMOEvidenceAssembler.assemble()`: sem parâmetro de escopo adicional (organizacional sempre), sem caso de 404 (a organização da sessão sempre existe).

### 3.4 Corpo (rascunho de referência, não implementação final)

```python
def assemble(self, organization_id: int) -> ExecutiveAssemblyResult:
    projects = self._domain_service.list_projects(organization_id) or []

    evidence: list[Evidence] = []
    total_projects = 0
    projects_with_status = 0
    projects_with_risk = 0
    projects_with_status_and_risk = 0
    projects_without_any_evidence = 0

    for project in projects:
        total_projects += 1
        status_evidence = self._framework.gather_context(organization_id, project.name, kind="status")
        risk_evidence = self._framework.gather_context(organization_id, project.name, kind="risk")

        has_status = bool(status_evidence)
        has_risk = bool(risk_evidence)

        if has_status:
            projects_with_status += 1
            evidence.append(self._enrich(status_evidence[0], project))
        if has_risk:
            projects_with_risk += 1
            evidence.append(self._enrich(risk_evidence[0], project))
        if has_status and has_risk:
            projects_with_status_and_risk += 1
        if not has_status and not has_risk:
            projects_without_any_evidence += 1

    return ExecutiveAssemblyResult(
        evidence=evidence,
        total_projects=total_projects,
        projects_with_status=projects_with_status,
        projects_without_status=total_projects - projects_with_status,
        projects_with_risk=projects_with_risk,
        projects_without_risk=total_projects - projects_with_risk,
        projects_with_status_and_risk=projects_with_status_and_risk,
        projects_without_any_evidence=projects_without_any_evidence,
    )

@staticmethod
def _enrich(item: Evidence, project) -> Evidence:
    return Evidence(
        source_type=item.source_type,
        source_id=item.source_id,
        source_label=item.source_label,
        content=item.content,
        metadata={**item.metadata, "project_id": project.id, "project_name": project.name},
    )
```

**Pontos de disciplina confirmados por este rascunho:**
- Duas chamadas explícitas por Project (`kind="status"`, `kind="risk"`) — nenhuma chamada genérica, nenhuma dependência de `gather_context_many()`.
- `evidence[0]` de cada chamada — mecanismo já garantido por `AnalysisRepository.list_analyses()` (ordenação `created_at DESC`), nunca histórico.
- `_enrich()` só adiciona `project_id`/`project_name` — `kind` e `created_at` já vêm preenchidos por `AIContextEngine.gather()`, nenhum enriquecimento adicional necessário.
- As sete contagens são calculadas na mesma passada do laço principal — nenhuma segunda iteração, nenhum recomputo.
- **Nenhuma linha deste corpo interpreta conteúdo, calcula prioridade, cria ranking, chama o LLM ou executa regra de negócio** — confirmação explícita exigida pela Founder Decision item 3.

---

## 4. Modelo de resposta

### 4.1 Request

```python
class ExecutiveAdvisorRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)
```

Sem `project_id`/`portfolio_id` — mesmo padrão de `PMOAdvisorRequest`/`DocumentAdvisorRequest`, porque o escopo é sempre a organização da sessão autenticada.

### 4.2 Modelo de citação

```python
class ExecutiveCitedEvidence(BaseModel):
    project_id: int
    project_name: str
    source_analysis_id: int
    kind: str
    created_at: datetime
```

**Novo, isolado, exclusivo do Executive Advisor** — `CitedProject` não é tocado, permanece servindo Portfolio/PMO Advisor sem nenhuma mudança (confirmação já exigida em AR-14 §2, reafirmada pela Founder Decision item 1). `kind` distingue explicitamente `"status"` de `"risk"` — lido diretamente de `Evidence.metadata["kind"]`, já preenchido por `AIContextEngine.gather()`, nenhum campo inventado.

### 4.3 Response

```python
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
```

Exatamente na forma definida pela Founder Decision (item 7).

### 4.4 Mapeamento (rascunho de referência)

```python
def _executive_advisor_response(explanation, result: ExecutiveAssemblyResult) -> ExecutiveAdvisorResponse:
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
```

**Somente evidências efetivamente citadas** (Founder Decision item 1): `explanation.recommendation.cited_evidence` já é o resultado filtrado de `RecommendationEngine.build()` por associação `source_id` — mesmo mecanismo comprovado em todos os Advisors anteriores (posição-independente, confirmado por teste desde o Portfolio Advisor, AR-12 §3/Cenário I).

### 4.5 Rota

```python
@router.post("/executive-advisor/ask", response_model=ExecutiveAdvisorResponse)
def ask_executive_advisor(
    request: ExecutiveAdvisorRequest,
    context: RequestContext = Depends(get_request_context),
    prompts: PromptRegistry = Depends(build_prompt_registry),
    provider: LLMProvider = Depends(build_provider),
    repository: AnalysisRepository = Depends(build_repository),
    rag_pipeline: RagPipeline = Depends(build_rag_pipeline),
    domain_service: DomainService = Depends(build_domain_service),
    _permission: None = Depends(require_permission("intelligence.read")),
):
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
```

Mesma RBAC (`intelligence.read`), mesmas dependências injetadas, `AdvisorExecutionError` tratado igual. Sem `HTTPException(404)` — mesmo motivo já registrado para PMO Advisor: `assemble()` nunca retorna `None`.

---

## 5. `ExecutiveAdvisorAgent`

`src/agents/executive_advisor/agent.py`, mesma forma dos demais Advisors baseados em `AnalysisRecord`:

```python
class ExecutiveAdvisorAgent:
    name = "executive_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(self, session, question, evidence, rag_context=None) -> dict:
        records_json = json.dumps(
            [
                {
                    "project_id": item.metadata["project_id"],
                    "project_name": item.metadata["project_name"],
                    "kind": item.metadata["kind"],
                    "content": item.content,
                    "source_analysis_id": item.source_id,
                    "source_created_at": str(item.metadata["created_at"]),
                }
                for item in evidence
            ],
            ensure_ascii=False,
        )
        final_prompt = self.framework.render_prompt(
            self.name, "advise", question=question, records_json=records_json
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
```

**`content` transportado sem achatar campos** (diferente de Portfolio/PMO Advisor): `kind="status"` e `kind="risk"` têm formatos de conteúdo estruturalmente diferentes (`health_status`/`key_findings`/`recommendations` vs. `risks`/`escalation_recommendation`) — achatar ambos em um schema único inventaria uma forma que não existe em nenhum dos dois `kind`s reais. O campo `"kind"` já diz ao modelo qual forma esperar dentro de `"content"`.

### 5.1 Prompt (`src/agents/executive_advisor/prompts/advise.md`) — diretrizes de conteúdo, não texto final

- Cada registro em `records_json` tem um `"kind"` (`"status"` ou `"risk"`) que determina a forma de `"content"` — o modelo deve ler `key_findings`/`health_status`/`recommendations` quando `kind="status"`, e `risks`/`escalation_recommendation` quando `kind="risk"`.
- Cada registro representa o estado **atual** daquele `kind` para aquele Project — nunca uma sequência temporal; o modelo nunca deve afirmar tendência, melhora ou deterioração ao longo do tempo, para nenhum Project nem para a organização.
- A ordem dos registros não implica prioridade — o conjunto é interpretado como um todo, nunca por posição (mesmo princípio já aplicado a Portfolio/PMO Advisor).
- O modelo pode identificar quais Projects exigem atenção da liderança, sempre nomeando o Project e fundamentando na evidência citada — nunca produzindo um ranking numérico ou ordenado sem base direta no conteúdo.
- O modelo nunca avalia risco especializado (permanece exclusivo do Risk Advisor), nunca avalia conformidade de processo (PMO Advisor) nem composição de portfólio (Portfolio Advisor), nunca cita documentos institucionais (Governance/Document Advisor).
- Se a organização tiver Projects sem nenhuma evidência (`projects_without_any_evidence > 0`), o modelo deve declarar explicitamente essa limitação na resposta, usando as contagens estruturais fornecidas — nunca generalizando silenciosamente para os Projects sem evidência.

---

## 6. Estratégia de cobertura

As sete contagens (§0, §3.4) são produzidas **inteiramente** dentro de `ExecutiveEvidenceAssembler.assemble()`, nunca recalculadas na rota nem no Agent. As invariantes exigidas pela Founder Decision (item 4) são garantidas pela própria aritmética do laço:

| Invariante | Garantia |
|---|---|
| `projects_with_status + projects_without_status = total_projects` | `projects_without_status` é literalmente `total_projects - projects_with_status` |
| `projects_with_risk + projects_without_risk = total_projects` | `projects_without_risk` é literalmente `total_projects - projects_with_risk` |
| `projects_with_status_and_risk ≤ min(projects_with_status, projects_with_risk)` | Só incrementado quando `has_status and has_risk`, subconjunto necessário de ambos |
| `projects_without_any_evidence = total_projects - projects_with_status - projects_with_risk + projects_with_status_and_risk` | Identidade de conjuntos (`|S∪R| = |S| + |R| - |S∩R|`), decorrência direta das quatro contagens anteriores — verificável em todo teste, nunca calculada por uma regra separada que possa divergir |

Um Project sem nenhuma evidência (`has_status = has_risk = False`) nunca incrementa `projects_with_status_and_risk`, e um Project com apenas uma das duas fontes nunca incrementa `projects_without_any_evidence` — estruturalmente impossível pela forma dos `if`s, não uma regra a verificar separadamente.

---

## 7. Rastreabilidade por `kind`

Cada `ExecutiveCitedEvidence` retornado carrega `kind` lido diretamente de `Evidence.metadata["kind"]` — preenchido por `AIContextEngine.gather()` desde sempre, sem nenhuma mudança de contrato. Duas citações do mesmo Project (uma de `kind="status"`, outra de `kind="risk"`) permanecem **distinguíveis** na resposta HTTP, cada uma com seu próprio `source_analysis_id` — nunca colapsadas nem ambíguas, resolvendo o achado registrado em AR-14 §2/Domain Blueprint §9.2.

---

## 8. Riscos residuais

| Risco | Origem | Mitigação registrada |
|---|---|---|
| Volume de chamadas dobrado em relação ao PMO Advisor para a mesma organização | Já registrado no Domain Blueprint §7.5/AR-14 §8 | Mesmo gatilho de performance já aprovado (20+ chamadas sequenciais ou p95 > 3s), atenção adicional mantida, nenhuma otimização antecipada |
| Conteúdo de `status` e `risk` têm schemas diferentes dentro do mesmo array `records_json` | Consequência estrutural de combinar dois `kind`s | Documentado explicitamente no prompt (§5.1) — o campo `kind` já diz ao modelo qual forma esperar, nenhuma normalização de schema necessária em código |
| Nome definitivo dos componentes (`ExecutiveEvidenceAssembler`, `ExecutiveCitedEvidence`, `ExecutiveAssemblyResult`) | Convenção de nomenclatura | Confirmados nesta etapa, prontos para implementação |

Nenhum risco listado é bloqueante para a implementação.

---

## 9. Testes obrigatórios

Os 13 cenários exigidos pela Founder Decision, nomeados A-M (mesma convenção lettered já usada nos Advisors anteriores):

| # | Cenário | Cobre |
|---|---|---|
| A | Project com status **e** risco | `projects_with_status_and_risk` incrementado, duas evidências geradas |
| B | Project somente com status | `projects_with_status` incrementado, `projects_with_risk` não |
| C | Project somente com risco | `projects_with_risk` incrementado, `projects_with_status` não |
| D | Project sem nenhuma evidência | `projects_without_any_evidence` incrementado, zero `Evidence` gerada para esse Project |
| E | Cobertura completa | Todos os Projects contribuem com pelo menos uma das duas fontes |
| F | Cobertura parcial | Síntese permitida, limitação declarada na resposta |
| G | Ausência total | `no_evidence()`, zero chamada ao LLM |
| H | Duas citações do mesmo Project com `kind`s diferentes | Ambas presentes em `cited_evidence`, `source_analysis_id` distintos, nunca colapsadas |
| I | Filtro de citações efetivamente utilizadas | `cited_evidence` contém apenas o que o LLM citou, nunca toda a evidência montada |
| J | Isolamento organizacional | Projects de outra organização nunca entram em `total_projects` nem em `evidence` |
| K | Ausência de tendência histórica | Estruturalmente garantido — apenas o registro mais recente de cada `kind` chega ao prompt |
| L | Ausência de ranking em código | Nenhuma ordenação por severidade/prioridade aplicada pelo Assembler ou pela rota — verificável por leitura de código e por teste de ordem-independência (mesmo padrão do Cenário I do Portfolio Advisor) |
| M | Ausência de chamada ao LLM sem evidência | Mesmo portão anti-alucinação, `_ExplodingProvider` como prova estrutural |

Camadas de teste (mesmo padrão de Portfolio/PMO Advisor): unitários para `ExecutiveEvidenceAssembler` (fakes, cobrem A-D principalmente); unitários para `ExecutiveAdvisorAgent` (fakes, cobrem H/I na formação do JSON); integração via `AdvisorFramework` real contra Postgres (cobrem E-M); HTTP via `TestClient` real (cobrem E-M novamente na camada de rota, mais RBAC/auditoria/rastreabilidade completa por `kind`).

---

## 10. Estratégia incremental

1. `ExecutiveEvidenceAssembler` + `ExecutiveAssemblyResult` (`src/agents/executive_advisor/evidence_assembler.py`) — testado isoladamente com fakes (cenários A-D).
2. `ExecutiveAdvisorAgent` + prompt (`src/agents/executive_advisor/agent.py`, `prompts/advise.md`) — testado isoladamente com fakes (cenários H/I na formação do JSON).
3. Rota + modelo de resposta (`ExecutiveAdvisorRequest`/`ExecutiveCitedEvidence`/`ExecutiveAdvisorResponse`/`_executive_advisor_response()` em `src/api/routes/intelligence.py`) — testes de integração via `AdvisorFramework` real (E-M) seguidos de testes HTTP (E-M).
4. Verificação final: `git diff --stat` vazio em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline/contrato `Evidence`/`CitedProject`/`PortfolioAdvisorResponse`/`PMOAdvisorResponse`; suíte completa; `ruff`/`tsc`/`eslint`.

Mesma sequência já usada em Delivery, Portfolio e PMO Advisor — nenhum passo novo inventado.

---

## 11. Recomendação

**GO para a implementação.**

Nenhuma questão de arquitetura permanece em aberto para o Executive Advisor: escopo, fontes, componente de composição, modelo de citação por `kind`, modelo de resposta, cobertura estrutural com invariantes explícitas, tratamento de ausência/cobertura parcial, e limite permanente contra ranking determinístico estão todos definidos com contrato de código de referência nesta etapa. A implementação segue a estratégia incremental de 4 passos (§10), com os 13 cenários obrigatórios (§9) como critério de aceite. Ao final, retorno obrigatório para Executive Review antes de qualquer trabalho posterior.
