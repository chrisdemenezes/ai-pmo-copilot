# Domain Blueprint — Delivery Advisor (etapa 2 de 6 do ciclo institucional)

**Autorização:** "Founder Decision — Delivery Advisor Specification" (veredito **APPROVED — GO para o Domain Blueprint**), fixando uma decisão arquitetural permanente para toda a STRATECH: a fronteira entre Classe A e Classe B é definida pela **cardinalidade de fontes primárias de evidência** (uma única chamada estrutural vs. duas ou mais), nunca pela quantidade de assuntos abordados na resposta — registrada em `AR-8-WAVE-5-ENTERPRISE-ADVISOR-MODEL-REVIEW.md` §4.2 (D-104). Sob essa definição, o Founder confirmou o Delivery Advisor como **Classe A**, com fonte oficial `AnalysisRecord`/`kind="status"` — podendo essa evidência conter referências textuais a riscos, ações e bloqueios sem deixar de ser uma única evidência. Nenhuma segunda consulta estrutural a `kind="risk"`/`kind="meeting"`/timeline/`action_items` está autorizada apenas para enriquecimento; isso exigiria uma nova evolução arquitetural, com possível reclassificação para Classe B, explicitamente autorizada pelo Founder — não uma decisão deste Domain Blueprint. Nenhum código escrito nesta etapa.

---

## Executive Summary

O Delivery Advisor é o quarto Advisor a passar pelo padrão institucional, e o segundo — depois do Risk Advisor — a ser **Classe A** sob a definição agora permanente (D-104): uma única fonte primária de evidência. A fonte já está decidida pelo Founder (`kind="status"`, §5) — este Domain Blueprint não reabre essa decisão, apenas a aplica: caracteriza o fluxo (idêntico ao Risk Advisor, `gather_context()` sem nenhuma extensão), o contrato do `DeliveryAdvisorAgent` (mesma forma de `AdvisorContract`), e os cenários de uso típicos (perguntas sobre entrega/cronograma/bloqueios respondidas a partir de `health_status`/`key_findings`/`recommendations` de um `AnalysisRecord` de status). Nenhum achado estrutural novo — confirmado por leitura direta do código já em produção (`AIContextEngine.gather()`, `AdvisorFramework.run()`, `RiskAdvisorAgent`). Recomendação ao final: **GO para a Architecture Review**.

---

## 0. Escopo e não-escopo deste documento

**Decide:** objetivo/responsabilidade do Delivery Advisor (reafirmando o catálogo), modelo arquitetural aplicado (idêntico ao Risk Advisor, nenhuma novidade), aplicação da fonte de evidência já decidida pelo Founder (`kind="status"`), e a caracterização conceitual dos cenários de uso (perguntas típicas sobre entrega/cronograma/bloqueios).

**Não decide (fica para etapas seguintes):**
- **Architecture Review:** se a fonte `kind="status"` é suficiente na prática para os primeiros casos de uso reais, ou se há um achado estrutural que só aparece ao formalizar o fluxo ponta a ponta (nenhum indício disso até aqui, mas a Architecture Review é a etapa que confirma).
- **Technical Design:** texto literal do prompt do `DeliveryAdvisorAgent`, wording exato do `no_evidence_answer` de domínio, `top_k` (se RAG suplementar for usado), nome definitivo da rota HTTP.
- **Não reabre:** a classificação Classe A nem a fonte `kind="status"` — ambas já são Founder Decision (D-104), não matéria deste Blueprint.

---

## 1. Grounding Audit — o que já existe, hoje, em código (reaproveitado sem alteração do Risk Advisor)

Confirmado por leitura direta do código já implementado (`src/services/advisor_framework/framework.py`, `src/services/ai_foundation/context_engine.py`, `src/agents/risk_advisor/agent.py`, `src/agents/project_status/prompts/analysis.md`):

