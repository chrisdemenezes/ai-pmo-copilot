# Technical Design — PMO Advisor

**Etapa 4 de 6** do ciclo institucional do PMO Advisor. Produzido sob autorização da Founder Decision que aprovou a AR-13 (`AR-13-PMO-ADVISOR-ARCHITECTURE-REVIEW.md`) com **GO para o Technical Design**, oficializando staleness (limiar de 14 dias, cálculo estrutural), controle de volume (5 registros mais recentes por Project), modelo de cobertura estrutural (5 contagens), fonte exclusiva `kind="status"`, e não-generalização do `PortfolioEvidenceAssembler`. Esta etapa detalha o contrato completo, sem escrever código.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Unidade de composição: Project, rastreável por `project_id` | Domain Blueprint (D-114) |
| Escopo: organizacional, via `DomainService.list_projects(organization_id, program_id=None)` | Domain Blueprint (D-114) |
| Fonte: exclusivamente `AnalysisRecord`/`kind="status"` — `kind="meeting"`, `action_items`, `kind="risk"`, RAG, respostas de outros Advisors fora de escopo | Domain Blueprint (D-114) |
| Histórico: PMO Advisor pode usar múltiplos registros por Project (diferente do Portfolio Advisor) | Domain Blueprint (D-114) |
| Staleness: limiar de **14 dias**, cálculo estrutural, sem configuração por organização | AR-13 (D-115) |
| Volume: **5 registros mais recentes por Project** (`evidence[:5]`), sem janela temporal | AR-13 (D-115) |
| Cobertura: 5 contagens estruturais (`total_projects`/`projects_with_status`/`projects_without_status`/`projects_stale`/`projects_current`) | AR-13 (D-115) |
| Generalização do `PortfolioEvidenceAssembler`: rejeitada neste Epic | Domain Blueprint (D-114), reafirmado AR-13 |
| Preservação integral de `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline/contrato `Evidence` | Domain Blueprint + AR-13 |

---

## 1. Executive Summary

Este Technical Design fecha o contrato de implementação do PMO Advisor sem introduzir nenhuma decisão nova de arquitetura — apenas formaliza, em nível de assinatura de função e estrutura de dados, o que a AR-13 já decidiu.

O componente central é `PMOEvidenceAssembler` (`src/agents/pmo_advisor/evidence_assembler.py`), estruturalmente paralelo ao `PortfolioEvidenceAssembler` mas comportamentalmente distinto: resolve o escopo organizacional diretamente (`DomainService.list_projects(organization_id)`, sem `portfolio_id`, portanto **sem caso de 404** — a organização do usuário sempre existe pela própria sessão), itera cada Project, chama `framework.gather_context(organization_id, project.name, kind="status")` uma vez por Project, e — **depois** do retorno, inteiramente em memória — calcula `staleness_days`/`is_stale` a partir do registro mais recente e recorta a lista para os 5 mais recentes. O corte e o cálculo nunca tocam `AdvisorFramework`/`AIContextEngine`, que continuam retornando o histórico completo, exatamente como hoje.

Cada `AnalysisRecord` selecionado (até 5 por Project) vira um item de `Evidence` independente — não um `Evidence` agregado por Project — porque `RecommendationEngine.build()` já filtra citações por `source_id` individual (mesmo mecanismo usado por Delivery Advisor para expor o histórico completo de um projeto). `staleness_days`/`is_stale` são calculados **uma vez por Project** e replicados identicamente em `Evidence.metadata` de todos os registros daquele Project, garantindo que o LLM sempre veja o mesmo fato de staleness independentemente de qual registro específico estiver lendo.

O modelo de resposta (`PMOAdvisorResponse`) reaproveita `CitedProject` (já definido para o Portfolio Advisor) sem duplicação, adiciona as 5 contagens estruturais como campos de topo. `cited_projects` pode conter o mesmo `project_id` mais de uma vez se o LLM citar múltiplos registros do mesmo Project — comportamento intencional, não um defeito: cada entrada rastreia uma citação de `AnalysisRecord` específico, e o Portfolio Advisor nunca exibia essa possibilidade apenas porque só tinha um `Evidence` por Project para citar.

**Recomendação: GO para a implementação.**

---

## 2. Fluxo completo

```
POST /pmo-advisor/ask
  { question: string }
        │
        ▼
