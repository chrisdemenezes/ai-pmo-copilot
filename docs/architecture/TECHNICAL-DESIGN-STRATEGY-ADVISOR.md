# Technical Design — Strategy Advisor

**Etapa 4 de 6** do ciclo institucional do Strategy Advisor. Produzido sob autorização da Founder Decision que aprovou condicionalmente a AR-15 (`AR-15-STRATEGY-ADVISOR-ARCHITECTURE-REVIEW.md`) com **GO para o Technical Design**, impondo dez condições explícitas — reafirmação da regra de alinhamento (nunca algoritmo/score/ranking/comparação lexical); independência total entre níveis (proibido herdar, decidir precedência, preencher ausência, criar/alterar estratégia); fontes exclusivas e fechadas para este Epic; formalização matemática do namespace sintético (fórmula definitiva, prova de ausência de colisão, proibido usar apenas `-entity_id` sem namespace por nível, proibido vazar o id sintético para a resposta HTTP ou usá-lo para consulta ao banco); modelo `StrategyCitedEvidence` com forma exata; política de timestamp fundamentada no modelo real; modelo de cobertura estrutural completo, sem condensação; tratamento de ausência/cobertura parcial; preservação integral da infraestrutura compartilhada. Esta etapa detalha o contrato completo, sem escrever código.

**Harmonização registrada (Founder Decision — "Technical Design do Strategy Advisor"):** a primeira versão desta etapa foi aprovada condicionalmente — o Founder identificou uma incompatibilidade real entre a afirmação de que `records_json` nunca exporia o `source_id` sintético ao modelo (§10, versão original) e o fato de `RecommendationEngine.build()` correlacionar citações exclusivamente por `Evidence.source_id` (§10.2), o que teria impedido qualquer citação de evidência de `declared_strategy` de funcionar. Este documento já reflete a versão harmonizada: o `source_id` sintético é exposto ao LLM exclusivamente como token técnico opaco de citação (§3.4, §10, §10.2), nunca como identidade de domínio, sempre convertido para a identidade real antes da resposta HTTP (§4.3, §5) — nenhuma mudança à fórmula do namespace (§3.1, já aprovada) ou a nenhum componente de infraestrutura compartilhada foi necessária para resolver a incompatibilidade.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Regra de alinhamento: sempre julgamento semântico do `StrategyAdvisorAgent`, nunca algoritmo/score/ranking/comparação lexical/regra determinística | AR-15 (D-127) + Founder Decision |
| Código restrito a: montar evidências, preservar identidades, calcular cobertura, restringir cada unidade à sua própria estratégia declarada | Founder Decision |
| Três unidades independentes e paralelas — Portfolio, Program, Project — sem precedência, sem herança, sem preenchimento de ausência, sem criação/alteração de estratégia | Domain Blueprint + AR-15 + Founder Decision |
| Fontes fechadas para este Epic: `Portfolio.strategic_objective`/`Program.objective`/`Project.objective` (estratégia); `AnalysisRecord`/`kind="status"`/`kind="risk"` (execução) | Domain Blueprint + Founder Decision |
| Identidade sintética disjunta aprovada como mecanismo interno do `StrategyEvidenceAssembler` — fórmula exata e prova de ausência de colisão são desta etapa | AR-15 + Founder Decision |
| `StrategyCitedEvidence`: modelo exclusivo, `level`/`entity_id`/`entity_name`/`kind`/`source_id`/`created_at`, nunca reaproveitando `CitedProject`/`ExecutiveCitedEvidence` | AR-15 + Founder Decision |
| Ausência total → `no_evidence()`, zero LLM; cobertura parcial → síntese com limitação declarada, contagens estruturais preservadas | Domain Blueprint + Founder Decision |
| Preservação integral de `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline/contrato `Evidence`/contratos dos Advisors existentes | Founder Decision |

---

## 1. Executive Summary

Este Technical Design fecha o contrato de implementação do Strategy Advisor sem introduzir nenhuma decisão nova de arquitetura — formaliza, em nível de fórmula matemática e assinatura de função, o que o Domain Blueprint e a AR-15 já decidiram, resolvendo as sete exigências adicionais impostas pela aprovação condicional.

O componente central é `StrategyEvidenceAssembler` (`src/agents/strategy_advisor/evidence_assembler.py`), quarto componente de composição Classe B: resolve todos os Portfolios da organização, percorre Portfolio→Program→Project (mesma traversal do Portfolio Advisor), busca `gather_context(kind="status")`/`gather_context(kind="risk")` exatamente uma vez por Project, e monta as unidades comparáveis de cada nível — nunca interpretando alinhamento, nunca chamando o LLM, nunca decidindo qual nível prevalece.

O achado central desta etapa é a **fórmula definitiva do namespace sintético**: `synthetic_source_id = -(real_entity_id * 10 + level_code)`, com `level_code` ∈ {1 (portfolio), 2 (program), 3 (project)} — uma codificação injetiva, determinística, estável, sem dependência de faixas arbitrárias (§3), com prova formal de que nunca colide com `AnalysisRecord.id` (sempre positivo) nem entre níveis (o dígito das unidades do valor codificado sempre identifica o nível de origem de forma única). O id real de cada entidade é preservado em `Evidence.metadata["real_entity_id"]` — nunca usado para consulta ao banco, nunca apresentado como identidade real, nunca exposto na resposta HTTP (§4).

**Correção registrada nesta revisão (Founder Decision — "Technical Design do Strategy Advisor"):** `Evidence.source_id` (o valor sintético, para evidência de estratégia declarada) **precisa** ser enviado ao LLM como um token técnico opaco de citação — nunca a identidade real — porque `RecommendationEngine.build()` correlaciona citações exclusivamente por `Evidence.source_id` (`by_id = {item.source_id: item for item in evidence}`), sem nenhum mecanismo alternativo (confirmado por leitura de código, §10.2), e essa correlação não pode ser alterada nesta etapa. O `StrategyAdvisorAgent` (§10) expõe o `source_id` sintético ao modelo exclusivamente como token de citação a ecoar de volta — nunca interpretado, nunca exibido ao usuário, sempre convertido para a identidade real antes da resposta HTTP.

O modelo de cobertura estrutural expõe 18 contagens (6 por nível × 3 níveis), todas calculadas em código, nunca condensadas em uma taxa genérica (§8).

**Recomendação: GO para a implementação.**

---

## 2. Contrato do `StrategyEvidenceAssembler`

### 2.1 Localização

`src/agents/strategy_advisor/evidence_assembler.py` — exclusivo do pacote do Advisor, mesmo padrão dos três `EvidenceAssembler`s já existentes.

### 2.2 Estrutura de dados

```python
from dataclasses import dataclass
from src.services.ai_foundation.types import Evidence