- `AdvisorFramework.gather_context(organization_id, project_name, kind)` → `AIContextEngine.gather()` — já resolve `project_name` para `project_id` via `resolve_scope_id()`, já filtra por `organization_id`/`kind`, já retorna `list[Evidence]` com `source_type="analysis_record"`. **Nenhuma mudança necessária** — mesma chamada exata já usada pelo Risk Advisor com `kind="risk"`; o Delivery Advisor usa a mesma assinatura com `kind="status"`.
- `AIContextEngine.gather()` já filtra `model_output.get("structured")` antes de construir cada `Evidence` — nenhum `AnalysisRecord` malformado chega ao Advisor.
- `AdvisorFramework.run()` — portão anti-alucinação (`if not evidence:`) já cobre o caso de nenhum `AnalysisRecord` de `kind="status"` existir para o projeto perguntado, sem nenhuma mudança: `RecommendationEngine.no_evidence(...)` responde, exatamente como já ocorre para o Risk Advisor.
- `RiskAdvisorAgent` (`src/agents/risk_advisor/agent.py`) é a referência estrutural direta: monta um JSON a partir de `evidence` (`risks_json`), opcionalmente enriquece com `rag_context` (supplementar, nunca fonte de uma alegação sozinha), chama `framework.render_prompt()`/`framework.call_llm()`, retorna via `parse_structured_output()`. O `DeliveryAdvisorAgent` replica exatamente essa forma, trocando `risks_json` por um JSON equivalente extraído de `evidence[].content` (`health_status`/`key_findings`/`recommendations`, per schema confirmado em `src/agents/project_status/prompts/analysis.md`).
- `RecommendationEngine.build()`/`ExplanationEngine.explain()` já operam sobre `source_analysis_id` — nenhuma mudança necessária, mesma forma do Risk Advisor.

**O que NÃO existe e não será inventado por este documento:** nenhuma segunda chamada a `gather_context()`; nenhum campo novo em `Evidence`; nenhuma mudança a `AIContextEngine`/`AdvisorFramework`; nenhuma entidade "Action" nova (confirmado, per Advisor Specification §grounding, que `action_items` só existe embutido em `AnalysisRecord`s de `kind="meeting"` — fora do escopo de evidência deste Advisor, per Founder Decision D-104).

---

## 2. Objetivo e responsabilidade (per `ENTERPRISE-ADVISOR-CATALOG.md` §6, reafirmado — não redecidido)

**Objetivo:** apoiar a execução operacional de um projeto (entrega, cronograma, bloqueios).

**Responsabilidade:** sintetizar o estado de entrega de um projeto a partir do `AnalysisRecord` de status mais relevante, respondendo perguntas em linguagem natural, sempre citando o(s) `AnalysisRecord`(s) real(is) — nunca uma afirmação sobre atraso/bloqueio sem essa evidência.

**Reafirmado, per Founder Decision (D-104):** riscos e ações só entram na resposta na medida em que já estejam mencionados em texto dentro de `key_findings`/`recommendations` do próprio `AnalysisRecord` de status — nunca como resultado de uma segunda consulta a `kind="risk"`/`kind="meeting"`.

---

## 3. Modelo aplicado — Framework-Mediated Evidence Assembly, Classe A (idêntico ao Risk Advisor, D-104 confirma a classificação)

```
Rota (POST /delivery-advisor/ask, nome definitivo per Technical Design)
  │
  ▼
Montagem de Contexto: framework.gather_context(organization_id, project_name, kind="status")
  │   (única chamada estrutural -- Classe A per D-104; nenhuma segunda
  │    chamada a kind="risk"/"meeting"/action_items)
  ▼
framework.run(delivery_advisor_agent, session, question, evidence, rag_context=None ou suplementar, no_evidence_answer=...)
  │   (compartilhado, byte-for-byte igual ao Risk Advisor -- auditoria, portão
  │    anti-alucinação, RecommendationEngine.build(), ExplanationEngine.explain())
  ▼
DeliveryAdvisorAgent.advise()  -- único componente novo desta Epic
```

