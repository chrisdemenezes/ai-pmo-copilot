# Domain Blueprint — Portfolio Advisor (etapa 2 de 6 do ciclo institucional, primeiro Advisor Classe B)

**Autorização:** "Founder Decision — Advisor Specification do Portfolio Advisor" (veredito **APPROVED CONDITIONALLY — GO para o Domain Blueprint**), fixando 8 diretrizes: (1) Classe B confirmada — composição ocorre sobre múltiplos projetos independentes do mesmo Portfolio, ainda que a fonte de cada um seja `AnalysisRecord`/`kind="status"`; (2) escopo inicial exclusivamente `kind="status"`, nenhuma segunda fonte (risk/meeting/action_items/RAG) neste Epic; (3) a composição não deve ficar na rota HTTP — um componente próprio do Portfolio Advisor deve assumir essa responsabilidade, nomenclatura e localização definitivas a decidir **neste documento**; (4) preservar byte-for-byte `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline/`RecommendationEngine`/`ExplanationEngine`; (5) avaliar impacto de performance de N chamadas a `gather_context()` sem otimização especulativa, registrando um gatilho objetivo; (6) definir comportamento para 8 casos de domínio obrigatórios; (7) rastreabilidade mínima por `Evidence` consolidada (`project_id`/`project_name`/`program_id`/`source_id`/`created_at`/conteúdo); (8) apresentar ao final Executive Summary, modelo de domínio, responsabilidade/localização do componente, fluxo de composição, limites de atuação, tratamento de projetos sem evidência, estratégia de rastreabilidade, riscos, critérios de sucesso, recomendação GO/NO-GO. Nenhum código escrito nesta etapa.

---

## Executive Summary

O Portfolio Advisor confirma-se Classe B (D-104): a composição não é sobre múltiplas fontes de *tipo* diferente (ainda `kind="status"` exclusivamente, per diretriz 2), mas sobre múltiplas fontes *independentes por escopo* — um `AnalysisRecord`/`kind="status"` por projeto, cada projeto sendo uma fonte primária própria. A composição vive inteiramente em um componente novo e específico deste Advisor — **`PortfolioEvidenceAssembler`** (§3), localizado em `src/agents/portfolio_advisor/`, nunca na rota HTTP (que permanece um adaptador fino) e nunca em `AdvisorFramework`/`AIContextEngine` (ambos preservados byte-for-byte, confirmado por não exigirem nenhum método novo — apenas chamadas repetidas ao que já existe). O componente resolve o Portfolio dentro do escopo organizacional reutilizando `DomainService` (Wave 2, já em produção, já org-scoped), lista Programs e Projects, solicita evidência de status de cada Project via `AdvisorFramework.gather_context()` (uma chamada por projeto), e consolida tudo em uma única `list[Evidence]` enriquecida com `project_id`/`project_name`/`program_id` em `metadata` — sem alterar o contrato `Evidence` em si. Os 8 casos de domínio obrigatórios (§7) são todos resolvidos por composição do que já existe: nenhum caso exige lógica de negócio nova, apenas o portão anti-alucinação já estrutural (`AdvisorFramework.run()`) e a semântica natural de "portfólio sem evidência" = lista vazia. Recomendação ao final: **GO para a Architecture Review.**

---

## 0. Escopo e não-escopo deste documento

**Decide:** modelo de domínio do Portfolio Advisor (§1); nome e localização definitivos do componente de montagem (§3, per exigência explícita do Founder nesta etapa); fluxo completo de composição (§4); tratamento conceitual dos 8 casos obrigatórios (§7); estratégia de rastreabilidade (§8); gatilho objetivo de performance (§9).

**Não decide (fica para etapas seguintes):**
- **Architecture Review:** validação formal de que o padrão de composição proposto (fora do Framework) não introduz nenhum acoplamento indevido; avaliação se este padrão deve ser mandatado como referência obrigatória para PMO/Executive Advisor (achado de AR-8 §7.3) ou apenas recomendado.
- **Technical Design:** texto literal do prompt do `PortfolioAdvisorAgent`; wording exato de `no_evidence_answer`; nome definitivo da rota HTTP; RBAC definitivo (`intelligence.read`, proposto por analogia ao Risk/Delivery Advisor, a confirmar).

---

## 1. Modelo de domínio do Portfolio Advisor

Confirmado por leitura direta de `src/database/models.py`/`src/database/domain_repository.py`/`src/services/domain_service.py` — nenhuma entidade nova:

```
Portfolio (1) ──── (N) Program ──── (N) Project ──── (N) AnalysisRecord (kind="status")
   │                                                          │
   │ organization_id direto                                   │ organization_id direto
   │ (Program/Project derivam                                 │ (já existente, Wave 1/3)
   │  transitivamente)                                         │
   ▼                                                          ▼
