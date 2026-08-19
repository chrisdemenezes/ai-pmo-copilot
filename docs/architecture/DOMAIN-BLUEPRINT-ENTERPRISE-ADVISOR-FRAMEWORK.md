# Domain Blueprint — Enterprise Advisor Framework

**Status:** Blueprint subordinado a `WAVE-3-DOMAIN-BLUEPRINT.md` (documento mestre da Wave 3). Nenhum Epic é implementado por este documento.
**Autorização:** Decisão Estratégica do Founder (2026-07-27) — adoção de um Framework de Orquestração Multiagente como infraestrutura de execução. Diretriz verbatim: "O framework será apenas infraestrutura de execução. Os Enterprise Advisors permanecem conceitos do domínio. O domínio nunca poderá depender do framework. Cada Advisor deverá possuir contrato próprio, responsabilidades bem definidas e independência arquitetural."

---

## 0. Estado herdado (o que já existe, e o que este Blueprint generaliza)

Hoje existem 4 agentes, sem base comum:

| Agente | Usa a Foundation? | Padrão |
|---|---|---|
| `RiskAdvisorAgent` | Sim — único que usa `AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/`render_analyst_prompt` | PoC provado em `POST /risk-advisor/ask` (W3-3) |
| `RiskReviewAgent` | Não | Chama `LLMProvider.generate()` diretamente |
| `ProjectStatusAgent` | Não | Chama `LLMProvider.generate()` diretamente |
| `MeetingIntelligenceAgent` | Não | Chama `LLMProvider.generate()` diretamente |

Não existe hoje nenhuma classe-base ou `Protocol` comum entre os 4 — puro duck typing. O Enterprise Advisor Framework **não é uma invenção do zero**: é a generalização do padrão já provado pelo `RiskAdvisorAgent`, estendido aos 7 Advisors restantes (`ENTERPRISE-ADVISOR-CATALOG.md`), com um contrato explícito no lugar do duck typing atual.

---

## 1. Escopo e não-escopo

**Escopo:** contratos, ciclo de vida, interfaces, comunicação entre agentes, orquestração, isolamento entre Advisors, compartilhamento de contexto, observabilidade, auditoria — todos como **infraestrutura de execução**.

**Não-escopo (explícito):**
- Nenhum Advisor é implementado aqui — apenas o framework que os executará (`ENTERPRISE-ADVISOR-CATALOG.md` cataloga, não implementa).
- Nenhuma substituição de `AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/`PromptRegistry`/`LLMProvider` — o Framework **invoca** esses componentes através do Advisor, nunca os reimplementa (Princípio 4, documento mestre).
- Nenhum Model Registry, Provider Router ou orquestrador de LLM — orquestração aqui significa coordenar **Advisors**, não modelos.

---

## 2. Contratos

```
AdvisorContract (Protocol — o "contrato próprio" exigido pelo Founder)
  name: str                              # identidade estável do Advisor
  input_schema: type                     # tipo de entrada validada
  output_schema: type                    # tipo de saída (Recommendation/Explanation, Foundation)
  scope: AdvisorScope                    # limites de atuação (ver ENTERPRISE-ADVISOR-CATALOG.md)

  def handle(request: input_schema, context: SessionContext) -> output_schema
```

Cada Advisor declara seu próprio `input_schema`/`output_schema` — o Framework nunca assume uma forma de entrada/saída genérica que force todos os Advisors a um único formato. Isso é o que garante "independência arquitetural" (diretriz do Founder): o Framework conhece apenas a forma do contrato, nunca o conteúdo de domínio de um Advisor específico.

---

## 3. Ciclo de vida de um Advisor

1. **Registro** — um Advisor se registra no Framework declarando seu `AdvisorContract` (nome, schemas, escopo). O registro é estático (nenhum Model Registry, nenhuma descoberta dinâmica em runtime que reintroduza a complexidade já rejeitada em D-041 para provedores de LLM).
2. **Invocação** — o Framework recebe uma requisição endereçada a um Advisor por nome, valida contra `input_schema`, invoca `handle(...)`.
3. **Execução** — dentro de `handle`, o Advisor usa a Foundation (`AIContextEngine`, `render_analyst_prompt`, `LLMProvider`) e, se aplicável, a Knowledge Platform (RAG) — o Framework não interfere no corpo da execução, apenas a envolve com observabilidade e auditoria (§6, §7).
4. **Resposta** — validada contra `output_schema`, devolvida ao chamador.
5. **Encerramento** — nenhum estado de Advisor sobrevive além da sessão que o invocou, a menos que persistido explicitamente via Enterprise Memory Model (nunca um estado implícito escondido no Framework).

