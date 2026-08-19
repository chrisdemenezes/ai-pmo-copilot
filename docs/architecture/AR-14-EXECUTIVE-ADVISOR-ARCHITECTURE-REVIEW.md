# AR-14 — Architecture Review do Executive Advisor

**Etapa 3 de 6** do ciclo institucional do Executive Advisor. Produzido sob autorização da Founder Decision que aprovou o Domain Blueprint (`DOMAIN-BLUEPRINT-EXECUTIVE-ADVISOR.md`) com **GO para a Architecture Review**, confirmando como oficiais: escopo organizacional; fontes exclusivas `kind="status"` + `kind="risk"`, cada Project contribuindo no máximo com o status mais recente e o risco mais recente; rejeição de `ProjectSummaryService` como fonte; rejeição de `gather_context_many()` neste Epic; `ExecutiveEvidenceAssembler` específico do pacote, não promovido a componente compartilhado; e delegando a esta etapa três decisões: modelo de citação (resolvendo o achado de `CitedProject` não carregar `kind`), cobertura estrutural (sete contagens), e tratamento de ausência/cobertura parcial. Nenhum código escrito nesta etapa.

---

## 0. O que já é oficial (não reaberto aqui)

1. Escopo organizacional, resolvido diretamente sobre os Projects da organização.
2. Fontes exclusivas: `AnalysisRecord`/`kind="status"` + `AnalysisRecord`/`kind="risk"` — no máximo um registro de cada por Project (o mais recente). Fora de escopo: `meeting`/`action_items`, RAG, documentos, respostas de outros Advisors, histórico completo.
3. `ProjectSummaryService` **não é usado** como fonte — composição direta sobre `AnalysisRecord`, preservando `source_id`/`project_id`/`organization_id`/`created_at`/rastreabilidade individual.
4. `gather_context_many()` **não implementado** neste Epic — o `ExecutiveEvidenceAssembler` executa explicitamente `gather_context(kind="status")` e `gather_context(kind="risk")`. Nenhuma alteração a `AdvisorFramework`/`AIContextEngine` autorizada.
5. `ExecutiveEvidenceAssembler` específico do pacote do Executive Advisor — não promovido a componente compartilhado nesta etapa.

---

## 1. Executive Summary

Esta Architecture Review resolve as três questões explicitamente delegadas pela Founder Decision sobre o Domain Blueprint, todas com base em capacidades já existentes no código, sem estender nenhum contrato compartilhado:

- **Modelo de citação**: um novo modelo de resposta específico do Executive Advisor — `ExecutiveCitedEvidence` (`project_id`, `project_name`, `source_analysis_id`, `kind`, `created_at`) — resolve a rastreabilidade por `kind` sem tocar `CitedProject`, que permanece exatamente como está, servindo Portfolio/PMO Advisor sem nenhuma alteração. `kind` já existe em `Evidence.metadata["kind"]`, preenchido por `AIContextEngine.gather()` desde sempre — nenhum campo novo em nenhum contrato compartilhado.
- **Cobertura estrutural**: sete contagens, todas calculadas pelo `ExecutiveEvidenceAssembler`, nunca pelo LLM — quatro delas espelhando exatamente o padrão já provado em PMO Advisor (pares "com"/"sem" por dimensão), mais três novas exigidas pela combinação de duas dimensões independentes (`projects_with_status_and_risk`, `projects_without_any_evidence`).
- **Ausência e cobertura parcial**: ausência total (nenhum Project da organização tem status nem risco) aciona `no_evidence()`, mesmo portão anti-alucinação já em produção, zero chamada ao LLM. Cobertura parcial **permite síntese** — mesmo comportamento já em produção no Portfolio/PMO Advisor (que sempre sintetizam a partir do que existe, nunca exigindo 100% de cobertura) — mas a resposta deve declarar explicitamente a limitação, usando as contagens estruturais já calculadas, nunca inventando uma generalização para Projects sem evidência.

**Recomendação: GO para o Technical Design.**

---

## 2. Decisão sobre o modelo de citação

### 2.1 O achado, confirmado