DomainService.get_portfolio()/list_programs()/list_projects()   AIContextEngine.gather()
   (Wave 2, já em produção, já org-scoped)                       (Wave 3, já em produção)
```

O Portfolio Advisor não introduz nenhuma nova entidade de domínio — opera inteiramente sobre a cadeia `Portfolio → Program → Project` já persistida (Wave 2) e sobre `AnalysisRecord` já persistido (Wave 1/3). O único artefato novo é o componente de composição (§3), que é *comportamento de montagem de evidência*, não uma entidade de domínio.

---

## 2. Objetivo e responsabilidade (per `ENTERPRISE-ADVISOR-CATALOG.md` §5, reafirmado)

**Objetivo:** apoiar decisões de composição e priorização de portfólio.

**Responsabilidade:** avaliar equilíbrio, dependências e sobreposição entre projetos/programas dentro de um portfólio — respondendo perguntas em linguagem natural, sempre citando programas/projetos reais.

**Reafirmado, per diretriz 2 desta autorização:** apenas `AnalysisRecord`/`kind="status"` compõe a evidência. Riscos e bloqueios só entram na síntese quando já mencionados dentro do conteúdo das próprias análises de status — mesma disciplina já aplicada ao Delivery Advisor (D-104/D-106).

---

## 3. Responsabilidade e localização do componente de montagem — decisão desta etapa

### 3.1 Nome definitivo

**`PortfolioEvidenceAssembler`** — nomenclatura escolhida (entre as duas sugeridas pelo Founder) por consistência com o vocabulário já estabelecido nesta plataforma (`RecommendationEngine`, `ExplanationEngine`, `AIFoundationAudit`): substantivo do domínio + sufixo de papel funcional, nunca "Context" (termo já reservado, com sentido específico, para `AIContextEngine`, evitando ambiguidade de leitura).

### 3.2 Localização definitiva

`src/agents/portfolio_advisor/evidence_assembler.py` — dentro do próprio pacote do Advisor, ao lado de `agent.py` e `prompts/`, nunca em `src/services/` (que reuniria componentes compartilhados). Isso materializa, na estrutura de diretórios, a exigência do Founder de que o componente **não é abstração genérica nesta etapa** — pertence exclusivamente ao Portfolio Advisor até que um segundo consumidor real (ex.: PMO Advisor, quando chegar sua vez) demonstre a mesma necessidade, per o princípio já aplicado a `normalize_rag_evidence()` (D-086: centralizado apenas quando dois consumidores reais existiram, não antes).

### 3.3 Responsabilidade exclusiva (per diretriz 3, reafirmada)

```
class PortfolioEvidenceAssembler:
    def __init__(self, domain_service: DomainService, framework: AdvisorFramework):
        ...
    def assemble(self, organization_id: int, portfolio_id: int) -> list[Evidence] | None:
        ...
```

- Valida e resolve o Portfolio dentro do escopo organizacional (`DomainService.get_portfolio()`).
- Lista Programs (`DomainService.list_programs()`).
- Lista Projects de cada Program (`DomainService.list_projects()`).
- Solicita a evidência de status de cada Project **por meio do `AdvisorFramework`** (`framework.gather_context(organization_id, project.name, kind="status")`), nunca acessando `AIContextEngine`/`AnalysisRepository` diretamente.
- Consolida as evidências em uma única lista, enriquecida (§8) antes de `AdvisorFramework.run()` ser chamado.

**O que este componente explicitamente NÃO faz (reafirmação literal das 6 restrições do Founder):** não pertence ao `AdvisorFramework`; não pertence ao `AIContextEngine`; não contém regra de negócio (não decide o que uma "sobreposição" ou "equilíbrio" significa — isso é interpretação do `PortfolioAdvisorAgent`/LLM); não interpreta evidências (não lê `content` para tirar conclusões, apenas resolve/agrupa/anota metadados estruturais); não chama o LLM; não se generaliza além do Portfolio Advisor nesta etapa.

---

## 4. Fluxo de composição de evidências

```
Rota (POST /portfolio-advisor/ask, nome definitivo per Technical Design)
  │   adaptador fino: extrai portfolio_id/question, monta SessionContext,
  │   delega tudo abaixo -- nenhuma lógica de composição na rota (diretriz 3)
  ▼