@dataclass(frozen=True)
class StrategyAssemblyResult:
    evidence: list[Evidence]
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
```

Mesma disciplina de `ExecutiveAssemblyResult`/`PMOAssemblyResult`: `frozen=True`, todas as 18 contagens já calculadas — a rota e o Agent nunca recalculam nada.

### 2.3 Assinatura

```python
class StrategyEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        self._domain_service = domain_service
        self._framework = framework

    def assemble(self, organization_id: int) -> StrategyAssemblyResult:
        ...
```

Mesmo formato de `ExecutiveEvidenceAssembler.assemble()`: sem parâmetro de escopo adicional (organizacional sempre), sem caso de 404.

### 2.4 Responsabilidade (corpo, rascunho de referência — não implementação final)

```python
def assemble(self, organization_id: int) -> StrategyAssemblyResult:
    portfolios = self._domain_service.list_portfolios(organization_id) or []

    evidence: list[Evidence] = []
    counts = _StrategyCoverageCounters()  # três instâncias internas, uma por nível

    # Passo 1 -- busca a execução de cada Project exatamente uma vez.
    # execution_by_project[project.id] = {"status": Evidence | None, "risk": Evidence | None}
    execution_by_project: dict[int, dict[str, Evidence | None]] = {}
    all_projects: list[Project] = []
    for portfolio in portfolios:
        for program in self._domain_service.list_programs(organization_id, portfolio.id) or []:
            for project in self._domain_service.list_projects(organization_id, program.id) or []:
                all_projects.append(project)
                status_evidence = self._framework.gather_context(organization_id, project.name, kind="status")
                risk_evidence = self._framework.gather_context(organization_id, project.name, kind="risk")
                execution_by_project[project.id] = {
                    "status": self._enrich_execution(status_evidence[0], project) if status_evidence else None,
                    "risk": self._enrich_execution(risk_evidence[0], project) if risk_evidence else None,
                }

    # Passo 2 -- unidade Project: estratégia própria vs. execução própria.
    for project in all_projects:
        counts.projects_total += 1
        exec_items = [e for e in execution_by_project[project.id].values() if e is not None]
        has_strategy = bool(project.objective)
        has_execution = bool(exec_items)
        if has_strategy:
            counts.projects_with_declared_strategy += 1
            evidence.append(self._declared_strategy_evidence("project", project.id, project.name, project.objective))
        if has_execution:
            counts.projects_with_execution_evidence += 1
            evidence.extend(exec_items)
        if has_strategy and has_execution:
            counts.projects_comparable += 1
        if has_strategy and not has_execution:
            counts.projects_with_strategy_without_execution += 1

    # Passo 3 -- unidade Program: estratégia própria vs. execução agregada dos seus Projects
    # (reaproveitando execution_by_project -- nenhuma nova chamada a gather_context()).
    for portfolio in portfolios:
        for program in self._domain_service.list_programs(organization_id, portfolio.id) or []:
            counts.programs_total += 1
            program_projects = self._domain_service.list_projects(organization_id, program.id) or []
            exec_items = [
                e for p in program_projects for e in execution_by_project[p.id].values() if e is not None
            ]
            has_strategy = bool(program.objective)
            has_execution = bool(exec_items)
            if has_strategy:
                counts.programs_with_declared_strategy += 1
                evidence.append(self._declared_strategy_evidence("program", program.id, program.name, program.objective))
            if has_execution:
                counts.programs_with_execution_evidence += 1
                # exec_items já estão em `evidence` via o passo 2 -- nunca duplicados aqui.
            if has_strategy and has_execution:
                counts.programs_comparable += 1
            if has_strategy and not has_execution:
                counts.programs_with_strategy_without_execution += 1

    # Passo 4 -- unidade Portfolio: estratégia própria vs. execução agregada de todos os
    # Projects sob todos os seus Programs (mesma reutilização de execution_by_project).
    for portfolio in portfolios:
        counts.portfolios_total += 1
        portfolio_projects = [
            p for program in (self._domain_service.list_programs(organization_id, portfolio.id) or [])
            for p in (self._domain_service.list_projects(organization_id, program.id) or [])
        ]
        exec_items = [
            e for p in portfolio_projects for e in execution_by_project[p.id].values() if e is not None
        ]
        has_strategy = bool(portfolio.strategic_objective)
        has_execution = bool(exec_items)
        if has_strategy:
            counts.portfolios_with_declared_strategy += 1
            evidence.append(self._declared_strategy_evidence("portfolio", portfolio.id, portfolio.name, portfolio.strategic_objective))
        if has_execution:
            counts.portfolios_with_execution_evidence += 1
        if has_strategy and has_execution:
            counts.portfolios_comparable += 1
        if has_strategy and not has_execution:
            counts.portfolios_with_strategy_without_execution += 1

    return StrategyAssemblyResult(evidence=evidence, **counts.as_dict())
