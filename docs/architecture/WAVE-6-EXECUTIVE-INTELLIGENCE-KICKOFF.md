# Wave 6 — Executive Intelligence: Architecture Kickoff

**Status:** documento orientador da Wave 6, autorizado pelo Founder ("Founder Decision — Encerramento Oficial da Wave 5", D-132, 2026-08-06). **Nenhum código é escrito por este documento. Nenhum Technical Design. Nenhum Domain Blueprint. Nenhuma implementação. Nenhuma alteração em `src/`, `tests/` ou `web/`.** Serve exclusivamente de base para a primeira Architecture Review da Wave 6 — não a substitui, não decide arquitetura definitiva.

**Precondição:** Wave 5 — Enterprise Advisors oficialmente encerrada (D-132) — Epic Ledger final: 8 de 8 Advisors implementados, testados, governados e aprovados (Delivery, Risk, Document, Governance, Portfolio, PMO, Executive, Strategy); quatro padrões Classe B consolidados; infraestrutura compartilhada preservada durante toda a Wave; nenhuma pendência técnica ou arquitetural aberta (`WAVE-5-COMPLETION-REVIEW.md`).

**Fundamentação:** este documento é fundamentado exclusivamente na arquitetura atualmente existente, nos oito Advisors já implementados, nas decisões permanentes registradas no Decision Log, e no código real da plataforma — nunca no `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` original (que descrevia uma "Executive Intelligence" conceitual pré-D-071, antes da própria Wave 5 existir como Wave separada). Onde esse Blueprint antigo diverge da arquitetura real hoje em produção, a arquitetura real prevalece sem exceção, e a divergência é nomeada explicitamente (§2.5).

---

## 1. Executive Summary

A Wave 5 entregou oito Enterprise Advisors funcionais e isolados — cada um responde, com evidência real e citável, a uma pergunta dentro de uma fronteira de domínio estreita e bem definida (execução de um Project, risco, composição de portfólio, staleness organizacional, decisão executiva, alinhamento estratégico, conformidade documental, governança institucional). Isso já é inteligência real, não um placeholder: cada Advisor cita `AnalysisRecord`s ou `Chunk`s reais, nunca inventa fatos, e `RecommendationEngine.no_evidence()` garante que nenhum deles sintetiza sobre o vazio.

**A lacuna que permanece após a Wave 5 é estrutural, não de qualidade**: `AdvisorFramework.run()` executa **exatamente um Advisor por chamada** (`src/services/advisor_framework/framework.py`, docstring: *"never a workflow engine, never autonomous routing between Advisors, never delegation from one Advisor to another"*) — uma garantia arquitetural deliberada, reafirmada em toda a AR-8 e nunca relaxada em nenhum dos oito ciclos institucionais da Wave 5. Isso significa que, hoje, **nenhum componente da plataforma consegue responder a uma pergunta que exija mais de um Advisor na mesma síntese** — por exemplo, "a execução dos meus projetos continua alinhada com a estratégia declarada E existe algum risco não mitigado que ameace essa estratégia?" exige o Strategy Advisor e o Risk Advisor simultaneamente, correlacionados, nunca dois relatórios isolados que o usuário precisa reconciliar manualmente.

**Por que os oito Advisors, isoladamente, ainda não representam inteligência executiva:** cada um responde com autoridade sobre seu próprio domínio, mas nenhum deles enxerga o outro, nenhum resolve conflito entre o que dois Advisors afirmam sobre a mesma organização, nenhum prioriza entre achados de domínios diferentes, e nenhum constrói uma narrativa executiva única a partir de múltiplas fontes de evidência independentes. Um executivo que precisa de uma visão consolidada hoje precisa perguntar a cada Advisor separadamente e fazer essa síntese na própria cabeça — exatamente o trabalho que a Wave 6 existe para absorver, sem nunca decidir por ele (Princípio 1, `STRATECH-Product-Constitution.html`: "não substitui o julgamento do PM/PMO... não decide, não prioriza").

A Wave 6 não constrói um nono Advisor. Ela constrói a camada que consome os oito Advisors já existentes como capacidades primárias, e só existe porque a Wave 5 já entregou uma base estável, testada e arquiteturalmente homogênea sobre a qual construir.

---

## 2. Estado Atual da Plataforma

