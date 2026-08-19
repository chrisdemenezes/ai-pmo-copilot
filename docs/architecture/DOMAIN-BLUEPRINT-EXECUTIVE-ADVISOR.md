# Domain Blueprint — Executive Advisor

**Etapa 2 de 6** do ciclo institucional do Executive Advisor. Produzido sob autorização da Founder Decision que aprovou a Advisor Specification (`ADVISOR-SPECIFICATION-EXECUTIVE-ADVISOR.md`) com **GO para o Domain Blueprint**, fixando como oficiais: Classe B com fontes iniciais `kind="status"` + `kind="risk"`; escopo organizacional a avaliar; seis fontes explicitamente fora de escopo inicial; identidade definitiva ("o que exige atenção ou decisão da liderança agora, considerando execução e risco?"); avaliação obrigatória de `ProjectSummaryService` e de `gather_context_many()`, ambas sem aprovação automática. Nenhum código escrito nesta etapa.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Classe B, fontes iniciais `AnalysisRecord`/`kind="status"` + `kind="risk"` | Advisor Specification + Founder Decision |
| Fora de escopo inicial: `meeting`/`action_items`, RAG/Knowledge Platform, documentos de governança, `Recommendation`, `Explanation`, respostas de outros Advisors | Founder Decision |
| Identidade: "o que exige atenção ou decisão da liderança agora, considerando execução e risco?" — nunca substitui PMO/Portfolio Advisor, nunca analisa risco especializado, nunca verifica governança, nunca analisa documentos, nunca orquestra Advisors | Founder Decision |
| Rota deve permanecer fina; decisões de composição nunca migram para `AdvisorFramework`/`AIContextEngine` | Founder Decision |
| Preservação integral de `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline nesta etapa | Founder Decision |

---

## 1. Executive Summary

Este Domain Blueprint resolve as quatro questões que a Founder Decision delegou explicitamente: escopo organizacional; componente de composição; reaproveitamento de `ProjectSummaryService`; e necessidade real de `gather_context_many()`.

**Escopo**: organizacional, resolvido via `DomainService.list_projects(organization_id)`, mesmo mecanismo já usado pelo PMO Advisor — sem traversal por Portfolio/Program, sem caso de 404 (a organização da sessão sempre existe).

**`ProjectSummaryService`: avaliado e rejeitado como fonte de evidência**, por não passar no próprio teste que a Founder Decision definiu (item 6). `summarize()`/`summarize_portfolio()`/`_aggregate()` retornam apenas contagens agregadas (`open_risks: int`, `latest_health_status: str`) — **nenhum `source_id` por item**, portanto sem rastreabilidade individual, desqualificado estruturalmente. `list_latest_risks()` **passa** no teste de rastreabilidade (`source_analysis_id`/`project_id`/`project_name`/`source_created_at` presentes), mas está fixado a exatamente um risco mais recente por projeto (sem parametrização de volume) e é código de produção que já serve a UI ("Riscos Brief") — reaproveitá-lo acoplaria o Executive Advisor a mudanças futuras motivadas por necessidades de UI, não de evidência executiva. `list_action_items()` passa no teste de rastreabilidade mas é `kind="meeting"`, explicitamente fora de escopo (item 3). **Recomendação: composição direta via `AnalysisRecord`**, mesmo padrão já usado por Portfolio/PMO Advisor.

**`gather_context_many()`: avaliado e rejeitado nesta etapa.** Duas chamadas explícitas (`gather_context(kind="status")` + `gather_context(kind="risk")`) por Project, dentro do próprio componente de composição do Executive Advisor, resolvem o requisito sem nenhuma mudança de `AdvisorFramework`/`AIContextEngine` — exatamente a extensão que AR-8 §3 já havia condicionado a "um Advisor real da Classe B demonstrar essa necessidade", e essa necessidade não está demonstrada: duas chamadas em Python dentro do laço já existente resolvem o problema por completo.

**Componente de composição**: `ExecutiveEvidenceAssembler` (nome provisório, a confirmar no Technical Design), `src/agents/executive_advisor/evidence_assembler.py`, exclusivo do pacote do Advisor — terceiro componente de composição Classe B, estruturalmente distinto de `PortfolioEvidenceAssembler` e `PMOEvidenceAssembler` (dois `kind`s por Project, cada um capturando apenas o registro mais recente — nunca histórico), confirmando que a generalização continua não sendo o caso mesmo com um terceiro consumidor real (D-118).

**Volume**: exatamente 1 registro de status mais recente e 1 registro de risco mais recente por Project — nunca histórico. Justificado diretamente pela própria identidade do Advisor definida pela Founder Decision ("agora", não "ao longo do tempo") — diferente do PMO Advisor, que precisa de histórico para detectar padrões recorrentes, tarefa explicitamente vedada ao Executive Advisor (item 4).

**Rastreabilidade**: achado que exige decisão do Technical Design, não desta etapa — `CitedProject` (reaproveitado sem alteração por Portfolio/PMO Advisor) **não carrega `kind`**, e a rastreabilidade exigida pela Founder Decision (item 9) inclui `kind` explicitamente. Registrado como questão aberta (§9), não decidido aqui.

**Recomendação: GO para a Architecture Review.**

---

## 2. Modelo de domínio

### 2.1 Unidade de composição

**Project**, mesma restrição estrutural já aplicada a Portfolio/PMO Advisor: `AnalysisRecord` só se associa a `project_id`, nunca a Portfolio/Program diretamente.

### 2.2 Dimensão nova: dois `kind`s independentes por Project

Diferente de todos os Advisors anteriores (que consomem exatamente um `kind`), o Executive Advisor consome **dois** — `status` e `risk` — como dimensões independentes da mesma unidade (Project). Um Project pode ter: ambos, apenas um, ou nenhum. Isso exige um modelo de cobertura em duas dimensões (§7), não uma única contagem como PMO Advisor.

### 2.3 O que cada `Evidence` representa

Cada item de `Evidence` corresponde a **um `AnalysisRecord`** (o mais recente de um `kind`, para um Project) — nunca um agregado. `Evidence.metadata["kind"]` já vem preenchido por `AIContextEngine.gather()` (`context_engine.py`: `metadata={"created_at": record.created_at, "kind": kind}`, confirmado por leitura de código) — nenhum campo novo necessário para saber se uma evidência é de status ou de risco.

---

## 3. Fontes definitivas desta etapa

| Fonte | Status |
|---|---|
| `AnalysisRecord`/`kind="status"` | Confirmada (Advisor Specification + Founder Decision) |
| `AnalysisRecord`/`kind="risk"` | Confirmada (Advisor Specification + Founder Decision) |
| `kind="meeting"`/`action_items` | Fora de escopo inicial — instrução explícita |
| Knowledge Platform/RAG | Fora de escopo inicial — instrução explícita |
| Documentos de governança | Fora de escopo inicial — instrução explícita |
| `Recommendation`/`Explanation`/respostas de outros Advisors | Proibido permanentemente |

Qualquer inclusão futura exige caso de uso executivo real demonstrado — não presumida nesta ou em nenhuma etapa futura sem evidência concreta.

---

## 4. Escopo de resolução

**Organizacional**, via `DomainService.list_projects(organization_id, program_id=None)` — idêntico ao mecanismo já usado pelo PMO Advisor, sem traversal Portfolio→Program, sem caso de 404 (a organização da sessão sempre existe). Reutilizado sem nenhuma extensão.

A síntese executiva é construída diretamente sobre os Projects da organização — nunca sobre um Portfolio específico (isso permaneceria exclusivo do Portfolio Advisor caso um caso de uso real o exigisse no futuro, não decidido aqui).

---

## 5. Componente de composição

### 5.1 Nome e localização (provisórios, a confirmar no Technical Design)

`ExecutiveEvidenceAssembler`, `src/agents/executive_advisor/evidence_assembler.py` — exclusivo do pacote do Advisor, mesmo padrão já estabelecido por `PortfolioEvidenceAssembler`/`PMOEvidenceAssembler`. Nunca em `src/services/`.

### 5.2 Responsabilidade

- Resolver os Projects da organização (`DomainService.list_projects`).
- Para cada Project: chamar `framework.gather_context(organization_id, project.name, kind="status")` e `framework.gather_context(organization_id, project.name, kind="risk")` — duas chamadas explícitas, nunca uma chamada genérica ao Framework (§8).
- Capturar apenas o item mais recente de cada `kind` (`evidence[0]`, mesma garantia estrutural de `list_analyses()` já usada por Portfolio Advisor) — nunca histórico.
- Enriquecer `Evidence.metadata` com `project_id`/`project_name` (mesmo padrão já usado por Portfolio/PMO Advisor).
- Calcular contagens de cobertura estruturais em duas dimensões (§7) — nunca pelo LLM.
- Entregar a lista consolidada de `Evidence` ao `AdvisorFramework.run()` — nunca chama o LLM diretamente, nunca interpreta conteúdo, nunca aplica regra decisória.

### 5.3 Rota permanece fina

`POST /executive-advisor/ask` segue exatamente o mesmo formato já estabelecido: injeta dependências, instancia `ExecutiveEvidenceAssembler`, chama `.assemble()`, instancia o Agent, chama `framework.run()`, mapeia a resposta — nenhuma lógica de composição na rota, nenhuma decisão de negócio na rota.

---

## 6. Decisão sobre `ProjectSummaryService`

### 6.1 Teste aplicado (os critérios da própria Founder Decision, item 6)

Para cada método candidato: preserva evidência primária? preserva `source_id`? preserva `project_id`? preserva `organization_id`? preserva `created_at`? rastreabilidade completa?

| Método | Evidência primária | `source_id` por item | `project_id` | `created_at` | Veredito |
|---|---|---|---|---|---|
| `summarize()`/`summarize_portfolio()`/`_aggregate()` | Não — apenas contagens agregadas (`open_risks: int`, `latest_health_status: str`) | **Ausente** | Presente (nível de resumo, não de item) | Ausente | **Reprovado** — sem rastreabilidade individual, nenhum `AnalysisRecord` específico pode ser citado |
| `list_action_items()` | Sim, por item | Presente (`source_analysis_id`) | Presente | Presente (`source_created_at`) | Estruturalmente aprovado, mas `kind="meeting"` — **fora de escopo por instrução explícita (item 3)** |
| `list_latest_risks()` | Sim, por item | Presente (`source_analysis_id`) | Presente | Presente (`source_created_at`) | Estruturalmente aprovado, mas ver §6.2 |

`organization_id` não é armazenado como campo por item em nenhum método — mas isso não é uma falha: é o mesmo padrão já aceito em todos os Advisors anteriores (o escopo organizacional é implícito na chamada, nunca replicado por `Evidence`).

### 6.2 Por que `list_latest_risks()`, mesmo aprovado no teste de rastreabilidade, não é reaproveitado

Duas razões, nenhuma delas "conveniência":

1. **Fixado a exatamente um risco mais recente por projeto**, sem parametrização — coincide com o volume que este Domain Blueprint já define para o Executive Advisor (§7), mas por acidente, não por design; qualquer mudança futura no volume esperado do Executive Advisor exigiria bifurcar o método ou alterar seu comportamento para outro consumidor (a "Riscos Brief" da UI), risco de acoplamento indevido.
2. **É código de produção que já serve diretamente uma superfície de UI existente.** Reaproveitá-lo tornaria o Executive Advisor dependente de decisões futuras de UI (ex.: se o "Riscos Brief" precisar mostrar 2 riscos mais recentes em vez de 1, ou mudar sua regra de dedup) sem que isso tenha qualquer relação com a necessidade do Executive Advisor.

### 6.3 Decisão

**Composição direta via `AnalysisRecord`**, chamando `AdvisorFramework.gather_context()` diretamente (§5.2) — nenhum reaproveitamento de `ProjectSummaryService`. Consistente com o próprio critério da Founder Decision: "caso contrário, recomendar composição direta via `AnalysisRecord`".

---

## 7. Estratégia de volume

### 7.1 Número máximo de status por Project

**1** — apenas o `AnalysisRecord`/`kind="status"` mais recente (`evidence[0]`, mesma garantia estrutural de `list_analyses()` ordenando por `created_at DESC`). Justificativa: a identidade do Advisor, definida pela própria Founder Decision, é uma pergunta de **estado atual** ("agora"), não de trajetória — trajetória e padrão recorrente pertencem exclusivamente a Delivery Advisor (um projeto) e PMO Advisor (organização), ambos explicitamente fora do papel do Executive Advisor (item 4). Usar apenas o registro mais recente torna estruturalmente impossível ao Executive Advisor alegar uma tendência — mesma disciplina já usada pelo Portfolio Advisor.

### 7.2 Número máximo de riscos por Project

**1** — apenas o `AnalysisRecord`/`kind="risk"` mais recente. Mesma justificativa de §7.1: o registro de risco mais recente já contém, em seu próprio `content.risks`, a lista completa de riscos identificados naquela análise — não é necessário histórico de múltiplas análises de risco para responder "quais riscos exigem atenção agora".

### 7.3 Quantidade esperada de Projects

Toda a organização (escopo organizacional, §4) — mesma ordem de grandeza já enfrentada pelo PMO Advisor, mas com o dobro de chamadas por Project (dois `kind`s em vez de um).

### 7.4 Tratamento de cobertura parcial

Cobertura estrutural em **duas dimensões independentes**, cada uma seguindo a mesma disciplina já provada em PMO Advisor:

| Campo | Definição |
|---|---|
| `total_projects` | Todos os Projects da organização |
| `projects_with_status` | Projects com `AnalysisRecord`/status | 
| `projects_without_status` | `total_projects - projects_with_status` |
| `projects_with_risk` | Projects com `AnalysisRecord`/risco |
| `projects_without_risk` | `total_projects - projects_with_risk` |

Um Project pode aparecer em `projects_with_status` e `projects_without_risk` simultaneamente (ou qualquer outra combinação) — as duas dimensões são independentes, nunca combinadas em uma única contagem "com evidência"/"sem evidência", porque isso esconderia qual das duas fontes está faltando. O modelo de resposta completo (nomes de campo definitivos) é decisão do Technical Design, não desta etapa.

### 7.5 Gatilhos de performance

Mesmo gatilho já aprovado para Portfolio/PMO Advisor, reafirmado sem alteração: 20+ chamadas sequenciais por montagem, ou p95 real acima de 3 segundos. **Atenção adicional registrada, não um novo gatilho**: como o Executive Advisor faz duas chamadas por Project (status + risco) contra uma do PMO Advisor, o mesmo limiar numérico de "20+ chamadas" é alcançado com aproximadamente metade do número de Projects — sinalizado para acompanhamento, sem justificar otimização antecipada.

---

## 8. Decisão sobre `gather_context_many()`

### 8.1 O que a Founder Decision pede comparar

**A.** Duas chamadas explícitas no assembler: `gather_context(kind="status")` + `gather_context(kind="risk")`.
**B.** Novo `gather_context_many(kinds: list[str])` no `AdvisorFramework`/`AIContextEngine`.

### 8.2 Avaliação pelos critérios exigidos

| Critério | Opção A (duas chamadas) | Opção B (`gather_context_many()`) |
|---|---|---|
| Contrato mínimo | Zero mudança de assinatura em qualquer componente compartilhado | Nova assinatura pública em `AdvisorFramework`/`AIContextEngine` |
| Ausência de lógica de composição no Framework | Composição (o que fazer com os dois resultados) permanece 100% no `ExecutiveEvidenceAssembler` | Mesmo que `gather_context_many()` apenas agregasse listas, introduziria a primeira noção de "múltiplos `kind`s" dentro do Engine — um passo em direção a conhecer vocabulário de domínio |
| Compatibilidade | Nenhum risco — mecanismo já usado por todos os Advisors Classe B anteriores | Precisaria ser aditiva (novo método, não substituição) para não quebrar nada — viável, mas desnecessária |
| Necessidade real | **Não demonstrada** — duas chamadas em Python resolvem o problema hoje, sem nenhuma limitação encontrada | Nenhum caso de uso real hoje que a chamada dupla não resolva |
| Ausência de generalização prematura | Sim — nada generalizado | Geraria uma abstração para um único consumidor real (o próprio Executive Advisor), exatamente o padrão que AR-8 §3 condicionou a uma necessidade real futura, ainda não chegada |

### 8.3 Decisão

**Opção A.** `gather_context_many()` **não está justificado nesta etapa** — nem "automaticamente aprovado" nem necessário. AR-8 §3 já havia registrado essa extensão como possível apenas "caso um Advisor real da Classe B demonstre essa necessidade" — o Executive Advisor, sendo Classe B com dois `kind`s, é o primeiro cenário que poderia demonstrá-la, mas a demonstração real seria "duas chamadas explícitas não bastam", o que não é o caso: bastam. `AdvisorFramework`/`AIContextEngine` permanecem preservados integralmente, conforme exigido (item 10).

---

## 9. Rastreabilidade

### 9.1 O que já é garantido, sem nenhuma mudança de contrato

- **Project**: `Evidence.metadata["project_id"]`/`["project_name"]`, enriquecimento aditivo (mesmo padrão de Portfolio/PMO Advisor).
- **`kind`**: `Evidence.metadata["kind"]`, já preenchido por `AIContextEngine.gather()` sem nenhuma mudança — confirmado por leitura de código.
- **`AnalysisRecord`**: `Evidence.source_id`, campo de topo já existente desde AR-9.
- **timestamp**: `Evidence.metadata["created_at"]`, já preenchido por `AIContextEngine.gather()`.
- **organização**: implícita no escopo da sessão (`organization_id`), mesmo padrão de todos os Advisors anteriores — nunca replicada por `Evidence`.

### 9.2 Achado que exige decisão do Technical Design (não decidido aqui)

`CitedProject` (`src/api/routes/intelligence.py`, já reaproveitado sem alteração por Portfolio/PMO Advisor: `project_id`, `project_name`, `source_analysis_id`, `source_created_at`) **não carrega `kind`**. Como a rastreabilidade exigida por esta Founder Decision (item 9) inclui explicitamente `kind`, e o Executive Advisor é o primeiro Advisor cujas citações podem ser de dois `kind`s diferentes para o mesmo Project (uma citação de status e uma de risco do mesmo Project seriam indistinguíveis em `CitedProject` sem esse campo), há duas soluções candidatas, nenhuma decidida aqui:

1. Um novo modelo de resposta específico do Executive Advisor (não reaproveitando `CitedProject`), evitando qualquer alteração a um contrato compartilhado — consistente com a disciplina já aplicada no Technical Design do PMO Advisor ("interromper antes de alterar contratos compartilhados").
2. Estender `CitedProject` com um campo `kind` — tecnicamente aditivo (Pydantic permite), mas afetaria o contrato também usado por Portfolio/PMO Advisor, exigindo avaliação própria antes de ser feito.

Nenhuma das duas é decidida nesta etapa — reservado ao Technical Design, mesma disciplina de nunca alterar um contrato compartilhado silenciosamente.

---

## 10. Limites de atuação (reafirmados, específicos desta Epic)

- Nunca substitui PMO Advisor (conformidade de processo/staleness/padrões) nem Portfolio Advisor (composição/equilíbrio de um portfólio específico).
- Nunca executa análise especializada de risco (permanece exclusivo do Risk Advisor) — o Executive Advisor lê o `AnalysisRecord`/risco já existente, nunca produz uma nova avaliação de risco.
- Nunca verifica governança nem analisa documentos (Governance/Document Advisor).
- Nunca orquestra outros Advisors — `AdvisorFramework.run()` executa exatamente um Advisor por chamada, restrição permanente desde a Fase 3.
- Nunca afirma tendência histórica, organizacional ou por projeto — estruturalmente impossível, já que apenas o registro mais recente de cada `kind` chega ao prompt (§7.1/§7.2).

---

## 11. Riscos

| Risco | Natureza | Mitigação registrada |
|---|---|---|
| Volume de chamadas dobrado em relação ao PMO Advisor para a mesma organização | Comprovado (fato estrutural: dois `kind`s × N projects) | Mesmo gatilho de performance já aprovado, atenção adicional registrada (§7.5), nenhuma otimização antecipada |
| `CitedProject` não suporta rastreabilidade por `kind` | Comprovado (leitura de código) | Decisão explicitamente reservada ao Technical Design (§9.2), nunca resolvida silenciosamente |
| Nenhum caso de uso real ainda demonstrado para `meeting`/RAG/governança | Não é risco — é a razão pela qual permanecem fora de escopo (item 3) | N/A — confirma a decisão, não a contesta |

Nenhum risco listado é bloqueante para a Architecture Review.

---

## 12. Critérios de sucesso

- Toda conclusão executiva rastreável a Project + `kind` + `AnalysisRecord` (`source_id`) + `created_at`, dentro da organização da sessão.
- Nenhuma citação de `Recommendation`/`Explanation`/resposta de outro Advisor, em nenhuma circunstância.
- Nenhuma afirmação de tendência — estruturalmente impossível, garantido por volume (§7).
- Cobertura em duas dimensões (status/risco) sempre estrutural, nunca calculada pelo LLM.
- Nenhuma chamada ao LLM quando não há nenhuma evidência (nem status nem risco) disponível para nenhum Project da organização.
- Nenhuma mudança de assinatura em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline exigida por este Blueprint.

---

## 13. Recomendação

**GO para a Architecture Review do Executive Advisor.**

Resolvido nesta etapa: escopo organizacional; rejeição fundamentada de `ProjectSummaryService` como fonte (composição direta via `AnalysisRecord` recomendada); rejeição fundamentada de `gather_context_many()` (duas chamadas explícitas no assembler); estratégia de volume (1 status + 1 risco mais recentes por Project, nunca histórico); modelo de cobertura em duas dimensões; componente de composição nomeado e localizado.

Reservado à Architecture Review/Technical Design, não decidido aqui: solução definitiva de rastreabilidade por `kind` (novo modelo de resposta vs. extensão aditiva de `CitedProject`); nomes definitivos de campos do modelo de resposta; estratégia de teste completa.
