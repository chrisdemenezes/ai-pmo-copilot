# AR-8 — Wave 5 Enterprise Advisor Model: Architecture Review

**Autorização:** "Founder Authorization — Wave 5 Architecture Review" (2026-07-30), em resposta ao achado do `WAVE-5-ARCHITECTURE-KICKOFF.md` (D-084) de que `AIContextEngine.gather(project_name, kind)` não atende uniformemente aos 7 Enterprise Advisors restantes.

**Objetivo:** responder, de forma permanente e exclusivamente com base no código e na arquitetura existentes, qual é o modelo arquitetural definitivo dos Enterprise Advisors — válido até a conclusão da STRATECH Enterprise v1.0.

**Restrições desta missão:** nenhum código, nenhum Domain Blueprint, nenhum Technical Design, nenhum Proof of Concept. Exclusivamente arquitetural.

**Método:** toda conclusão abaixo é rastreável a um arquivo e uma linha de código real — `src/services/advisor_framework/`, `src/services/ai_foundation/`, `src/services/knowledge_platform/`, `src/agents/risk_advisor/agent.py`, `src/api/routes/intelligence.py::ask_risk_advisor`, `src/database/models.py`. Nenhuma conclusão nasce de hipótese.

---

## 1. A questão arquitetural principal — Opção A vs. Opção B

### 1.1 O que o código real já faz hoje (não uma escolha de estilo — uma restrição estrutural já em produção)

`src/api/routes/intelligence.py::ask_risk_advisor` (linhas 513-536):

```python
session = SessionContext(...)
framework = AdvisorFramework(repository, prompts, provider, rag_pipeline)

evidence = framework.gather_context(session.organization_id, session.project_name, kind="risk")
rag_context = framework.gather_rag_context(session.organization_id, request.question, top_k=5)

agent = RiskAdvisorAgent(framework)
explanation = framework.run(agent, session, request.question, evidence, rag_context)
```

`src/services/advisor_framework/framework.py::AdvisorFramework.run()`:

```python
def run(self, advisor, session, question, evidence, rag_context=None, no_evidence_answer=None):
    AIFoundationAudit.record_question(self._repository, session, advisor.name, question)
    if not evidence:
        return ExplanationEngine.explain(RecommendationEngine.no_evidence(no_evidence_answer))
    model_output = advisor.advise(session, question, evidence, rag_context)
    ...
```

**Fato estrutural, não estilístico:** `run()` precisa inspecionar `evidence` **antes** de decidir se chama `advisor.advise()` — o portão anti-alucinação ("sem evidência, nunca chama o LLM") só existe porque a evidência já foi coletada e entregue a `run()` de fora para dentro. `RiskAdvisorAgent.advise()` (`src/agents/risk_advisor/agent.py`) nunca chama `gather_context`/`gather_rag_context` — apenas recebe `evidence`/`rag_context` como parâmetros e os transforma em `risks_json`/`additional_context_json` para o prompt.

Embora `RiskAdvisorAgent` **possua** uma referência ao `framework` (usada para `render_prompt`/`call_llm`), o desenho já em produção nunca usa essa referência para autocoleta de evidência dentro de `advise()`.

### 1.2 Por que a Opção A (Advisor consome diretamente suas fontes) é estruturalmente incompatível com o portão já provado

Se cada Advisor coletasse sua própria evidência dentro de `advise()`, o portão "sem evidência, sem LLM" teria de ser duplicado dentro de cada um dos 7 Advisors (violando reuso — o mesmo tipo de duplicação que o Princípio 4 do Framework já proíbe), **ou** o Framework precisaria invocar o Advisor duas vezes (uma para coletar, outra para decidir) — um desenho estranho e nunca cogitado pelo código real. A Opção A exigiria desfazer uma garantia já em produção (D-046/D-068: "no_evidence() executa sem chamar o LLM").

### 1.3 Decisão

**Opção B — o Advisor recebe um contexto (evidência) previamente preparado por uma camada comum antes de ser invocado.** Isto não é uma preferência de estilo desta revisão — é a única opção compatível com o portão anti-alucinação já provado em produção desde a Fase 3/4 da Wave 3.

**Precisão adicional (achado desta revisão, não presente no Kickoff):** hoje, "quem prepara" esse contexto é a **rota** (`ask_risk_advisor`), não um componente reutilizável — cada nova rota de Advisor reimplementaria essa decisão do zero, com risco real de duplicação à medida que os 7 Advisors forem implementados. A seção 3 resolve isso nomeando essa responsabilidade explicitamente, sem inventar um componente novo além do que o Framework já expõe.

---

