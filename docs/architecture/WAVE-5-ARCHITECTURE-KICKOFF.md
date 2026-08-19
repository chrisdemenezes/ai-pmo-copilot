# Wave 5 — Enterprise Advisors: Architecture Kickoff

**Status:** documento orientador da Wave 5, autorizado pelo Founder ("Founder Decision" de encerramento da Wave 4 e abertura da Wave 5, 2026-07-30). **Nenhum código é escrito por este documento.** Serve de base para a Architecture Review da Wave 5 e para os Domain Blueprints individuais de cada Advisor — não substitui nenhum dos dois.

**Precondição:** Wave 4 (Enterprise Operations) oficialmente encerrada (D-083) — Epic Ledger final: W4-1/W4-3/W4-4 Concluídos, W4-2 Deferred, W4-5 Consolidated into W4-1, W4-6 Deferred.

**Mandato do Founder para esta Wave:** "até aqui vocês construíram a infraestrutura operacional; a partir da Wave 5, o desafio passa a ser demonstrar inteligência executiva utilizando essa infraestrutura, sem comprometer os princípios arquiteturais consolidados."

---

## 1. Objetivo da Wave 5

Implementar os 7 Enterprise Advisors restantes do catálogo (`ENTERPRISE-ADVISOR-CATALOG.md`), reaproveitando integralmente a infraestrutura já provada em produção pela Wave 3 (`AdvisorFramework`, Digital PMO Intelligence Foundation, Knowledge Platform/RAG) e, onde grounded, a infraestrutura recém-entregue pela Wave 4 (Event Model/Publisher/Dispatcher, Workflow Runtime/Execution Tracking) — sem introduzir nenhuma arquitetura paralela, nenhum novo Framework, nenhum novo registry.

O Risk Advisor (Wave 3, D-046/D-068) é a prova de que o padrão funciona; esta Wave generaliza esse padrão para os 7 Advisors restantes: **Executive, Strategy, PMO, Portfolio, Delivery, Governance, Document**.

---

## 2. Grounding — o que já existe e funciona (não hipótese)

### 2.1 Advisor Framework (Fase 3/4, Wave 3 — provado em produção)

Contrato real (`src/services/advisor_framework/types.py`), não especulativo:

```python
class AdvisorContract(Protocol):
    name: str
    def advise(
        self, session: SessionContext, question: str,
        evidence: list[Evidence], rag_context: RagContext | None = None,
    ) -> dict: ...
```

`AdvisorFramework` (`src/services/advisor_framework/framework.py`) expõe `gather_context`, `gather_rag_context`, `render_prompt`, `call_llm`, `run` — cada um um passthrough fino a um componente já existente (`AIContextEngine`, `RagPipeline`, `PromptRegistry`, `LLMProvider`, `RecommendationEngine`, `ExplanationEngine`, `AIFoundationAudit`). `run()` executa **exatamente um** Advisor por chamada — nunca um motor de roteamento entre Advisors, nunca delegação implícita.

**Nota de reconciliação documental:** o `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` original (pré-Fase 3) descrevia um contrato `input_schema`/`output_schema` genérico por Advisor e uma superfície `handle(request, context)`. A implementação real (D-067) rejeitou deliberadamente essa especulação — o contrato de produção é o `AdvisorContract.advise(...)` acima, nomeado literalmente a partir do que `RiskAdvisorAgent` já fazia. Este Kickoff usa o contrato **real**, não o documento pré-Fase 3.

### 2.2 Digital PMO Intelligence Foundation (Wave 3)

`AIContextEngine.gather(organization_id, project_name, kind) -> list[Evidence]` — resolve `AnalysisRecord`s reais, escopados por `project_id` (nunca por nome como chave) e por `kind` (ex.: `"risk"`). `RecommendationEngine.no_evidence()`/`.build()` — o anti-hallucination guard: nenhum Advisor cita o que não pode evidenciar. `ObservabilityRecorder`/`AIFoundationAudit` — toda invocação e toda pergunta são auditadas incondicionalmente.