```

**Pontos de disciplina confirmados por este rascunho:**
- `gather_context()` chamado **exatamente uma vez por `kind` por Project**, nunca repetido para Program/Portfolio — a agregação é sempre releitura de `execution_by_project`, nunca uma nova consulta (Domain Blueprint §5.2, reafirmado).
- Cada unidade só é comparada contra o campo de objetivo que ela mesma declarou (`project.objective`/`program.objective`/`portfolio.strategic_objective`) — nunca herdado (AR-15 §3/§4).
- **Nenhuma linha deste corpo interpreta conteúdo, calcula alinhamento, gera ranking, chama o LLM ou decide qual nível prevalece** — confirmação explícita exigida pela Founder Decision item 1.
- Evidência de execução duplicada entre unidades (o mesmo `AnalysisRecord` contribuindo para Project, Program e Portfolio simultaneamente) aparece **uma única vez** na lista `evidence` final — a agregação em nível de contagem (`programs_with_execution_evidence`, etc.) nunca implica duplicar o item de `Evidence` em si.

---

## 3. Namespace sintético — fórmula definitiva e prova de ausência de colisão

### 3.1 Fórmula

```python
_LEVEL_CODE: dict[str, int] = {"portfolio": 1, "program": 2, "project": 3}


def _synthetic_source_id(level: str, real_entity_id: int) -> int:
    return -(real_entity_id * 10 + _LEVEL_CODE[level])
```

Usada **exclusivamente** para `Evidence.source_id` de evidência de estratégia declarada — nunca para evidência de execução, que continua usando `AnalysisRecord.id` real diretamente.

### 3.2 Prova de ausência de colisão

**Contra `AnalysisRecord.id`:** `AnalysisRecord.id` é uma coluna `SERIAL`/`IDENTITY`, sempre um inteiro positivo (`≥ 1`). Como `real_entity_id ≥ 1` (mesma garantia para `Portfolio.id`/`Program.id`/`Project.id`, também `SERIAL`) e `_LEVEL_CODE[level] ≥ 1`, o produto `real_entity_id * 10 + level_code ≥ 11 > 0` — portanto `_synthetic_source_id()` é **sempre estritamente negativo**. Como todo `AnalysisRecord.id` é estritamente positivo, a interseção entre os dois conjuntos é vazia por construção, para qualquer valor de `real_entity_id`, sem depender de nenhuma faixa numérica arbitrária.

**Entre os três níveis:** para qualquer inteiro codificado `real_entity_id * 10 + level_code`, o **dígito das unidades** é sempre `level_code` — porque `real_entity_id * 10` é, por definição, um múltiplo de 10 (contribui `0` ao dígito das unidades), e `level_code ∈ {1, 2, 3}` é sempre um único dígito menor que 10. Logo, o dígito das unidades do valor codificado identifica **de forma única e sem ambiguidade** o nível de origem, para qualquer magnitude de `real_entity_id` — dois `real_entity_id` diferentes do mesmo nível produzem códigos diferentes (a função `x ↦ x*10+c` é estritamente crescente e portanto injetiva para `c` fixo); o mesmo `real_entity_id` numérico em dois níveis diferentes (ex.: `Portfolio.id = 7` e `Program.id = 7`) produz códigos diferentes (`71` vs. `72`), nunca colidindo.

**Decodificação, determinística e total:**

```python
def _decode_synthetic_source_id(synthetic_id: int) -> tuple[str, int]:
    encoded = -synthetic_id
    level_code = encoded % 10
    real_entity_id = encoded // 10
    level = {1: "portfolio", 2: "program", 3: "project"}[level_code]
    return level, real_entity_id