Inventário fundamentado em leitura direta de código (`src/`), não em nenhum documento conceitual anterior.

### 2.1 Enterprise Domain (Wave 2)

Modelo relacional real (`src/database/models.py`): `Organization`, `User`/`Role`/`Permission`/`RolePermission`/`UserRole` (RBAC), `Portfolio` → `Program` → `Project` (com `UserProjectMembership`), `ApiKey`, `UserSession`, `Invitation`, `AuditLog`. Acesso exclusivamente via `DomainService` (`src/services/domain_service.py`) — `list_portfolios`/`list_programs`/`list_projects`/`get_*`/`create_*`, sempre organization-scoped, nunca uma segunda via de acesso.

**Entrega hoje:** a estrutura organizacional oficial (quem existe, quem pertence a quem, quem declarou qual objetivo) — usada por todo Advisor Classe B para resolver escopo, e pelo Strategy Advisor como fonte primária de estratégia declarada (`Portfolio.strategic_objective`/`Program.objective`/`Project.objective`).

### 2.2 Knowledge Platform (Wave 3)

`Document`/`DocumentVersion`/`Chunk` (RAG) e `MemoryRecord` (Enterprise Memory, Wave 3 Fase 2). Componentes: `EmbeddingProvider` (Protocol + `MockEmbeddingProvider`), `VectorRepository` (Protocol + `PgVectorRepository`), `KnowledgeRepository.index()`/`.search()`, `RagPipeline.retrieve(organization_id, query, top_k) -> RagContext`, `DocumentIngestionService`, `EnterpriseMemoryService.classify()`/`.list_by_category()`.

**Entrega hoje:** busca semântica sobre documentos institucionais indexados (consumida hoje pelo Document/Governance Advisor via `AIContextEngine.normalize_rag_evidence()`, e supletivamente pelo Risk Advisor via `gather_rag_context()`) e classificação de memória organizacional em 5 categorias (`DOCUMENTAL`/`OPERACIONAL`/`DECISOES`/`APRENDIZADOS`/`ORGANIZACIONAL`).

**Achado grounded, não hipótese:** `EnterpriseMemoryService` está implementado e testado desde a Wave 3 Fase 2, mas **nenhum dos oito Advisors o consome hoje** (confirmado por busca em `src/agents/*_advisor/`, zero ocorrência de `MemoryRecord`/`EnterpriseMemoryService`) — o próprio docstring do serviço já registrava a intenção de "ser consumido por um futuro Advisor via o Advisor Framework". É uma capacidade real, construída, íntegra, e sem consumidor até hoje — relevante para §8/§9, nunca decidido aqui. Distinto e sem nenhuma sobreposição com `web/lib/executive-memory/` (frontend-only, stateless, consumido diretamente pela UI de Workspace/Dashboard, nunca pelo backend).

### 2.3 Enterprise Operations (Wave 4)

`EventRecord`/`DeadLetterEvent`/`WorkflowExecution`. `EventPublisher`/`InProcessEventPublisher` → `EventDispatcher.dispatch()` (`src/services/events/dispatcher.py`) — pub/sub em processo, tabela de despacho fixa por `event_type`, retry síncrono (até 3 tentativas) com dead-letter em falha. `WorkflowRuntime.run(workflow_name, steps, triggering_event)` (`src/workflows/runtime.py`) — executor mínimo de passos, **sempre disparado por um evento já publicado**, nunca por uma pergunta de usuário; dono exclusivo do ciclo de vida `running`/`completed`/`failed` (`ExecutionTracker`). Único workflow real registrado hoje: `document_indexed_workflow.py`. `src/workflows/pmo_workflow.py` é **Historical Superseded Architecture** (D-074) — preservado por rastreabilidade, nunca importado, nunca base para código novo.

**Fato de código crítico para a Wave 6 (docstring literal de `runtime.py`):** *"Never substitutes `AdvisorFramework.run()` — a workflow step is a pure function, never business logic, never Advisor intelligence."* O Workflow Runtime **não é** um mecanismo de invocação de Advisor e nunca foi desenhado para orquestrar uma pergunta de usuário através de múltiplos Advisors — ele reage a eventos já publicados (ex.: `document.indexed`), não a perguntas.

### 2.4 Enterprise Advisors (Wave 5)