**Achado arquitetural relevante para esta Wave (grounded no código, não hipotético):** `AIContextEngine.gather()` foi desenhado e provado para exatamente a forma do Risk Advisor — um projeto, um `kind`. Nem todos os 7 Advisors se encaixam nessa forma sem extensão:

| Advisor | Encaixe em `gather(project_name, kind)` | Observação |
|---|---|---|
| Delivery | Direto — escopo de projeto único | Mesmo padrão do Risk Advisor |
| Portfolio | Parcial — precisa de `portfolio_id`, não `project_name` | Extensão de escopo, não um novo Engine |
| PMO | Parcial — precisa agregar múltiplos `kind`/projetos | Extensão de agregação, não um novo Engine |
| Executive | Parcial — síntese multi-fonte (Dashboard, Decision Center, riscos, ações), não um único `kind` | Provável composição de `Evidence` de múltiplas chamadas a `gather()`, nunca um segundo Engine |
| Strategy | Parcial — evidência pode não existir ainda no domínio (objetivos estratégicos declarados) | Pode legitimamente cair em `no_evidence()` até que o domínio declare objetivos |
| Governance | **Não se aplica** — evidência são documentos de governança (Decision Log, Technical Debt, Mission Control), não `AnalysisRecord` | Evidência vem de RAG (Knowledge Platform), não de `AIContextEngine` |
| Document | **Não se aplica** — RAG é a evidência primária, não suplementar | Inverte a relação evidence/rag_context que os demais Advisors usam |

Este achado **não é resolvido por este documento** — é registrado para que o primeiro Domain Blueprint de Advisor que encontrar essa lacuna a resolva de forma grounded (extensão pontual de `AIContextEngine`, nunca um Engine genérico especulativo), em vez de qualquer Advisor futuro reimplementar sua própria busca de evidência por fora do Framework.

### 2.3 Enterprise Knowledge Platform + RAG Pipeline (Wave 3)

`KnowledgeRepository` (fachada única) → `EmbeddingProvider` (Mock hoje) + `PgVectorRepository`. `RagPipeline.retrieve()` compõe busca + ranking determinístico, retorna `RagContext` com `chunk_ids` rastreáveis. `rag_context` é **opcional e suplementar** no contrato hoje (nunca a única base de uma afirmação, exceto para o Document Advisor — ver 2.2). Nenhum Advisor acessa `pgvector`/`EmbeddingProvider` diretamente — sempre via `KnowledgeRepository`/`RagPipeline`.

### 2.4 Enterprise Operations (Wave 4 — recém-entregue, primeiro consumo real disponível)

- **`document.indexed`** (`KnowledgeRepository.index()`) já publica um evento real com produtor real — exatamente o gatilho que o **Document Advisor** consumiria, sem nenhuma mudança estrutural em `KnowledgeRepository` (confirmado no Blueprint da Wave 4 §4 e em D-080).
- **Workflow Runtime + Execution Tracking** (W4-4) — executor mínimo de passos puros, já provado ponta a ponta. **Não é o mecanismo de invocação de um Advisor** (Advisors são síncronos, requisição/resposta, via `AdvisorFramework.run()`) — é infraestrutura de orquestração operacional, para fluxos como "ao indexar um documento, registrar algo" (W4-4). Nenhum Advisor deve ser invocado a partir de um passo de Workflow nesta Wave, a menos que um caso de uso real e aprovado o exija — permanece um risco a vigiar (§7), não uma decisão já tomada.
- **EventPublisher/EventDispatcher** — se um Advisor, no futuro, precisar publicar um evento de domínio (ex.: `DocumentAdvisorAnswered`), o caminho já existe e é reutilizável sem nova abstração — mas nenhum Advisor publica eventos nesta Wave a menos que um consumidor real seja identificado (mesmo princípio "Grounded before Generalized" que já governou W4-2/W4-6).

---

