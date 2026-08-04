# PORTFOLIO ADVISOR — EXECUTIVE EVIDENCE (Wave 5)

**Autorização:** "Founder Decision — Technical Design do Portfolio Advisor" (veredito **APPROVED — GO para implementação, Etapa 5 de 6**), encerrando o ciclo institucional de 6 etapas (D-092): Advisor Specification (D-108) → Domain Blueprint (D-109) → Architecture Review AR-12 (D-110) → Technical Design (D-111) → **Implementação, este documento** → Executive Review.

**Escopo confirmado:** exclusivamente o Portfolio Advisor, seguindo estritamente as 8 diretrizes obrigatórias desta autorização. Nenhuma expansão de escopo além do autorizado.

---

## Executive Summary

O Portfolio Advisor — primeiro Advisor Classe B (D-104) — foi implementado reutilizando integralmente `AdvisorFramework`/`AIContextEngine`/`DomainService` (Wave 2). O único componente estrutural novo, `PortfolioEvidenceAssembler`, vive exclusivamente em `src/agents/portfolio_advisor/` (diretriz 1), nunca em `src/services/`. Cada Project contribui exatamente uma `Evidence` — seu `AnalysisRecord` de status mais recente, selecionado mecanicamente via `evidence[0]` — e as 5 proibições da diretriz 4 (nunca interpretar, comparar `health_status`, calcular tendência, atribuir pesos, ou aplicar regra adicional) foram verificadas por leitura direta de código: o Assembler não contém nenhuma dessas operações em nenhuma linha. O modelo de resposta (`PortfolioAdvisorResponse`) expõe `total_projects`/`projects_with_evidence`/`projects_without_evidence` calculados inteiramente pelo Assembler, nunca pelo LLM. Os 11 cenários obrigatórios (A-K) foram comprovados em duas camadas — Framework (12 testes) e HTTP (11 testes) — mais 12 testes unitários do Assembler e 5 do Agent, totalizando **35 testes novos**. `git diff --stat` vazio em todos os arquivos de Framework/Foundation/Workflow/Event/`DomainService`. **Recomendação: GO para o encerramento do Epic do Portfolio Advisor.**

---

## 1. Preservação da infraestrutura compartilhada (diretriz 2)

Confirmado por `git diff --stat` vazio — nenhum destes arquivos foi tocado por esta implementação:

```
src/services/advisor_framework/framework.py
src/services/ai_foundation/context_engine.py
src/services/ai_foundation/recommendation_engine.py
src/services/ai_foundation/explanation_engine.py
src/services/ai_foundation/types.py
src/workflows/
src/services/events/
src/services/domain_service.py
src/database/domain_repository.py
```

`AdvisorFramework.run()` executa o `PortfolioAdvisorAgent` exatamente como já executa Risk/Document/Governance/Delivery Advisor. `DomainService`/`DomainRepository` (Wave 2) reutilizados sem nenhuma extensão — nenhum método novo, nenhuma assinatura alterada. O contrato `Evidence` permanece idêntico desde AR-9 — nenhum campo novo, nenhuma mudança de tipo.

---

## 2. Fluxo funcional completo

```
Cliente (pergunta sobre composição/equilíbrio de um portfólio)
  │
  ▼
POST /portfolio-advisor/ask  (RBAC intelligence.read, mesma permissão do Risk/Delivery Advisor)
  │
  ▼
PortfolioEvidenceAssembler.assemble(organization_id, portfolio_id)
  │  ├─ DomainService.get_portfolio() -- None → 404
  │  ├─ DomainService.list_programs() -- Wave 2, já em produção
  │  ├─ DomainService.list_projects() -- por Program
  │  └─ para cada Project: framework.gather_context(kind="status")
  │       → seleciona evidence[0] mecanicamente
  │       → enriquece metadata (portfolio_id/program_id/project_id/project_name)
  ▼
framework.run(portfolio_advisor_agent, session, question, evidence, no_evidence_answer=...)
  │  byte-for-byte igual a qualquer outro Advisor
  ▼
PortfolioAdvisorResponse{answer, total_projects, projects_with_evidence,
                          projects_without_evidence, cited_projects}
```

---

## 3. Arquivos alterados

**Backend — produção**
- `src/agents/portfolio_advisor/__init__.py`, `agent.py`, `evidence_assembler.py`, `prompts/advise.md` (novos).
- `src/api/routes/intelligence.py` — import de `PortfolioAdvisorAgent`/`PortfolioEvidenceAssembler`/`PortfolioAssemblyResult`/`DomainService`/`build_domain_service` (reaproveitado de `portfolio.py`, sem duplicação); `PortfolioAdvisorRequest`/`PortfolioAdvisorResponse`/`CitedProject` (novos); rota `POST /portfolio-advisor/ask` (nova); `_portfolio_advisor_response()` (nova).