`src/services/ai_foundation/` — `AIContextEngine.gather(organization_id, project_name, kind)`, `RecommendationEngine.build(answer, cited_ids, evidence)`/`.no_evidence()`, `ExplanationEngine.explain()` (envelope de `rationale` padrão, ADR-V2-007: "síntese informativa... não é uma decisão automática"), `render_analyst_prompt()` (preâmbulo institucional compartilhado + template do Advisor), `ObservabilityRecorder`, `AIFoundationAudit`.

`src/services/advisor_framework/framework.py` — `AdvisorFramework.gather_context()`/`.gather_rag_context()`/`.normalize_rag_evidence()`/`.render_prompt()`/`.call_llm()`/`.run(advisor, session, question, evidence, rag_context=None, no_evidence_answer=None) -> Explanation`. `run()` executa exatamente um `AdvisorContract` por chamada.

Oito Advisors reais em `src/agents/`, cada um com `agent.py` (implementa `AdvisorContract`) e, para os quatro Classe B, `evidence_assembler.py` dedicado:

| Advisor | Classe | Rota | Composição de evidência |
|---|---|---|---|
| Delivery | A | `POST /delivery-advisor/ask` | `gather_context(kind="status")`, uma chamada |
| Risk | A | `POST /risk-advisor/ask` | `gather_context(kind="risk")` + RAG supletivo (`gather_rag_context()`) |
| Document | D | `POST /document-advisor/ask` | RAG é a fonte primária (`normalize_rag_evidence()`) |
| Governance | D | `POST /governance-advisor/ask` | RAG é a fonte primária, mesma forma do Document Advisor |
| Portfolio | B | `POST /portfolio-advisor/ask` | `PortfolioEvidenceAssembler` — um item por Project |
| PMO | B | `POST /pmo-advisor/ask` | `PMOEvidenceAssembler` — staleness organizacional |
| Executive | B | `POST /executive-advisor/ask` | `ExecutiveEvidenceAssembler` — `kind="status"` + `kind="risk"` por Project |
| Strategy | B | `POST /strategy-advisor/ask` | `StrategyEvidenceAssembler` — estratégia declarada + execução, 3 níveis |

**Entrega hoje:** oito respostas isoladas, cada uma fundamentada, citável, auditada — mas nunca correlacionadas entre si por nenhum componente da plataforma.

### 2.5 Divergência registrada com o Blueprint conceitual antigo (nunca usado como fonte de verdade)

`DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` nomeava um espaço conceitual de "Executive Intelligence" e "8 Enterprise Advisors" ainda dentro da Wave 3, antes de D-071 separar formalmente Wave 5 (Enterprise Advisors) e Wave 6 (Executive Intelligence) em duas Waves distintas e sequenciais. Este Kickoff não herda nenhuma decisão de composição, arquitetura ou nomenclatura desse documento — apenas o fato, já superado, de que a necessidade de uma camada de síntese multi-Advisor foi identificada desde cedo. Toda decisão de arquitetura da Wave 6 parte exclusivamente do estado real descrito em §2.1-§2.4.

---

## 3. O que é Executive Intelligence

**Definição institucional (esta missão):** Executive Intelligence é a camada que **consome as respostas já produzidas por um ou mais Enterprise Advisors** e as transforma em uma síntese executiva única — nunca uma nova fonte de evidência primária, nunca um nono Advisor, nunca uma reimplementação do que os oito já fazem.

**O que diferencia um Advisor de Executive Intelligence:**
- Um Advisor responde **dentro de** uma fronteira de domínio fixa (um `kind`, uma composição fixa de `kind`s, ou RAG), sempre via exatamente uma chamada a `AdvisorFramework.run()`.
- Executive Intelligence responde **através de** fronteiras de domínio — a pergunta do usuário pode exigir Strategy Advisor + Risk Advisor + Executive Advisor na mesma resposta, e a camada precisa decidir quais, executá-los, e reconciliar o que cada um afirma.
- Um Advisor nunca sabe que outro Advisor existe (confirmado em todos os oito `agent.py` — nenhum importa ou referencia outro Advisor). Executive Intelligence é, por definição, o primeiro componente da plataforma cuja responsabilidade central é justamente essa consciência multi-Advisor.