## 2. Responsabilidades definitivas (nenhuma ambígua)

| Responsabilidade | Componente responsável (real, hoje) | Papel na Wave 5 |
|---|---|---|
| Descobrir/decidir **quais** evidências buscar (o "quê") | Hoje: a rota, inline (`ask_risk_advisor`) | **Passa a ser responsabilidade do próprio Advisor** — uma função/método de "montagem de contexto" colocado junto ao Advisor (não um componente genérico novo), decidindo `kind`/escopo/quantidade de chamadas |
| Consultar repositórios (`AnalysisRecord`) | `AIContextEngine.gather()`, via `AdvisorFramework.gather_context()` | Inalterado — permanece o único ponto de acesso a `AnalysisRecord` |
| Consultar RAG | `RagPipeline`/`KnowledgeRepository`, via `AdvisorFramework.gather_rag_context()` | Inalterado — permanece o único ponto de acesso a conteúdo documental |
| Consultar eventos | Nenhum componente hoje | Ver §6 — não introduzido nesta Wave |
| Consultar memória (Enterprise Memory Model) | `EnterpriseMemoryService` existe, mas **não está exposta** por nenhum método de `AdvisorFramework` hoje (confirmado: zero `gather_memory` no código) | Adicionar um passthrough fino (`gather_memory`), **somente quando um Advisor real o exigir** — mesmo princípio "Grounded before Generalized" que já resolveu D-079/D-083 |
| Montar contexto (transformar evidência bruta em estrutura pronta para prompt, ex.: `risks_json`) | O próprio Advisor (`RiskAdvisorAgent.advise()`) | Inalterado — é interpretação de domínio, nunca generalizável sem o Framework passar a conhecer vocabulário de domínio |
| Construir prompt (compor preâmbulo institucional + template do Advisor) | `render_analyst_prompt`, via `AdvisorFramework.render_prompt()` | Inalterado — compartilhado, uniforme |
| Chamar LLM (com observabilidade) | `ObservabilityRecorder.record_call()`, via `AdvisorFramework.call_llm()` | Inalterado — compartilhado, uniforme |
| Interpretar resposta bruta do LLM (parsing do JSON de saída) | O próprio Advisor (`parse_structured_output`, domain-specific) | Inalterado |
| Validar forma genérica da resposta (`structured`/`answer`) | `AdvisorFramework.run()` (`AdvisorExecutionError`) | Inalterado — compartilhado |
| Normalizar em `Recommendation` (filtrar citações inventadas) | `RecommendationEngine.build()` | Inalterado — compartilhado |
| Envelopar com `rationale` | `ExplanationEngine.explain()` | Inalterado — compartilhado |
| Auditar a pergunta | `AIFoundationAudit.record_question()`, dentro de `run()` | Inalterado — compartilhado, incondicional |
| Aplicar o portão anti-alucinação (sem evidência → sem LLM) | `AdvisorFramework.run()` | Inalterado — a garantia estrutural que fundamenta toda esta revisão |
| Adaptação HTTP (montar `SessionContext`, invocar a montagem de contexto do Advisor, chamar `run()`) | A rota | Passa a ser **apenas** isso — a decisão de "o quê" buscar deixa de morar na rota (ver linha 1 desta tabela) |

---

## 3. Papel definitivo do `AIContextEngine`

**`AIContextEngine` é, e deve permanecer, um coletor de evidências — nunca um organizador de contexto.**

**Justificativa técnica:** `AIContextEngine.gather()` (`src/services/ai_foundation/context_engine.py`) faz exatamente uma coisa — resolve `AnalysisRecord`s reais por `organization_id`/escopo/`kind` e os empacota em `Evidence` opacos (`summary: dict`, deliberadamente não interpretado pela Foundation, per o próprio docstring do `Evidence`). A "organização" — transformar essa evidência bruta em uma narrativa pronta para prompt (`risks_json`, por exemplo) — já é feita pelo próprio Advisor (`RiskAdvisorAgent.advise()`), nunca pelo Engine.

Se o `AIContextEngine` passasse a "organizar contexto", ele precisaria conhecer o vocabulário de domínio de cada Advisor (o que é um "risco", o que é uma "composição de portfólio") — isso violaria diretamente o princípio já estabelecido (Blueprint do Framework, "o Framework nunca cresce para conhecer a lógica de negócio de um Advisor específico") e duplicaria o que `render_analyst_prompt` + `advise()` já fazem hoje, com sucesso, para o Risk Advisor.

