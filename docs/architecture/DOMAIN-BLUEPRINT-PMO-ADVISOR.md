# Domain Blueprint — PMO Advisor

**Etapa 2 de 6** do ciclo institucional do PMO Advisor (D-092). Produzido sob autorização da Founder Decision que aprovou a Advisor Specification (`ADVISOR-SPECIFICATION-PMO-ADVISOR.md`) com **GO para o Domain Blueprint**, condicionado a sete diretrizes obrigatórias. Nenhum código escrito nesta etapa — missão exclusivamente de modelagem de domínio.

---

## 0. Diretrizes obrigatórias desta etapa (verbatim da Founder Decision)

1. PMO Advisor permanece Classe B; proibido usar `Recommendation`, `Explanation`, resposta de outro Advisor ou qualquer interpretação previamente produzida como evidência.
2. Avaliar explicitamente a unidade de agregação (Portfolio / Program / Project) — nenhuma decisão presumida.
3. Avaliar se `kind="meeting"` é realmente necessário, com base em consumidor e caso de uso real; na ausência dessa necessidade, manter exclusivamente `kind="status"`.
4. Avaliar objetivamente o conceito de *staleness*: quando um Project é considerado desatualizado, e se essa decisão pertence ao prompt ou à lógica estrutural.
5. Avaliar se dois consumidores Classe B justificam generalizar `PortfolioEvidenceAssembler` — decisão baseada em reutilização real, não antecipada.
6. Avaliar o risco de duplicidade de evidências caso múltiplos `kind`s venham a ser usados no futuro — sem implementar solução.
7. Preservar integralmente `AdvisorFramework`, `AIContextEngine`, Workflow Runtime, Event Pipeline, `RecommendationEngine`, `ExplanationEngine`.

Cada seção abaixo resolve um item, citando o código real que fundamenta a conclusão.

---

## 1. Executive Summary

O PMO Advisor é o segundo Advisor Classe B da STRATECH. Sua composição de evidência é **por Project** — forçado pelo modelo de dados, não por preferência de design, já que `AnalysisRecord` só se associa a `project_id`, nunca a `Portfolio`/`Program` diretamente. O escopo de composição (quais Projects entram no conjunto) é, por sua vez, **organizacional**, refletindo textualmente a Responsabilidade já catalogada ("através de múltiplos projetos de uma organização") — resolvido diretamente por `DomainService.list_projects_by_organization()`, já em produção desde a Wave 2, sem qualquer traversal Portfolio→Program.

A avaliação de `kind="meeting"` conclui que **não é necessário nesta etapa**: o único consumidor real de `kind="meeting"` (`ProjectSummaryService.list_action_items()`) resolve uma necessidade de UI (listagem de pendências), não um sinal de padrão de processo, e não carrega estado de conclusão (`completed`) que permitiria calcular atraso de forma estrutural. O sinal de "atrasos recorrentes" que o catálogo exige do PMO Advisor é obtido integralmente a partir do **histórico completo** de `AnalysisRecord`/`kind="status"` por Project (o mesmo `kind` já usado por Delivery e Portfolio Advisor), lido na íntegra — não apenas `evidence[0]` como no Portfolio Advisor.

*Staleness* é definida como um fato estrutural, nunca uma interpretação de prompt: o Advisor não decide o que é "desatualizado" — a `PMOEvidenceAssembler` (nome provisório) calcula a idade em dias do `AnalysisRecord` de status mais recente de cada Project e anexa esse número computado à evidência, seguindo o mesmo princípio já aplicado a `total_projects`/`projects_with_evidence` no Portfolio Advisor ("nunca confiar no LLM para fatos que o código já sabe com precisão"). O valor numérico do limiar (quantos dias == desatualizado) é uma decisão de produto explicitamente reservada ao Technical Design, não inventada aqui.

A generalização de `PortfolioEvidenceAssembler` foi avaliada e **rejeitada nesta etapa**: a lógica de seleção de evidência diverge estruturalmente entre os dois Advisors (um `Evidence` por Project vs. histórico completo por Project), e a lógica de resolução de escopo também diverge (Portfolio→Program→Project vs. `list_projects_by_organization()` direto). A semelhança é superficial (ambos iteram projetos e chamam `gather_context()`), não comportamental — não atende ao padrão de reutilização real já exigido em toda a missão (`normalize_rag_evidence()` só foi centralizado quando dois consumidores tinham comportamento *idêntico*, D-086).