Nenhuma etapa deste fluxo diverge do já implementado e testado para o Risk Advisor — a única peça nova é o próprio `DeliveryAdvisorAgent` (interpretação de domínio sobre `health_status`/`key_findings`/`recommendations`, §6).

---

## 4. Contrato do `DeliveryAdvisorAgent` (nenhum contrato novo)

```
class DeliveryAdvisorAgent:
    name = "delivery_advisor"
    def advise(self, session: SessionContext, question: str,
               evidence: list[Evidence], rag_context: RagContext | None = None) -> dict:
        ...
```

Mesma forma exata de `AdvisorContract`, já provada por `RiskAdvisorAgent` e `DocumentAdvisorAgent` — nenhuma alteração ao Protocol.

---

## 5. Fonte de evidência (já decidida pelo Founder, D-104 — aplicada aqui, não redecidida)

`AIContextEngine.gather(organization_id, project_name, kind="status")` — fonte primária e única. Schema confirmado (`src/agents/project_status/prompts/analysis.md`): `{health_status: "green|yellow|red", key_findings: [string], recommendations: [string]}`, exposto ao Advisor via `evidence[].content`.

**Regra institucional confirmada (D-104), aplicada literalmente:** `health_status`, `key_findings`, `recommendations`, e quaisquer referências textuais a riscos/ações/bloqueios que já estejam dentro desses campos (porque o autor da análise de status as mencionou), tudo isso é **uma única evidência** — nunca uma segunda fonte. O `DeliveryAdvisorAgent` não interpreta esses textos como uma nova categoria estrutural (não os classifica como "risco" ou "ação" separadamente) — apenas os cita como parte do conteúdo do `AnalysisRecord` de status, exatamente como já estão.

**Explicitamente fora de alcance desta Epic (D-104):** qualquer chamada a `gather_context(kind="risk")` ou `gather_context(kind="meeting")` para complementar a resposta. Se um caso de uso real exigir isso, é uma nova evolução arquitetural (possível Classe B), não uma decisão de Technical Design.

RAG suplementar (`gather_rag_context()`/`rag_context`) permanece opcional, mesmo papel que já ocupa para o Risk Advisor — nunca a fonte primária, nunca introduz uma alegação que a evidência de `kind="status"` não sustente.

---

## 6. Fluxos — cenários de uso típicos

Caracterizados **conceitualmente** — o que cada um significa e que evidência o fundamenta — sem prescrever o texto exato do prompt (Technical Design).

### 6.1 Pergunta sobre estado geral de entrega

Ex.: "Como está a entrega do projeto X?" — resolvido inteiramente por `health_status`/`key_findings`/`recommendations` do `AnalysisRecord` de status mais recente (ou mais relevante, conforme `AIContextEngine.gather()` já ordena). Resposta cita o `source_analysis_id` real.

### 6.2 Pergunta sobre bloqueios

Ex.: "Existem bloqueios no projeto X?" — resolvido pelo texto já presente em `key_findings`/`recommendations`, se o autor da análise de status já os mencionou. **Se nenhum `AnalysisRecord` de status menciona bloqueios, a resposta correta é dizer que não há evidência de bloqueio nessa fonte** — nunca inferir um bloqueio que não está no texto, e nunca consultar `kind="meeting"` para procurar um.

### 6.3 Ausência de evidência

Nenhum `AnalysisRecord` de `kind="status"` existe para o projeto perguntado. Mecanismo: idêntico ao já provado para Risk/Document/Governance Advisor — `AdvisorFramework.run()`'s `if not evidence:` → `RecommendationEngine.no_evidence(...)`. **Nenhum componente novo.** O `no_evidence_answer` de domínio (texto exato) é decisão de Technical Design.

**Ponto comum aos três cenários (garantia estrutural, não nova):** `RecommendationEngine.build()` já garante que nenhuma citação aparece na resposta sem estar presente na `evidence` efetivamente entregue — mesmo portão já provado, nenhuma garantia nova a construir.

---

## 7. Limites de atuação (idênticos a todos os Advisors, `AR-8` §8 — reafirmados, não redecididos)

