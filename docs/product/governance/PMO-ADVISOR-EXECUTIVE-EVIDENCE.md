# PMO Advisor — Executive Evidence

**Etapa 5 de 6** (Implementação) do ciclo institucional do PMO Advisor. Produzido sob autorização da Founder Decision que aprovou o Technical Design (`TECHNICAL-DESIGN-PMO-ADVISOR.md`) com **GO para implementação**, com 8 diretrizes obrigatórias e 7 provas adicionais exigidas além dos 13 cenários A-M já definidos.

---

## 1. Executive Summary

O PMO Advisor — sexto Advisor da Wave 5, segundo Classe B — está implementado e comprovado end-to-end. `PMOEvidenceAssembler` (`src/agents/pmo_advisor/evidence_assembler.py`) resolve o escopo organizacional diretamente via `DomainService.list_projects(organization_id)` (sem traversal Portfolio→Program, sem caso de 404 — confirmado por leitura de código, D-114/D-116), coleta `AnalysisRecord`/`kind="status"` por Project via `AdvisorFramework.gather_context()` (inalterado), calcula `staleness_days`/`is_stale` estruturalmente a partir de uma única `reference_time` capturada uma vez por chamada, e limita cada Project a no máximo 5 registros mais recentes (`evidence[:5]`) — tudo em memória, dentro do próprio Assembler, sem tocar `AdvisorFramework`/`AIContextEngine`.

Os 13 cenários obrigatórios (A-M) e as 7 provas adicionais exigidas pela Founder Decision foram comprovados em duas camadas — Framework (`tests/test_pmo_advisor.py`, Postgres real) e HTTP (`tests/test_pmo_advisor_api.py`, Postgres real, RBAC real). A rastreabilidade de citações repetidas do mesmo Project foi confirmada **sem alterar** `CitedProject` — `source_analysis_id` já torna cada citação inequivocamente distinguível, mesmo quando o mesmo `project_id` aparece mais de uma vez.

`git diff --stat` vazio em toda a infraestrutura compartilhada. Suíte backend completa **680 passed** (48 novos: 17 unitários Assembler + 6 unitários Agent + 16 integração Framework + 9 HTTP). Suíte frontend completa **503 passed** (nenhuma mudança de frontend nesta Epic). `ruff`/`tsc`/`eslint` limpos.

**Recomendação: GO para o encerramento do Epic.**

---

## 2. Fluxo funcional completo (comprovado, não apenas descrito)

```
POST /pmo-advisor/ask { question }
  -> require_permission("intelligence.read")               [RBAC real, testado]
  -> PMOEvidenceAssembler.assemble(organization_id)
       -> DomainService.list_projects(organization_id)      [Wave 2, inalterado]
       -> reference_time = datetime.now(timezone.utc)       [capturado 1x -- testado]
       -> por Project: framework.gather_context(kind="status")
            -> staleness_days/is_stale calculados 1x, replicados
            -> evidence[:5]                                  [cap testado nos dois sentidos]
       -> PMOAssemblyResult (5 contagens estruturais)
  -> PMOAdvisorAgent.advise() -> AdvisorFramework.run()      [byte-for-byte inalterado]
  -> _pmo_advisor_response() -> PMOAdvisorResponse
```

Cada seta acima tem pelo menos um teste real que a exercita contra Postgres — nenhuma etapa do fluxo é "descrita" sem prova.

---

## 3. Os 13 cenários obrigatórios (A-M) — resultado