```

`_decode_synthetic_source_id(_synthetic_source_id(level, id)) == (level, id)` para todo `level`/`id` válidos — identidade verificável por teste de propriedade (§12).

### 3.3 Determinismo, estabilidade, compatibilidade de tipo

- **Determinístico**: função pura de `(level, real_entity_id)`, sem estado externo, sem aleatoriedade, sem dependência de ordem de iteração.
- **Estável**: o mesmo par `(level, real_entity_id)` produz sempre o mesmo `synthetic_source_id`, em qualquer chamada, em qualquer momento — não depende de quantas outras entidades existem na organização (diferente de um esquema de faixas fixas por posição de iteração, que seria instável).
- **Compatível com o tipo de dados utilizado**: `Evidence.source_id: int` — Python `int` é de precisão arbitrária, sem risco de overflow para nenhuma magnitude real de `entity_id`; nenhuma mudança ao contrato `Evidence` é necessária.

### 3.4 Escopo de uso — o que é interno e o que é exposto como token opaco

- **Nunca usado para consulta ao banco** — toda consulta a `Portfolio`/`Program`/`Project` continua usando o id real, via `DomainService`.
- **Nunca apresentado como identidade real, em nenhuma superfície voltada ao usuário ou ao cliente da API** — o id sintético não aparece em nenhum campo de `StrategyCitedEvidence` nem de nenhuma resposta HTTP.
- **Nunca vaza para a resposta HTTP** — confirmado em `StrategyCitedEvidence` (§5): `entity_id`/`source_id` (para `kind="declared_strategy"`) sempre lêem `Evidence.metadata["real_entity_id"]`, nunca `Evidence.source_id`.
- **Exposto ao LLM exclusivamente como token técnico opaco de citação** (decisão explícita do Founder, harmonizando esta revisão) — o `StrategyAdvisorAgent` (§10) inclui o valor sintético no `records_json`, sob o mesmo nome de campo (`"source_id"`) já usado por todo Advisor anterior, para que o modelo o ecoe de volta em `cited_analysis_ids`; o prompt instrui explicitamente que esse valor nunca representa uma identidade real de domínio e nunca deve ser interpretado ou exibido, apenas citado.
- **Permanece o único mecanismo de correlação viável sem alterar `RecommendationEngine`** — sua função é permitir que `by_id = {item.source_id: item for item in evidence}` nunca colida quando o array de evidência combina `AnalysisRecord.id` e ids de domínio na mesma chamada (achado da AR-15 §6.1), e ao mesmo tempo seja o valor que o modelo consegue efetivamente citar de volta (§10.2).

---

## 4. Estratégia de conversão para identidades reais

### 4.1 `Evidence.metadata` para evidência de estratégia declarada

```python
def _declared_strategy_evidence(self, level: str, real_entity_id: int, entity_name: str, objective: str) -> Evidence:
    return Evidence(
        source_type="declared_strategy",
        source_id=_synthetic_source_id(level, real_entity_id),
        source_label=f"{level.capitalize()} {entity_name} -- objetivo declarado",
        content={"objective": objective},
        metadata={
            "level": level,
            "real_entity_id": real_entity_id,
            "entity_name": entity_name,
            "declared_objective": objective,
            "kind": "declared_strategy",
        },
    )
```

Preserva, no mínimo, exatamente os elementos exigidos pela Founder Decision item 4: `level`, `real_entity_id`, `entity_name`, `declared_objective`, `kind`.

### 4.2 `Evidence.metadata` para evidência de execução

```python
def _enrich_execution(self, item: Evidence, project: Project) -> Evidence:
    return Evidence(
        source_type=item.source_type,
        source_id=item.source_id,  # AnalysisRecord.id real, nunca sintético
        source_label=item.source_label,
        content=item.content,
        metadata={
            **item.metadata,  # já contém "kind" ("status"/"risk") e "created_at"
            "level": "project",  # execução só existe estruturalmente no nível Project (Domain Blueprint §2)
            "real_entity_id": project.id,
            "entity_name": project.name,
        },
    )
```

**Confirmação de honestidade de rastreabilidade:** mesmo quando um item de execução é reaproveitado na agregação de uma unidade Program/Portfolio (§2.4), seu `level`/`real_entity_id`/`entity_name` sempre identificam o **Project de origem real** — nunca relabelado como pertencendo ao Program/Portfolio que o agrega, porque `AnalysisRecord` estruturalmente nunca se associa a Program/Portfolio diretamente (mesmo fato já usado para fixar a unidade de composição em todos os Advisors Classe B anteriores).

### 4.3 Mapeamento na resposta HTTP

```python
def _strategy_cited_evidence(item: Evidence) -> "StrategyCitedEvidence":
    kind = item.metadata["kind"]
    if kind == "declared_strategy":
        source_id = item.metadata["real_entity_id"]  # nunca item.source_id (sintético)
        created_at = None  # ver §6
    else:
        source_id = item.source_id  # AnalysisRecord.id real
        created_at = item.metadata["created_at"]
    return StrategyCitedEvidence(
        level=item.metadata["level"],
        entity_id=item.metadata["real_entity_id"],
        entity_name=item.metadata["entity_name"],
        kind=kind,
        source_id=source_id,
        created_at=created_at,
    )