**Quais decisões passam a ser possíveis:** um executivo poderá perguntar algo que hoje exige perguntar a três Advisors separadamente e reconciliar manualmente — e receber uma resposta única, fundamentada nas evidências de todos os Advisors relevantes, com qualquer conflito entre eles tornado explícito (nunca escondido, nunca resolvido silenciosamente por um algoritmo).

**O que muda para o usuário:** a pergunta deixa de precisar nomear o Advisor certo — hoje o usuário escolhe `/portfolio-advisor` ou `/strategy-advisor` explicitamente; com Executive Intelligence, a pergunta é feita uma vez, e a camada decide (mecanismo não definido nesta missão, §8) quais Advisors ela precisa consultar para respondê-la com integridade.

---

## 4. Capacidades Esperadas

Identificação conceitual, sem decisão de implementação — cada capacidade abaixo é um comportamento que a Wave 6 precisa cobrir, não um componente já nomeado.

- **Executive Briefing** — uma síntese periódica ou sob demanda do estado da organização, compondo achados de múltiplos Advisors (ex.: status de execução + riscos abertos + alinhamento estratégico) em uma única leitura executiva, nunca oito respostas separadas.
- **Cross-Advisor Correlation** — reconhecer quando dois ou mais Advisors falam sobre a mesma unidade organizacional (o mesmo Project, o mesmo Portfolio) e apresentar essa relação explicitamente, nunca inferir uma conexão que nenhuma evidência sustenta.
- **Conflict Detection** — identificar quando dois Advisors produzem afirmações que parecem divergir (ex.: Strategy Advisor afirma alinhamento, Risk Advisor identifica um risco crítico não mitigado que ameaça esse mesmo objetivo) e expor o conflito ao usuário, nunca resolvê-lo silenciosamente nem decidir qual Advisor "está certo" — mesmo limite institucional já reafirmado pelo Strategy Advisor (nunca decide qual nível prevalece, AR-15 §3).
- **Recommendation Prioritization** — quando múltiplos Advisors produzem achados relevantes, apresentá-los de forma que o executivo entenda o que é mais urgente — nunca um ranking numérico ou score automático (mesmo limite já permanente em todo Advisor da Wave 5: nenhum ranking determinístico calculado em código).
- **Executive Narrative** — a capacidade de compor prosa coerente a partir de múltiplas respostas estruturadas de Advisors distintos, sem perder a rastreabilidade de qual afirmação veio de qual Advisor e de qual evidência.
- **Decision Support** — apresentar a informação consolidada de forma que apoie uma decisão humana — nunca tomar a decisão, nunca recomendar uma ação específica como se fosse a única correta (Princípio 1 da Product Constitution, permanente e nunca revisitado por nenhuma Wave até aqui).
- **Organizational Intelligence** — visão que atravessa múltiplas unidades organizacionais (vários Portfolios, vários Programs) simultaneamente, algo que hoje só o Strategy Advisor e o Executive Advisor tocam parcialmente, cada um dentro de sua própria fronteira Classe B.

Nenhuma dessas sete capacidades tem, nesta missão, um componente de código associado, uma assinatura de método, ou uma decisão de onde ela residiria na arquitetura — isso é trabalho do primeiro Domain Blueprint da Wave 6.

---

## 5. Fronteiras Arquiteturais

```
Advisor (8 existentes, Wave 5)
  │  responde dentro de UMA fronteira de domínio fixa,
  │  via exatamente uma chamada a AdvisorFramework.run()
  ▼
Executive Intelligence (Wave 6 — não existe ainda)
  │  consome respostas de múltiplos Advisors,
  │  correlaciona, detecta conflito, sintetiza narrativa executiva
  ▼
Workflow Runtime (Wave 4 — existe, mas é orientado a evento, não a pergunta)
  │  NUNCA invocado por uma pergunta de usuário — só reage a
  │  eventos já publicados (ex.: document.indexed)
  ▼
Enterprise Domain (Wave 2 — existe)
  │  persiste Organization/Portfolio/Program/Project/User,
  │  única fonte de verdade estrutural
```

**Quem interpreta?** Hoje, cada Advisor interpreta exclusivamente sua própria evidência (nunca a Foundation, nunca o Framework — confirmado em todos os oito `agent.py`, o julgamento semântico é sempre do LLM dentro do Advisor). Executive Intelligence, quando existir, interpretará a **relação entre** interpretações já produzidas pelos Advisors — nunca reinterpretará a evidência primária diretamente (isso seria duplicar o trabalho de um Advisor já existente, violando reuso).

