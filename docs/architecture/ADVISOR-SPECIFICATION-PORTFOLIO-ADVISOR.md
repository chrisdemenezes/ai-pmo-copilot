# Advisor Specification — Portfolio Advisor (quinto uso do padrão institucional, primeiro Classe B)

**Autorização:** "Founder Decision" (encerramento oficial do Delivery Advisor, etapa 6 de 6) — Founder declarou o Delivery Advisor oficialmente concluído, reconhecendo: permanece Classe A; utiliza exclusivamente `AnalysisRecord`/`kind="status"`; a interpretação temporal pertence ao domínio do Advisor; o Framework compartilhado permaneceu inalterado; os cenários de melhora, deterioração e histórico insuficiente foram comprovados; a suíte completa permanece verde. Autorizada a abertura do ciclo institucional do **Portfolio Advisor**, seguindo integralmente o processo de 6 etapas (D-092): **1. Advisor Specification (este documento)** → 2. Domain Blueprint → 3. Architecture Review → 4. Technical Design → 5. Implementação → 6. Executive Review. O Founder nomeou o Advisor diretamente nesta decisão, caracterizando-o explicitamente como o **primeiro Advisor Classe B** (D-104), que deve "validar a composição de duas ou mais fontes independentes sem transferir essa responsabilidade para o `AdvisorFramework`".

---

## Executive Summary

O Portfolio Advisor é o quinto Advisor a passar pelo padrão institucional e o **primeiro de Classe B** (`AR-8` §4: agregada — múltiplos projetos e/ou múltiplos `kind`, compostos na etapa de montagem de contexto, nunca no Framework). Diferente de todos os Advisors anteriores (Classe A: Risk, Delivery; Classe D: Document, Governance), este é o primeiro cujo Objetivo — "avaliar equilíbrio, dependências e sobreposição entre projetos/programas dentro de um portfólio" — exige, por natureza, evidência de **mais de um projeto simultaneamente**, algo que `AIContextEngine.gather()` nunca resolve sozinho (aceita exatamente um `project_name` por chamada). Este documento apresenta uma **proposta grounded, não uma decisão final**, de como essa composição ocorre sem nenhuma mudança ao `AdvisorFramework`/`AIContextEngine`: reutilizar `DomainService.list_programs()`/`list_projects()` (Wave 2, já em produção, já org-scoped com segurança) para resolver os projetos-membro do portfólio, e então chamar `framework.gather_context(organization_id, project_name, kind="status")` **uma vez por projeto**, concatenando os resultados em uma única `evidence: list[Evidence]` antes de `framework.run()` — exatamente o mesmo lugar (a rota) onde toda composição de evidência já acontece hoje para os demais Advisors, apenas repetida N vezes em vez de uma. Esta é a decisão que estabelece o padrão de referência que os próximos Advisors de Classe B (PMO, Executive) devem replicar (risco residual nomeado em AR-8 §7.3) — por isso reservada para confirmação explícita no Domain Blueprint, não decidida unilateralmente aqui.

---

## 1. Identidade do Advisor

| Campo | Valor |
|---|---|
| Nome | Portfolio Advisor |
| Posição no catálogo | `ENTERPRISE-ADVISOR-CATALOG.md` §5 (5º de 8 Advisors) |
| Classe (per AR-8 §4 / D-104) | **Classe B — agregada**, primeiro Advisor desta classe a ser implementado |
| Advisors da mesma Classe, ainda não implementados | PMO Advisor, Executive Advisor — replicarão o padrão que este Advisor estabelecer |

---

## 2. Objetivo e responsabilidade (per `ENTERPRISE-ADVISOR-CATALOG.md` §5, reafirmado)

**Objetivo:** apoiar decisões de composição e priorização de portfólio.

**Responsabilidade:** avaliar equilíbrio, dependências e sobreposição entre projetos/programas dentro de um portfólio — respondendo perguntas em linguagem natural, sempre citando programas/projetos reais.

**Reafirmado, per catálogo:** não decide alocação de orçamento ou prioridade — apenas evidencia trade-offs para quem decide.

---

## 3. Contrato (nenhum contrato novo — reaproveita `AdvisorContract`, mesma forma de todo Advisor)

```
class PortfolioAdvisorAgent:
    name = "portfolio_advisor"
    def advise(self, session: SessionContext, question: str,
               evidence: list[Evidence], rag_context: RagContext | None = None) -> dict:
        ...
```

Mesma forma exata já provada por Risk/Delivery/Document/Governance Advisor — nenhuma alteração ao Protocol. **Ponto central desta Classe:** o Advisor em si (`advise()`) recebe `evidence` **já composta**, exatamente como qualquer Advisor recebe hoje — a composição de múltiplas fontes acontece **antes** de `framework.run()` ser chamado, na etapa de montagem de contexto (§4), nunca dentro do próprio `advise()` e nunca dentro do Framework.

