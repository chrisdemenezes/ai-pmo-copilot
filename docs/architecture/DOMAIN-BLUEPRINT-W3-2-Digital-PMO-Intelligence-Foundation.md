# Domain Blueprint — Epic W3-2: Digital PMO Intelligence Foundation

**Wave:** 3, Epic W3-2 — substitui definitivamente a proposta anterior "AI Platform Foundation" (avaliada e adiada em D-041/`DOMAIN-BLUEPRINT-AI-PLATFORM-FOUNDATION.md`, por ausência de consumidor real para Provider Strategy/Model Registry/Prompt Versioning). Esta é uma decisão estratégica nova do Founder, com escopo diferente — infraestrutura compartilhada de execução de Enterprise Analysts, não seleção/roteamento de modelos.
**Status:** Blueprint. Aguardando Revisão Arquitetural antes da Technical Design, per o fluxo institucional.
**Princípio permanente que rege todo desenho abaixo:** a STRATECH é um Executive Decision Operating System. Sua IA opera como um Digital PMO — executa continuamente atividades equivalentes às de um Analista Operacional de PMO. **A IA opera. Os gestores decidem.** Nenhum componente desta Foundation pode violar esse princípio (nenhuma decisão autônoma, nenhuma ação sem evidência, nenhuma recomendação sem explicação).

---

## 1. Objetivo da Foundation

Fornecer a infraestrutura compartilhada de inteligência que **todo** Enterprise Analyst da STRATECH (o Risk Advisor, hoje, e cada especialista operacional futuro) reutiliza, em vez de reimplementar. A Foundation elimina duplicação de código entre analistas e padroniza 5 comportamentos que hoje só existem, ad hoc, dentro da rota `POST /api/risk-advisor/ask` (`src/api/routes/intelligence.py`): montagem de contexto institucional, evidência verificável, formato de recomendação, explicação da origem da recomendação, e auditoria/observabilidade da execução.

**A Foundation não é uma funcionalidade de negócio.** Nenhum usuário final a acessa diretamente; ela não aparece em nenhuma tela. Ela é consumida exclusivamente por código de Enterprise Analyst (hoje: Risk Advisor; amanhã: qualquer novo especialista que a Wave 3 aprovar).

## 2. Responsabilidades

| Responsabilidade | O que a Foundation garante |
|---|---|
| Contexto institucional | Todo Enterprise Analyst recebe os dados institucionais já persistidos (análises, riscos, ações) relevantes à pergunta, resolvidos de uma forma única e testada — nunca reimplementados por analista. |
| Evidência verificável | Nenhuma conclusão é aceita sem estar ancorada em `AnalysisRecord`s reais que o próprio Analyst recebeu como entrada — nunca dados inventados pelo modelo. |
| Recomendação padronizada | Toda saída de um Analyst tem a mesma forma (`answer` + evidência citada), independente do domínio. |
| Explicação obrigatória | Toda recomendação é acompanhada de uma explicação legível de sua origem — nunca uma resposta "opaca". |
| Prompt reutilizável | Todo Analyst compõe seu prompt especializado sobre uma base institucional comum (filosofia "IA opera, gestores decidem" + contrato de formato de resposta), sem duplicar esse texto em cada agente. |
| Contexto de sessão efêmero | Dados de identidade/projeto necessários durante uma única requisição trafegam por um objeto único, nunca persistido além da requisição. |
| Auditoria uniforme | Toda pergunta feita a qualquer Analyst é registrada com o mesmo padrão (ator, analyst, projeto, pergunta) — nunca a resposta do modelo — sem que cada rota reimplemente essa regra. |
| Observabilidade | Toda chamada a um provider de IA feita através de um Analyst tem sua latência e uso de tokens registrados, de forma uniforme — fechando o gap real que D-041 identificou (`ProductionLLMProvider.generate()` descartava `message.usage`) e que hoje tem, pela primeira vez, um requisito concreto puxando sua resolução (esta própria Epic). |

## 3. Limites (o que a Foundation NÃO faz)