`CitedProject` (`src/api/routes/intelligence.py`, reaproveitado sem alteração por Portfolio Advisor e PMO Advisor: `project_id`, `project_name`, `source_analysis_id`, `source_created_at`) não carrega `kind`. Como o Executive Advisor pode citar, para o mesmo Project, uma evidência de `kind="status"` e outra de `kind="risk"`, as duas citações seriam indistinguíveis em `CitedProject` — a única forma de saber qual é qual seria consultar o banco pelo `source_analysis_id`, quebrando a promessa de que a resposta HTTP já é autoexplicativa.

### 2.2 Decisão

**Novo modelo específico do Executive Advisor**, exatamente na forma já sugerida pela Founder Decision:

```
ExecutiveCitedEvidence {
    project_id: int
    project_name: str
    source_analysis_id: int
    kind: str
    created_at: datetime
}
```

`CitedProject` **não é alterado** — permanece com sua forma atual, servindo exclusivamente Portfolio/PMO Advisor, sem nenhuma mudança de comportamento ou assinatura.

### 2.3 Confirmações exigidas pela Founder Decision

- **Origem do `kind`**: já existe, sem nenhum código novo — `AIContextEngine.gather(organization_id, project_name, kind)` (`context_engine.py`) já preenche `Evidence.metadata["kind"] = kind` para todo `Evidence` retornado, confirmado por leitura direta do código (mesmo trecho já citado no Domain Blueprint §9.1). `ExecutiveCitedEvidence.kind` é uma leitura direta de `item.metadata["kind"]`, nenhum campo inventado.
- **Compatibilidade**: total — `ExecutiveCitedEvidence` é um modelo Pydantic novo, isolado, usado exclusivamente pela resposta do Executive Advisor (`ExecutiveAdvisorResponse`, nome provisório do Technical Design). Nenhuma classe existente é modificada.
- **Ausência de impacto nos Advisors existentes**: confirmada por construção — como `CitedProject` permanece intocado, `PortfolioAdvisorResponse` e `PMOAdvisorResponse` (ambos já em produção) continuam exatamente como estão, `git diff` vazio esperado em ambos.
- **Retorno somente das evidências efetivamente citadas**: mesmo mecanismo já provado em todos os Advisors anteriores — a lista de `ExecutiveCitedEvidence` é construída a partir de `explanation.recommendation.cited_evidence` (já filtrado por `RecommendationEngine.build()` por associação `source_id`), nunca da lista completa de evidência montada — apenas o que o LLM efetivamente citou aparece na resposta.

---

## 3. Contrato do `ExecutiveEvidenceAssembler`

Descrito em termos de responsabilidade e forma — o código de referência completo é responsabilidade do Technical Design (etapa 4), não desta etapa.

### 3.1 Responsabilidade

- Resolver os Projects da organização (`DomainService.list_projects(organization_id)`, sem traversal Portfolio/Program).
- Para cada Project: chamar `framework.gather_context(organization_id, project.name, kind="status")` e `framework.gather_context(organization_id, project.name, kind="risk")` — duas chamadas explícitas e independentes, nunca uma chamada genérica.
- Capturar apenas o item mais recente de cada `kind` (`evidence[0]` de cada chamada) — nunca histórico, mesma garantia estrutural de `AnalysisRepository.list_analyses()` já usada por todos os Advisors baseados em `AnalysisRecord`.
- Enriquecer `Evidence.metadata` com `project_id`/`project_name` (mesmo padrão de Portfolio/PMO Advisor) — `kind` já vem preenchido, nenhum enriquecimento adicional necessário para essa dimensão.
- Calcular as sete contagens de cobertura estrutural (§4) — nunca pelo LLM.
- Nunca interpretar conteúdo, nunca chamar o LLM, nunca aplicar regra decisória — mesma disciplina permanente de todo componente de composição desde o primeiro Advisor Classe B.

### 3.2 Entrada e saída (forma, não implementação)

- **Entrada**: `organization_id: int`.
- **Saída**: uma estrutura de resultado (nome definitivo reservado ao Technical Design, ex.: `ExecutiveAssemblyResult`) contendo, no mínimo: a lista consolidada de `Evidence` (até 2 itens por Project — um de cada `kind`, quando existentes) e as sete contagens estruturais (§4), todas já calculadas.

### 3.3 Localização

`src/agents/executive_advisor/evidence_assembler.py` — exclusivo do pacote do Advisor, confirmando §5 do Domain Blueprint: não promovido a componente compartilhado nesta etapa.