**Recomendação: GO para a Architecture Review.**

---

## 2. Modelo de domínio do PMO Advisor

### 2.1 Fato estrutural que governa esta seção

`AnalysisRecord` só carrega `project_id` (`src/database/models.py`; confirmado por leitura direta em `project_summary_service.py:120`, `record.project_id`). Não existe, em nenhum lugar do schema, um `AnalysisRecord` associado a `Portfolio.id` ou `Program.id`. Isso significa que **qualquer** Advisor cuja evidência vem de `AnalysisRecord` — Risk, Delivery, Portfolio, e agora PMO — necessariamente compõe sua evidência **por Project**, porque é a única unidade que produz o dado bruto.

Isso já resolve, por si só, a pergunta "a unidade de composição é Portfolio, Program ou Project?" — não é uma escolha estilística, é uma restrição do modelo de dados já vigente.

### 2.2 Duas perguntas distintas que a Founder Decision combina em uma

A diretriz 2 mistura duas perguntas que a Domain Blueprint separa explicitamente, para não presumir nenhuma:

| Pergunta | Resposta | Fundamento |
|---|---|---|
| **Unidade de composição** — o que cada `Evidence` representa? | **Project** (mesma unidade do Portfolio Advisor) | Único nível com `AnalysisRecord` real |
| **Escopo de resolução** — que conjunto de Projects entra na composição? | **Organizacional** (todos os Projects da organização) | Responsabilidade catalogada: "identificar padrões de processo... através de múltiplos projetos **de uma organização**" (`ENTERPRISE-ADVISOR-CATALOG.md` §4) |

O escopo organizacional é resolvido sem nenhum método novo: `DomainService.list_projects(organization_id, program_id=None)` já retorna `list_projects_by_organization(organization_id)` (`src/services/domain_service.py:129-136`) — o mesmo método usado hoje por `ProjectSummaryService`. Nenhum traversal Portfolio→Program é necessário para o caso primário do PMO Advisor, ao contrário do Portfolio Advisor, cujo domínio é estruturalmente diferente (avaliar **um** portfólio específico, não a organização inteira).

Um escopo `portfolio_id` opcional (para "PMO Review de um portfólio específico") permanece **fora de escopo desta etapa** — não foi pedido pela Founder Decision, e adicioná-lo agora seria decidir algo não solicitado. Caso um caso de uso real apareça, reutilizaria o mesmo padrão de traversal já usado pelo Portfolio Advisor (`list_programs()` → `list_projects()`), sem inventar mecanismo novo.

### 2.3 O que cada Evidence carrega

Espelhando a rastreabilidade já estabelecida para o Portfolio Advisor, mas adaptada à unidade "processo ao longo do tempo" em vez de "estado atual":

- `project_id`, `project_name` — identidade do Project (via `Evidence.metadata`, enriquecimento aditivo, contrato `Evidence` inalterado).
- **Histórico completo** de `AnalysisRecord`/`kind="status"` do Project (não apenas `evidence[0]`) — necessário porque "atrasos recorrentes" é, por definição, um padrão observável apenas ao longo de múltiplos registros, nunca de um único snapshot.
- `staleness_days` — fato numérico computado estruturalmente (ver §4), nunca interpretado pelo LLM.

---

## 3. Kind="meeting": avaliação de necessidade real

### 3.1 O que já existe (fato de código, não hipótese)

`kind="meeting"` **já é usado em produção**, mas por um consumidor com propósito diferente do PMO Advisor:

```python
# src/services/project_summary_service.py:81-135
def list_action_items(self, organization_id, project_name=None, project_id=None) -> list[dict]:
    records = self._repository.list_analyses(..., kind="meeting", limit=None)
    for record in records:
        for item in model_output.get("action_items") or []:
            items.append({
                "project_name": ..., "project_id": ...,
                "description": item["description"],
                "owner": ..., "due_date": ...,
                "source_analysis_id": ..., "source_created_at": ...,
            })
```