---

## 4. Fonte de evidência — composição Classe B (proposta grounded, não decidida — reservada para o Domain Blueprint)

### 4.1 O problema estrutural, confirmado por leitura de código

`AIContextEngine.gather(organization_id, project_name, kind)` (`src/services/ai_foundation/context_engine.py`) resolve exatamente **um** `project_name` por chamada (via `resolve_scope_id()`), e retorna evidência apenas desse escopo. Um Portfolio, por definição, agrega múltiplos Programs, cada um com múltiplos Projects (`Portfolio` 1→N `Program` 1→N `Project`, `src/database/models.py`). Nenhuma chamada única a `gather_context()` — hoje ou amanhã, sem alterar sua assinatura — pode retornar evidência de mais de um projeto. Isso é exatamente o que caracteriza a Classe B (`AR-8` §4): múltiplas chamadas, compostas fora do Framework.

### 4.2 Resolução de membros do portfólio — componente já existente, reaproveitado sem extensão

Confirmado por leitura direta de `src/services/domain_service.py` (Wave 2, já em produção, já usado pelas rotas `/portfolios`/`/programs`/`/projects`):

- `DomainService.list_programs(organization_id, portfolio_id)` — já resolve com segurança organizacional: retorna `None` (não uma lista vazia) se o `portfolio_id` não existir ou não pertencer à organização, via `get_portfolio()` (org-scoped) como portão antes de `list_programs_by_portfolio()` (não org-scoped por si só). O mesmo padrão 404-not-403 já usado por toda a API de Enterprise Domain.
- `DomainService.list_projects(organization_id, program_id)` — mesmo padrão, um portão (`get_program()`, org-scoped) antes de `list_projects_by_program()`.

**Nenhum destes métodos é novo — ambos já existem, testados, em produção desde a Wave 2.** A proposta desta Advisor Specification é reutilizá-los, nunca estendê-los: `list_programs(org_id, portfolio_id)` → para cada `Program`, `list_projects(org_id, program.id)` → lista final de nomes de `Project` que pertencem ao portfólio, com segurança organizacional herdada estruturalmente (nenhum projeto de outra organização pode aparecer, pois cada portão já falha antes de alcançá-lo).

### 4.3 Composição da evidência — proposta, a confirmar no Domain Blueprint

```
Rota (POST /portfolio-advisor/ask, nome definitivo per Technical Design)
  │
  ▼
projects = resolve_portfolio_projects(domain_service, organization_id, portfolio_id)
  │   (usa exclusivamente DomainService.list_programs()/list_projects(), acima --
  │    nenhum método novo de repositório/serviço)
  ▼
evidence = []
for project in projects:
    evidence += framework.gather_context(organization_id, project.name, kind="status")
  │   (N chamadas ao MESMO método já existente, cada uma idêntica à que o
  │    Delivery Advisor já faz uma única vez -- a composição é literalmente
  │    a concatenação das N listas, no código da rota, nunca no Framework)
  ▼
framework.run(portfolio_advisor_agent, session, question, evidence, ...)
  │   (byte-for-byte igual a qualquer outro Advisor -- run() nunca soube, e
  │    continua não sabendo, que a evidence recebida veio de 1 ou N fontes)
  ▼
PortfolioAdvisorAgent.advise()  -- único componente novo desta Epic
```

**Por que isso não viola "sem transferir a responsabilidade para o `AdvisorFramework`" (exigência explícita do Founder):** `AdvisorFramework.gather_context()`/`run()` permanecem exatamente como são hoje — chamados N vezes e 1 vez, respectivamente, sem nenhuma mudança de assinatura, sem nenhum novo método. A responsabilidade de "quantos projetos, quais projetos, como concatenar" vive inteiramente no código da rota (mesma camada onde a Montagem de Contexto de todo Advisor já acontece) — nunca dentro do Framework compartilhado.

**`kind` proposto:** `"status"`, por analogia direta ao Delivery Advisor (D-104/D-106) — cada projeto contribui seu `AnalysisRecord` de status mais recente (per a mesma regra de recência já estabelecida), permitindo ao Portfolio Advisor sintetizar equilíbrio/sobreposição a partir do estado real de cada projeto. **Não decidido de forma final aqui** — o Domain Blueprint deve confirmar se `kind="status"` é suficiente ou se `kind="risk"` também deveria compor (uma terceira dimensão de chamadas, ainda Classe B, apenas mais fontes).

### 4.4 Achado explicitamente reservado para o Domain Blueprint