---

## 4. Cobertura estrutural

Sete contagens, todas calculadas pelo `ExecutiveEvidenceAssembler`, nunca pelo LLM — quatro delas seguindo exatamente o padrão de pares já provado no PMO Advisor, três novas exigidas pela combinação de duas dimensões.

| Campo | Definição | Relação |
|---|---|---|
| `total_projects` | Todos os Projects da organização | — |
| `projects_with_status` | Projects com `AnalysisRecord`/`kind="status"` | ⊆ `total_projects` |
| `projects_without_status` | `total_projects - projects_with_status` | `projects_with_status + projects_without_status = total_projects` |
| `projects_with_risk` | Projects com `AnalysisRecord`/`kind="risk"` | ⊆ `total_projects` |
| `projects_without_risk` | `total_projects - projects_with_risk` | `projects_with_risk + projects_without_risk = total_projects` |
| `projects_with_status_and_risk` | Interseção — Projects com **ambos** | ⊆ `projects_with_status` ∩ `projects_with_risk` |
| `projects_without_any_evidence` | Projects sem status **e** sem risco (a única categoria de "zero cobertura" real) | `total_projects - (projects_with_status ∪ projects_with_risk)` |

**Distinção explícita, mesma disciplina já usada em PMO Advisor:** as duas dimensões (status/risco) são independentes — um Project pode estar em `projects_with_status` e simultaneamente em `projects_without_risk`. Nenhuma das sete contagens é combinada em uma única métrica "com evidência"/"sem evidência" genérica, porque isso esconderia qual das duas fontes está faltando para um Project específico.

**Invariante adicional a testar no Technical Design**: `projects_with_status_and_risk ≤ min(projects_with_status, projects_with_risk)`, e `projects_without_any_evidence ≤ min(projects_without_status, projects_without_risk)` — ambas consequências matemáticas diretas da definição por conjuntos, verificáveis estruturalmente, nunca calculadas por regra separada que possa divergir.

---

## 5. Tratamento de ausência e cobertura parcial

### 5.1 Ausência total

Quando `projects_without_any_evidence == total_projects` (nenhum Project da organização tem status **nem** risco) — a lista de `Evidence` está vazia, aciona `no_evidence()`, **zero chamada ao LLM**. Mesmo portão anti-alucinação já em produção desde o Risk Advisor, reaplicado sem nenhuma extensão.

### 5.2 Cobertura parcial

**Síntese permitida** — mesmo comportamento já em produção no Portfolio Advisor e no PMO Advisor, nenhum dos quais exige 100% de cobertura para responder. Sempre que existir pelo menos um item de `Evidence` (de qualquer `kind`, de qualquer Project), o Executive Advisor sintetiza a partir do que está disponível.

**Limitação explicitada, obrigatória**: o prompt (Technical Design, não decidido aqui) deve instruir o modelo a declarar, na própria resposta, que a síntese é baseada apenas nos Projects com evidência disponível — usando as contagens estruturais já calculadas (§4) como fato pronto, nunca deixando o LLM estimar ou generalizar silenciosamente para os Projects sem evidência. Mesma disciplina já aplicada à ausência de tendência histórica no Portfolio/PMO Advisor: a limitação é garantida estruturalmente (as contagens existem e são precisas) e reforçada textualmente (o prompt instrui a declará-la), nunca inventada pelo modelo.

### 5.3 Cobertura completa

Quando `projects_without_any_evidence == 0` — nenhuma limitação a declarar; mesma síntese, sem ressalva estrutural.

---

## 6. Limites reafirmados (item 9 da Founder Decision)

- Nunca afirma tendência histórica — estruturalmente garantido, apenas o registro mais recente de cada `kind` chega ao prompt (Domain Blueprint §7.1/§7.2).
- Nunca substitui Risk Advisor (análise especializada de risco), PMO Advisor (conformidade de processo/staleness) ou Portfolio Advisor (composição/equilíbrio de um portfólio específico).
- **Nunca calcula ranking determinístico** — nenhum algoritmo de ordenação por severidade/criticidade é aplicado pelo `ExecutiveEvidenceAssembler` ou pela rota; qualquer noção de "quais Projects exigem mais atenção" é interpretação do próprio LLM sobre o conjunto de evidências fornecido, nunca um cálculo em código — mesma disciplina já aplicada a "ordem não implica prioridade" no Portfolio Advisor (AR-12 §3), estendida aqui explicitamente a qualquer forma de ranking.
- Nunca consome `Recommendation`/`Explanation` de outro Advisor.
- Nunca orquestra outros Advisors — `AdvisorFramework.run()` executa exatamente um Advisor por chamada, restrição permanente desde a Fase 3.