---

## 4. Interfaces

- **Advisor → Framework:** implementação de `AdvisorContract` (§2), registrada uma única vez.
- **Framework → Advisor:** `handle(request, context)` — única superfície de invocação; o Framework nunca chama um método interno de um Advisor específico.
- **Advisor → Foundation:** inalterado — `AIContextEngine.gather()`, `render_analyst_prompt()`, `RecommendationEngine.build()`, `ExplanationEngine.explain()`, exatamente como o `RiskAdvisorAgent` já faz hoje.
- **Advisor → Knowledge Platform:** apenas via `KnowledgeRepository` (nunca direto a `pgvector`), quando o Advisor usa RAG.

---

## 5. Comunicação entre agentes e orquestração

Nesta Wave, comunicação entre Advisors é **opcional e explícita**, nunca implícita: se um Advisor precisar do resultado de outro (ex.: PMO Advisor consultando um sinal do Risk Advisor), a chamada é uma invocação explícita através do Framework (mesma superfície `handle`), nunca um acoplamento direto entre dois módulos de Advisor. Nenhum barramento de mensagens ou fila assíncrona entre Advisors é introduzido nesta Wave — não há caso de uso comprovado que o exija; se surgir, é uma extensão registrada e aprovada (Critério de evolução §9), não um pressuposto deste Blueprint.

Orquestração, no escopo desta Wave, significa: rotear uma requisição ao Advisor correto por nome, aplicar observabilidade/auditoria uniformes (§6/§7), e — quando um Advisor invoca outro — garantir que o isolamento (§6) e a validação de contrato (§2) se apliquem também à chamada interna.

---

## 6. Isolamento entre Advisors

- Falha em um Advisor nunca deve derrubar outro nem a plataforma — o Framework captura exceções por invocação (tratamento de exceções explícito, CLAUDE.md) e retorna um erro estruturado, nunca propaga uma exceção não tratada ao chamador HTTP.
- Nenhum Advisor acessa o estado interno de outro diretamente — toda interação passa pelo contrato (§2/§4).
- Escopo de dados (`organization_id`) é aplicado uniformemente pelo Framework antes de `handle` ser chamado — um Advisor nunca decide por conta própria se pode ler dados de outra organização (mesma disciplina de Tenant Isolation, Security Hardening Gate D-045).

---

## 7. Compartilhamento de contexto

O único veículo de contexto compartilhado entre uma requisição e os componentes que ela invoca é `SessionContext` (Foundation, já existente) — o Framework não introduz um segundo mecanismo de contexto. Se um Advisor precisa de conhecimento de execuções anteriores, isso é resolvido via Enterprise Memory Model (memória operacional, `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §2.2), nunca por um cache ad-hoc dentro do Framework.

---

## 8. Observabilidade e auditoria

- Toda invocação de Advisor é medida por `ObservabilityRecorder.record_call()` (Foundation, já existente e reaproveitado, nunca duplicado) — o Framework garante que isso acontece uniformemente para os 8 Advisors, em vez de depender de cada Advisor lembrar de instrumentar a si mesmo.
- Toda pergunta/resposta de Advisor é registrada por `AIFoundationAudit.record_question()` — sempre, evidência ou não, mesmo padrão já usado pelo Risk Advisor.
- Nenhum Advisor implementa sua própria observabilidade ou auditoria paralela — isso é exatamente a "infraestrutura comum" que a Fase 3 do plano de execução constrói antes de qualquer Advisor individual (Fase 4).

---

## 9. Critérios de evolução

1. **Nenhum Advisor implementa infraestrutura própria** (observabilidade, auditoria, contexto, orquestração) — usa exclusivamente o que o Framework e a Foundation já provêm. Violação disso é a exceção rejeitada explicitamente pelo plano de execução ("Nenhum Advisor poderá criar infraestrutura própria").
2. **Comunicação assíncrona ou por fila entre Advisors só é introduzida mediante caso de uso comprovado e aprovação do Founder** — nunca antecipada especulativamente.
3. **O contrato de um Advisor (`AdvisorContract`) é versionado como qualquer outra interface pública** — mudança de `input_schema`/`output_schema` de um Advisor já em produção segue o mesmo rigor aditivo-primeiro já validado por TD-008.
4. **O Framework nunca cresce para conhecer a lógica de negócio de um Advisor específico** — se isso começar a acontecer, é sinal de que a responsabilidade pertence ao Advisor, não ao Framework (mesmo princípio de "infraestrutura nunca é domínio", Princípio 1 do documento mestre).