Esse consumidor alimenta a página "Ações" do Workspace — uma **listagem factual** de itens pendentes, não um mecanismo de detecção de padrão. Ponto crítico: o schema de `action_items` (`src/agents/meeting_intelligence/prompts/analysis.md`) não tem campo de conclusão (`completed`/`resolved`). Não existe, hoje, nenhuma forma estrutural de saber se um `action_item` com `due_date` vencido ainda está pendente ou já foi resolvido em uma reunião posterior — calcular "atraso" a partir disso exigiria uma nova capacidade (rastreamento de estado de item de ação) que não existe e que esta etapa **não está autorizada a criar**.

### 3.2 Conclusão, baseada em caso de uso real (não especulação)

**`kind="meeting"` não é necessário para o PMO Advisor nesta etapa.** O sinal "atrasos recorrentes" exigido pelo catálogo é obtido inteiramente a partir de `kind="status"`, lido como histórico completo por Project:

- Um Project cujo `health_status` permanece `"red"`/`"yellow"` ao longo de múltiplos `AnalysisRecord`s consecutivos evidencia atraso recorrente **sem precisar de `action_items`** — o mesmo dado bruto que o Delivery Advisor já usa para identificar tendência dentro de um único projeto, aqui observado através de múltiplos projetos.
- "Ausência de atualização" é, por definição, uma propriedade de `kind="status"` (quando foi o último registro), não de `kind="meeting"`.
- "Lacunas de governança" — mesma técnica já validada no Governance Advisor: interpretação textual de `key_findings`/`recommendations` já presentes no `AnalysisRecord` de status, nunca uma segunda fonte estrutural.

**Decisão institucional (mantendo a instrução literal da Founder Decision):** manter exclusivamente `AnalysisRecord`/`kind="status"`. Se um caso de uso real e concreto envolvendo `action_items` surgir no futuro (por exemplo, se `action_items` ganhar um campo de conclusão), essa seria uma evolução arquitetural nova, com sua própria Architecture Review — não presumida aqui.

---

## 4. Staleness: definição objetiva

### 4.1 O que a Founder Decision pede

Duas perguntas: (a) quando um Project é "desatualizado"; (b) se isso é uma decisão de prompt ou de lógica estrutural.

### 4.2 Resposta à pergunta (b) primeiro, porque ela restringe a resposta de (a)

A disciplina já estabelecida nesta missão inteira — aplicada a `total_projects`/`projects_with_evidence`/`projects_without_evidence` no Portfolio Advisor — é que **qualquer fato que o código consegue calcular com precisão nunca é delegado ao LLM**. A idade em dias de um registro (`created_at` já é campo estrutural de `Evidence`, confirmado em AR-9/AR-12) é exatamente esse tipo de fato: `staleness_days = today - most_recent_status.created_at`, uma subtração de datas, zero ambiguidade.

**Decisão: o cálculo pertence à lógica estrutural, nunca ao prompt.** A `PMOEvidenceAssembler` computa `staleness_days` por Project e o anexa como fato pronto (ex.: em `Evidence.metadata` ou em um campo companheiro do modelo de resposta) — o prompt recebe o número já calculado, nunca calcula ele mesmo, e nunca decide sozinho, de forma inconsistente entre chamadas, "quantos dias contam como desatualizado".

### 4.3 O limiar numérico é uma decisão de produto, não de arquitetura

Não existe hoje, em nenhum ponto do código (`grep` confirmado, nenhum resultado de `stale`/`days_since`/threshold), um precedente reutilizável de "quantos dias sem atualização = alerta". Inventar um número (7? 14? 30?) nesta Domain Blueprint seria decidir silenciosamente uma regra de negócio sem evidência de necessidade real — exatamente o que a disciplina desta missão proíbe. **O valor numérico do limiar é reservado explicitamente ao Technical Design**, onde poderá ser parametrizado (ex.: constante nomeada, não mágica) e testado com cenários reais. O que esta etapa decide, de forma definitiva, é apenas o **local** onde a decisão vive: estrutural, nunca no prompt.

---

## 5. `PortfolioEvidenceAssembler`: avaliação de generalização

### 5.1 O teste aplicado

A mesma pergunta já respondida para `normalize_rag_evidence()` em D-086: existe reutilização **real** (comportamento idêntico), ou apenas semelhança superficial de forma?