**Quem consolida?** Hoje, nada consolida entre Advisors — cada `AdvisorFramework.run()` produz exatamente uma `Explanation` isolada. Este é precisamente o papel que falta e que a Wave 6 investigará.

**Quem executa?** `AdvisorFramework.run()` continua sendo o único ponto de execução de um Advisor individual — preservado integralmente, nunca reescrito para orquestrar múltiplos Advisors internamente (isso violaria a garantia "exatamente um Advisor por chamada" que toda a Wave 5 respeitou).

**Quem persiste?** `Enterprise Domain`/`Knowledge Platform` continuam sendo os únicos donos de dados persistentes. Nenhuma capacidade da Wave 6 nomeada em §4 exige, por si só, um novo dado persistido — mas se a Wave 6 vier a precisar (ex.: cache de correlação, histórico de briefings), isso é uma questão em aberto (§8), nunca decidida aqui.

**Quem apenas apresenta?** A camada de apresentação (`web/`) permanece fora do escopo arquitetural desta missão — nenhuma alteração em `web/` é autorizada aqui, e nenhuma decisão de UI é tomada.

---

## 6. Fluxo Conceitual

```
Pergunta do usuário
        │
        ▼
Executive Intelligence               (não decidido: onde este componente
        │                             reside, se é um novo serviço, se
        │                             reaproveita AdvisorFramework de
        │                             alguma forma aditiva — §8)
        ▼
seleção dos Advisors necessários      (não decidido: automática via
        │                             classificação da pergunta, ou
        │                             explícita via parâmetro do
        │                             chamador — §8)
        ▼
execução                              (cada Advisor selecionado ainda
        │                             passa por exatamente uma chamada
        │                             a AdvisorFramework.run(), preservado
        │                             integralmente — não decidido: as
        │                             chamadas são paralelas ou
        │                             sequenciais — §8)
        ▼
correlação                            (não decidido: como duas Explanations
        │                             de Advisors distintos são comparadas
        │                             ou relacionadas — §8)
        ▼
síntese                               (não decidido: quem compõe a
        │                             narrativa final — um novo componente,
        │                             um novo LLM call, ou composição
        │                             estrutural sem LLM — §8)
        ▼
explicação                            (ExplanationEngine já existe e já
        │                             produz um rationale padrão por
        │                             Explanation individual — não
        │                             decidido: como um rationale
        │                             multi-Advisor é composto — §8)
        ▼
resposta executiva
```

Nenhuma etapa deste fluxo tem, nesta missão, uma assinatura de método, um nome de classe, ou uma decisão de qual componente já existente ela reaproveita — isso é trabalho do primeiro Domain Blueprint da Wave 6.

---

## 7. Papel dos Oito Advisors

| Advisor | Qual informação produz | Qual informação consome | Contribuição para Executive Intelligence |
|---|---|---|---|
| **Delivery** | Estado de execução (`health_status`/`key_findings`/`recommendations`) de um Project específico, com leitura de tendência temporal pelo LLM sobre o histórico completo de `kind="status"` | `AnalysisRecord`/`kind="status"`, um Project por chamada | Sinal de execução no nível mais granular — insumo para qualquer síntese que precise descer ao Project individual |
| **Risk** | Síntese conversacional sobre riscos já identificados de um Project, com contexto RAG supletivo | `AnalysisRecord`/`kind="risk"` + RAG supletivo | Sinal de risco no nível de Project — insumo central para Conflict Detection quando cruzado com Strategy/Executive |
| **Document** | Resposta fundamentada em chunks de documentos institucionais indexados | `Chunk` via RAG (fonte primária) | Contexto documental — pode fundamentar uma Executive Narrative com referência a política/documento oficial |
| **Governance** | Classificação de conformidade (uma de 5 categorias oficiais) fundamentada em hierarquia documental | `Chunk` via RAG (fonte primária) | Sinal de conformidade institucional — relevante quando uma síntese executiva toca decisões que podem violar governança |
| **Portfolio** | Composição de saúde de todos os Projects de um Portfolio, sem ranking | `AnalysisRecord`/`kind="status"`, um item por Project via `PortfolioEvidenceAssembler` | Visão agregada de execução por Portfolio — insumo natural para Executive Briefing e Organizational Intelligence |
| **PMO** | Staleness organizacional — quais Projects não reportam status há quanto tempo | `AnalysisRecord`/`kind="status"`, histórico completo via `PMOEvidenceAssembler` | Sinal de saúde de processo — relevante para Decision Support quando a ausência de dado é, ela mesma, um achado |
| **Executive** | O que exige atenção da liderança agora, combinando status e risco por Project | `AnalysisRecord`/`kind="status"` + `kind="risk"` via `ExecutiveEvidenceAssembler` | Já é a resposta mais próxima de uma síntese executiva hoje — mas ainda dentro de uma única chamada, nunca correlacionada com Strategy/Governance |
| **Strategy** | Se a execução permanece alinhada com a estratégia declarada, em três níveis independentes (Portfolio/Program/Project) | Objetivo declarado (`Portfolio.strategic_objective`/`Program.objective`/`Project.objective`) + `AnalysisRecord`/`kind="status"`/`kind="risk"` via `StrategyEvidenceAssembler` | O único Advisor que já compara dois tipos de fonte — mais próximo estruturalmente do que Executive Intelligence precisará fazer entre Advisors inteiros, não apenas entre dois `kind`s |