**Extensão necessária, não substituição:** para atender Advisors com escopo diferente de "um projeto, um kind" (Portfolio, PMO, Executive — ver §4), a resolução correta **não é generalizar a assinatura de `gather()`** (isso a tornaria um organizador). A resolução correta é: o Advisor (na sua etapa de montagem de contexto, §2) chama `gather_context()` **múltiplas vezes** (uma por projeto do portfólio, por exemplo) e compõe as listas de `Evidence` resultantes — o Engine continua fazendo exatamente uma coisa, chamada repetidamente por quem sabe o motivo (o Advisor), nunca generalizado para saber "portfólio" ou "múltiplos projetos" por conta própria.

---

## 4. Classificação arquitetural dos 7 Enterprise Advisors (nascida do código, não de hipótese)

A classificação correta não nasce de um rótulo de negócio (o exemplo ilustrativo do Founder — "Project/Knowledge/Executive Intelligence" — é intuitivo, mas a linha real que separa arquitetura é **a natureza e a cardinalidade da fonte de evidência**, confirmada em código):

| Classe | Advisors | Fonte de evidência real | Como se encaixa em `AIContextEngine.gather()` (§3) |
|---|---|---|---|
| **A — Analysis-Record Intelligence (escopo único)** | Risk Advisor (referência), Delivery Advisor | `AnalysisRecord`, um projeto, um `kind` | Encaixe direto, uma única chamada — exatamente a forma já provada |
| **B — Analysis-Record Intelligence (agregada)** | PMO Advisor, Portfolio Advisor, Executive Advisor | `AnalysisRecord`, múltiplos projetos e/ou múltiplos `kind` | Múltiplas chamadas a `gather_context()`, compostas na etapa de montagem de contexto do próprio Advisor — **sem alterar o Engine** |
| **C — Declarative Intelligence (evidência pode ainda não existir)** | Strategy Advisor | `AnalysisRecord`/objetivos declarados, quando existirem no domínio | Mesmo mecanismo da Classe A; hoje, legitimamente cai em `no_evidence()` sempre — comportamento correto, não um bug |
| **D — Knowledge/Document Intelligence (RAG como evidência primária)** | Document Advisor, Governance Advisor | Conteúdo documental via `KnowledgeRepository`/`RagPipeline` — para o Governance Advisor, o corpus são os próprios documentos de governança (Decision Log, Technical Debt, Mission Control), ingeridos pelo mesmo `ingest()`/`index()` já existente | `RagContext` deixa de ser suplementar e passa a ser a evidência primária — ver achado §4.1 |

### 4.1 Achado que a Classe D exige (registrado, não resolvido aqui — é Technical Design)

O tipo `Evidence` (`src/services/ai_foundation/types.py`) já é genérico o suficiente para representar qualquer fato citável — `summary: dict` é "opaco à Foundation por design". Isso significa que a Classe D **não exige nenhuma abstração nova**: a etapa de montagem de contexto do Document/Governance Advisor pode envolver cada chunk retornado por `gather_rag_context()` em um `Evidence` (`kind="document_chunk"`, `summary={chunk_id, document_id, text}`), reaproveitando o mesmo portão anti-alucinação e o mesmo `RecommendationEngine.build()` sem nenhuma mudança de Framework.

**Risco residual nomeado (§7):** o campo `Evidence.source_analysis_id: int` e `Recommendation`/`RecommendationEngine.build(cited_ids: list[int])` estão nomeados em vocabulário de `AnalysisRecord` (`source_analysis_id`, `cited_analysis_ids`). `Chunk.id` (tabela `chunks`) também é `Integer`, portanto **tipo-compatível**, mas o nome do campo confunde um futuro leitor. Isso é uma questão de nomenclatura a resolver no Technical Design do primeiro Advisor da Classe D — não uma barreira arquitetural, não algo a decidir nesta revisão.

---

## 5. Relação entre Advisors e Knowledge Platform (RAG)

**Nem todos os Advisors usam RAG da mesma forma — dois papéis distintos, ambos já provados em código:**

- **RAG suplementar (opcional):** Classes A, B, C — exatamente o padrão já em produção no Risk Advisor (`rag_context: RagContext | None = None`, nunca a única base de uma afirmação). Um Advisor destas classes só ganha RAG se um caso de uso real exigir contexto documental além do `AnalysisRecord`.
- **RAG primário (evidência principal):** Classe D — Document e Governance Advisor. Aqui o RAG não é suplementar, é a fonte de `Evidence` em si (§4.1).

**Nenhum Advisor acessa `PgVectorRepository`/`EmbeddingProvider` diretamente** — sempre via `KnowledgeRepository`/`RagPipeline`, através de `AdvisorFramework.gather_rag_context()`, sem exceção. Esta regra (já estabelecida na Wave 3) permanece definitiva.