### 5.2 Comparação direta, campo a campo

| Aspecto | `PortfolioEvidenceAssembler` (Portfolio Advisor) | Assembler do PMO Advisor (proposto) |
|---|---|---|
| Resolução de escopo | `get_portfolio()` → `list_programs(portfolio_id)` → `list_projects(program_id)` (traversal de 3 níveis) | `list_projects(organization_id, program_id=None)` → direto, 1 chamada |
| Seleção de evidência por Project | `evidence[0]` — mecanicamente **apenas o mais recente** | **Histórico completo** — todos os `AnalysisRecord`s de status do Project |
| Justificativa da seleção | Pergunta é "estado atual comparado entre Projects" (AR-12) | Pergunta é "padrão ao longo do tempo, por Project e entre Projects" |
| Metadados agregados | `portfolio_id`/`program_id`/`project_id`/`project_name` | `project_id`/`project_name` + `staleness_days` calculado |
| Contagens estruturais | `total_projects`/`projects_with_evidence` | Mesmo princípio, mas sem noção de Portfolio/Program |

A única semelhança real é a forma do laço ("para cada Project, chamar `gather_context()` uma vez, empacotar em `Evidence`"). A **lógica de seleção de evidência diverge estruturalmente** (`evidence[0]` vs. histórico completo) — não é um parâmetro trivial, é uma decisão de domínio diferente, fundamentada em perguntas diferentes que os dois Advisors respondem (AR-12 já estabeleceu que "cada Advisor aplica a mesma regra permanente D-104 à unidade de composição correta para sua própria pergunta").

### 5.3 Decisão

**Não generalizar nesta etapa.** Um componente compartilhado hoje teria que expor um parâmetro de "modo de seleção" (mais recente vs. histórico completo) e um parâmetro de "modo de resolução de escopo" (Portfolio-rooted vs. organization-wide) — ou seja, se tornaria uma abstração configurável por flags para acomodar dois casos, o oposto do princípio "Grounded before Generalized" já aplicado a `normalize_rag_evidence()` (só centralizado quando o comportamento era literalmente idêntico entre Document e Governance Advisor).

O componente do PMO Advisor será implementado como `PMOEvidenceAssembler` (nome provisório, a confirmar no Technical Design), em `src/agents/pmo_advisor/`, seguindo exatamente o mesmo **padrão estrutural** de localização e responsabilidade já estabelecido por `PortfolioEvidenceAssembler` — mesma disciplina, código independente.

**Gatilho real para revisitar esta decisão, registrado explicitamente:** se um **terceiro** Advisor Classe B (Executive Advisor) precisar de uma composição cujo comportamento seja *idêntico* a um dos dois já existentes (mesma seleção de evidência, mesma resolução de escopo), aí sim há reutilização real a extrair — nunca antes disso, e nunca por simetria superficial.

---

## 6. Risco de duplicidade de evidência entre múltiplos `kind`s (registro, não solução)

Como o PMO Advisor usa hoje exclusivamente `kind="status"` (§3), este risco é **especulativo/futuro** — registrado porque a Founder Decision pediu avaliação explícita, não porque exista hoje.

**Cenário de risco:** se um segundo `kind` (ex.: `"meeting"`) for adicionado no futuro para o mesmo Project, o mesmo fato de domínio (ex.: um atraso) poderia aparecer descrito em dois `AnalysisRecord`s de `kind`s diferentes gerados a partir do mesmo evento real (uma reunião discutindo o mesmo bloqueio já registrado em um status update). Sem um mecanismo de deduplicação, o LLM poderia citar as duas evidências como se fossem duas confirmações independentes do mesmo padrão, inflando artificialmente a confiança de um "padrão recorrente" que na verdade é um único fato relatado duas vezes.

**Por que não é resolvido agora:** resolver isso exigiria um mecanismo de correlação entre `AnalysisRecord`s de `kind`s diferentes (ex.: por período de tempo ou por conteúdo semelhante) que não existe hoje e que não tem, hoje, nenhum consumidor real — implementá-lo especulativamente violaria a mesma disciplina aplicada em §3 e §5. Fica registrado como risco residual, com gatilho explícito: revisitar apenas se/quando um segundo `kind` for de fato adicionado à composição do PMO Advisor.