---

## 8. Questões Arquiteturais

Levantadas, não respondidas — decisões que precisarão ser resolvidas antes do primeiro Domain Blueprint da Wave 6:

1. **Existe um Executive Orchestrator?** Se sim, é um componente novo, ou uma extensão aditiva de algo já existente? `AdvisorFramework.run()` foi desenhado explicitamente para nunca fazer isso (§2.4) — um orquestrador precisaria residir estruturalmente acima dele, nunca dentro.
2. **Quem decide quais Advisors executar para uma pergunta dada?** Classificação automática (e, se sim, por qual mecanismo — outro LLM call, regras, embedding de intenção?) ou seleção explícita pelo chamador (ex.: o próprio frontend nomeia os Advisors relevantes)?
3. **As execuções dos Advisors selecionados serão paralelas ou sequenciais?** Cada uma já é uma chamada isolada e independente a `AdvisorFramework.run()` — não há dependência estrutural conhecida entre elas hoje, mas isso não foi validado para nenhum cenário real multi-Advisor.
4. **Existe cache?** Nenhum Advisor da Wave 5 usa cache hoje (confirmado por leitura de código — toda chamada a `gather_context()`/`gather_rag_context()` é uma consulta real). Uma camada que potencialmente executa vários Advisors por pergunta muda o perfil de custo/latência de forma que a Wave 5 nunca precisou considerar.
5. **Como explicar conflitos?** `ExplanationEngine.explain()` produz hoje um `rationale` de uma única `Recommendation`. Não existe, em nenhum componente atual, um mecanismo para expressar "o Advisor X afirma A, o Advisor Y observa B, que aparenta divergir".
6. **Como citar múltiplos Advisors na mesma resposta?** Cada Advisor tem seu próprio modelo de citação (`CitedProject`, `ExecutiveCitedEvidence`, `StrategyCitedEvidence`, etc.) — nenhum unificado. Uma resposta executiva que cita dois Advisors precisa de um modelo de citação que hoje não existe.
7. **Como medir confiança?** Nenhum Advisor da Wave 5 expõe um score de confiança — apenas evidência citada ou ausência dela (binário, via `no_evidence()`). Uma síntese multi-Advisor pode precisar comunicar graus diferentes de robustez de evidência entre os Advisors que consultou.
8. **Como evitar duplicação?** Se dois Advisors selecionados citam o mesmo `AnalysisRecord`/`Chunk` subjacente (ex.: Executive e Strategy ambos leem `kind="status"` do mesmo Project), a resposta final precisa reconhecer isso, nunca apresentar como se fossem dois fatos independentes.
9. **`EnterpriseMemoryService` (§2.2) participa da Wave 6?** É uma capacidade real, construída, testada, sem consumidor até hoje — a Wave 6 é o primeiro candidato natural, mas isso não está decidido aqui.
10. **O Workflow Runtime tem algum papel na Wave 6, mesmo que indireto?** Ele é orientado a evento, não a pergunta (§2.3/§5) — mas se Executive Intelligence vier a precisar de um "Executive Briefing periódico" (§4), isso poderia ser modelado como algo disparado por um evento agendado, não por uma pergunta síncrona. Não decidido.