```

O `source_id` sintético de `Evidence` é lido **apenas** por `RecommendationEngine.build()` internamente (via `by_id`); a rota nunca lê `explanation.recommendation.cited_evidence[i].source_id` diretamente para `kind="declared_strategy"` — sempre `metadata["real_entity_id"]`.

---

## 5. Modelo `StrategyCitedEvidence`

```python
class StrategyCitedEvidence(BaseModel):
    level: str          # "portfolio" | "program" | "project"
    entity_id: int       # id real -- nunca o sintético
    entity_name: str
    kind: str             # "declared_strategy" | "status" | "risk"
    source_id: int         # entity_id real (declared_strategy) ou AnalysisRecord.id real (status/risk)
    created_at: datetime | None   # None para declared_strategy (§6); real para status/risk
```

Novo, isolado, exclusivo do Strategy Advisor — `CitedProject`/`ExecutiveCitedEvidence` nunca tocados, confirmado por `git diff` vazio na implementação. `level` e o terceiro valor de `kind` (`"declared_strategy"`) são as duas extensões que nenhum dos dois modelos existentes consegue expressar (AR-15 §6.3, reafirmado).

---

## 6. Política de timestamp

### 6.1 Verificação no modelo real

Por leitura direta de `src/database/models.py`: `Portfolio`, `Program` e `Project` possuem **apenas `created_at`** (timestamp de criação da linha) como campo de data/hora confiável — nenhum dos três possui um campo `updated_at`/`modified_at` genérico. `Portfolio`/`Program`/`Project` possuem também `last_updated`/`next_review` (`Date`, nullable), mas são campos de negócio de cadência de revisão preenchidos manualmente pelo usuário — não são um registro de auditoria automático de quando `strategic_objective`/`objective` especificamente foi definido ou alterado, e podem ficar `None` ou desatualizados independentemente do campo de objetivo ter sido editado.

### 6.2 Decisão

`created_at` da linha **não é um timestamp confiável para "quando o objetivo foi declarado"** — reflete apenas a criação inicial do registro, podendo o campo de objetivo ter sido preenchido ou alterado muito depois (o campo é nullable e claramente editável após a criação, pela própria tela de Portfolio/Program Management). Usar `created_at` da linha inventaria uma precisão que não existe, e usar o horário da própria consulta (`datetime.now()`) é explicitamente proibido pela Founder Decision (item 6).

**Decisão: `StrategyCitedEvidence.created_at` é `None` para `kind="declared_strategy"`**, em toda circunstância — nunca inventado, nunca aproximado por `created_at` da linha, nunca pelo horário da consulta. Para `kind="status"`/`"risk"`, `created_at` continua sendo o `AnalysisRecord.created_at` real, exatamente como em todo Advisor anterior.

---

## 7. Fluxo completo

```
POST /strategy-advisor/ask
  { question: string }
        │
        ▼
require_permission("intelligence.read")   -- mesma RBAC de Delivery/Portfolio/PMO/Executive Advisor
        │
        ▼
StrategyEvidenceAssembler.assemble(organization_id)
  │
  ├─ DomainService.list_portfolios(organization_id)         -- Wave 2, já em produção
  ├─ para cada Portfolio: list_programs(organization_id, portfolio.id)
  ├─ para cada Program: list_projects(organization_id, program.id)
  │     (mesma traversal Portfolio→Program→Project já usada pelo Portfolio Advisor)
  │
  └─ para cada Project (uma única vez):
        status_evidence = framework.gather_context(org_id, project.name, kind="status")
        risk_evidence   = framework.gather_context(org_id, project.name, kind="risk")
            (AdvisorFramework/AIContextEngine inalterados)
        (armazenado em execution_by_project, reaproveitado por Program/Portfolio)

  para cada Project/Program/Portfolio:
        has_strategy = bool(objective próprio)
        has_execution = bool(execução própria ou agregada)
        se has_strategy: evidence.append(declared_strategy Evidence, source_id sintético)
        se has_execution: evidence.extend(execução, source_id real)
        18 contagens estruturais calculadas (§8)

  retorna StrategyAssemblyResult(evidence, 18 contagens)
        │
        ▼
StrategyAdvisorAgent(framework)
        │
        ▼
AdvisorFramework.run(agent, session, question, result.evidence,
                      no_evidence_answer="...")                 -- INALTERADO
        │
        ▼
_strategy_advisor_response(explanation, result) → StrategyAdvisorResponse
  (cited_evidence via §4.3 -- nunca expõe source_id sintético NA RESPOSTA HTTP;
   o token sintético foi visível ao LLM como token de citação em records_json, §10)