---

## 6. Relação entre Advisors e Workflow Runtime

**Confirmado: a separação é definitiva e permanece inalterada.**

`WorkflowRuntime` (Wave 4, `src/workflows/runtime.py`) executa uma sequência fixa de passos puros, nunca contendo regra de negócio, nunca inteligência — seu único propósito é orquestrar operações e registrar execução (`workflow_executions`). Um Advisor produz inteligência (evidência → LLM → recomendação), invocado sincronamente via `AdvisorFramework.run()`, nunca como um passo de workflow.

**Regra definitiva:** nenhum passo de `WorkflowRuntime` pode invocar `AdvisorFramework.run()` ou qualquer `AdvisorContract.advise()` — isso colapsaria a distinção "Workflow Runtime nunca executa inteligência" que o próprio Founder fixou como princípio central do Epic W4-4. Nenhum Advisor é registrado como handler de `EventDispatcher` (ver §7) nem invocado a partir de um workflow. As duas linhas de execução (requisição/resposta síncrona de Advisor vs. execução rastreada de Workflow) permanecem paralelas e nunca se cruzam.

---

## 7. Relação entre Advisors e Event Pipeline

**Os Advisors não consomem eventos diretamente — consomem apenas os dados que uma operação (produtora do evento) já persistiu.**

Justificativa: `AdvisorFramework.run()` é uma chamada síncrona de requisição/resposta, auditada e com portão anti-alucinação — um Advisor registrado como handler de `EventDispatcher` (Wave 4) precisaria operar de forma assíncrona/best-effort, com uma semântica de auditoria e retry completamente diferente (a mesma já usada por `EventDispatcher`/`WorkflowRuntime`, nunca desenhada para invocar um LLM). Misturar os dois modelos de execução duplicaria — ou pior, enfraqueceria — o portão anti-alucinação.

**O que já funciona sem exigir isso:** quando `KnowledgeRepository.index()` publica `document.indexed` (W4-3), o efeito real que interessa ao Document Advisor não é o evento em si — é a linha `Chunk` que `index()` já persistiu. O Document Advisor lê essa `Chunk` via `RagPipeline.retrieve()` (mesmo caminho de sempre), nunca subscrevendo o evento. **Nenhum Advisor se registra em `EventDispatcher` nesta Wave.**

---

## 8. Relação entre Advisors e Domain

**Confirmado, sem exceção, para os 7 Advisors:**

- Advisors nunca executam regras de negócio — `RiskAdvisorAgent.advise()` (e todo `AdvisorContract`) apenas lê `Evidence` já persistida e retorna um `dict` interpretado por `RecommendationEngine`; nenhuma escrita em nenhum repositório de domínio ocorre dentro de `advise()`.
- Advisors nunca alteram entidades — nenhum Advisor tem acesso de escrita a `Portfolio`/`Program`/`Project`/`Invitation`/etc.; o único efeito colateral de uma pergunta a um Advisor é a entrada em `AuditLog` via `AIFoundationAudit.record_question()` (auditoria, não mutação de domínio).
- Advisors apenas produzem inteligência — a saída de todo `AdvisorContract.advise()` é sempre `Explanation` (síntese informativa, "não é uma decisão automática", per o próprio `ExplanationEngine.RATIONALE_TEMPLATE`, ADR-V2-007).

Este princípio já está codificado e provado nos 8 "Limites de atuação" do `ENTERPRISE-ADVISOR-CATALOG.md` — esta revisão apenas confirma que o código real o sustenta estruturalmente, não apenas por convenção documental.

---

## 9. Modelo definitivo — Enterprise Advisor Architecture (permanente até a STRATECH Enterprise v1.0)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Rota HTTP (adaptador fino)                                          │
│  - constrói SessionContext                                          │
│  - invoca a etapa de montagem de contexto do Advisor                │
│  - chama AdvisorFramework.run(advisor, session, question, evidence, │
│    rag_context)                                                     │
└───────────────────────┬───────────────────────────────────────────────┘
                         │
┌────────────────────────▼──────────────────────────────────────────────┐
│ Montagem de Contexto (por Advisor — não um componente genérico novo)  │
│  - decide QUAIS chamadas fazer (kind, escopo, quantas vezes)           │
│  - chama AdvisorFramework.gather_context()/.gather_rag_context()      │
│    (uma ou várias vezes, conforme a Classe A/B/C/D, §4)                │
│  - nunca acessa AIContextEngine/RagPipeline/KnowledgeRepository        │
│    diretamente — sempre via os métodos finos do Framework             │
└───────────────────────┬───────────────────────────────────────────────┘
                         │  evidence: list[Evidence], rag_context