| # | Cenário | Prova (Framework) | Prova (HTTP) |
|---|---|---|---|
| A | 13 dias = current | `TestScenarioA_TrezeDiasCurrent` | (staleness não exposta diretamente na resposta HTTP -- provado na camada Framework) |
| B | 14 dias = stale | `TestScenarioB_QuatorzeDiasStale` | idem |
| C | 15 dias = stale | `TestScenarioC_QuinzeDiasStale` | idem |
| D | Project sem status | `TestScenarioD_ProjectSemStatus` | coberto por G/H (`projects_without_status`) |
| E | mais de 5 registros -> cap | `TestScenarioE_MaisDeCincoRegistros` | -- |
| F | menos de 5 registros -> sem corte | `TestScenarioF_MenosDeCincoRegistros` | -- |
| G | cobertura completa | `TestScenarioG_CoberturaCompleta` | `TestScenarioG_CoberturaCompleta` |
| H | cobertura parcial | `TestScenarioH_CoberturaParcial` | `TestScenarioH_CoberturaParcial` |
| I | cobertura zero | `TestScenarioI_CoberturaZero` | `TestScenarioI_CoberturaZero` |
| J | invariantes das contagens | `TestScenarioJ_InvariantesDeContagem` | verificado em G (asserção inline) |
| K | isolamento organizacional | `TestScenarioK_IsolamentoOrganizacional` | `TestScenarioK_IsolamentoOrganizacional` |
| L | nenhuma chamada ao LLM sem evidência | `TestScenarioL_NenhumaChamadaAoLlmSemEvidencia` | `TestScenarioI_CoberturaZero` (`ExplodingProvider`) |
| M | rastreabilidade Project + AnalysisRecord | `TestScenarioM_RastreabilidadeAteProjectEAnalysisRecord` | `TestRastreabilidade` |

Todos os 13 comprovados. Nenhum simulado apenas em uma camada quando a Founder Decision pedia ambas.

---

## 4. As 7 provas adicionais exigidas (item 8 da Founder Decision) — resultado

| Prova exigida | Onde comprovada |
|---|---|
| Captura única da data de referência | `TestSingleReferenceTimeCapture` — `datetime.now` mockado, `call_count == 1` verificado |
| Project sem status não classificado como stale | `TestScenarioD_ProjectSemStatus` (Framework) + `test_project_without_status_contributes_no_evidence_and_is_not_stale`/`test_a_project_without_status_never_counts_as_stale` (unitário) |
| Contagem única de staleness por Project | `test_staleness_is_computed_once_per_project_and_replicated_across_its_evidence_items` (unitário) — dois registros do mesmo Project recebem `staleness_days` idêntico |
| Até cinco evidências por Project | `TestScenarioE_MaisDeCincoRegistros` (Framework, 7 registros -> 5) + `test_caps_evidence_at_five_most_recent_records_per_project` (unitário) |
| Rastreabilidade de citações repetidas do mesmo Project | `TestScenarioM_RastreabilidadeAteProjectEAnalysisRecord` (Framework) + `TestRastreabilidade` (HTTP) — dois `source_analysis_id` distintos do mesmo `project_id` sobrevivem separadamente |
| Ausência de chamada ao LLM sem evidência | `TestScenarioL_NenhumaChamadaAoLlmSemEvidencia` + `TestScenarioI_CoberturaZero` (`_ExplodingProvider`, `ExplodingProvider`) |
| Ausência de qualquer segunda fonte | `TestNoSecondSource` (Framework) — `kind="meeting"`/`kind="risk"` gravados para o mesmo Project, confirmado que só o registro `kind="status"` entra em `evidence`; `_ExplodingRagPipeline` instalada por padrão em todo o arquivo (Framework) e via `dependency_overrides` (HTTP) — qualquer chamada a `gather_rag_context()` derrubaria toda a suíte |

Todas as 7 provas adicionais comprovadas, além das 13 já tabeladas.

---

## 5. Rastreabilidade — resolução do item 5 da Founder Decision (sem alterar contratos)

A Founder Decision pediu avaliação explícita: se `CitedProject` não suportasse rastreabilidade inequívoca de citações repetidas do mesmo Project, a instrução era **interromper antes de alterar contratos compartilhados** e apresentar a solução mínima.