---

## 7. Preservação da infraestrutura compartilhada

Confirmado por leitura de código, sem nenhuma alteração proposta nesta etapa:

- `AdvisorFramework.gather_context(organization_id, project_name, kind)` (`framework.py:45-47`) — usado sem extensão; a `PMOEvidenceAssembler` chama esse método existente uma vez por Project, exatamente como `PortfolioEvidenceAssembler` já faz.
- `AdvisorFramework.run()` (`framework.py:71+`) — nenhuma mudança de assinatura necessária; o PMO Advisor recebe uma lista de `Evidence` já montada, como todo Advisor Classe A/B.
- `AIContextEngine.gather()` (`context_engine.py:19`) — inalterado; único ponto de acesso a `AnalysisRecord`.
- `RecommendationEngine`/`ExplanationEngine` — inalterados; nenhuma extensão de contrato necessária, `Evidence` permanece o contrato genérico já evoluído em AR-9.
- Workflow Runtime / Event Pipeline — não incidem; PMO Advisor não é invocado por workflow nem registrado como handler de evento (mesma restrição permanente de todos os Advisors).
- `DomainService.list_projects()` — reutilizado sem modificação (Wave 2, já em produção).

---

## 8. Riscos residuais

| Risco | Origem | Mitigação registrada |
|---|---|---|
| Volume de chamadas `gather_context()` em escopo organizacional pode ser maior que o de um único Portfolio | Organizações com muitos Projects | Mesmo gatilho de performance já aprovado para o Portfolio Advisor (20+ chamadas sequenciais ou p95 > 3s) — nenhuma otimização antecipada, avaliação reservada ao Technical Design |
| Limiar numérico de staleness ainda não definido | Decisão de produto, não de arquitetura | Reservado ao Technical Design, parametrizável, não hardcoded silenciosamente |
| Nome definitivo do componente (`PMOEvidenceAssembler` é provisório) | Convenção de nomenclatura | Confirmar no Technical Design, mesmo padrão de `PortfolioEvidenceAssembler` |
| Duplicidade de evidência entre `kind`s futuros | Especulativo — não incide hoje | Registrado em §6, gatilho explícito para revisitar apenas se um segundo `kind` for adicionado |
| Detecção de "atrasos recorrentes" depende de interpretação textual do LLM sobre histórico de `health_status`/`key_findings` | Mesma natureza de risco já aceito no Governance Advisor (interpretação de conteúdo, não comparação determinística) | Nenhuma nova mitigação necessária — mesmo padrão já em produção |

Nenhum risco listado é bloqueante para a Architecture Review.

---

## 9. Critérios de sucesso

Herdados do catálogo (`ENTERPRISE-ADVISOR-CATALOG.md` §4), reafirmados sem alteração:

- Todo padrão identificado referencia Projects/dados reais — nenhuma generalização sem evidência de múltiplos Projects.
- Nenhuma citação de `Recommendation`/`Explanation`/resposta de outro Advisor como evidência (diretriz 1).
- `staleness_days` sempre calculado estruturalmente, nunca inventado ou estimado pelo LLM.
- Cobertura (quantos Projects têm evidência de status, quantos não têm) sempre estrutural, nunca calculada pelo LLM — mesmo padrão já provado no Portfolio Advisor.
- Nenhuma chamada a `gather_rag_context()` em nenhum ponto do fluxo (RAG fora de escopo, per Advisor Specification §3.3).

---

## 10. Recomendação

**GO para a Architecture Review do PMO Advisor.**

Questões resolvidas nesta etapa, não a serem reabertas sem nova Founder Decision: unidade de composição (Project, forçada pelo modelo de dados); escopo de resolução (organizacional, via `list_projects_by_organization()`); necessidade de `kind="meeting"` (não necessário, `kind="status"` com histórico completo é suficiente); local da decisão de staleness (estrutural, nunca prompt); generalização do Assembler (rejeitada nesta etapa, gatilho explícito registrado para um terceiro consumidor real).

Questões explicitamente reservadas à Architecture Review / Technical Design, não decididas aqui: valor numérico do limiar de staleness; nome definitivo do componente; modelo de resposta completo (contagens estruturais, campos expostos); estratégia de teste dos cenários obrigatórios.
