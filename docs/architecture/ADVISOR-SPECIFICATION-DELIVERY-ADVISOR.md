# Advisor Specification — Delivery Advisor (terceiro uso do padrão institucional, Classe A)

**Autorização:** "Founder Decision" (encerramento oficial do Governance Advisor) — Founder declarou o Governance Advisor oficialmente concluído, reconhecendo: arquitetura íntegra; reutilização comprovada; hierarquia documental aplicada corretamente; classificação de governança implementada sem alterar o Framework; rastreabilidade documental revalidada; suíte completa confirmando estabilidade. Autorizada a abertura do ciclo institucional do **Delivery Advisor**, seguindo integralmente o processo de 6 etapas (D-092): **1. Advisor Specification (este documento)** → 2. Domain Blueprint → 3. Architecture Review → 4. Technical Design → 5. Implementação → 6. Executive Review.

---

## Executive Summary

O Delivery Advisor é o **terceiro Advisor a passar pelo padrão institucional**, mas o **primeiro desde o Risk Advisor a ser Classe A** (escopo único, `AR-8` §4) — diferente estruturalmente dos dois últimos (Document/Governance, Classe D, RAG como evidência primária). Onde Document e Governance precisaram de um método novo (`normalize_rag_evidence()`), o Delivery Advisor **não precisa de nada novo**: reutiliza `AIContextEngine.gather(organization_id, project_name, kind)` exatamente como o Risk Advisor já faz — o próprio achado que originou a Architecture Kickoff da Wave 5 (D-084) já confirmou que "dos 7 Advisors restantes, só o Delivery Advisor se encaixa diretamente" nesse método sem extensão. Isso torna esta Epic, arquiteturalmente, a mais simples desde o Risk Advisor — zero achado estrutural novo esperado até aqui. O único ponto que esta Advisor Specification não resolve, deixando explicitamente para o Domain Blueprint, é qual `kind` exato de `AnalysisRecord` (`"status"`, `"risk"`, ou uma composição de mais de um) melhor satisfaz o objetivo do catálogo de sintetizar "ações, riscos e histórico de análise" em uma única síntese de entrega.

---

## 1. Identidade do Advisor

| Campo | Valor |
|---|---|
| Nome | Delivery Advisor |
| Posição no catálogo | `ENTERPRISE-ADVISOR-CATALOG.md` §6 (6º de 8 Advisors) |
| Classe (per AR-8 §4, nascida do código) | **Classe A — escopo único**, mesma forma do Risk Advisor |
| Segundo Advisor da mesma Classe | Risk Advisor (já implementado — referência de padrão desta Classe, W3-3/W3-4) |

---

## 2. Objetivo e responsabilidade (per `ENTERPRISE-ADVISOR-CATALOG.md` §6, reafirmado)

**Objetivo:** apoiar a execução operacional de um projeto (entrega, cronograma, bloqueios).

**Responsabilidade:** sintetizar o estado de entrega de um projeto a partir de ações, riscos e histórico de análise já existentes — respondendo perguntas em linguagem natural, sempre citando `AnalysisRecord`s/ações reais.

---

## 3. Contrato (nenhum contrato novo — reaproveita `AdvisorContract`, mesma forma do Risk Advisor)

```
class DeliveryAdvisorAgent:
    name = "delivery_advisor"
    def advise(self, session: SessionContext, question: str,
               evidence: list[Evidence], rag_context: RagContext | None = None) -> dict:
        ...
```

Fluxo (idêntico ao já provado pelo Risk Advisor, não ao dos dois últimos Advisors de Classe D): Rota → Montagem de Contexto (`framework.gather_context(organization_id, project_name, kind=...)`, já existente, zero mudança) → `AdvisorFramework.run()` (compartilhado, inalterado) → `DeliveryAdvisorAgent.advise()`. RAG é **opcional/suplementar** aqui, não primário (diferente de Document/Governance) — mesmo papel que já ocupa para o Risk Advisor (`gather_rag_context()` chamado à parte, `rag_context` passado como parâmetro suplementar, nunca a fonte de evidência principal).

---

## 4. Fonte de evidência (achado a resolver no Domain Blueprint, não decidido aqui)

`AIContextEngine.gather(organization_id, project_name, kind)` sobre `AnalysisRecord`s já existentes — confirmado suficiente por D-084 sem nenhuma extensão. **Achado grounded, explicitamente não resolvido nesta Advisor Specification:** o catálogo descreve a responsabilidade do Advisor como abrangendo três conceitos — ações (`action_items`, hoje só existentes dentro do payload de `kind="meeting"`), riscos (`kind="risk"`) e histórico de análise/estado (`kind="status"`, `health_status`/`key_findings`/`recommendations`, per `src/agents/project_status/prompts/analysis.md`). Uma síntese que precisasse literalmente das três fontes exigiria **mais de uma chamada a `gather_context()`** — o que reclassificaria o Advisor para Classe B (agregada), contradizendo a classificação Classe A já decidida em AR-8/D-085 e o achado de D-084 (que fala de **um** `kind` que se encaixa diretamente). **Interpretação proposta, não decisão final:** o `kind="status"` é a fonte primária e única (uma chamada), por ser o `AnalysisRecord` cujo objetivo (relatório de status de projeto: `health_status`/`key_findings`/`recommendations`) mais diretamente corresponde a "entrega, cronograma, bloqueios" do catálogo — riscos e ações entrariam apenas como citação textual dentro de `key_findings`/`recommendations`, se o autor da análise de status já os mencionou, nunca como uma segunda chamada estrutural. Esta interpretação preserva a Classe A; **fica para o Domain Blueprint confirmá-la ou decidir de outra forma** (ex.: se o Founder preferir uma síntese mais rica sobre risco+ação+status, isso exigiria reclassificar o Advisor para Classe B, uma mudança de escopo maior que esta Specification não assume unilateralmente).