require_permission("intelligence.read")   -- mesma RBAC do Delivery/Portfolio Advisor
        │
        ▼
PMOEvidenceAssembler.assemble(organization_id)
  │
  ├─ DomainService.list_projects(organization_id)             -- Wave 2, já em produção
  │     (nunca None: escopo organizacional sempre resolve pela própria sessão)
  │
  ├─ reference_time = datetime.now(timezone.utc)               -- calculado UMA VEZ para toda a chamada
  │
  └─ para cada Project:
        total_projects += 1
        project_evidence = framework.gather_context(organization_id, project.name, kind="status")
            (AdvisorFramework/AIContextEngine inalterados -- histórico completo, ordenado created_at DESC)
        se vazio:
            continue                                            -- Project sem status, não conta em nenhuma
                                                                   outra contagem
        projects_with_status += 1
        most_recent = project_evidence[0]
        staleness_days = (reference_time - most_recent.metadata["created_at"]).days
        is_stale = staleness_days >= PMO_STALENESS_THRESHOLD_DAYS   -- constante = 14
        se is_stale: projects_stale += 1  senão: projects_current += 1
        capped = project_evidence[:PMO_MAX_RECORDS_PER_PROJECT]     -- constante = 5
        para cada item em capped:
            evidence.append(Evidence(..., metadata={
                **item.metadata, project_id, project_name,
                staleness_days, is_stale,
            }))
  projects_without_status = total_projects - projects_with_status
  retorna PMOAssemblyResult(evidence, total_projects, projects_with_status,
                             projects_without_status, projects_stale, projects_current)
        │
        ▼
PMOAdvisorAgent(framework)
        │
        ▼
AdvisorFramework.run(agent, session, question, result.evidence,
                      no_evidence_answer="...")                 -- INALTERADO, mesmo portão anti-alucinação
        │
        ▼
_pmo_advisor_response(explanation, result) → PMOAdvisorResponse
```

Nenhum passo deste fluxo introduz uma chamada nova a `AdvisorFramework`/`AIContextEngine` além de `gather_context()`, já existente e já usado por todos os Advisors baseados em `AnalysisRecord`.

---

## 3. Contrato do `PMOEvidenceAssembler`

### 3.1 Localização

`src/agents/pmo_advisor/evidence_assembler.py` — dentro do pacote do próprio Advisor, nunca em `src/services/`, mesmo princípio já aplicado ao `PortfolioEvidenceAssembler` (generalização recusada em D-114/AR-13).

### 3.2 Constantes nomeadas

```python
# src/agents/pmo_advisor/evidence_assembler.py

PMO_STALENESS_THRESHOLD_DAYS = 14
PMO_MAX_RECORDS_PER_PROJECT = 5
```

Nenhuma das duas é lida de configuração de organização, variável de ambiente, ou tabela de banco — são constantes de módulo, exatamente como a Founder Decision instruiu ("não criar configuração por organização neste Epic").

### 3.3 Estrutura de dados

```python
from dataclasses import dataclass
from src.services.ai_foundation.types import Evidence


@dataclass(frozen=True)
class PMOAssemblyResult:
    evidence: list[Evidence]
    total_projects: int
    projects_with_status: int
    projects_without_status: int
    projects_stale: int
    projects_current: int
```

Mesma disciplina do `PortfolioAssemblyResult`: `frozen=True`, todas as contagens já calculadas — a rota e o Advisor nunca recalculam nada, apenas leem os campos.

### 3.4 Assinatura

```python
class PMOEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        self._domain_service = domain_service
        self._framework = framework

    def assemble(self, organization_id: int) -> PMOAssemblyResult:
        ...
```

**Diferença deliberada em relação ao `PortfolioEvidenceAssembler.assemble()`:** não recebe `portfolio_id`, não retorna `PMOAssemblyResult | None`. O escopo do PMO Advisor é a própria organização da sessão — não existe um identificador externo que possa "não resolver" (ao contrário de `portfolio_id`, que pode apontar para um Portfolio inexistente ou de outra organização). Não há, portanto, caso de 404 para este Advisor — `assemble()` sempre retorna um `PMOAssemblyResult` válido, mesmo quando a organização não tem nenhum Project (`total_projects=0`, todas as demais contagens em zero, `evidence=[]`).

### 3.5 Corpo (rascunho de referência, não implementação final)

```python
from datetime import datetime, timezone