- **Não é um agente.** Não decide, não analisa domínio, não escreve prompts de negócio — isso permanece em `src/agents/<nome>/`.
- **Não introduz Vector Store, pgvector, embeddings ou RAG.** O Context Engine só lê dados institucionais já estruturados e persistidos (`AnalysisRecord` via os repositórios/serviços já existentes) — nunca busca semântica.
- **Não introduz Knowledge Platform.** Nenhum armazenamento de conhecimento novo; a "base de conhecimento" continua sendo exclusivamente `AnalysisRecord`.
- **Não introduz Executive Memory permanente.** O Session Context é efêmero por definição (Seção 4.6) — descartado ao final da requisição, nunca persistido entre sessões.
- **Não introduz um Multi-Agent Framework.** A Foundation serve analistas individuais, invocados um de cada vez por uma rota HTTP; nenhuma orquestração entre analistas, nenhum planejamento autônomo, nenhuma auto-execução, nenhum agente colaborativo.
- **Não substitui nem estende o contrato público de `LLMProvider`, `PromptRegistry` ou `parse_structured_output`.** A Foundation compõe sobre eles (Seção 7), nunca os duplica.
- **Não cria um Model Registry, Provider Router ou Prompt Versioning** — a avaliação de D-041 continua válida: nenhum consumidor real pede seleção de múltiplos providers ou múltiplas versões de um mesmo prompt hoje. Isso permanece fora desta Epic.
- **Se qualquer um dos itens acima parecer necessário durante a implementação, a implementação para imediatamente e uma Decision Proposal é produzida** — per instrução explícita do Founder. Nenhuma exceção silenciosa.

## 4. Componentes

### 4.1 AI Context Engine
`src/services/ai_foundation/context_engine.py` — `AIContextEngine.gather(organization_id, project_name, kind) -> list[Evidence]`. Resolve os dados institucionais já persistidos relevantes a uma pergunta, delegando à mesma leitura já usada hoje (`AnalysisRepository.list_analyses`, o que `ProjectSummaryService.list_latest_risks`/`list_action_items` já fazem por trás) — nenhuma query nova, nenhuma tabela nova. Generaliza, em vez de duplicar por analista, a montagem de "os dados que já sei sobre este projeto".

### 4.2 Evidence Engine
`src/services/ai_foundation/types.py::Evidence` — um formato único de evidência (`source_analysis_id`, `source_created_at`, `kind`, `summary`) que todo Analyst usa para representar "um fato já verificado". O Context Engine produz `Evidence`; o Recommendation Engine consome `Evidence`. Nenhum dado que não seja um `Evidence` rastreável a um `AnalysisRecord` real chega ao LLM ou sai como citação.

### 4.3 Recommendation Engine
`src/services/ai_foundation/recommendation_engine.py::RecommendationEngine` — normaliza a saída do LLM (já parseada por `parse_structured_output`, reaproveitado sem alteração) em um `Recommendation` (`answer` + `cited_evidence: list[Evidence]`), **descartando qualquer id de evidência citada pelo modelo que não estava na lista de `Evidence` realmente fornecida** (mesma defesa que a rota do Risk Advisor já aplica manualmente hoje, agora centralizada). Também padroniza a resposta canônica para "nenhuma evidência disponível" (sem chamar o LLM), a mesma otimização que o Risk Advisor já usa.

### 4.4 Explanation Engine
`src/services/ai_foundation/explanation_engine.py::ExplanationEngine` — envolve um `Recommendation` em um `Explanation`, garantindo que toda resposta carregue, de forma padronizada, a lista de evidências que a sustentam e uma nota fixa de que a resposta é síntese informativa, não uma decisão automática (per ADR-V2-007, Seção 9). É o que garante, estruturalmente, que nenhuma recomendação seja "opaca".

### 4.5 Prompt Registry Evolution
`src/services/ai_foundation/prompt_composer.py::render_analyst_prompt(prompt_registry, agent_name, prompt_name, **variables)` — **não é um novo registry.** Compõe, por cima do `PromptRegistry.get()` já existente (contrato inalterado), um preâmbulo institucional único (`src/services/ai_foundation/prompts/analyst_preamble.md`: a filosofia "IA opera, gestores decidem" + o contrato de formato JSON de resposta) com o template especializado de cada Analyst. Cada Analyst continua escrevendo apenas as instruções do seu próprio domínio.

### 4.6 Session Context
`src/services/ai_foundation/types.py::SessionContext` — dataclass imutável (`organization_id`, `user_id`, `session_id`, `project_name`) construída a partir do `RequestContext` já resolvido por `get_request_context` no início de cada requisição, e descartada ao final dela. **Nunca persistida** — nenhuma tabela, nenhum cache entre requisições. É explicitamente o oposto de "Executive Memory permanente".

### 4.7 Audit Integration
`src/services/ai_foundation/audit_integration.py::AIFoundationAudit.record_question(repository, session, analyst_name, question)` — delega inteiramente a `AdministrationRepository.record_audit` (nenhuma tabela nova), padronizando a ação como `f"{analyst_name}.question_asked"` e o payload (`project_name`, `question`) — **nunca a resposta do modelo**, mesma disciplina que o Risk Advisor já criou manualmente (Security Hardening Gate/D-046), agora codificada uma única vez.