---

## 5. Dependências de infraestrutura (todas já prontas — nenhuma extensão esperada, ao contrário dos dois Advisors anteriores)

| Dependência | Status |
|---|---|
| `AIContextEngine.gather()` (Wave 3 Fase 2/3) | Pronto — já confirmado por D-084 como o único método que se encaixa diretamente no Delivery Advisor sem extensão. |
| `AdvisorFramework`/`AdvisorContract` (Wave 3 Fase 3/4) | Pronto — mesma forma exata do Risk Advisor. |
| `RagPipeline`/`gather_rag_context()` (se usado como suplementar) | Pronto, opcional — mesmo papel que já ocupa para o Risk Advisor. |
| `RecommendationEngine`/`ExplanationEngine` | Prontos, inalterados desde o rename de W5-1 — `source_id` já genérico, funciona sem mudança para `source_type="analysis_record"`. |
| Método novo de Framework | **Nenhum esperado** — diferente de Document/Governance (`normalize_rag_evidence()`), esta Epic não introduz nenhuma extensão estrutural até prova em contrário no Domain Blueprint. |

---

## 6. Limites de atuação (idênticos a todos os Advisors, `AR-8` §8 — reafirmados, não redecididos)

- Nunca invocado por `WorkflowRuntime`; nunca registrado como handler de `EventDispatcher`.
- Nunca executa regra de negócio, nunca altera entidade — produz exclusivamente `Explanation`/`Recommendation`.
- Nunca interpreta além da evidência — se a pergunta não tem `AnalysisRecord` relevante, `no_evidence()`, nunca infere.
- **Específico deste Advisor (catálogo §6, reafirmado aqui):** não decide replanejamento — evidencia o estado atual de entrega para quem decide, nunca prescreve uma ação corretiva como se fosse uma decisão já tomada.

---

## 7. Riscos/decisões herdadas, ainda não resolvidas (não redecididas aqui)

1. **Definição exata do `kind`/composição de evidência (§4)** — decisão do Domain Blueprint, com potencial impacto na classificação Classe A vs. B se o Founder exigir síntese de múltiplas fontes.
2. **`no_evidence_answer` de domínio** (mensagem própria, ex. "nenhum registro de entrega/status encontrado para este projeto" — não a genérica de risco) — decisão de Technical Design.
3. **`top_k`/uso de RAG suplementar** — se o Delivery Advisor usar `rag_context` como o Risk Advisor faz, mesmo risco residual de `top_k` não validado já registrado para os demais Advisors.
4. **TD-015** — não incide neste Advisor (Classe A não usa `normalize_rag_evidence()`); nenhuma ação necessária aqui.
5. **Achado a confirmar:** se `action_items`/`risks` precisarem ser citados explicitamente (não apenas mencionados em prosa dentro de `key_findings`), isso pode exigir compor evidência de mais de um `kind` — Domain Blueprint deve decidir, não presumido aqui.

---

## 8. Critérios de sucesso (per catálogo §6)

Nenhuma afirmação sobre atraso/bloqueio sem uma ação ou análise real como evidência.

---

## 9. Riscos identificados (consolidado)

| Risco | Bloqueante? | Onde resolver |
|---|---|---|
| Definição exata do `kind`/possível reclassificação Classe A→B | Não | Domain Blueprint |
| `no_evidence_answer`/`top_k` de domínio não definidos | Não | Technical Design |
| RAG suplementar (se usado) sem validação de uso real | Não | Technical Design |

Nenhum risco listado bloqueia a abertura do Domain Blueprint.

---

## 10. Recomendação GO/NO-GO para o Domain Blueprint

**GO.** Nenhuma infraestrutura nova é esperada — esta Epic reutiliza exatamente a forma já provada pelo Risk Advisor (`gather_context()`, sem nenhum método novo de Framework), tornando-a a Epic arquiteturalmente mais simples desde então. O único ponto em aberto (qual `kind`/composição de evidência) é uma decisão de domínio a ser resolvida no Domain Blueprint, não uma lacuna arquitetural.

Per instrução do Founder: nenhuma implementação iniciada; retorno obrigatório para Executive Review antes de prosseguir ao Domain Blueprint (etapa 2).
