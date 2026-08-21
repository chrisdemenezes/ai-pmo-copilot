# Technical Design — Package M: Learnings → Executive Intelligence

STRATECH V1 Product & Capability Completion (Founder Mandate), Fase 5.

## 1. Contexto real (audit, não hipótese)

- "Aprendizados" (`web/lib/organizational-intelligence/organizational-learnings.ts`)
  **não é uma entidade persistida** -- é uma view puramente derivada, calculada
  no frontend a partir de `GET /api/risks/latest`/`GET /api/action-items` já
  buscados: agrupa por igualdade textual exata de `description`, corta em 3+
  projetos distintos (`MIN_OCCURRENCES`), ordena por contagem desc então
  descrição asc, exibe no máximo 5. Não existe tabela `learnings` no backend.
- `AIContextEngine`/`AdvisorFramework` (`src/services/ai_foundation/`,
  `src/services/advisor_framework/`) já são os únicos pontos sancionados de
  acesso a evidência para todo Advisor -- `Evidence` (`source_type`,
  `source_id`, `source_label`, `content`, `metadata`) já é genérico o
  suficiente para um novo `source_type` sem qualquer mudança de schema.
- `ExecutiveOrchestrator`/`synthesize()` (Decision Support/Executive
  Narrative) tem uma restrição arquitetural explícita e repetida (Vision,
  Princípios 1/3/6/11): a Síntese consome exclusivamente as `Explanation`s
  já coletadas, **nunca `Evidence` bruta, nunca uma nova evidência de negócio**.
  Portanto Learnings nunca podem entrar pela Síntese -- só pelo caminho de
  evidência de um Advisor específico, antes da Síntese.
- `PMOAdvisorAgent`/`ExecutiveAdvisorAgent` são os dois únicos Advisors com
  escopo organization-wide (sem projeto/portfolio específico) -- exatamente o
  escopo de Decision Support/Executive Narrative quando a pergunta é sobre a
  organização inteira. Os dois já ligam `records_json` diretamente do array
  `evidence` recebido, com acesso posicional a chaves de `metadata`
  específicas de cada Advisor (nenhum dos dois tolera um item de formato
  diferente na mesma lista -- confirmado lendo `agent.py` de ambos).
- `RecommendationEngine.build()` monta `by_id = {item.source_id: item for
  item in evidence}` -- uma citação inventada por um `source_id` sintético
  correria risco real de colidir com um `AnalysisRecord.id` real (sempre
  positivo) se ambos compartilhassem a mesma lista `evidence`.

## 2. Decisão de design (por que não a integração óbvia)

A integração mais simples -- anexar Learnings como itens `Evidence` extras em
`PMOEvidenceAssembler`/`ExecutiveEvidenceAssembler`'s próprio `evidence` --
foi avaliada e **rejeitada**: quebraria imediatamente `agent.py` de ambos
(acesso posicional a `metadata["project_id"]` etc., que um item de Learning
não tem e não deveria fingir ter -- um Learning não é sobre um projeto só),
e arriscaria colisão de `source_id` dentro do mesmo `by_id` de citação.

**Decisão**: Learnings nunca entram em `evidence`/`cited_evidence`. Cada um
dos dois Advisors, dentro do próprio `advise()`, pede Learnings ao
`AdvisorFramework` (`gather_organizational_learnings()`) como uma variável de
prompt **separada** (`$learnings_json`), explicitamente rotulada no prompt
como contexto de apoio, nunca citável, nunca a base única de uma resposta.
Consequência: o Evidence Gate (`AdvisorFramework.run()`: `if not evidence`)
e todo campo de citação estruturado (`cited_projects`/`cited_evidence`)
continuam byte-a-byte como antes -- ausência ou presença de Learnings nunca
muda se um Advisor "tem evidência".

## 3. O que foi implementado

- `src/services/ai_foundation/organizational_learning.py` (novo): espelho
  deliberado, em Python, do mesmo algoritmo de `organizational-learnings.ts`
  (não é código compartilhado -- fronteira de linguagem -- mas é a mesma
  regra determinística, documentada como tal). Consome
  `ProjectSummaryService.list_latest_risks()`/`list_action_items()`
  verbatim -- zero query nova, zero tabela nova.
- `AIContextEngine.gather_organizational_learnings(organization_id)`: monta
  os dois grupos (risco/ação), aplica o corte de 3+, ordena, corta em 5,
  devolve `list[Evidence]` com `source_type="organizational_learning"` e
  `source_id` **negativo** (nunca colide com um `AnalysisRecord.id`, sempre
  positivo).