## 3. Catálogo de escopo — os 7 Advisors (referência: `ENTERPRISE-ADVISOR-CATALOG.md`)

| # | Advisor | Evidência primária | Observação de encaixe (§2.2) |
|---|---|---|---|
| 1 | Executive | Síntese de sinais já existentes (Dashboard, Decision Center, Portfolio Intelligence) | Composição de `Evidence`, RAG opcional |
| 2 | Strategy | Objetivos estratégicos declarados no domínio (quando existirem) | Pode legitimamente usar `no_evidence()` hoje |
| 3 | PMO | Padrões através de múltiplos projetos (atraso recorrente, ausência de atualização) | Agregação multi-projeto/multi-kind |
| 4 | Portfolio | Composição/equilíbrio de um portfólio | Escopo por `portfolio_id` |
| 5 | Delivery | Estado de entrega de um projeto (ações, riscos, análises) | Encaixe direto, mesmo padrão do Risk Advisor |
| 6 | Governance | Conformidade com a própria governança STRATECH (Decision Log, TD, Mission Control) | Evidência via RAG sobre documentos de governança ingeridos |
| 7 | Document | Conteúdo de documentos corporativos ingeridos | RAG como evidência primária, não suplementar |

Nenhum destes 7 é implementado por este Kickoff. Cada um exige seu próprio Domain Blueprint (mesmo padrão de auditoria-antes-de-abstração do Risk Advisor), Architecture Review (quando o achado de §2.2 o exigir), Technical Design, Implementação, Governança e Executive Review — o mesmo ciclo institucional usado em toda a Wave 4.

---

## 4. Princípios arquiteturais permanentes (carregados das Waves 1-4, reafirmados para a Wave 5)

- **Reuso máximo, zero arquitetura paralela** — nenhum segundo Framework, nenhum segundo Context Engine, nenhum segundo Prompt Registry, nenhum segundo mecanismo de auditoria.
- **Um Advisor por chamada** — `AdvisorFramework.run()` nunca roteia entre Advisors nem delega de um para outro implicitamente (Wave 3, D-067).
- **Anti-hallucination guard obrigatório** — toda afirmação de todo Advisor rastreável a um dado real (`AnalysisRecord`, chunk de documento, ou registro de governança); `no_evidence()` sempre que a evidência não existir.
- **Tenant isolation sem exceção** — todo acesso escopado por `organization_id`, aplicado pelo Framework antes de qualquer execução de Advisor.
- **`correlation_id` de origem única** (Wave 4) — se um Advisor publicar um evento, o identificador vem de `RequestIDMiddleware`/`request_id_var`, nunca cunhado por um Advisor.
- **Workflow Runtime nunca decide, nunca executa inteligência** (Wave 4, princípio central do W4-4) — se algum fluxo futuro tentar colocar lógica de Advisor dentro de um passo de workflow, isso é uma violação arquitetural a ser barrada, não uma conveniência de implementação.
- **"Grounded before Generalized"** (D-079, D-083) — nenhuma extensão de `AIContextEngine`, nenhum novo Advisor, nenhuma nova integração é construída sem um consumidor real e evidência de código — o mesmo padrão que já derrubou Event Metrics e Integration Gateway nesta Wave 4 se aplica integralmente aqui.

---

## 5. Sequenciamento proposto (para confirmação na Architecture Review — não decidido aqui)

Duas âncoras reais disponíveis hoje, sem necessidade de nenhuma nova infraestrutura:

1. **Delivery Advisor** — encaixe direto e comprovado em `AIContextEngine.gather()`, menor risco, mais próximo do padrão já validado pelo Risk Advisor. Candidato natural a **primeiro Epic da Wave 5** (mesmo raciocínio que já elegeu o PMO Advisor como segundo candidato no catálogo original, antes de W4 existir).
2. **Document Advisor** — único Advisor com um evento de produtor real já disponível (`document.indexed`, Wave 4) esperando por ele; prova o valor concreto da Wave 4 para a Wave 5, exatamente como o Founder pediu ("demonstrar inteligência executiva utilizando essa infraestrutura").