---

## 9. Roadmap da Wave 6 (proposto, não decidido)

Decomposição preliminar em Epics — nenhum destes é um Domain Blueprint; cada um precisará do próprio ciclo institucional completo antes de qualquer código.

### Epic W6-1 — Executive Orchestration Foundation

- **Objetivo:** resolver as questões arquiteturais §8.1-§8.4 (existência e forma do orquestrador, seleção de Advisors, paralelismo, cache) e estabelecer o primeiro mecanismo real de invocar mais de um Advisor para a mesma pergunta.
- **Problema:** hoje não existe nenhum caminho de código que execute dois Advisors para a mesma pergunta do usuário.
- **Dependências:** os 8 Advisors da Wave 5 (concluídos), `AdvisorFramework` (preservado, nunca alterado internamente).
- **Consumidores:** todos os Epics seguintes desta Wave dependem deste.
- **Resultado esperado:** um mecanismo comprovado (não necessariamente o final) de invocar N Advisors para uma pergunta e obter N `Explanation`s correlacionáveis.

### Epic W6-2 — Cross-Advisor Correlation & Conflict Detection

- **Objetivo:** resolver §8.5/§8.6/§8.8 — identificar quando Advisors falam da mesma unidade organizacional, expor conflitos, evitar duplicação de citação.
- **Problema:** hoje nenhum componente compara duas `Explanation`s entre si.
- **Dependências:** Epic W6-1.
- **Consumidores:** Executive Narrative (W6-3), Decision Support (W6-4).
- **Resultado esperado:** capacidade de, dadas N `Explanation`s, identificar sobreposição de unidade organizacional e sinalizar divergência textual entre Advisors, sem decidir qual está certo.

### Epic W6-3 — Executive Narrative & Citation Model

- **Objetivo:** resolver §8.6/§8.7 — um modelo de citação que unifica referências a múltiplos Advisors, e a composição de prosa executiva coerente a partir de múltiplas `Explanation`s.
- **Problema:** hoje cada Advisor tem seu próprio modelo de citação isolado; nenhum consegue expressar uma resposta que cita dois Advisors.
- **Dependências:** Epic W6-1, Epic W6-2.
- **Consumidores:** toda superfície de usuário que consumirá Executive Intelligence.
- **Resultado esperado:** uma resposta executiva única, fundamentada, rastreável até os Advisors e evidências de origem.

### Epic W6-4 — Executive Briefing & Organizational Intelligence

- **Objetivo:** as capacidades §4 mais amplas — visão periódica/sob demanda multi-unidade, endereçando também §8.9 (papel do `EnterpriseMemoryService`) e §8.10 (papel do Workflow Runtime em um briefing periódico).
- **Problema:** hoje não existe nenhuma síntese que atravesse múltiplos Portfolios/Programs simultaneamente combinando múltiplos Advisors.
- **Dependências:** Epic W6-1, Epic W6-2, Epic W6-3.
- **Consumidores:** liderança executiva, via superfície ainda não decidida (`web/`, fora de escopo arquitetural desta missão).
- **Resultado esperado:** um Executive Briefing real, gerado sob demanda ou periodicamente, citando evidência de múltiplos Advisors e domínios organizacionais.

A ordem entre W6-2/W6-3/W6-4 e o escopo exato de cada um permanecem sujeitos à primeira Architecture Review da Wave 6 — este roadmap é um ponto de partida, não uma sequência aprovada.

---

## 10. Riscos Arquiteturais

Riscos reais, fundamentados em fatos de código já confirmados — nenhuma especulação.