Esta Advisor Specification **não decide**: (a) se a composição acontece na rota (proposta acima) ou se merece um pequeno helper de módulo dedicado (ainda fora do Framework, apenas organização de código); (b) o `kind` definitivo (§4.3); (c) o volume esperado de chamadas a `gather_context()` por portfólio (um portfólio com muitos programas/projetos gera muitas chamadas sequenciais — risco de performance a avaliar, não bloqueante); (d) se este é o padrão que **deve** ser documentado como referência formal para PMO/Executive Advisor (per AR-8 §7.3), ou se cada um desses Advisors, ao chegar sua vez, pode justificar uma variação. Per instrução do Founder, o Domain Blueprint é a etapa que confirma ou ajusta esta proposta — não esta Specification.

---

## 5. Dependências de infraestrutura

| Dependência | Status |
|---|---|
| `AIContextEngine.gather()`/`AdvisorFramework.gather_context()` (Wave 3) | Pronto — chamado N vezes, sem nenhuma mudança de assinatura. |
| `DomainService.list_programs()`/`list_projects()` (Wave 2) | Pronto — já org-scoped, já em produção, reaproveitado sem extensão. |
| `AdvisorFramework`/`AdvisorContract` (Wave 3 Fase 3/4) | Pronto — mesma forma exata dos demais Advisors. |
| `RecommendationEngine`/`ExplanationEngine` | Prontos, inalterados — já operam sobre `evidence: list[Evidence]` de qualquer tamanho, sem soberania sobre sua origem. |
| Método novo de Framework | **Nenhum esperado** — mesma disciplina já aplicada ao Delivery Advisor; a composição Classe B vive inteiramente fora do Framework (§4.3). |

---

## 6. Limites de atuação (idênticos a todos os Advisors, `AR-8` §8 — reafirmados, não redecididos)

- Nunca invocado por `WorkflowRuntime`; nunca registrado como handler de `EventDispatcher`.
- Nunca executa regra de negócio, nunca altera entidade — produz exclusivamente `Explanation`/`Recommendation`.
- Nunca interpreta além da evidência — se o portfólio não tem projetos com `AnalysisRecord` relevante, `no_evidence()`, nunca infere.
- **Específico deste Advisor (catálogo §5, reafirmado aqui):** não decide alocação de orçamento ou prioridade — evidencia trade-offs de composição para quem decide, nunca prescreve uma realocação como se fosse uma decisão já tomada.

---

## 7. Riscos/decisões herdadas, ainda não resolvidas (não redecididas aqui)

1. **Padrão de composição Classe B (§4)** — proposta grounded apresentada, não decisão final; confirmação/ajuste é do Domain Blueprint. Impacto direto nos próximos Advisors de Classe B (PMO, Executive), per risco já nomeado em AR-8 §7.3.
2. **`kind` definitivo por chamada de projeto** (`"status"` proposto, `"risk"` possivelmente adicional) — Domain Blueprint.
3. **Volume de chamadas a `gather_context()` por portfólio** — nenhum dado real de uso ainda; risco de performance a avaliar, não bloqueante nesta etapa.
4. **`no_evidence_answer` de domínio** (mensagem própria, ex. "nenhum projeto deste portfólio possui análise de status registrada") — decisão de Technical Design.
5. **TD-015** — não incide neste Advisor (nenhum uso de `normalize_rag_evidence()`/RAG previsto).
6. **RBAC** — reaproveitamento de `intelligence.read` (mesmo padrão de Risk/Delivery Advisor) é a expectativa; confirmação formal é do Technical Design.

---

## 8. Critérios de sucesso (per catálogo §5)

Toda recomendação de composição rastreável a projetos/programas reais do portfólio avaliado.

---

## 9. Riscos identificados (consolidado)

| Risco | Bloqueante? | Onde resolver |
|---|---|---|
| Padrão de composição Classe B não confirmado (§4) | Não | Domain Blueprint |
| `kind` definitivo por chamada de projeto | Não | Domain Blueprint |
| Volume de chamadas a `gather_context()` por portfólio | Não | Technical Design |
| `no_evidence_answer`/nome de rota de domínio | Não | Technical Design |

Nenhum risco listado bloqueia a abertura do Domain Blueprint.

---

## 10. Recomendação GO/NO-GO para o Domain Blueprint

**GO.** Nenhuma infraestrutura nova é esperada — a composição Classe B proposta (§4) reutiliza integralmente componentes já em produção (`AIContextEngine.gather()`, `DomainService.list_programs()`/`list_projects()`), sem nenhuma extensão de Framework. O ponto em aberto (padrão exato de composição, per achado de AR-8 §7.3) é uma decisão de domínio a confirmar no Domain Blueprint — não uma lacuna arquitetural, e sua resolução aqui estabelece o padrão de referência que os próximos Advisors de Classe B devem replicar.

Per instrução do Founder: nenhuma implementação iniciada; retorno obrigatório para Executive Review antes de prosseguir ao Domain Blueprint (etapa 2).