Os demais 5 (Executive, Strategy, PMO, Portfolio, Governance) dependem, em graus variados, da resolução do achado de §2.2 (extensão de `AIContextEngine` ou fonte de evidência alternativa) — cada um exige seu próprio grounding antes de entrar no Epic Ledger. Recomenda-se que a Architecture Review confirme a ordem exata; este documento apenas identifica os dois candidatos sem pré-requisito de extensão de Framework.

---

## 6. Itens fora de escopo (permanecem proibidos, herdados das Waves 1-4)

Filas distribuídas, brokers externos, DSLs, motor de orquestração multiagente autônomo (achado histórico de `pmo_workflow.py`, D-074 — permanece Historical Superseded Architecture), roteamento automático entre Advisors, comunicação assíncrona entre Advisors sem caso de uso comprovado (Blueprint do Framework §5, ainda vigente), Event Metrics (Deferred, D-079), Integration Gateway (Deferred, D-083), qualquer painel/dashboard novo (Advisors sintetizam em linguagem natural, nunca recriam visualizações já existentes), Workflow Runtime invocando lógica de Advisor.

---

## 7. Riscos previstos

- **Achado de §2.2 é o maior risco de escopo** — se subestimado, pode levar a duplicar `AIContextEngine` por Advisor (violação direta de "reuso máximo"). Mitigação: cada Domain Blueprint de Advisor deve responder explicitamente como resolve esse encaixe antes de qualquer código.
- **Tentação de acoplar Workflow Runtime a Advisors** — o Founder já demarcou que Workflow Runtime nunca executa inteligência; qualquer proposta de Technical Design que misture os dois deve ser rejeitada na Architecture Review.
- **Governance Advisor exige ingestão de documentos de governança** (Decision Log, Technical Debt, Mission Control) na Knowledge Platform — isso é uma operação de `ingest()`/`index()` já existente, mas é a primeira vez que documentos internos de governança (não corporativos externos) seriam ingeridos; vale confirmar se isso é grounded (não há Advisor Governance ainda, então hoje não há necessidade real) antes de priorizar esse Advisor.
- **Strategy Advisor pode não ter evidência real hoje** — "objetivos estratégicos declarados" pode não existir como conceito de domínio ainda; se assim for, o Advisor legitimamente retorna `no_evidence()` sempre, o que pode ser confundido com um bug em vez de comportamento correto — deve ser documentado explicitamente no Domain Blueprint desse Advisor.

---

## 8. Critérios de sucesso da Wave 5

- Cada Advisor implementado reutiliza `AdvisorFramework`/`AdvisorContract` sem modificação de contrato além de extensões explicitamente aprovadas.
- Nenhuma citação de nenhum Advisor sem evidência real rastreável.
- `EventDispatcher`/`WorkflowRuntime` (Wave 4) permanecem byte-a-byte inalterados, a menos que um Advisor precise publicar um evento real com consumidor real comprovado.
- Nenhuma arquitetura paralela introduzida — confirmado por Architecture Review antes de cada Technical Design.
- `document.indexed` (Wave 4) tem, ao final da Wave 5, pelo menos um consumidor real (o Document Advisor) — fechando o gap que a Wave 4 deixou intencionalmente aberto.

---

## 9. Próximos passos (ciclo institucional, inalterado)

1. Architecture Review da Wave 5 sobre este Kickoff (equivalente à AR-7 da Wave 4) — deve confirmar ou revisar o sequenciamento de §5 e avaliar formalmente o achado de §2.2.
2. Aprovação explícita do Founder à Architecture Review.
3. Domain Blueprint individual do primeiro Advisor escolhido (grounded, auditoria-antes-de-abstração).
4. Technical Design, Implementação, Governança, Executive Review — por Advisor, um Epic de cada vez, mesmo padrão da Wave 4.

**Nenhum código é escrito, nenhuma implementação é iniciada por este documento.**