### 4.8 Observability
`src/services/ai_foundation/observability.py::ObservabilityRecorder.record_call(analyst_name, session, fn)` — envolve a chamada `provider.generate(prompt)` de qualquer Analyst, medindo a latência (`time.monotonic()`) e capturando o uso de tokens quando o provider o expõe (ver Seção 7 — `ProductionLLMProvider` passa a expor `last_usage` como atributo opcional, sem alterar o contrato do `LLMProvider` Protocol), e registra tudo via o `logging` estruturado já usado em todo o projeto (nenhum novo armazenamento de métricas — nenhuma tabela, nenhum serviço externo). Fecha o gap real de D-041 sem inventar um "AI Governance Dashboard" que ninguém pediu.

## 5. Fluxo de execução

1. A rota do Analyst (ex.: `POST /api/risk-advisor/ask`) resolve `RequestContext` (já existente, RBAC já aplicado antes deste fluxo começar).
2. Constrói um `SessionContext` efêmero a partir do `RequestContext`.
3. Chama `AIContextEngine.gather(...)` para obter a lista de `Evidence` relevante (ex.: os riscos mais recentes do projeto).
4. Se a lista de evidência vier vazia, o `RecommendationEngine` devolve a resposta canônica de "nada para sintetizar" **sem chamar o LLM** — o fluxo pula direto para o passo 8.
5. O Analyst compõe seu prompt especializado via `render_analyst_prompt(...)` (preâmbulo institucional + template do domínio + evidência serializada).
6. O Analyst chama `provider.generate(prompt)` **através de** `ObservabilityRecorder.record_call(...)`, que mede latência e tokens.
7. A saída bruta é parseada por `parse_structured_output` (inalterado); o `RecommendationEngine` valida as citações contra a evidência realmente fornecida e produz um `Recommendation`.
8. O `ExplanationEngine` envolve o `Recommendation` em um `Explanation`.
9. `AIFoundationAudit.record_question(...)` registra a pergunta (nunca a resposta) — **executado independentemente do resultado do passo 4** (mesmo quando não há evidência, a pergunta ainda é auditada, per o Domain Blueprint do Risk Advisor §12).
10. A rota do Analyst serializa o `Explanation` no seu próprio Pydantic response model e retorna.

## 6. Regras arquiteturais

- **Cada responsabilidade cruzada (contexto, evidência, recomendação, explicação, auditoria, observabilidade) existe uma única vez**, dentro de `src/services/ai_foundation/`. Nenhum Enterprise Analyst pode reimplementar qualquer uma delas.
- **Todo novo Enterprise Analyst é obrigado a consumir a Foundation** para essas 6 responsabilidades — não é opcional.
- **A Foundation nunca conhece o domínio de um Analyst específico.** `Evidence.summary` é um `dict` opaco à Foundation — apenas o Analyst e o seu prompt sabem interpretá-lo. Isso mantém a Foundation genuinamente compartilhável entre domínios diferentes (riscos hoje; cronograma, orçamento, documentos, no futuro).
- **Nenhuma extensão do contrato público de `LLMProvider`, `PromptRegistry` ou `parse_structured_output`** — a Foundation só compõe sobre eles.
- **Reversibilidade:** o Risk Advisor é migrado para consumir a Foundation nesta mesma Epic (Seção 8) — prova viva de que o desenho funciona para um consumidor real, não apenas teórico.

## 7. Contratos públicos

```python
# src/services/ai_foundation/types.py
@dataclass(frozen=True)
class Evidence:
    source_analysis_id: int
    source_created_at: datetime
    kind: str
    summary: dict  # campos específicos do domínio (ex.: description/probability/impact/mitigation)

@dataclass(frozen=True)
class SessionContext:
    organization_id: int
    user_id: int
    session_id: str
    project_name: str | None = None

@dataclass(frozen=True)
class Recommendation:
    answer: str
    cited_evidence: list[Evidence]

@dataclass(frozen=True)
class Explanation:
    recommendation: Recommendation
    rationale: str  # nota fixa "síntese informativa, não decisão automática" + contagem de evidências usadas


# src/services/ai_foundation/context_engine.py
class AIContextEngine:
    def __init__(self, repository: AnalysisRepository): ...
    def gather(self, organization_id: int, project_name: str | None, kind: str) -> list[Evidence]: ...


# src/services/ai_foundation/recommendation_engine.py
class RecommendationEngine:
    NO_EVIDENCE_ANSWER: str = "Nenhuma evidência identificada ainda para este projeto."

    @staticmethod
    def build(answer: str, cited_ids: list[int], evidence: list[Evidence]) -> Recommendation: ...

    @staticmethod
    def no_evidence() -> Recommendation: ...


# src/services/ai_foundation/explanation_engine.py
class ExplanationEngine:
    @staticmethod
    def explain(recommendation: Recommendation) -> Explanation: ...


# src/services/ai_foundation/prompt_composer.py
def render_analyst_prompt(
    prompt_registry: PromptRegistry, agent_name: str, prompt_name: str, **variables: str
) -> str: ...


# src/services/ai_foundation/audit_integration.py
class AIFoundationAudit:
    @staticmethod
    def record_question(
        repository: AnalysisRepository, session: SessionContext, analyst_name: str, question: str
    ) -> None: ...


# src/services/ai_foundation/observability.py
class ObservabilityRecorder:
    @staticmethod
    def record_call(
        analyst_name: str, session: SessionContext, fn: Callable[[], str]
    ) -> str: ...  # invoca fn() (o provider.generate(prompt)), loga latência/tokens, devolve o resultado inalterado
```