**Backend — testes**
- `tests/test_portfolio_advisor_evidence_assembler.py` (novo, 7 testes) — unitários com fakes: seleção mecânica de `evidence[0]`, um Project com muitos registros nunca pesa mais que um com um único registro, enriquecimento de metadata sem alterar o contrato `Evidence`, Project sem status contribui zero evidência, Portfolio sem Programs, chamada exata de `gather_context(kind="status")` por Project.
- `tests/test_portfolio_advisor_agent.py` (novo, 5 testes) — unitários do `PortfolioAdvisorAgent.advise()`: serialização, nunca reordena a evidência recebida.
- `tests/test_portfolio_advisor.py` (novo, 12 testes) — integração via `AdvisorFramework`/`DomainService` reais (PostgreSQL real), cobrindo os 11 cenários A-K.
- `tests/test_portfolio_advisor_api.py` (novo, 11 testes) — HTTP real: cenários A-K aplicáveis + RBAC + resposta malformada (502) + trilha de auditoria, com um `RagPipeline` de dependência substituído por um dublê que lança exceção caso `.retrieve()` seja chamado, provando estruturalmente ausência de RAG.

**Governança**
- `docs/product/stratech-v2/DECISION-LOG.md`, `CHANGELOG.md`, `web/lib/mock/mission-control-data.ts` — espelhados (D-112).

---

## 4. Evidência de cobertura completa, parcial e zero (diretriz 6, itens A/B/C)

| Cenário | Teste (Framework) | Teste (HTTP) | Resultado |
|---|---|---|---|
| **A. Cobertura completa** | `TestScenarioA_CoberturaCompleta` | `TestScenarioA_CoberturaCompleta` | `total_projects == projects_with_evidence`, todos os Projects citáveis |
| **B. Cobertura parcial** | `TestScenarioB_CoberturaParcial` | `TestScenarioB_CoberturaParcial` | `projects_without_evidence > 0`, calculado estruturalmente, resposta nunca generaliza |
| **C. Cobertura zero** | `TestScenarioC_CoberturaZero` | `TestScenarioC_CoberturaZero` | `no_evidence()` sem chamada ao LLM (`_ExplodingProvider` nunca invocado) |

---

## 5. Isolamento organizacional e Portfolio inexistente (diretriz 6, itens D/E/F)

| Cenário | Teste (Framework) | Teste (HTTP) | Resultado |
|---|---|---|---|
| **D. Portfolio sem Programs/Projects** | `TestScenarioD_PortfolioSemProgramsOuProjects` (2 testes) | `TestScenarioD_PortfolioSemProgramsOuProjects` | `evidence == []`, `total_projects == 0` |
| **E. Portfolio inexistente** | `TestScenarioE_PortfolioInexistente` | `TestScenarioE_PortfolioInexistente` | `assemble()` retorna `None` → rota retorna **404** |
| **F. Portfolio de outra organização** | `TestScenarioF_PortfolioDeOutraOrganizacao` | `TestScenarioF_PortfolioDeOutraOrganizacao` | Mesmo resultado do caso E — `get_portfolio()` já filtra por `organization_id` na própria query, nenhuma distinção observável entre "não existe" e "não é seu" |

---

## 6. Rastreabilidade e ausência de peso por histórico (diretriz 6, itens G/H)

**G. Cada Project contribui somente com o status mais recente:** `TestScenarioG_ApenasOStatusMaisRecente` (Framework) / `TestScenarioG_ApenasOStatusMaisRecente` (HTTP) — Project com registro antigo (`red`, 2026-07-01) e recente (`green`, 2026-08-01): apenas o `source_id` do registro recente sobrevive na evidência consolidada.

**H. Project com muitos históricos não pesa mais que Project com um único status:** `TestScenarioH_HistoricoNaoPesaMais` — Project A com 3 registros históricos e Project B com 1 registro único contribuem, cada um, **exatamente uma** `Evidence` — verificado por `len(result.evidence) == 2` (nunca 4).

---

## 7. Ordem sem prioridade e citação seletiva (diretriz 6, itens I/J)

**I. Ordem alfabética não implica prioridade:** `TestScenarioI_OrdemNaoImplicaPrioridade` — mesma lista de `cited_ids` aplicada contra a evidência em ordem direta e invertida via `RecommendationEngine.build()`: o conjunto de citações sobreviventes é idêntico nos dois casos, provando que a filtragem de citação é indiferente à posição — nunca posicional.

**J. `cited_projects` contém apenas Projects efetivamente citados:** `TestScenarioJ_CitedProjectsApenasOsCitados` (Framework) / testes de cobertura parcial (HTTP) — um LLM scriptado que cita apenas 1 de 2 Projects disponíveis produz `cited_projects` com exatamente 1 item, nunca os 2 disponíveis.

---

## 8. Ausência de chamada ao LLM sem evidência (diretriz 6, item K)