---

## 7. Preservação de infraestrutura — confirmação

Nenhuma das decisões desta etapa exige mudança de assinatura ou comportamento em:

- `AdvisorFramework.gather_context()`/`run()` — o `ExecutiveEvidenceAssembler` chama `gather_context()` duas vezes por Project (uma por `kind`), exatamente a forma já suportada hoje.
- `AIContextEngine.gather()` — inalterado; `kind` já é parâmetro existente, `Evidence.metadata["kind"]` já preenchido.
- `RecommendationEngine`/`ExplanationEngine` — nenhuma extensão; `Evidence` permanece o contrato genérico já evoluído em AR-9, enriquecido apenas via `metadata`.
- Workflow Runtime/Event Pipeline — não incidem, mesma restrição permanente de todos os Advisors.
- Contrato `Evidence` — inalterado.
- Contratos dos Advisors existentes (`CitedProject`, `PortfolioAdvisorResponse`, `PMOAdvisorResponse`, etc.) — inalterados; `ExecutiveCitedEvidence` é um modelo novo e isolado (§2), nunca uma modificação de contrato compartilhado.

---

## 8. Riscos residuais

| Risco | Origem | Mitigação registrada |
|---|---|---|
| Volume de chamadas dobrado em relação ao PMO Advisor para a mesma organização | Já registrado no Domain Blueprint §7.5 | Mesmo gatilho de performance já aprovado (20+ chamadas sequenciais ou p95 > 3s), atenção adicional mantida, nenhuma otimização antecipada |
| Sete contagens estruturais aumentam a superfície de teste em relação aos Advisors anteriores | Consequência direta de duas dimensões independentes | Invariantes matemáticas explícitas registradas (§4), verificáveis estruturalmente no Technical Design |
| Nome definitivo dos componentes (`ExecutiveEvidenceAssembler`, `ExecutiveCitedEvidence`, `ExecutiveAssemblyResult`) ainda provisório | Convenção de nomenclatura | Confirmar no Technical Design |

Nenhum risco listado é bloqueante para o Technical Design.

---

## 9. Critérios de sucesso

Herdados do Domain Blueprint, reafirmados, mais os específicos desta etapa:

- Toda citação retornada carrega `project_id`/`project_name`/`source_analysis_id`/`kind`/`created_at`, sempre rastreável a um `AnalysisRecord` real.
- Duas citações do mesmo Project em `kind`s diferentes permanecem distinguíveis na resposta HTTP, sem exigir consulta adicional ao banco.
- As sete contagens de cobertura sempre estruturais, nunca calculadas pelo LLM; invariantes aritméticas verificadas em todo teste.
- Ausência total aciona `no_evidence()` sem chamada ao LLM; cobertura parcial sempre sintetiza com limitação declarada.
- Nenhuma citação de `Recommendation`/`Explanation`/resposta de outro Advisor.
- Nenhum ranking determinístico calculado em código.
- `git diff --stat` vazio em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline/contrato `Evidence`/`CitedProject` ao final da implementação.

---

## 10. Recomendação

**GO para o Technical Design do Executive Advisor.**

Questões resolvidas nesta etapa, oficiais a partir de agora: modelo de citação (`ExecutiveCitedEvidence`, novo, isolado, `CitedProject` intocado); cobertura estrutural (sete contagens, invariantes explícitas); tratamento de ausência (no_evidence, zero LLM) e cobertura parcial (síntese permitida com limitação declarada); limite adicional confirmado (nenhum ranking determinístico em código).

Questões reservadas ao Technical Design, não decididas aqui: nomes definitivos dos componentes; contrato completo de código (assinaturas, corpo de referência); estrutura do prompt; estratégia de teste completa (cenários obrigatórios).