┌────────────────────────▼──────────────────────────────────────────────┐
│ AdvisorFramework.run() (compartilhado, invariante, 7/7 Advisors)       │
│  1. AIFoundationAudit.record_question()             -- incondicional  │
│  2. Portão anti-alucinação: sem evidência → no_evidence(), nunca LLM   │
│  3. advisor.advise(session, question, evidence, rag_context)          │
│  4. Validação genérica de forma (structured/answer)                   │
│  5. RecommendationEngine.build()  -- filtra citação inventada          │
│  6. ExplanationEngine.explain()   -- rationale padrão, ADR-V2-007      │
└───────────────────────┬───────────────────────────────────────────────┘
                         │  advisor.advise(...)
┌────────────────────────▼──────────────────────────────────────────────┐
│ Advisor (AdvisorContract.advise) — domínio, nunca infraestrutura       │
│  - transforma Evidence bruta em estrutura de prompt (ex.: risks_json)  │
│  - framework.render_prompt() + framework.call_llm()                   │
│  - interpreta a resposta bruta do LLM (parse_structured_output)       │
└─────────────────────────────────────────────────────────────────────────┘
```

**Nomenclatura oficial do modelo:** *Framework-Mediated Evidence Assembly* — o Advisor decide **o quê** buscar (Classe A/B/C/D), a Foundation decide **como** buscar (via métodos finos, invariantes), o Framework garante **quando** o LLM pode ser chamado (o portão), e o Advisor interpreta **o que significa** (domínio). Nenhuma dessas quatro responsabilidades se sobrepõe às demais.

Este modelo é a generalização mínima e grounded do que já funciona hoje para o Risk Advisor — não introduz nenhum componente novo além de nomear explicitamente a "montagem de contexto" como responsabilidade do Advisor (hoje implícita na rota) e, quando um Advisor real exigir, um passthrough fino adicional (`gather_memory`) no mesmo padrão de `gather_context`/`gather_rag_context`.

---

## 10. Riscos residuais

1. **Nomenclatura de `Evidence`/`Recommendation` acoplada a `AnalysisRecord`** (§4.1) — `source_analysis_id`/`cited_analysis_ids` confundem quando a evidência é um chunk de documento. Resolver no Technical Design do primeiro Advisor da Classe D (Document ou Governance) — renomear para um vocabulário neutro (`source_id`/`cited_ids`) é uma mudança aditiva e de baixo risco, não uma reestruturação.
2. **`gather_memory` ainda não existe** — se o primeiro Advisor real que precisar de Enterprise Memory for adiado, isso é aceitável (mesmo padrão de Event Metrics/Integration Gateway); se for necessário cedo, é uma adição de método fino ao Framework, não uma mudança de modelo.
3. **Composição de múltiplas chamadas a `gather_context()` (Classe B) ainda não tem um padrão de código de referência** — o primeiro Advisor da Classe B (provavelmente PMO ou Portfolio) estabelece esse padrão; deve ser documentado explicitamente no seu Domain Blueprint para que os demais o repliquem, evitando reinvenção por Advisor.
4. **Tentação de mover a "montagem de contexto" para dentro do Framework** (generalizá-la) deve ser resistida — isso repetiria o erro já corrigido pela Fase 3 (rejeição do `input_schema`/`output_schema` genérico, D-067). Cada Advisor mantém sua própria montagem de contexto, nunca uma fábrica genérica.

Nenhum destes riscos bloqueia a abertura do primeiro Domain Blueprint — todos são resolvíveis no nível de Technical Design de cada Advisor, sem exigir uma segunda Architecture Review da Wave 5.

---

## 11. Recomendação Go/No-Go

**GO para a abertura do primeiro Domain Blueprint da Wave 5.**

Nenhuma inconsistência arquitetural foi encontrada que exija interrupção ou decisão adicional do Founder antes de prosseguir. O modelo definitivo (§9) resolve o achado do Kickoff (D-084) sem introduzir nenhuma abstração especulativa, sem modificar `AdvisorFramework`/`AIContextEngine`/`RagPipeline` além do que um consumidor real venha a exigir, e preserva integralmente as garantias já provadas em produção pelo Risk Advisor (Wave 3) e pela separação Advisor/Workflow/Event (Wave 4).

A escolha do primeiro Advisor (Delivery, per encaixe direto na Classe A, ou Document, per consumidor real já disponível de `document.indexed`) permanece uma decisão do Founder a ser confirmada no início do Domain Blueprint correspondente — não decidida por esta revisão.