def assemble(self, organization_id: int) -> PMOAssemblyResult:
    projects = self._domain_service.list_projects(organization_id) or []
    reference_time = datetime.now(timezone.utc)

    evidence: list[Evidence] = []
    total_projects = 0
    projects_with_status = 0
    projects_stale = 0
    projects_current = 0

    for project in projects:
        total_projects += 1
        project_evidence = self._framework.gather_context(
            organization_id, project.name, kind="status"
        )
        if not project_evidence:
            continue

        projects_with_status += 1
        most_recent = project_evidence[0]
        staleness_days = (reference_time - most_recent.metadata["created_at"]).days
        is_stale = staleness_days >= PMO_STALENESS_THRESHOLD_DAYS
        if is_stale:
            projects_stale += 1
        else:
            projects_current += 1

        for item in project_evidence[:PMO_MAX_RECORDS_PER_PROJECT]:
            evidence.append(
                Evidence(
                    source_type=item.source_type,
                    source_id=item.source_id,
                    source_label=item.source_label,
                    content=item.content,
                    metadata={
                        **item.metadata,
                        "project_id": project.id,
                        "project_name": project.name,
                        "staleness_days": staleness_days,
                        "is_stale": is_stale,
                    },
                )
            )

    return PMOAssemblyResult(
        evidence=evidence,
        total_projects=total_projects,
        projects_with_status=projects_with_status,
        projects_without_status=total_projects - projects_with_status,
        projects_stale=projects_stale,
        projects_current=projects_current,
    )
```

**Pontos de disciplina confirmados por este rascunho:**
- `reference_time` é calculado **uma única vez**, antes do laço — garante que todo `staleness_days` desta chamada usa a mesma referência de "agora", mesmo que a organização tenha centenas de Projects e a iteração leve tempo mensurável. Sem isso, dois Projects poderiam receber `staleness_days` inconsistentes só por causa de quando, dentro do laço, cada um foi processado.
- `staleness_days`/`is_stale` são calculados a partir de `most_recent = project_evidence[0]` — **antes** do corte de volume, mas o valor é o mesmo depois do corte, porque `project_evidence[0]` nunca é removido por um corte de 5 (o corte remove do índice 5 em diante, nunca o índice 0).
- O corte (`project_evidence[:PMO_MAX_RECORDS_PER_PROJECT]`) acontece **depois** do cálculo de staleness, mas isso é irrelevante para o resultado — ambos leem a mesma lista já ordenada, a única diferença é quantos itens de `Evidence` são de fato criados.
- Nenhuma chamada a `gather_context()` recebe um parâmetro de limite — `AIContextEngine.gather()` continua sendo chamado exatamente como hoje, sem mudança de assinatura.

---

## 4. Cálculo de staleness — detalhamento final

Resolvendo os cinco pontos que a Founder Decision pediu explicitamente nesta etapa:

### 4.1 Constante nomeada

`PMO_STALENESS_THRESHOLD_DAYS = 14`, em `src/agents/pmo_advisor/evidence_assembler.py` (§3.2). Nenhum valor mágico solto no corpo da função.

### 4.2 Timezone

**UTC, sempre.** `most_recent.metadata["created_at"]` é o `AnalysisRecord.created_at` do banco, uma coluna `DateTime(timezone=True)` (`src/database/models.py`) com `default=_utcnow` (`datetime.now(timezone.utc)`) — já timezone-aware desde a escrita. `reference_time` usa exatamente o mesmo padrão: `datetime.now(timezone.utc)`, já o padrão permanente do resto do código (`administration_service.py`, `invitations.py`, `in_process_publisher.py` — todos usam `datetime.now(timezone.utc)`, nunca `datetime.utcnow()` nem hora local). Subtrair dois `datetime`s timezone-aware é seguro e não gera `TypeError` de comparação naive/aware.

### 4.3 Data de referência

`datetime.now(timezone.utc)`, capturada **uma vez** no início de `assemble()` (§3.5), nunca recalculada por Project. Isso evita que a passagem de meia-noite UTC durante a execução de uma única chamada faça dois Projects processados em momentos diferentes do mesmo laço receberem `staleness_days` calculados contra referências diferentes.

### 4.4 Comportamento na fronteira exata de 14 dias

`is_stale = staleness_days >= PMO_STALENESS_THRESHOLD_DAYS` — **inclusivo**. Aos 14 dias exatos, `is_stale = True`. Esta é a mesma convenção já usada no código para estados terminais na fronteira (`Invitation.status()`, `src/database/models.py`: `if self.expires_at <= now: ...expired`) — no limiar exato, o estado "vencido"/"desatualizado" já se aplica, nunca espera um dia a mais. Confirmado pela tabela de testes exigida pela Founder Decision: 13 dias → `current`; 14 dias → `stale`; 15 dias → `stale`.

`staleness_days` é `(reference_time - most_recent.metadata["created_at"]).days` — a propriedade `.days` de um `timedelta` já trunca para baixo (nunca arredonda para cima), então um registro com exatamente 13 dias e 23 horas de idade produz `staleness_days = 13` (`current`), nunca `14` por arredondamento. Nenhuma lógica adicional de arredondamento é necessária — é o comportamento padrão de `timedelta.days` em Python.

### 4.5 Gatilho futuro de recalibração

Registrado explicitamente, não implementado: o valor de 14 dias é uma heurística de produto, não uma medição real (AR-13 §2.2 — nenhuma telemetria de cadência de atualização existe hoje). **Gatilho de recalibração:** quando o produto tiver uma capacidade real de observar o intervalo médio/mediano entre atualizações de status por organização (hoje inexistente), ou quando uso real gerar evidência concreta de falso-positivo/falso-negativo reportada por um usuário real — o que vier primeiro. Recalibração é sempre uma decisão de governança nova (Decision Log), nunca um ajuste silencioso de constante, e nunca vira configuração por organização apenas por causa desse gatilho ter sido acionado — a mudança seria no valor da constante global, a menos que uma nova necessidade real e comprovada de valores diferentes por organização apareça (o que exigiria sua própria análise, não presumida aqui).

### 4.6 Metadados entregues ao Advisor — confirmação

Cada `Evidence.metadata` de cada registro de status contém, além de `created_at`/`kind` (já existentes) e `project_id`/`project_name` (Domain Blueprint): `staleness_days: int`, `is_stale: bool`. O `PMOAdvisorAgent` serializa esses dois campos para o JSON do prompt (§6) — o LLM lê os números já prontos, nunca subtrai datas.

---

## 5. Modelo de resposta

### 5.1 Request

```python
class PMOAdvisorRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)

    _validate_question = field_validator("question")(_ensure_has_content)