- Nunca invocado por `WorkflowRuntime`; nunca registrado como handler de `EventDispatcher`.
- Nunca executa regra de negócio, nunca altera entidade — produz exclusivamente `Explanation`/`Recommendation`.
- Nunca interpreta além da evidência — se a pergunta não tem `AnalysisRecord` de status relevante, `no_evidence()`, nunca infere.
- **Específico deste Advisor (catálogo §6, reafirmado):** não decide replanejamento — evidencia o estado atual de entrega para quem decide, nunca prescreve uma ação corretiva como se fosse uma decisão já tomada.
- **Específico desta Founder Decision (D-104):** nunca consulta uma segunda fonte estrutural (`kind="risk"`/`"meeting"`/action_items) para enriquecer a resposta — isso permaneceria Classe A apenas se resolvido por evolução arquitetural futura, explicitamente autorizada.

---

## 8. Riscos e decisões que ficam para a Architecture Review/Technical Design (não bloqueiam este Blueprint)

1. **Suficiência prática de `kind="status"` como única fonte** — nenhum indício contrário até aqui; a Architecture Review é a etapa que confirma isso com uma auditoria formal, não apenas leitura de código.
2. **Wording exato do `no_evidence_answer`** — Technical Design.
3. **`top_k`/uso de RAG suplementar** — se usado, mesmo risco residual de `top_k` não validado já registrado para os demais Advisors — Technical Design.
4. **TD-015** — não incide neste Advisor (Classe A via `gather_context()`, não `normalize_rag_evidence()`); nenhuma ação necessária.
5. **Nome definitivo da rota HTTP** (`/delivery-advisor/ask`, proposto per convenção já usada pelos 3 Advisors anteriores) — Technical Design confirma.

Nenhum risco listado bloqueia o avanço para a Architecture Review.

---

## 9. Fora de escopo (explícito)

- Qualquer segunda chamada estrutural a `gather_context()` com outro `kind`, per Founder Decision D-104 — reservado para uma evolução arquitetural futura, se necessária.
- Qualquer nova entidade "Action"/"Bloqueio" — riscos e ações permanecem texto embutido em `AnalysisRecord`s existentes, nunca uma nova tabela/modelo nesta Epic.
- Qualquer alteração a `AdvisorFramework`, `AIContextEngine`, Workflow Runtime, Event Pipeline, ou à lógica de `RecommendationEngine` — arquitetura do Risk Advisor preservada integralmente.
- Decisão de replanejamento — o Advisor evidencia, nunca decide.

---

## 10. Critérios de sucesso do Epic (per catálogo §6)

1. Nenhuma afirmação sobre atraso/bloqueio sem um `AnalysisRecord` de status real como evidência.
2. `no_evidence()` funciona sem chamada ao LLM quando não há `AnalysisRecord` de `kind="status"` relevante — mesmo padrão já provado.
3. Nenhuma citação inventada sobrevive à resposta — mesmo portão já provado (`RecommendationEngine.build()`).
4. Isolamento organizacional preservado — nenhum `AnalysisRecord` de outra organização/projeto aparece na resposta (estrutural, já garantido por `organization_id`/`project_id`-scoping em `AIContextEngine.gather()`).
5. Nenhuma segunda consulta estrutural a outro `kind` — verificável por leitura de código do `DeliveryAdvisorAgent`/rota (uma única chamada a `gather_context()`).

---

## 11. Recomendação GO/NO-GO para a Architecture Review

**GO.** Toda a infraestrutura necessária já existe e já foi validada por um consumidor real (Risk Advisor) — este Domain Blueprint não identifica nenhum achado que exija mudança estrutural. A fonte de evidência (`kind="status"`) e a classificação (Classe A) já são Founder Decision (D-104), aplicadas aqui sem reabertura. O único ponto que a Architecture Review deve confirmar é a suficiência prática dessa fonte única para os primeiros casos de uso reais — não um risco estrutural, uma validação formal.

---

## 12. Próximo passo

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de prosseguir à Architecture Review (etapa 3).