| Risco | Evidência (código real) | Por que é real |
|---|---|---|
| Violação da garantia "um Advisor por chamada" se o orquestrador for implementado dentro de `AdvisorFramework` | `framework.py`, docstring de `run()`: *"never a workflow engine, never autonomous routing"* | Esta garantia foi respeitada em todos os 8 ciclos institucionais da Wave 5 sem exceção; qualquer solução que a quebre exigiria reabrir uma decisão arquitetural já consolidada oito vezes |
| Confundir Workflow Runtime com um mecanismo de invocação de Advisor | `runtime.py`, docstring: *"Never substitutes AdvisorFramework.run()"* — orientado a evento, não a pergunta | Já nomeado explicitamente como risco no `WAVE-5-ARCHITECTURE-KICKOFF.md` §2.3 antes mesmo da Wave 5 começar; permanece válido, ainda não materializado |
| Modelo de citação fragmentado (§8.6) tornar-se um obstáculo de fato, não apenas teórico | 8 modelos de citação distintos e isolados já em produção (`CitedProject`, `ExecutiveCitedEvidence`, `StrategyCitedEvidence`, etc.), nenhum reutilizável entre si por design | Cada um foi deliberadamente isolado durante a Wave 5 para nunca alterar o contrato de um Advisor existente ao introduzir outro — a mesma disciplina, aplicada ingenuamente à Wave 6, produziria um nono modelo de citação isolado em vez de resolver o problema real |
| `EnterpriseMemoryService` permanecer capacidade morta indefinidamente | Implementado desde a Wave 3 Fase 2, zero consumidor confirmado por busca em `src/agents/` | Risco de dívida arquitetural silenciosa — não é um risco de a Wave 6 usá-lo (isso ainda não foi decidido), é o risco de a pergunta nunca ser feita explicitamente e a capacidade permanecer não avaliada indefinidamente |
| Volume de chamadas ao LLM crescer de forma não avaliada | Cada Advisor individual já executa 1-2 chamadas a `gather_context()`/`gather_rag_context()` mais 1 chamada ao LLM; uma pergunta que selecione N Advisors multiplica esse custo por N antes mesmo de somar o custo de síntese | Nenhum dos 8 Advisors da Wave 5 precisou considerar esse cenário — é estruturalmente novo para a Wave 6 |

Nenhum risco listado é bloqueante para a abertura do ciclo institucional da Wave 6 — todos são endereçáveis na Architecture Review e nos Domain Blueprints subsequentes.

---

## 11. Critérios de Encerramento

A Wave 6 poderá ser considerada concluída quando, objetivamente:

1. Todas as questões arquiteturais §8 tiverem sido respondidas por decisão explícita do Founder (não inferidas, não decididas unilateralmente por este Tech Lead).
2. Cada Epic do roadmap §9 (ou sua versão final decidida na Architecture Review) tiver percorrido o ciclo institucional completo já usado em toda a Wave 5 — Domain Blueprint → Architecture Review → Technical Design → Implementação → Encerramento — com aprovação explícita do Founder em cada etapa.
3. Pelo menos uma capacidade de §4 estiver implementada, testada e funcional em produção, citando evidência real de dois ou mais Advisors distintos na mesma resposta.
4. `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline/contrato `Evidence`/todos os oito Advisors da Wave 5 permanecerem preservados sem alteração destrutiva (confirmado por `git diff --stat` a cada Epic, mesma disciplina de toda a Wave 5) — extensões aditivas são esperadas e aceitáveis, quebras não são.
5. Nenhuma pendência técnica ou arquitetural permanecer aberta, com o mesmo padrão de rigor aplicado ao `WAVE-5-COMPLETION-REVIEW.md`.
6. Um Wave 6 Completion Review for produzido e aprovado pelo Founder, nos mesmos termos institucionais já estabelecidos para a Wave 5.

---

## Recomendação

**GO para a primeira Architecture Review da Wave 6**, fundamentada neste Kickoff.

Este documento não decide nenhuma arquitetura definitiva — levanta o estado real da plataforma, define institucionalmente o que é Executive Intelligence, nomeia as capacidades esperadas sem implementá-las, expõe as fronteiras arquiteturais e o fluxo conceitual sem decidir componentes, propõe um roadmap preliminar sujeito a revisão, e levanta dez questões arquiteturais reais que precisam de decisão explícita do Founder antes do primeiro Domain Blueprint. Nenhuma inconsistência arquitetural relevante entre os oito Advisors ou qualquer componente existente foi encontrada durante esta análise — a única divergência identificada (§2.5, o Blueprint conceitual pré-D-071) já era esperada e não constitui uma inconsistência de código, apenas um documento histórico corretamente superado. Nenhuma implementação da Wave 6 deverá começar antes da aprovação explícita do Founder sobre este Kickoff e a produção da Architecture Review correspondente.