`ProductionLLMProvider` (`src/llm/providers/production_provider.py`) ganha um atributo opcional `last_usage: TokenUsage | None`, populado a cada `generate()` a partir de `message.usage` (já retornado pela API da Anthropic e hoje descartado) — sem alterar a assinatura de `generate()` nem o `LLMProvider` Protocol. `MockLLMProvider` não precisa implementar isso; `ObservabilityRecorder` trata a ausência do atributo como "sem dado de custo disponível", nunca como erro.

## 8. Reuso pelos futuros Enterprise Analysts

Um novo Analyst hipotético (ex.: "Schedule Advisor") precisaria escrever apenas:

```python
# src/agents/schedule_advisor/agent.py -- só regras de domínio
class ScheduleAdvisorAgent:
    def __init__(self, model_client, prompt_registry):
        self.model_client = model_client
        self.prompt_registry = prompt_registry

    def advise(self, question: str, evidence: list[Evidence]) -> dict:
        prompt = render_analyst_prompt(
            self.prompt_registry, "schedule_advisor", "advise",
            question=question, evidence_json=json.dumps([e.summary for e in evidence]),
        )
        raw = self.model_client.generate(prompt)
        return parse_structured_output(raw)
```

```markdown
<!-- src/agents/schedule_advisor/prompts/advise.md -- só o prompt especializado -->
Question: $question
Schedule evidence: $evidence_json
Respond with {"answer": "...", "cited_analysis_ids": [...]}
```

E, na rota, apenas: permissão específica (`Depends(require_permission("schedule.read"))` ou equivalente), `AIContextEngine.gather(..., kind="schedule")`, `RecommendationEngine.build(...)`, `ExplanationEngine.explain(...)`, `AIFoundationAudit.record_question(...)` — a mesma sequência do Risk Advisor, sem reimplementar nenhuma das 6 responsabilidades cruzadas.

## 9. Critérios de aceite

- Um novo Enterprise Analyst precisa implementar **apenas**: regras específicas do domínio (`agent.py::advise`), prompt especializado (`prompts/advise.md`), interface (rota HTTP + seção Workspace), e permissões específicas.
- Contexto, evidência, recomendação, explicação, auditoria e observabilidade **nunca são reimplementados** — são consumidos da Foundation.
- O Risk Advisor (Epic W3-3) é migrado para consumir a Foundation nesta Epic, prova de que o desenho funciona para um consumidor real — não apenas uma promessa teórica.
- Nenhum dos itens da Seção 3 (Vector Store, RAG, Knowledge Platform, Executive Memory permanente, Multi-Agent Framework, planejamento/reflexão/auto-execução autônomos, agentes colaborativos, Model Registry/Provider Router/Prompt Versioning) é introduzido.
- `ProductionLLMProvider` passa a expor uso de tokens sem quebrar nenhum consumidor existente (contrato `LLMProvider.generate() -> str` inalterado).
- Toda pergunta feita por qualquer Analyst é auditada; toda chamada a um provider é observada (latência mínima; tokens quando disponíveis).

## 10. Decision Log

Esta Epic substitui, com escopo genuinamente diferente, o Epic W3-2 anterior ("AI Platform Foundation", D-041, adiado por ausência de consumidor real para Provider Strategy/Model Registry/Prompt Versioning). A avaliação de D-041 permanece correta para aquele escopo — nenhuma dessas 3 sub-áreas tem consumidor real hoje, e nenhuma delas está sendo construída por esta Epic. O novo escopo ("Digital PMO Intelligence Foundation": Context/Evidence/Recommendation/Explanation/Prompt composition/Session/Audit/Observability) é uma decisão estratégica distinta do Founder, registrada nesta janela, com um consumidor real e imediato: o Risk Advisor (Epic W3-3, já implementado), que será migrado para a Foundation como prova de reuso. Será formalizada como uma nova entrada no Decision Log (`D-047`) na conclusão da Technical Design/Implementação, per a convenção já estabelecida (uma correção de escopo é uma nova entrada, nunca uma edição retroativa de D-041).