```

---

## 8. Modelo de cobertura estrutural

### 8.1 As 18 contagens (§2.2), por nível

Para cada nível `L` ∈ {`portfolios`, `programs`, `projects`}:

| Campo | Definição |
|---|---|
| `{L}_total` | Todas as instâncias de `L` na organização |
| `{L}_with_declared_strategy` | Instâncias com o campo de objetivo próprio preenchido |
| `{L}_without_declared_strategy` | `{L}_total - {L}_with_declared_strategy` |
| `{L}_with_execution_evidence` | Instâncias com pelo menos uma evidência de execução (direta para Project, agregada para Program/Portfolio) |
| `{L}_comparable` | Interseção: `with_declared_strategy ∩ with_execution_evidence` |
| `{L}_with_strategy_without_execution` | `with_declared_strategy` menos `comparable` |

### 8.2 Invariantes testáveis

- `{L}_with_declared_strategy + {L}_without_declared_strategy = {L}_total`
- `{L}_comparable + {L}_with_strategy_without_execution = {L}_with_declared_strategy`
- `{L}_comparable ≤ min({L}_with_declared_strategy, {L}_with_execution_evidence)`

Nenhuma das 18 contagens é condensada em uma taxa/percentual genérico — cada uma é um inteiro exato calculado pela aritmética do laço em `StrategyEvidenceAssembler.assemble()`, nunca pelo LLM (Founder Decision item 7).

---

## 9. Tratamento de ausência e cobertura parcial

- **Ausência total**: `portfolios_comparable == 0 and programs_comparable == 0 and projects_comparable == 0` (nenhuma unidade comparável em nenhum nível, em toda a organização) → `result.evidence` vazio → `AdvisorFramework.run()` aciona `no_evidence()` automaticamente (mesmo portão já em produção, sem nenhuma lógica adicional no Strategy Advisor) → zero chamada ao LLM.
- **Cobertura parcial**: qualquer unidade comparável em qualquer nível → síntese permitida; o prompt (§10) instrui o modelo a declarar explicitamente quais níveis/unidades não puderam ser avaliados, usando as 18 contagens já calculadas.

---

## 10. `StrategyAdvisorAgent` (rascunho de referência)

```python
class StrategyAdvisorAgent:
    name = "strategy_advisor"

    def __init__(self, framework: AdvisorFramework):
        self.framework = framework

    def advise(self, session, question, evidence, rag_context=None) -> dict:
        records_json = json.dumps(
            [
                {
                    "level": item.metadata["level"],
                    "entity_id": item.metadata["real_entity_id"],
                    "entity_name": item.metadata["entity_name"],
                    "kind": item.metadata["kind"],
                    "content": item.content,
                    "source_id": item.source_id,  # token de citação -- sintético para
                        # declared_strategy, AnalysisRecord.id real para status/risk;
                        # ver §10.2 -- nunca a identidade real de domínio para declared_strategy.
                }
                for item in evidence
            ],
            ensure_ascii=False,
        )
        final_prompt = self.framework.render_prompt(self.name, "advise", question=question, records_json=records_json)
        raw_output = self.framework.call_llm(self.name, session, final_prompt)
        return parse_structured_output(raw_output)
```

**Correção desta revisão:** `records_json` inclui `"entity_id"` (sempre a identidade real, `metadata["real_entity_id"]`, útil ao modelo para nomear a unidade em prosa) **e** `"source_id"` (sempre `item.source_id`, o valor efetivamente presente em `Evidence.source_id` — sintético para `declared_strategy`, `AnalysisRecord.id` real para `status`/`risk`). O modelo deve **citar sempre `"source_id"`** em `cited_analysis_ids`, nunca `"entity_id"` — apenas `"source_id"` é o que `RecommendationEngine.build()` consegue correlacionar de volta a um item de `Evidence` (§10.2).

### 10.1 Diretrizes de prompt (não texto final)

- Cada registro tem `"level"` (`"portfolio"`/`"program"`/`"project"`) e `"kind"` (`"declared_strategy"`/`"status"`/`"risk"`) — o modelo deve ler `content.objective` quando `kind="declared_strategy"`, e a forma real de status/risco (já estabelecida para o Executive Advisor) nos demais casos.
- Cada unidade (identificada por `level`+`entity_id`) é avaliada **apenas contra seus próprios registros** — o modelo nunca compara a execução de um Project contra o objetivo de outro Project/Program/Portfolio.
- **`"source_id"` é um token técnico opaco de citação, não uma identidade de domínio** — o modelo deve sempre copiá-lo literalmente para `cited_analysis_ids` ao citar aquele registro, nunca interpretá-lo, nunca exibi-lo na resposta em prosa, nunca assumir qualquer significado sobre seu valor numérico (positivo ou negativo). Para se referir à unidade em prosa, o modelo usa `"entity_name"`/`"level"`, nunca `"source_id"`.
- O julgamento de alinhamento é sempre semântico, sempre fundamentado nos dois registros da mesma unidade (objetivo declarado + execução), sempre citado por `source_id` — nunca um score, nunca um ranking, nunca influenciado pela quantidade de evidência de execução disponível.
- O modelo nunca decide qual nível prevalece caso observe divergência textual entre declarações de níveis diferentes da mesma cadeia — pode apenas observar, nunca resolver.
- O modelo nunca infere um objetivo para uma unidade sem `objective`/`strategic_objective` próprio — declara a ausência explicitamente quando relevante à pergunta.

### 10.2 Prova de que nenhum outro mecanismo de correlação existe sem alterar `RecommendationEngine`

Por leitura direta de `src/services/ai_foundation/recommendation_engine.py`:

```python
def build(answer, cited_ids, evidence):
    by_id = {item.source_id: item for item in evidence}
    cited = [by_id[cited_id] for cited_id in cited_ids if cited_id in by_id]
    return Recommendation(answer=answer, cited_evidence=cited)