PortfolioEvidenceAssembler.assemble(organization_id, portfolio_id)
  │
  ├─ domain_service.get_portfolio(organization_id, portfolio_id)
  │     -- None se não existe ou não pertence à organização (§7, casos 1/2)
  │     -- reaproveita o mesmo portão 404-not-403 já usado por toda a API
  │        de Enterprise Domain (nenhuma extensão)
  │
  ├─ domain_service.list_programs(organization_id, portfolio_id)
  │     -- pode ser [] (§7, caso 3)
  │
  ├─ para cada Program: domain_service.list_projects(organization_id, program.id)
  │     -- pode ser [] por Program (§7, caso 4)
  │
  ├─ para cada Project resolvido: framework.gather_context(organization_id,
  │     project.name, kind="status")
  │     -- pode retornar [] por Project (§7, caso 5) -- não é erro, é estado
  │        legítimo ("projeto ainda sem análise de status")
  │
  └─ enriquecimento: para cada Evidence retornada, constrói uma NOVA Evidence
        (mesmo dataclass, `frozen=True` -- nunca mutação), com metadata
        estendida: {..., "project_id": project.id, "project_name": project.name,
        "program_id": program.id} -- feito inteiramente dentro do Assembler,
        nunca em AIContextEngine (§8)
  ▼
evidence: list[Evidence]  -- pode ser [] no total (§7, casos 3/4, ou todos os
  projetos sem status) -- consolidação simples de concatenação, sem lógica
  ▼
framework.run(portfolio_advisor_agent, session, question, evidence,
               no_evidence_answer="...", ...)
  │   byte-for-byte igual a qualquer outro Advisor -- run() nunca soube, e
  │   continua não sabendo, que evidence veio de 1 ou N projetos
  ├─ if not evidence: RecommendationEngine.no_evidence(...)  -- cobre §7
  │     casos 3/4/todos-sem-status, sem nenhum mecanismo novo
  ├─ PortfolioAdvisorAgent.advise(...)  -- único componente de interpretação
  └─ RecommendationEngine.build()/ExplanationEngine.explain()  -- inalterados