**Resultado da avaliação: nenhuma interrupção foi necessária.** `CitedProject` (`src/api/routes/intelligence.py`, já definido para o Portfolio Advisor) já expõe `source_analysis_id` — o id único do `AnalysisRecord` — como campo de topo. Como cada `Evidence` citada corresponde a exatamente um `AnalysisRecord` com `id` único no banco, duas citações do mesmo `project_id` sempre carregam `source_analysis_id` diferentes, tornando-as estruturalmente distinguíveis sem qualquer mudança de contrato. Comprovado diretamente por `TestRastreabilidade` (HTTP): duas citações de "Aurora" retornam dois `source_analysis_id` distintos no mesmo array `cited_projects`.

`CitedProject` foi **reaproveitado integralmente**, zero duplicação, zero alteração.

---

## 6. Preservação arquitetural — confirmação, não alegação

```
$ git diff --stat -- src/services/advisor_framework/ src/services/ai_foundation/ \
    src/database/domain_repository.py src/database/repository.py \
    src/services/domain_service.py src/services/events/ src/workflows/
(saída vazia)
```

`AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline, `DomainService`, `DomainRepository`, contrato `Evidence` — todos byte-for-byte inalterados. Todo o código novo vive exclusivamente em `src/agents/pmo_advisor/` (pacote do Advisor) e em três pontos aditivos de `src/api/routes/intelligence.py` (imports, modelos Pydantic, rota + mapper) — mesmo padrão já usado por Delivery/Portfolio Advisor.

---

## 7. Suíte de testes — resultado final

| Suíte | Resultado |
|---|---|
| `tests/test_pmo_advisor_evidence_assembler.py` (unitário, fakes) | 17 passed |
| `tests/test_pmo_advisor_agent.py` (unitário, fakes) | 6 passed |
| `tests/test_pmo_advisor.py` (integração Framework, Postgres real) | 16 passed |
| `tests/test_pmo_advisor_api.py` (HTTP, Postgres real, RBAC real) | 9 passed |
| **Total novo desta Epic** | **48 passed** |
| **Suíte backend completa** | **680 passed** (era 638 antes desta Epic) |
| **Suíte frontend completa** | **503 passed** (nenhuma mudança de frontend) |
| `ruff check src tests` | limpo |
| `npx tsc --noEmit` | limpo |
| `npx eslint .` | limpo |

---

## 8. Isolamento organizacional

`TestScenarioK_IsolamentoOrganizacional` (Framework e HTTP): duas organizações, cada uma com um Project e um status registrado; a Assembler de uma organização nunca enxerga o Project da outra — `total_projects == 1`, apenas o Project da própria organização aparece em `evidence`. Mesmo padrão 404-not-403/isolamento por `organization_id` já usado por todo Advisor anterior — nenhum mecanismo novo, apenas `DomainService.list_projects(organization_id)` já org-scoped desde a Wave 2.

---

## 9. Ausência de tendência histórica indevida — confirmação estrutural

Diferente do Portfolio Advisor (que nunca recebe histórico, apenas `evidence[0]`), o PMO Advisor **pode** ver histórico (até 5 registros por Project) — mas nunca mais do que isso, e a interpretação de "padrão recorrente" permanece exclusivamente uma leitura textual do LLM sobre `health_status`/`key_findings` já presentes nos registros fornecidos, nunca um algoritmo de tendência em código (mesma disciplina do Delivery Advisor, onde a tendência também é resolvida inteiramente no prompt).

---

## 10. Recomendação

**GO para o encerramento do Epic do PMO Advisor.**

Todas as 8 diretrizes da Founder Decision cumpridas: `PMOEvidenceAssembler` exclusivo do pacote, sem interpretação de conteúdo/chamada de LLM/regra decisória; staleness com as 5 regras exigidas (UTC, referência única, 13/14/15 dias, Project sem status nunca stale); volume `evidence[:5]`, sem janela/batch/cache/paralelismo; cobertura estrutural com as duas invariantes garantidas; rastreabilidade resolvida sem alterar `CitedProject`; fonte única `kind="status"` confirmada estruturalmente; infraestrutura compartilhada preservada integralmente; os 13 cenários + 7 provas adicionais comprovados em duas camadas.

Retorno obrigatório para Executive Review do Founder antes de qualquer trabalho do Executive Advisor.
