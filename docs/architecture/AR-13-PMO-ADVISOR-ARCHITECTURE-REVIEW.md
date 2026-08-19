# AR-13 — Architecture Review do PMO Advisor

**Etapa 3 de 6** do ciclo institucional do PMO Advisor. Produzido sob autorização da Founder Decision que aprovou o Domain Blueprint (`DOMAIN-BLUEPRINT-PMO-ADVISOR.md`) com **GO para a Architecture Review**, confirmando como oficiais as decisões já tomadas (unidade de composição = Project; escopo = organizacional; fonte = exclusivamente `AnalysisRecord`/`kind="status"`; histórico completo por Project autorizado; generalização do `PortfolioEvidenceAssembler` recusada) e delegando a esta etapa quatro decisões pendentes: staleness (limiar, localização, metadados), controle de volume, modelo de cobertura estrutural, e confirmação final de preservação de infraestrutura. Nenhum código escrito nesta etapa.

---

## 0. O que já é oficial (não reaberto aqui)

Confirmado pela Founder Decision sobre o Domain Blueprint, citado aqui apenas como base, não redecidido:

1. Unidade de composição: **Project**, rastreável por `project_id`.
2. Escopo: **organizacional**, via `DomainService.list_projects(organization_id, program_id=None)`, sem traversal obrigatório por Portfolio/Program.
3. Fonte de evidência: exclusivamente `AnalysisRecord`/`kind="status"`. `kind="meeting"`, `action_items`, `kind="risk"`, RAG e respostas de outros Advisors permanecem fora de escopo.
4. Histórico: ao contrário do Portfolio Advisor (`evidence[0]` mecânico), o PMO Advisor pode usar o **histórico de status por Project** para identificar padrões recorrentes e evolução operacional.
8. Generalização do `PortfolioEvidenceAssembler`: **rejeitada neste momento**. Gatilho de revisão: terceiro Advisor Classe B com comportamento estruturalmente idêntico a um componente já existente.

---

## 1. Executive Summary

Esta Architecture Review resolve as quatro questões explicitamente delegadas pela Founder Decision, todas com base em capacidades **já existentes** no código, sem estender nenhum contrato compartilhado:

- **Staleness**: limiar inicial de **14 dias** sem novo `AnalysisRecord`/`kind="status"`, justificado como duas janelas de reporte semanal consecutivas perdidas — heurística de mercado para PMO, não extraída de telemetria real (nenhuma existe hoje no produto), registrada explicitamente como constante inicial revisável, nunca como valor validado por dados. Cálculo pertence à `PMOEvidenceAssembler` (`staleness_days` = diferença entre "hoje" e o `created_at` do `AnalysisRecord` de status mais recente do Project); o Advisor recebe `staleness_days` e `is_stale` já prontos em `Evidence.metadata`, nunca calcula a comparação.
- **Controle de volume**: **limite máximo de registros por Project** (não janela temporal) — um corte simples (`evidence[:N]`) sobre a lista já ordenada por `created_at DESC` que `AnalysisRepository.list_analyses()` já garante (mesma garantia estrutural usada desde AR-11/AR-12), aplicado inteiramente dentro da `PMOEvidenceAssembler`, sem qualquer mudança de assinatura em `AdvisorFramework`/`AIContextEngine`. Valor inicial: **5 registros mais recentes por Project**. Janela temporal foi avaliada e descartada — poderia zerar a evidência de um Project só porque seu último reporte caiu fora da janela, colidindo semanticamente com "zero cobertura" (categoria já definida e distinta desde o Portfolio Advisor).
- **Cobertura estrutural**: as cinco contagens exigidas (`total_projects`, `projects_with_status`, `projects_without_status`, `projects_stale`, `projects_current`) são calculadas inteiramente pela `PMOEvidenceAssembler`, nunca pelo LLM — mesmo padrão já provado no Portfolio Advisor. Relações aritméticas explícitas definidas em §4.
- **Preservação de infraestrutura**: confirmada por leitura de código — nenhuma mudança de assinatura necessária em `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime, Event Pipeline.

**Recomendação: GO para o Technical Design.**

---

## 2. Staleness: decisão final

### 2.1 Limiar inicial

**14 dias** sem um novo `AnalysisRecord`/`kind="status"` para o Project.

### 2.2 Justificativa operacional

Não existe hoje, em nenhum ponto do produto (confirmado por busca de código no Domain Blueprint, §4.2 — nenhum resultado para `stale`/`days_since`/cadência documentada), uma cadência de atualização de status observada ou declarada. Inventar um número "baseado em dados" seria falso — não há dados. O valor de 14 dias é adotado como **heurística inicial de mercado**: duas janelas de reporte semanal consecutivas sem atualização é o padrão mais comum de alerta de PMO em ferramentas de gestão de portfólio, escolhido por ser conservador (não sinaliza atraso a cada semana perdida, apenas quando o padrão se repete) e simples de justificar a um usuário real. **Este valor é registrado explicitamente como não-empírico** — não deve ser apresentado a ninguém como "baseado em dados históricos da organização", porque não é. Fica sujeito a revisão quando uso real gerar evidência (ex.: reclamações de falso-positivo, ou o inverso).

### 2.3 Localização da regra

Constante nomeada dentro do módulo da `PMOEvidenceAssembler` (ex.: `PMO_STALENESS_THRESHOLD_DAYS = 14`), **nunca** no prompt do `PMOAdvisorAgent`. O cálculo (`staleness_days`, `is_stale`) é feito inteiramente em código — mesma disciplina já aplicada às contagens estruturais do Portfolio Advisor ("nunca confiar no LLM para fatos que o código já sabe com precisão").

**Sem configuração por organização.** A Founder Decision instrui explicitamente não criar configuração por organização sem necessidade comprovada — não existe hoje nenhum consumidor real pedindo um limiar por tenant, então esta etapa não cria esse mecanismo. Se uma organização real precisar de um limiar diferente, isso seria uma extensão futura, justificada por um caso de uso real, não antecipada aqui.

### 2.4 Metadados entregues ao Advisor

Cada evidência de Project carrega, em `Evidence.metadata` (enriquecimento aditivo, contrato `Evidence` inalterado):

- `project_id`, `project_name` — identidade (já decidido no Domain Blueprint).
- `staleness_days: int` — dias desde o `AnalysisRecord`/status mais recente do Project.
- `is_stale: bool` — `staleness_days > PMO_STALENESS_THRESHOLD_DAYS`, calculado em código.

O prompt do `PMOAdvisorAgent` recebe esses dois fatos já prontos por Project — nunca subtrai datas, nunca decide sozinho o que conta como desatualizado.

---

## 3. Controle de volume: decisão final

### 3.1 Mecanismo escolhido: limite de registros, não janela temporal

| Opção avaliada | Resultado |
|---|---|
| **Limite máximo de registros por Project** | **Escolhido.** Determinístico, mecânico (slice sobre lista já ordenada), nunca esvazia a evidência de um Project que de fato tem histórico. |
| Janela temporal (ex.: últimos 90 dias) | **Descartada.** Um Project cujo último reporte caiu fora da janela ficaria com evidência zerada — indistinguível de "nunca reportou" (categoria já reservada para "zero cobertura" desde o Portfolio Advisor), gerando ambiguidade semântica nas contagens estruturais de §4. |
| Combinação dos dois | **Descartada por desnecessária.** Adicionar uma segunda dimensão de corte sem um caso de uso real que o exija violaria a mesma disciplina de "Grounded before Generalized" já aplicada ao longo desta Epic — o limite de registros sozinho já é suficiente e determinístico. |

### 3.2 Fundamento estrutural, zero mudança de infraestrutura

`AnalysisRepository.list_analyses()` (`src/database/repository.py:135-150`) já ordena por `created_at.desc(), id.desc()` **incondicionalmente**, para qualquer `kind` — a mesma garantia que já sustenta `evidence[0]` no Portfolio Advisor (AR-12) e a leitura de tendência no Delivery Advisor. O corte de volume é, portanto, um **slice em memória** (`evidence[:N]`) aplicado **dentro da `PMOEvidenceAssembler`**, depois que `AdvisorFramework.gather_context()` retorna a lista completa — nenhuma mudança de assinatura em `gather_context()`/`AIContextEngine.gather()`, que continuam retornando o histórico completo exatamente como hoje. A `PMOEvidenceAssembler` é a única camada ciente do corte, assim como já é a única camada ciente da seleção `evidence[0]` no Portfolio Advisor.

### 3.3 Valor inicial

**5 registros mais recentes por Project.**

Justificativa: o Delivery Advisor já demonstra, em produção, que 2 pontos são suficientes para descrever uma tendência simples (melhora/deterioração) dentro de um único projeto. O PMO Advisor precisa de mais pontos por Project para diferenciar um "padrão recorrente" real de uma flutuação isolada, mas **sem** replicar o histórico inteiro de um Project que já tem dezenas de registros — o que inflaria o contexto de forma desproporcional justamente nos Projects mais antigos/mais bem documentados, sem necessariamente adicionar sinal proporcional. Cinco registros dão margem para 2-3 ciclos de comparação além do estado atual, mantendo o payload por Project pequeno e previsível independentemente de quão longa seja a história real do Project. Mesmo tratamento de "constante inicial, não configuração por organização" de §2.3 aplica-se aqui.

### 3.4 Regra uniforme e determinística — confirmação

O corte se aplica **igualmente a todo Project**, sem exceção por tipo, tamanho de organização, ou qualquer outro critério — a mesma quantidade de registros (5) é solicitada para todo Project que tenha ao menos um `AnalysisRecord`/status, exatamente como pedido pela Founder Decision.

---

## 4. Cobertura estrutural: modelo final

Todas as cinco contagens são calculadas pela `PMOEvidenceAssembler`/camada de rota, nunca pelo LLM — mesmo padrão do Portfolio Advisor (`total_projects`/`projects_with_evidence`/`projects_without_evidence`, já provado em D-111/D-112).

| Campo | Definição | Relação |
|---|---|---|
| `total_projects` | Todos os Projects no escopo organizacional resolvido (`list_projects_by_organization()`) | — |
| `projects_with_status` | Projects com pelo menos um `AnalysisRecord`/`kind="status"` | ⊆ `total_projects` |
| `projects_without_status` | Projects sem nenhum `AnalysisRecord`/`kind="status"` | `total_projects - projects_with_status` |
| `projects_stale` | Projects em `projects_with_status` cujo `is_stale = true` | ⊆ `projects_with_status` |
| `projects_current` | Projects em `projects_with_status` cujo `is_stale = false` | `projects_with_status - projects_stale` |

**Distinção explícita, para evitar ambiguidade:** um Project sem nenhum status registrado (`projects_without_status`) **nunca** é contado como `projects_stale` — são categorias estruturalmente diferentes (ausência total de evidência vs. evidência existente porém desatualizada), mesma disciplina que já separou "zero cobertura" de "cobertura parcial" no Portfolio Advisor. A soma `projects_with_status + projects_without_status` sempre iguala `total_projects`; a soma `projects_stale + projects_current` sempre iguala `projects_with_status`.

O `PMOAdvisorResponse` (modelo de resposta, a definir em detalhe no Technical Design) expõe as cinco contagens como campos estruturais do payload HTTP, exatamente como `PortfolioAdvisorResponse` expõe `total_projects`/`projects_with_evidence`/`projects_without_evidence` hoje — nenhum desses números é parseado de ou gerado pela resposta do LLM.

---

## 5. Preservação de infraestrutura — confirmação final

Nenhuma das decisões desta etapa exige mudança de assinatura ou comportamento em:

- `AdvisorFramework.gather_context()`/`run()` — a `PMOEvidenceAssembler` chama `gather_context(organization_id, project_name, kind="status")` uma vez por Project, exatamente como `PortfolioEvidenceAssembler` já faz; o corte de volume e o cálculo de staleness acontecem **depois** do retorno, inteiramente dentro do Assembler.
- `AIContextEngine.gather()` — continua retornando o histórico completo (`limit=None`), sem mudança; o truncamento é responsabilidade exclusiva do Assembler do PMO Advisor, nunca da camada compartilhada.
- `RecommendationEngine`/`ExplanationEngine` — nenhuma extensão de contrato necessária; `Evidence` permanece o contrato genérico já evoluído em AR-9, enriquecido apenas via `metadata`.
- Workflow Runtime / Event Pipeline — não incidem, mesma restrição permanente de todos os Advisors.
- `DomainService.list_projects()` — reutilizado sem modificação.

Nenhuma mudança proposta a `src/database/repository.py::list_analyses()` — seus parâmetros `limit`/`created_from`/`created_to` já existentes foram avaliados como mecanismo teórico para o controle de volume (§3.1), mas a decisão final aplica o corte em memória na Assembler, não na query, para manter a assinatura de `AIContextEngine.gather()` (que não expõe `limit` a quem chama) completamente intocada.

---

## 6. Riscos residuais

| Risco | Origem | Mitigação registrada |
|---|---|---|
| Limiar de 14 dias e cap de 5 registros são heurísticas iniciais, não validadas por dados reais | Ausência de telemetria de cadência de reporte no produto | Registrado explicitamente como não-empírico em §2.2/§3.3; revisão reservada a evidência real de uso, nunca a ajuste especulativo |
| Volume de chamadas `gather_context()` em escopo organizacional | Organizações com muitos Projects | Mesmo gatilho de performance já aprovado para o Portfolio Advisor (20+ chamadas sequenciais ou p95 > 3s) — nenhuma otimização antecipada |
| Nome definitivo do componente (`PMOEvidenceAssembler`) e do módulo de constantes | Convenção de nomenclatura | Confirmar no Technical Design |
| Interpretação de "padrão recorrente" continua sendo leitura textual do LLM sobre o histórico estruturado (`health_status`/`key_findings` por registro) | Mesma natureza de risco já aceito no Governance Advisor | Nenhuma nova mitigação necessária — mesmo padrão já em produção |

Nenhum risco listado é bloqueante para o Technical Design.

---

## 7. Critérios de sucesso

Herdados do Domain Blueprint, reafirmados sem alteração, mais os específicos desta etapa:

- Todo padrão identificado referencia Projects/dados reais — nenhuma generalização sem evidência de múltiplos Projects.
- `staleness_days`/`is_stale` sempre calculados estruturalmente, nunca inventados ou estimados pelo LLM.
- As cinco contagens de cobertura sempre estruturais, nunca calculadas pelo LLM.
- `projects_stale + projects_current = projects_with_status`; `projects_with_status + projects_without_status = total_projects` — verificável em todo teste.
- Corte de volume aplicado uniformemente, sem exceção por Project.
- Nenhuma chamada a `gather_rag_context()` em nenhum ponto do fluxo.
- Nenhuma mudança de assinatura em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine` (`git diff --stat` vazio nesses arquivos ao final da implementação).

---

## 8. Recomendação

**GO para o Technical Design do PMO Advisor.**

Questões resolvidas nesta etapa, oficiais a partir de agora: limiar de staleness (14 dias, constante não-empírica, localizada na Assembler); mecanismo de controle de volume (corte de 5 registros mais recentes por Project, aplicado em memória na Assembler, zero mudança de infraestrutura); modelo de cobertura estrutural (cinco contagens, relações aritméticas explícitas, distinção clara entre "sem status" e "desatualizado").

Questões reservadas ao Technical Design, não decididas aqui: nome definitivo dos componentes (`PMOEvidenceAssembler`, módulo de constantes); contrato completo de `PMOAdvisorResponse`; estrutura do prompt do `PMOAdvisorAgent`; estratégia de teste dos cenários obrigatórios (a definir, análoga aos 11 cenários A-K do Portfolio Advisor, adaptada às novas dimensões staleness/volume/cobertura de 5 categorias).