`TestScenarioK_NenhumaChamadaAoLlmSemEvidencia` (Framework) e `TestScenarioC_CoberturaZero`/`TestScenarioD_PortfolioSemProgramsOuProjects` (HTTP) — `_ExplodingProvider`/`ExplodingProvider` (que levanta `AssertionError` se `.generate()` for chamado) usado em todos os cenários de evidência vazia: a suíte inteira passando é, em si, a prova de que o portão anti-alucinação (`if not evidence:` em `AdvisorFramework.run()`, inalterado) cobre o Portfolio Advisor sem nenhum mecanismo novo.

---

## 9. Ausência de tendência histórica do Portfolio (diretriz 6, verificação estrutural adicional)

Confirmado por leitura direta de `src/agents/portfolio_advisor/agent.py`: `projects_json` (enviado ao LLM) contém, por Project, exatamente um snapshot (`health_status`/`key_findings`/`recommendations`/`source_analysis_id`/`source_created_at`) — **nenhuma sequência temporal por projeto está presente**. A proibição de o Advisor afirmar tendência histórica consolidada do Portfolio (diretriz 6 do Technical Design) é estruturalmente impossível de violar por acidente, não apenas uma instrução textual do prompt.

---

## 10. Ausência de segunda/supplementary fonte (RAG)

**Busca direta no código-fonte:**

```
$ grep -n "gather_rag_context" src/agents/portfolio_advisor/agent.py src/agents/portfolio_advisor/evidence_assembler.py
(nenhum resultado)
```

**Prova estrutural em teste:** `tests/test_portfolio_advisor.py` constrói `AdvisorFramework` com `rag_pipeline=None` em todos os 12 testes — qualquer chamada acidental a `gather_rag_context()` levantaria `AttributeError` imediatamente. `tests/test_portfolio_advisor_api.py` substitui a dependência `build_rag_pipeline` por um dublê (`_ExplodingRagPipeline`) cujo `.retrieve()` lança `AssertionError` — os 11 testes do arquivo passam porque a rota nunca a invoca.

---

## 11. Confirmação: `PortfolioEvidenceAssembler` exclusivamente dentro do pacote (diretriz 1)

`src/agents/portfolio_advisor/evidence_assembler.py` — não promovido a `src/services/` nesta implementação, exatamente como decidido em D-109/AR-12 e reafirmado nesta autorização.

---

## 12. Testes executados e resultados

| Suíte | Resultado |
|---|---|
| Backend completo (`pytest`) | **638 passed**, 0 failed (603 pré-existentes + 35 novos desta Epic: 7 unitários do Assembler + 5 unitários do Agent + 12 integração Framework + 11 HTTP) |
| Frontend completo (`vitest`) | **503 passed** (69 arquivos) — nenhum arquivo de frontend tocado nesta Epic |
| `ruff check src tests` | Limpo |
| `npx tsc --noEmit` | Limpo |
| `npx eslint .` | Limpo |

---

## 13. Critérios de aceite da Technical Design (D-111) — confirmação

1. ✅ `PortfolioEvidenceAssembler` exclusivamente dentro do pacote do Advisor (§11).
2. ✅ Preservação integral de `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline/`RecommendationEngine`/`ExplanationEngine`/contrato `Evidence` (§1).
3. ✅ Um `Evidence` por Project, seleção mecânica via `evidence[0]` (§6, cenário G).
4. ✅ As 5 proibições do Assembler confirmadas por leitura de código — nenhuma interpretação, comparação, cálculo de tendência, peso, ou regra adicional.
5. ✅ Modelo de resposta com `total_projects`/`projects_with_evidence`/`projects_without_evidence` calculados estruturalmente (§4).
6. ✅ Todos os 11 cenários obrigatórios (A-K) comprovados em duas camadas (§4-§8).
7. ✅ Gatilho de performance mantido, nenhuma otimização antecipada (nenhuma mudança nesta implementação).
8. ✅ Suíte completa verde; `ruff`/`tsc`/`eslint` limpos.

---

## 14. Riscos residuais (reconfirmados, nenhum bloqueante)

1. **Qualidade da síntese pelo LLM real** (fora do escopo de testes com provider scriptado) — mitigado pela garantia estrutural de que os dados que o modelo recebe são comprovadamente corretos, não-invertidos, e sem histórico oculto (§9).
2. **Volume de `AnalysisRecord`s históricos descartados por Project** — mesmo risco já aceito e justificado em AR-12; histórico completo permanece consultável via Delivery Advisor.
3. **Gatilho de performance** (>20 chamadas sequenciais ou p95 > 3s) — registrado, não implementado; nenhuma ação até ser cruzado por dado real.
4. **TD-015** — não incide (Classe B via `gather_context()` múltiplo, não `normalize_rag_evidence()`).

Nenhum risco bloqueia o encerramento do Epic.

---

## 15. Confirmação de encerramento

Todos os critérios de aceite atendidos. Nenhuma expansão de escopo além do autorizado. **Recomendação: GO para o encerramento do Epic do Portfolio Advisor.**

Per instrução explícita do Founder: retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor.