```

Sem `project_id`/`portfolio_id` — mesmo padrão de `DocumentAdvisorRequest` (`src/api/routes/intelligence.py:189-196`), porque o escopo é sempre a organização da sessão autenticada, nunca um parâmetro do chamador.

### 5.2 Response

```python
class PMOAdvisorResponse(BaseModel):
    answer: str
    total_projects: int
    projects_with_status: int
    projects_without_status: int
    projects_stale: int
    projects_current: int
    cited_projects: list[CitedProject]
```

`CitedProject` **reaproveitado** de `src/api/routes/intelligence.py:174-178` (já definido para o Portfolio Advisor: `project_id`, `project_name`, `source_analysis_id`, `source_created_at`) — nenhuma classe nova, nenhuma duplicação.

### 5.3 Mapeamento (rascunho de referência)

```python
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
```

**Nota sobre `cited_projects` e duplicidade intencional:** ao contrário do Portfolio Advisor (onde cada Project contribui exatamente um `Evidence`, tornando `cited_projects` naturalmente único por `project_id`), o PMO Advisor pode citar múltiplos registros do mesmo Project (até 5 disponíveis). Se o LLM citar 2 registros do mesmo Project, `cited_projects` terá 2 entradas com o mesmo `project_id`, cada uma com `source_analysis_id` diferente — rastreabilidade até o `AnalysisRecord` específico, não apenas até o Project (exigência explícita da Founder Decision, item 7: "rastreabilidade até Project e AnalysisRecord"). Nenhuma deduplicação é aplicada — deduplicar destruiria exatamente a rastreabilidade que a Founder Decision pede.

### 5.4 Rota

```python
@router.post("/pmo-advisor/ask", response_model=PMOAdvisorResponse)
def ask_pmo_advisor(
    request: PMOAdvisorRequest,
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
```

Mesma RBAC (`intelligence.read`, já protege Risk/Delivery/Portfolio Advisor), mesmas dependências injetadas (`build_prompt_registry`/`build_provider`/`build_repository`/`build_rag_pipeline`/`build_domain_service`, todas já existentes), `AdvisorExecutionError` tratado igual. **Sem `HTTPException(404)`** — diferente da rota do Portfolio Advisor, porque `assemble()` nunca retorna `None` (§3.4).

---

## 6. `PMOAdvisorAgent`

`src/agents/pmo_advisor/agent.py`, mesma forma dos demais Advisors baseados em `AnalysisRecord` (serializa evidência para JSON, chama `render_prompt`/`call_llm`, delega parsing a `parse_structured_output`, nunca interpreta domínio):

```python
class PMOAdvisorAgent:
    name = "pmo_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(self, session, question, evidence, rag_context=None) -> dict:
        records_json = json.dumps(
            [
                {
                    "project_id": item.metadata["project_id"],
                    "project_name": item.metadata["project_name"],
                    "staleness_days": item.metadata["staleness_days"],
                    "is_stale": item.metadata["is_stale"],
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
            self.name, "advise", question=question, records_json=records_json
        )
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
```

### 6.1 Prompt (`src/agents/pmo_advisor/prompts/advise.md`) — diretrizes de conteúdo

- Cada registro em `records_json` já traz `staleness_days`/`is_stale` prontos — o modelo nunca deve calcular ou estimar esses valores, apenas lê-los.
- Registros com o mesmo `project_id` pertencem ao mesmo Project; dentro do mesmo `project_id`, o primeiro registro encontrado é o mais recente (garantia estrutural, `AnalysisRepository.list_analyses()` ordena por `created_at DESC`) — os demais são apenas histórico para observar recorrência/evolução, nunca substituem o estado atual.
- A ordem entre `project_id`s diferentes não implica prioridade (mesmo princípio já aplicado ao Portfolio Advisor, AR-12 §3) — o conjunto é interpretado como um todo, nunca por posição.
- Padrões só podem ser afirmados com base em múltiplos registros reais do mesmo Project ou de múltiplos Projects — nunca generalizados a partir de um único ponto.
- Toda afirmação deve citar o(s) Project(s) envolvidos pelo nome.
- O Advisor nunca avalia composição/equilíbrio de portfólio (limite do Portfolio Advisor), nunca cita documentos institucionais (limite do Governance Advisor), nunca narra a trajetória de um único projeto isoladamente sem contexto organizacional (limite do Delivery Advisor).

---

## 7. Estratégia de cobertura

As cinco contagens (§0, tabela) são produzidas **inteiramente** dentro de `PMOEvidenceAssembler.assemble()` (§3.5), nunca recalculadas na rota nem no Advisor. As invariantes exigidas pela Founder Decision são garantidas **pela própria aritmética do laço**, não verificadas depois:

- `projects_with_status + projects_without_status = total_projects` — verdadeiro porque `projects_without_status` é definido literalmente como `total_projects - projects_with_status` (nunca computado de forma independente que pudesse divergir).
- `projects_stale + projects_current = projects_with_status` — verdadeiro porque cada Project que entra em `projects_with_status` (via `continue` não executado) incrementa exatamente um dos dois (`is_stale` é booleano, `if/else` mutuamente exclusivo, nunca os dois nem nenhum).
- Um Project sem status (`project_evidence` vazio) executa `continue` **antes** de qualquer incremento de `projects_stale`/`projects_current` — estruturalmente impossível de contar como stale.

Estas três garantias não são testadas como "regras de negócio" separadas — são consequência direta da forma do código, e os testes da §9 verificam o resultado observável (as contagens), não a implementação interna.

---

## 8. Riscos residuais

| Risco | Origem | Mitigação registrada |
|---|---|---|
| Limiar de 14 dias e cap de 5 registros continuam sendo heurísticas não validadas por telemetria real | Ausência de dados históricos de cadência | Gatilho de recalibração explícito (§4.5); nunca ajustado silenciosamente |
| Volume de chamadas `gather_context()` em escopo organizacional | Organizações com muitos Projects | Mesmo gatilho de performance já aprovado para o Portfolio Advisor (20+ chamadas sequenciais ou p95 > 3s), reafirmado, nenhuma otimização antecipada |
| `cited_projects` pode conter `project_id` duplicado | Consequência intencional de citar múltiplos registros do mesmo Project | Documentado explicitamente como comportamento correto (§5.3), não uma falha a corrigir |
| Interpretação de "padrão recorrente" continua sendo leitura textual do LLM sobre histórico estruturado | Mesma natureza de risco já aceito no Governance Advisor | Nenhuma nova mitigação necessária — mesmo padrão já em produção |

Nenhum risco listado é bloqueante para a implementação.

---

## 9. Testes obrigatórios

Os 13 cenários exigidos pela Founder Decision, nomeados para rastreabilidade na implementação (mesma convenção lettered A-M já usada no Portfolio Advisor):

| # | Cenário | Cobre |
|---|---|---|
| A | Registro com exatamente 13 dias de idade → `is_stale = False` | Fronteira inferior |
| B | Registro com exatamente 14 dias de idade → `is_stale = True` | Fronteira exata (inclusiva) |
| C | Registro com exatamente 15 dias de idade → `is_stale = True` | Fronteira superior |
| D | Project sem nenhum `AnalysisRecord`/status → não conta em `projects_stale` nem `projects_current`, conta em `projects_without_status` | Ausência total de evidência |
| E | Project com mais de 5 registros de status → apenas os 5 mais recentes viram `Evidence` | Corte de volume |
| F | Project com menos de 5 registros de status → todos viram `Evidence`, nenhum corte aplicado | Ausência de corte quando desnecessário |
| G | Cobertura completa — todos os Projects da organização têm status | Contagens quando `projects_with_status = total_projects` |
| H | Cobertura parcial — alguns Projects com status, outros sem | Contagens mistas |
| I | Cobertura zero — nenhum Project da organização tem status | `no_evidence_answer`, todas as contagens refletem ausência |
| J | Invariantes aritméticas (`projects_with_status + projects_without_status = total_projects`; `projects_stale + projects_current = projects_with_status`) verificadas em todos os cenários acima | Consistência estrutural |
| K | Isolamento organizacional — Projects de outra organização nunca entram em `total_projects` nem em `evidence` | Segurança multi-tenant |
| L | Nenhuma chamada ao LLM quando `evidence` está vazio (organização sem nenhum status em nenhum Project) | Portão anti-alucinação, mesmo padrão `no_evidence()` |
| M | Rastreabilidade — cada item de `cited_projects` aponta a um `project_id`/`source_analysis_id` real e verificável no banco, incluindo o caso de múltiplas citações do mesmo Project (§5.3) | Traceability completa |

Camadas de teste (mesmo padrão do Portfolio Advisor): unitários para `PMOEvidenceAssembler` (fakes, sem banco — cobrem A-F principalmente), unitários para `PMOAdvisorAgent` (fakes), integração via `AdvisorFramework` real contra Postgres (cobrem G-L), HTTP via `TestClient` real (cobrem G-L novamente na camada de rota, mais RBAC e `no_evidence` na resposta HTTP, mais M).

---

## 10. Estratégia incremental

1. `PMOEvidenceAssembler` + `PMOAssemblyResult` + constantes (`src/agents/pmo_advisor/evidence_assembler.py`) — testado isoladamente com fakes (cenários A-F).
2. `PMOAdvisorAgent` + prompt (`src/agents/pmo_advisor/agent.py`, `prompts/advise.md`) — testado isoladamente com fakes.
3. Rota + modelo de resposta (`PMOAdvisorRequest`/`PMOAdvisorResponse`/`_pmo_advisor_response()` em `src/api/routes/intelligence.py`, reaproveitando `CitedProject`) — testes de integração via `AdvisorFramework` real (G-L) seguidos de testes HTTP (G-M).
4. Verificação final: `git diff --stat` vazio em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline/`DomainService`/`DomainRepository`/`Evidence`; suíte completa; `ruff`/`tsc`/`eslint`.

Mesma sequência já usada em Delivery e Portfolio Advisor — nenhum passo novo inventado.

---

## 11. Recomendação

**GO para a implementação.**

Nenhuma questão de arquitetura permanece em aberto para o PMO Advisor: unidade de composição, escopo, fonte, staleness (limiar, timezone, referência, fronteira, gatilho de recalibração), controle de volume, modelo de cobertura estrutural, e modelo de resposta HTTP estão todos definidos com contrato de código de referência nesta etapa. A implementação segue a estratégia incremental de 4 passos (§10), com os 13 cenários obrigatórios (§9) como critério de aceite. Ao final, retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor.