- `AdvisorFramework.gather_organizational_learnings()`: passthrough fino,
  mesma convenção de todo outro método ali.
- `src/agents/shared/organizational_learning_prompt.py`: serialização
  compartilhada (`learnings_json()`) entre os dois únicos Advisors que a
  usam -- não duplicada entre `pmo_advisor/agent.py`/`executive_advisor/agent.py`.
- `PMOAdvisorAgent.advise()`/`ExecutiveAdvisorAgent.advise()`: cada um chama
  `self.framework.gather_organizational_learnings(session.organization_id)`
  e passa `learnings_json=...` como variável adicional ao renderizar o
  próprio prompt -- `evidence`/`records_json` continuam exatamente como
  antes.
- `pmo_advisor/prompts/advise.md`/`executive_advisor/prompts/advise.md`:
  nova seção "Organizational Learnings", instruindo explicitamente o modelo
  a nunca citá-la via `cited_analysis_ids` e nunca usá-la como base única.

## 4. Preservação de contrato (mecânica, não afirmada)

- **Tenant Isolation**: `gather_organizational_learnings` nunca recebe nada
  além de `organization_id`; toda leitura (`list_latest_risks`/
  `list_action_items`) já escopa por `organization_id` internamente (mesma
  disciplina de todo outro método do Context Engine). Testado
  explicitamente (`TestGatherOrganizationalLearnings::
  test_learnings_are_scoped_by_organization_cross_tenant_impossible`).
- **Fail-closed / Evidence Gate**: nunca alterado -- Learnings nunca entram
  em `evidence`. Testado explicitamente em `test_pmo_advisor.py`/
  `test_executive_advisor.py` (`test_organizational_learnings_never_
  substitute_for_missing_status_...evidence`): 3+ projetos com o mesmo
  risco/ação recorrente (Learnings reais) e zero análises de status ->
  resposta ainda é "Nenhuma análise de status...", LLM nunca chamado
  (`_ExplodingProvider`).
- **Absence of Learnings never breaks Advisors**: organização sem nenhuma
  análise de risco/reunião -> `gather_organizational_learnings` retorna
  `[]` -> `learnings_json([])` = `"[]"` -> `Template.safe_substitute`
  preenche a variável normalmente, prompt válido, nenhum erro.
- **No fabricated evidence**: a regra de corte (3+ projetos distintos,
  igualdade textual exata) é idêntica à já aprovada para a página
  "Aprendizados" -- nenhum limiar novo, nenhuma interpretação nova.
- **No second parallel RAG**: zero uso de `RagPipeline`/embeddings/vector
  search -- Learnings vêm exclusivamente de `AnalysisRecord` já persistido,
  mesmo dado que "Aprendizados" já mostra.
- **Never a 9th Advisor**: nenhuma nova `AdvisorIdentity`, nenhuma mudança
  em `selection_rule.py`/`catalog.py` -- os dois Advisors existentes (PMO,
  Executive) continuam os únicos consumidores.

## 5. Testes (os 6 mandados)

1. Relevante incluído: `test_a_recurring_risk_across_3_projects_is_included`.
2. Irrelevante excluído: `test_a_risk_seen_in_only_2_projects_is_excluded`.
3. Cross-tenant impossível: `test_learnings_are_scoped_by_organization_cross_tenant_impossible`.
4. Organização sem Learnings: `test_organization_with_no_data_at_all_returns_no_learnings`.
5. Múltiplos Learnings: `test_caps_at_5_learnings_in_fixed_category_order_risks_before_actions`.
6. Insuficiência de evidência permanece fail-closed:
   `test_organizational_learnings_never_substitute_for_missing_status_evidence`
   (PMO) e o equivalente em `test_executive_advisor.py` (Executive).

Mais: 8 testes puros do algoritmo (`test_organizational_learning.py`, sem
banco, rodam localmente) e 2 testes de integração por Advisor provando que
`learnings_json` chega ao prompt corretamente (`test_pmo_advisor_agent.py`/
`test_executive_advisor_agent.py`).

## 6. Não-Escopo

- Nenhuma citação individual de um Learning (nunca aparece em
  `cited_projects`/`cited_evidence` -- é contexto, não fato citável).
- Nenhum Advisor além de PMO/Executive recebe Learnings (Risk/Delivery/
  Portfolio/Strategy são escopados a um projeto ou portfolio específico;
  Document/Governance são RAG-escopados -- nenhum dos dois combina
  naturalmente com um padrão cross-project).
- Nenhuma tabela `learnings` nova -- continua 100% derivado em tempo de
  leitura, dos e para os mesmos dados que "Aprendizados" já expõe.