```

A única chave de correlação que este método aceita é `Evidence.source_id` — não existe parâmetro adicional, não existe correlação por `metadata`, não existe segunda função de matching. Como o Founder proibiu explicitamente qualquer alteração a `RecommendationEngine` nesta etapa, e como o modelo só pode citar um registro devolvendo um valor que exista em `by_id`, a única forma estruturalmente possível de o modelo citar uma evidência de `kind="declared_strategy"` é ele receber, no `records_json`, exatamente o mesmo valor que está em `Evidence.source_id` daquele item — o `synthetic_source_id`. Não há caminho alternativo dentro dos limites impostos por esta Founder Decision; a exposição do token sintético ao LLM (exclusivamente como valor a ecoar, nunca a interpretar) é, portanto, não uma preferência de implementação, mas a única solução compatível com a preservação integral de `RecommendationEngine` já exigida desde o Domain Blueprint.

---

## 11. Riscos residuais

| Risco | Origem | Mitigação registrada |
|---|---|---|
| Volume de chamadas — mesmo perfil do Executive Advisor (2 × total de Projects), mas agora com traversal adicional Portfolio→Program | Já registrado no Domain Blueprint | Mesmo gatilho de performance já aprovado; `execution_by_project` garante zero chamadas duplicadas |
| 18 contagens tornam o modelo de resposta mais largo que qualquer Advisor anterior | Decisão explícita da Founder Decision item 7 (proibição de condensar) | Aceito conscientemente — nenhuma contagem omitida |
| `created_at=None` para `declared_strategy` pode surpreender um consumidor da API que espere sempre um timestamp | Consequência direta da política de timestamp (§6) | Documentado explicitamente no contrato; nunca inventado como alternativa |
| **Inconsistência identificada e corrigida nesta revisão:** a versão original desta etapa afirmava que `records_json` nunca expunha o `source_id` sintético ao modelo, o que teria quebrado a correlação de citação para `declared_strategy` (`RecommendationEngine.build()` correlaciona exclusivamente por `Evidence.source_id`) | Comprovado por leitura de código (§10.2), identificado pelo Founder antes da implementação | Corrigido nesta mesma revisão (§10/§10.2) — `source_id` sintético agora exposto ao LLM exclusivamente como token de citação opaco, nunca interpretado, sempre convertido para identidade real antes da resposta HTTP; cenário de teste P adicionado especificamente para este caminho |

Nenhum risco listado é bloqueante para a implementação.

---

## 12. Cenários de teste obrigatórios

| # | Cenário | Cobre |
|---|---|---|
| A | Project com `objective` e execução (status+risk) | `projects_comparable` incrementado |
| B | Project com `objective` mas sem execução | `projects_with_strategy_without_execution` incrementado |
| C | Project sem `objective` mas com execução | Nem comparável nem "with_strategy_without_execution" — apenas `projects_with_execution_evidence` |
| D | Project sem `objective` e sem execução | Nenhuma das 3 contagens de "with" incrementada |
| E | Program com `objective`, Projects sob ele com execução, Program sem `objective` próprio de nenhum Project necessariamente | `programs_comparable` via agregação, independente do estado de cada Project individualmente |
| F | Portfolio com `strategic_objective`, agregação de execução de múltiplos Programs/Projects | `portfolios_comparable`, nenhuma chamada duplicada de `gather_context()` |
| G | Program sem `objective` entre um Portfolio comparável e um Project comparável | Ausência intermediária confirmada não propagar (AR-15 §4) |
| H | Ausência total (nenhuma unidade comparável em nenhum nível) | `no_evidence()`, zero chamada ao LLM |
| I | Cobertura parcial (algumas unidades comparáveis, outras não) | Síntese permitida, limitação declarada |
| J | Colisão potencial de id — `Portfolio.id` numericamente igual a um `AnalysisRecord.id` presente na mesma resposta | `source_id` sintético nunca colide, citação correta preservada |
| K | Teste de propriedade: `_decode_synthetic_source_id(_synthetic_source_id(level, id)) == (level, id)` para amostra ampla de `level`/`id` | Prova de injetividade (§3.2) |
| L | `source_id` sintético nunca aparece em `StrategyCitedEvidence` (nem para `declared_strategy` nem em nenhum outro campo) | Confirmação de não-vazamento (§3.4) |
| M | Duas citações da mesma unidade Project com `kind`s diferentes (`declared_strategy` + `status`) permanecem distinguíveis | Rastreabilidade multi-kind, mesmo padrão do Executive Advisor |
| N | Isolamento organizacional — Portfolios/Programs/Projects de outra organização nunca entram em nenhuma contagem | Mesmo padrão de todos os Advisors anteriores |
| O | `created_at` sempre `None` para `kind="declared_strategy"`, sempre preenchido para `status`/`risk` | Política de timestamp (§6) |

### 12.1 Cenários adicionais exigidos pela Founder Decision de harmonização

| # | Cenário | Cobre |
|---|---|---|
| P | **Citação real de `declared_strategy` ponta a ponta** — `_ScriptedProvider` cita o `source_id` sintético de um registro `declared_strategy` real (via `framework.run()` completo, nunca um fake isolado); `explanation.recommendation.cited_evidence` resolve exatamente ao item correto | Prova de que a correlação funciona de fato — o cenário que teria capturado a inconsistência original |
| Q | **Conversão do token sintético para identidade real** — `_strategy_advisor_response()` mapeia um `Evidence` de `declared_strategy` citado (`source_id` sintético) para `StrategyCitedEvidence.entity_id`/`.source_id` sempre iguais ao id real, nunca ao valor sintético | Confirmação de conversão (§4.3) |
| R | **Ausência de vazamento do token** — o `source_id` sintético nunca aparece em nenhum campo de `StrategyAdvisorResponse` (serialização completa da resposta HTTP inspecionada) | Mesmo cenário de L, reafirmado no nível da resposta HTTP completa |
| S | **Portfolio/Program/Project com o mesmo id real geram tokens sintéticos distintos** — ex.: `Portfolio.id = 7` e `Program.id = 7` na mesma organização produzem `source_id`s sintéticos diferentes (`-71` vs. `-72`), ambos citáveis sem ambiguidade | Prova de disjunção entre níveis (§3.2), cenário explícito além do teste de propriedade genérico |
| T | **Estratégia declarada e execução citadas simultaneamente** — uma resposta cita, na mesma chamada, um registro `declared_strategy` (`source_id` sintético) e um registro `status`/`risk` (`AnalysisRecord.id` real) sem colisão nem perda de nenhuma das duas citações | Prova de coexistência correta dos dois espaços de identificador na mesma resposta |
| U | **Descarte de token inventado** — o modelo cita um `source_id` (sintético ou real) que nunca esteve em `evidence`; `RecommendationEngine.build()` já filtra por `cited_id in by_id` (mecanismo existente, inalterado) — confirmado especificamente para o caso de um valor sintético jamais emitido pelo `StrategyEvidenceAssembler` | Reafirmação do portão anti-alucinação de citação para o novo espaço de identificador |

Cenários J (colisão com `AnalysisRecord`) e K (propriedade de round-trip da decodificação) já cobrem, respectivamente, duas das oito exigências da Founder Decision de harmonização; P-U cobrem as seis restantes.

Camadas de teste (mesmo padrão de Executive/PMO Advisor): unitários para `StrategyEvidenceAssembler` (fakes, cobrem A-G, J, K, L, O, S); unitários para `StrategyAdvisorAgent` (fakes, cobrem M, R na formação do JSON); integração via `AdvisorFramework` real contra Postgres (cobrem H-N, P, Q, T, U); HTTP via `TestClient` (cobrem H-N, P, Q, R, T, U novamente, mais RBAC/auditoria).

---

## 13. Estratégia incremental

1. `StrategyEvidenceAssembler` + `StrategyAssemblyResult` + funções de namespace sintético (`_synthetic_source_id`/`_decode_synthetic_source_id`) — testadas isoladamente com fakes (cenários A-G, testes de propriedade K).
2. `StrategyAdvisorAgent` + prompt (`src/agents/strategy_advisor/agent.py`, `prompts/advise.md`) — testado isoladamente com fakes (cenário M, confirmação L de não-vazamento na formação do JSON).
3. Rota + modelo de resposta (`StrategyAdvisorRequest`/`StrategyCitedEvidence`/`StrategyAdvisorResponse`/`_strategy_advisor_response()` em `src/api/routes/intelligence.py`) — testes de integração via `AdvisorFramework` real (H-O) seguidos de testes HTTP (H-O).
4. Verificação final: `git diff --stat` vazio em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline/contrato `Evidence`/`CitedProject`/`PortfolioAdvisorResponse`/`PMOAdvisorResponse`/`ExecutiveAdvisorResponse`; suíte completa; `ruff`/`tsc`/`eslint`.

Mesma sequência já usada em Delivery, Portfolio, PMO e Executive Advisor — nenhum passo novo inventado.

---

## 14. Recomendação

**GO para a implementação.**

Nenhuma questão de arquitetura permanece em aberto para o Strategy Advisor: fórmula definitiva do namespace sintético com prova formal de ausência de colisão; estratégia de conversão para identidades reais garantindo zero vazamento na resposta HTTP; contrato de citação harmonizado — o token sintético é exposto ao LLM exclusivamente como valor de citação opaco (§10/§10.2, correção desta revisão, com prova de que nenhum outro mecanismo de correlação é possível sem alterar `RecommendationEngine`), nunca interpretado, nunca exposto ao usuário; modelo `StrategyCitedEvidence` completo; política de timestamp fundamentada no modelo real (`created_at=None` para `declared_strategy`, nunca inventado); modelo de cobertura estrutural com 18 contagens e invariantes explícitas; tratamento de ausência/cobertura parcial; contrato completo do `StrategyEvidenceAssembler` e do `StrategyAdvisorAgent`. A implementação segue a estratégia incremental de 4 passos (§13), com os 21 cenários obrigatórios (§12/§12.1) como critério de aceite. Ao final, retorno obrigatório para Executive Review antes de qualquer trabalho posterior.