```

**Confirmação explícita (diretriz 4):** nenhuma etapa acima introduz um método novo em `AdvisorFramework`/`AIContextEngine`. `gather_context()` é chamado N vezes com a mesma assinatura já existente; `run()` é chamado exatamente 1 vez, como sempre.

---

## 5. Limites de atuação (idênticos a todos os Advisors, `AR-8` §8 — reafirmados, não redecididos)

- Nunca invocado por `WorkflowRuntime`; nunca registrado como handler de `EventDispatcher`.
- Nunca executa regra de negócio, nunca altera entidade — produz exclusivamente `Explanation`/`Recommendation`.
- Nunca interpreta além da evidência — se o portfólio não tem projetos com `AnalysisRecord` de status relevante, `no_evidence()`, nunca infere.
- **Específico deste Advisor (catálogo §5, reafirmado):** não decide alocação de orçamento ou prioridade — evidencia trade-offs de composição para quem decide.
- **Específico do `PortfolioEvidenceAssembler` (diretriz 3, reafirmada):** nunca interpreta conteúdo de evidência, nunca chama o LLM, nunca decide o que é "equilíbrio"/"sobreposição" — apenas resolve, lista e concatena.

---

## 6. Tratamento de projetos sem evidência

Um Project sem `AnalysisRecord` de `kind="status"` simplesmente não contribui nenhuma `Evidence` à lista consolidada — não é um erro, não gera exceção, não é sinalizado de forma especial pelo `PortfolioEvidenceAssembler` (que apenas concatena o que `gather_context()` devolveu, vazio ou não, por projeto). A ausência **parcial** (alguns projetos com evidência, outros sem, §7 caso 6) é tratada de forma idêntica — a lista final simplesmente contém menos itens do que o total de projetos do portfólio. **Regra de domínio a codificar no prompt (Technical Design, não decidida aqui):** o `PortfolioAdvisorAgent` nunca deve afirmar ou implicar cobertura de 100% do portfólio quando a evidência cobre apenas parte dos projetos — deve declarar explicitamente quantos/quais projetos sustentam a síntese, nunca generalizar silenciosamente para os que não têm evidência.

---

## 7. Casos obrigatórios de domínio (per diretriz 6, comportamento conceitual — não implementação)

| # | Caso | Comportamento |
|---|---|---|
| 1 | Portfolio não existe | `get_portfolio()` retorna `None` → `PortfolioEvidenceAssembler.assemble()` propaga `None` → rota mapeia para 404, mesmo padrão 404-not-403 já usado por `GET /portfolios/{id}` — nenhuma distinção entre "não existe" e "existe, mas não é seu" na resposta (nenhum vazamento de existência). |
| 2 | Portfolio pertence a outra organização | Idêntico ao caso 1 — `get_portfolio(organization_id, portfolio_id)` já filtra por organização na própria query; resultado é o mesmo `None`, nenhuma distinção observável. |
| 3 | Portfolio sem Programs | `list_programs()` retorna `[]` → nenhum Project resolvido → `evidence == []` → `no_evidence()`, sem chamada ao LLM. |
| 4 | Portfolio com Programs, sem Projects | `list_projects()` retorna `[]` para todo Program → mesmo resultado do caso 3. |
| 5 | Projects sem `AnalysisRecord` de status | Cada chamada a `gather_context()` para esses projetos retorna `[]` — se **todos** os projetos do portfólio estiverem nesse estado, resultado idêntico ao caso 3/4 (`no_evidence()`). |
| 6 | Parte dos Projects com evidência, parte sem | `evidence` não vazia, mas parcial — `PortfolioAdvisorAgent` deve declarar explicitamente a cobertura parcial (§6), nunca generalizar. Não é um caso de erro nem de `no_evidence()`. |
| 7 | Múltiplos Projects críticos (ex.: vários `red`) | Caso normal de síntese — cada `Evidence` carrega `project_id`/`project_name` (§8), permitindo ao Advisor nomear individualmente cada projeto crítico na resposta, citando todos, nunca resumindo "vários projetos" sem nomeá-los. |
| 8 | Históricos com datas de atualização diferentes entre projetos | Cada `Evidence` carrega seu próprio `created_at` (§8) — o prompt (Technical Design) deve instruir o Advisor a nunca presumir sincronia entre as análises de projetos diferentes, citando a data de cada uma quando relevante para a resposta. **Proposta, não decisão final:** o Assembler inclui apenas o `AnalysisRecord` de status **mais recente por projeto** (não o histórico completo de cada projeto) — a síntese de portfólio é sobre o estado atual comparado entre projetos, não sobre a evolução temporal de cada um isoladamente (papel já resolvido pelo Delivery Advisor); confirmação reservada à Architecture Review/Technical Design. |

---

## 8. Estratégia de rastreabilidade (per diretriz 7)

`Evidence.metadata` (já um campo genérico, dict aberto, per seu próprio design em AR-9: "carries auxiliary, source-specific facts... without inventing a new top-level field per future source_type") é estendido pelo `PortfolioEvidenceAssembler` — nunca por `AIContextEngine` — com os três campos que `gather_context()` não inclui hoje (`project_id`, `project_name`, `program_id`), construindo uma nova instância de `Evidence` (dataclass `frozen=True`, nunca mutada) a partir da que `gather_context()` devolveu:

```
Evidence(
    source_type="analysis_record",          # já existente, inalterado
    source_id=original.source_id,            # já é o id do AnalysisRecord (source_id)
    source_label=original.source_label,       # já existente, inalterado
    content=original.content,                 # conteúdo da análise, já existente
    metadata={
        **original.metadata,                  # created_at, kind -- já existentes
        "project_id": project.id,
        "project_name": project.name,
        "program_id": program.id,
    },
)
```

Nenhum campo novo no dataclass `Evidence` em si — apenas uso do campo `metadata` exatamente como projetado para "fatos auxiliares específicos da fonte", sem inventar um campo de topo por `source_type`. `RecommendationEngine.build()`/`ExplanationEngine.explain()` continuam operando sobre `source_id` para filtrar citações — inalterados, confirmando que o enriquecimento é aditivo e opaco ao Framework. O `PortfolioAdvisorAgent` cita os Projects que sustentam a síntese lendo `metadata["project_name"]`/`metadata["project_id"]` de cada item de `evidence` — mesma disciplina de citação real já aplicada a todo Advisor anterior.

---

## 9. Performance (per diretriz 5 — avaliar, não otimizar especuladamente)

**Confirmado, não implementado:** cada chamada a `gather_context()` já é uma consulta indexada e barata (`AnalysisRecord.organization_id`/`project_id`/`kind`, todos indexados per `src/database/repository.py`) — N chamadas sequenciais para N projetos é o comportamento aceito nesta etapa. **Nenhuma otimização especulativa introduzida:** sem API batch, sem paralelismo, sem cache específico, sem novo repository agregado, per instrução explícita do Founder.

**Gatilho objetivo registrado para futura otimização** (a validar/ajustar com dado real de uso, não uma medição já realizada): se um portfólio real exigir mais de **20 chamadas sequenciais** a `gather_context()` (ou seja, mais de 20 Projects ativos no mesmo Portfolio) **ou** se a latência p95 observada de `POST /portfolio-advisor/ask` em uso real exceder **3 segundos**, isso deve ser registrado como uma Decision Proposal explícita (mesmo padrão já usado para "Knowledge Version Resolution", D-090) avaliando batch/paralelismo/cache — nunca implementado preventivamente sem esse gatilho ser cruzado por dado real.

---

## 10. Riscos e decisões que ficam para a Architecture Review/Technical Design (não bloqueiam este Blueprint)

1. **Confirmação do padrão de composição** (§3/§4) como referência obrigatória (ou apenas recomendada) para PMO/Executive Advisor — Architecture Review, per achado já nomeado em AR-8 §7.3.
2. **Proposta de "apenas o status mais recente por projeto"** (§7, caso 8) — confirmação reservada à Architecture Review/Technical Design.
3. **Wording exato do prompt** para cobertura parcial (§6) e para datas heterogêneas (§7, caso 8) — Technical Design.
4. **Nome definitivo da rota HTTP, RBAC definitivo** (`intelligence.read` proposto por analogia) — Technical Design.
5. **TD-015** — não incide (nenhum uso de RAG/`normalize_rag_evidence()` neste Advisor).
6. **Gatilho de performance** (§9) — registrado, não uma decisão de otimização; nenhuma ação até ser cruzado por dado real.

Nenhum risco listado bloqueia o avanço para a Architecture Review.

---

## 11. Critérios de sucesso (per catálogo §5 + diretrizes desta autorização)

1. Toda recomendação de composição rastreável a projetos/programas reais do portfólio avaliado (per catálogo).
2. Nenhuma citação de projeto sem o `project_id`/`project_name` real presente em `evidence` (§8).
3. Nenhuma resposta implica cobertura de 100% do portfólio quando a evidência é parcial (§6/§7 caso 6).
4. `no_evidence()` funciona sem chamada ao LLM quando nenhum projeto do portfólio tem evidência de status (§7 casos 3/4/5) — mesmo padrão já provado.
5. Portfolio inexistente ou de outra organização nunca distinguível na resposta (§7 casos 1/2) — mesmo portão 404-not-403 já estrutural.
6. Nenhum método novo em `AdvisorFramework`/`AIContextEngine` — confirmável por leitura de código do `PortfolioEvidenceAssembler`.

---

## 12. Recomendação GO/NO-GO para a Architecture Review

**GO.** O componente de composição (`PortfolioEvidenceAssembler`, §3) tem nome, localização e responsabilidade definidos nesta etapa, per exigência explícita do Founder — nenhuma decisão de nomenclatura fica pendente. Toda a infraestrutura necessária já existe e já está em produção (`DomainService`, `AIContextEngine.gather()`) — nenhuma extensão de Framework identificada. Os 8 casos de domínio obrigatórios (§7) são resolvidos por composição do que já existe, sem lógica de negócio nova. O único ponto que a Architecture Review deve confirmar formalmente é se este padrão de composição deve ser mandatado como referência obrigatória para os próximos Advisors de Classe B — não um risco estrutural, uma decisão de governança do processo.

---

## 13. Próximo passo

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de prosseguir à Architecture Review (etapa 3).
