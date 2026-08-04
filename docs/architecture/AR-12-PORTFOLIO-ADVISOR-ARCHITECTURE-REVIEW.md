# AR-12 — Portfolio Advisor: Architecture Review

**Autorização:** "Founder Decision — Domain Blueprint do Portfolio Advisor" (veredito **APPROVED — GO para a Architecture Review**), confirmando como oficiais: (1) `PortfolioEvidenceAssembler` permanece componente exclusivo do Portfolio Advisor, dentro do próprio pacote, não promovido a `src/services/` nesta etapa; (2) `Evidence.metadata` continua sendo o único mecanismo de transporte de `project_id`/`project_name`/`program_id`, nenhuma alteração ao contrato `Evidence`; (3) esta revisão deve analisar explicitamente dois pontos — **A. peso da evidência** (um `Evidence` por Project, representando seu estado atual, independentemente do volume de `AnalysisRecord`s históricos, e sua consistência com o Delivery Advisor) e **B. ordem da composição** (Programs → Projects não representa prioridade semântica; o Advisor interpreta o conjunto, nunca a posição; nenhum algoritmo novo); (4) preservar integralmente `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline/`RecommendationEngine`/`ExplanationEngine`. Nenhum código, nenhum Technical Design produzido aqui.

**Etapa do ciclo institucional:** 3 de 6 (Domain Blueprint concluído D-109 → **Architecture Review, este documento** → Founder Approval → Technical Design → Implementação → Executive Review).

**Método:** toda conclusão é rastreável a código real — `src/database/domain_repository.py`, `src/services/domain_service.py`, `src/services/ai_foundation/context_engine.py`, `src/database/repository.py::list_analyses`, `src/agents/delivery_advisor/agent.py`.

---

## Executive Summary

Esta Architecture Review resolve os dois pontos que o Domain Blueprint deixou em aberto (§10 do Domain Blueprint). **Ponto A (peso da evidência):** confirmado — cada Project contribui com exatamente um `Evidence`, o de seu `AnalysisRecord` de status mais recente, independentemente de quantos registros históricos existam. Esta decisão é **consistente** com o Delivery Advisor, não contraditória: os dois Advisors reutilizam a mesma garantia estrutural (`AnalysisRepository.list_analyses()` já ordena por `created_at.desc()`), mas cada um define, em sua própria camada de domínio, uma unidade de evidência diferente porque respondem perguntas diferentes — o Delivery Advisor sintetiza a *trajetória* de um único projeto (por isso consome o histórico inteiro), o Portfolio Advisor sintetiza uma *comparação instantânea* entre múltiplos projetos (por isso consome apenas o estado mais recente de cada um). **Ponto B (ordem da composição):** confirmado — a ordem de iteração Programs→Projects é puramente incidental à ordenação alfabética/por código já existente em `list_programs_by_portfolio()`/`list_projects_by_program()` (`ORDER BY Program.code`/`Project.name`), nunca uma classificação de prioridade; nenhum algoritmo é necessário para "neutralizar" essa ordem porque ela nunca carregou significado — a instrução ao `PortfolioAdvisorAgent` (Technical Design) é textual, não estrutural. Nenhuma mudança de código nesta etapa em nenhum dos dois pontos. Recomendação ao final: **GO para o Technical Design.**

---

## 1. Reafirmação das decisões já permanentes (não redecididas aqui)

- **`PortfolioEvidenceAssembler`** (D-109): componente exclusivo, localizado em `src/agents/portfolio_advisor/evidence_assembler.py`, não promovido a componente compartilhado nesta etapa.
- **`Evidence.metadata`** como único mecanismo de rastreabilidade (`project_id`/`project_name`/`program_id`): nenhuma alteração ao contrato `Evidence`.
- **Fluxo, responsabilidades, casos de domínio:** idênticos ao já caracterizado no Domain Blueprint (`DOMAIN-BLUEPRINT-PORTFOLIO-ADVISOR.md` §4/§6/§7) — não reabertos aqui.

---

## 2. Ponto A — Peso da evidência (um `Evidence` por Project)

### 2.1 A pergunta concreta

Um Project pode ter múltiplos `AnalysisRecord`s de `kind="status"` ao longo do tempo — exatamente a mesma situação que o Delivery Advisor já trata (AR-11/D-105/D-106). A questão desta revisão: quando o `PortfolioEvidenceAssembler` chama `framework.gather_context(organization_id, project.name, kind="status")` para um Project, ele recebe potencialmente **vários** registros (todo o histórico daquele projeto) — quantos desses devem entrar na `evidence` consolidada do Portfolio?

### 2.2 Grounding — o que já é garantido estruturalmente, sem nenhuma mudança

Confirmado por leitura direta (mesmo achado já usado em AR-11 §2): `AnalysisRepository.list_analyses()` (`src/database/repository.py`) já ordena por `created_at.desc()` para qualquer `kind`, sem exceção — `AIContextEngine.gather()` preserva essa ordem. Isso significa que, para cada Project, `evidence[0]` do resultado de `gather_context()` **já é**, hoje, o `AnalysisRecord` de status mais recente daquele projeto — sem nenhum código de ordenação a escrever.

### 2.3 Decisão: um `Evidence` por Project — o mais recente

**Confirmado.** O `PortfolioEvidenceAssembler`, ao processar o resultado de `gather_context()` para cada Project, seleciona apenas o primeiro item (`evidence[0]`, já garantido ser o mais recente) antes de adicioná-lo à lista consolidada do portfólio — descartando o restante do histórico daquele projeto para os fins desta composição. Isso é **seleção mecânica de um elemento de uma lista já ordenada pelo Framework**, não uma interpretação de conteúdo: o Assembler nunca lê `content` para decidir qual registro é "mais relevante", apenas toma a posição já garantida como mais recente — mesma natureza de operação que `normalize_rag_evidence()` já realiza (envelope mecânico, nunca interpretação de domínio, D-086/AR-9 §3).

### 2.4 Consistência com o Delivery Advisor — análise explícita, conclusão registrada

**Não há contradição — são unidades de evidência diferentes, por design, porque as perguntas são diferentes:**

| | Delivery Advisor | Portfolio Advisor |
|---|---|---|
| Escopo de `gather_context()` | Um projeto | N projetos (um por chamada) |
| O que consome do resultado por projeto | **Todo o histórico** (`evidence` completa) | **Apenas `evidence[0]`** (o mais recente) |
| Pergunta que responde | Trajetória de *um* projeto ao longo do tempo (D-104: "o AnalysisRecord mais recente representa o estado atual... registros anteriores utilizáveis apenas como contexto histórico ou tendência") | Comparação instantânea entre *múltiplos* projetos — equilíbrio, sobreposição, dependências (catálogo §5) |
| Por que o histórico completo é necessário (ou não) | Necessário — a tendência (melhora/estabilidade/deterioração) só existe comparando registros ao longo do tempo de um mesmo projeto | Desnecessário e potencialmente confuso — misturar histórico de N projetos multiplicaria o volume de evidência sem servir à pergunta de portfólio, e correria o risco de o Advisor comparar o status *antigo* de um projeto com o status *atual* de outro, uma inconsistência que o próprio Founder já preveniu na diretriz de recência do Delivery Advisor (D-104: "o AnalysisRecord mais recente representa o estado atual") |

**Conclusão arquitetural registrada:** a regra "o `AnalysisRecord` de status mais recente representa o estado atual" (D-104, permanente) é aplicada **de forma consistente** pelos dois Advisors — o Delivery Advisor a aplica *dentro* de um projeto (mais recente = atual, resto = histórico); o Portfolio Advisor a aplica *entre* projetos (cada projeto contribui apenas seu estado atual, nunca seu histórico, para que a comparação entre projetos seja sempre "estado atual contra estado atual", nunca "estado atual de um contra estado antigo de outro"). Isso não é uma segunda regra nova — é a mesma regra permanente, aplicada à unidade de composição correta para cada Advisor. Nenhum algoritmo de comparação de datas entre projetos é necessário: a garantia de recência já vem de `list_analyses()`, reaproveitada sem mudança.

---

## 3. Ponto B — Ordem da composição (Programs → Projects não é prioridade)

### 3.1 Grounding — a ordem já existente, confirmada incidental

Confirmado por leitura direta de `src/database/domain_repository.py`:

- `list_programs_by_portfolio(portfolio_id)` — `ORDER BY Program.code`.
- `list_projects_by_program(program_id)` — `ORDER BY Project.name`.

Ambas ordenações são **alfabéticas/por código**, escolhidas por essas funções (já existentes, Wave 2, reutilizadas sem extensão) por previsibilidade de listagem — o mesmo critério já usado por toda tela administrativa desta plataforma (ex.: listagem de Portfolios/Programs na UI). Nenhuma dessas ordens jamais carregou, em nenhum ponto do código, um significado de prioridade/criticidade/urgência.

### 3.2 Decisão: a ordem de composição é estruturalmente sem peso semântico — nenhum algoritmo necessário

**Confirmado.** Como a ordem já não representa prioridade (§3.1) e o `PortfolioEvidenceAssembler` apenas concatena, na ordem em que os itera, as listas já devolvidas por `list_programs_by_portfolio()`/`list_projects_by_program()`/`gather_context()` — não é necessário nenhum algoritmo de reordenação, embaralhamento, ou normalização para "remover" uma prioridade que nunca existiu estruturalmente. O que é necessário, per instrução do Founder, é puramente textual: o prompt do `PortfolioAdvisorAgent` (Technical Design) deve instruir o modelo a nunca inferir importância a partir da posição de um projeto na lista de evidências — interpretar o **conjunto**, cada item citável independentemente de sua posição, exatamente o mesmo princípio já aplicado à hierarquia documental do Governance Advisor (AR-10: precedência é conhecimento de domínio no prompt, nunca lógica estrutural) e à recência do Delivery Advisor (AR-11: interpretação de sequência é conhecimento de domínio, nunca algoritmo).

---

## 4. Preservação confirmada (não apenas alegada)

Nenhuma linha de `AdvisorFramework`, `AIContextEngine`, Workflow Runtime, Event Pipeline, `RecommendationEngine` ou `ExplanationEngine` precisa mudar para nenhuma das duas decisões desta revisão — ambas resolvidas inteiramente dentro do `PortfolioEvidenceAssembler` (seleção mecânica do item mais recente, §2) ou como conteúdo de prompt (interpretação de conjunto vs. posição, §3), a mesma natureza de mudança já aplicada à hierarquia documental do Governance Advisor e à recência/tendência do Delivery Advisor.

---

## 5. Riscos residuais

1. **Wording exato da instrução "interprete o conjunto, não a posição" no prompt** — decisão de Technical Design; risco de ambiguidade mitigado por um teste explícito comparando duas ordens de composição diferentes (mesmo conjunto de projetos, ordem de itens trocada) e confirmando resposta semanticamente equivalente.
2. **Volume de `AnalysisRecord`s de status por projeto descartado (§2.3)** — nenhum dado é perdido de forma insegura (o histórico completo permanece consultável via Delivery Advisor); risco de auditabilidade não aplicável, pois `cited_analysis_ids` sempre aponta para o registro real usado.
3. **Riscos já registrados no Domain Blueprint (§10), não agravados:** confirmação do padrão de composição como referência obrigatória para PMO/Executive Advisor; wording de `no_evidence_answer`/cobertura parcial; nome de rota/RBAC definitivo; gatilho de performance (nenhuma mudança nesta revisão).

Nenhum risco listado bloqueia o avanço para o Technical Design.

---

## 6. Critérios de sucesso (reafirmados do Domain Blueprint, com os dois pontos desta revisão incorporados)

1. Toda recomendação de composição rastreável a projetos/programas reais do portfólio avaliado.
2. Nenhuma citação de projeto sem `project_id`/`project_name` real presente em `evidence`.
3. Nenhuma resposta implica cobertura de 100% do portfólio quando a evidência é parcial.
4. Cada Project contribui exatamente um `Evidence` (o mais recente) — critério novo desta revisão, verificável por leitura de código/teste do `PortfolioEvidenceAssembler`.
5. Nenhuma resposta atribui importância a um projeto com base em sua posição na composição — critério novo desta revisão, verificável por teste de equivalência semântica sob reordenação.
6. `no_evidence()` funciona sem chamada ao LLM quando nenhum projeto do portfólio tem evidência de status.
7. Portfolio inexistente ou de outra organização nunca distinguível na resposta.
8. Nenhum método novo em `AdvisorFramework`/`AIContextEngine`.

---

## 7. Recomendação GO/NO-GO para o Technical Design

**GO.** Os dois pontos mandatados por esta revisão foram resolvidos com evidência de código: o peso da evidência (um `Evidence` por Project, o mais recente) é consistente com o Delivery Advisor por aplicar a mesma regra permanente (D-104) à unidade de composição correta para cada Advisor (§2.4); a ordem da composição nunca carregou significado semântico, confirmado pela leitura das próprias funções de ordenação já em produção (§3.1), exigindo apenas instrução textual de prompt, nenhum algoritmo. `AdvisorFramework`, `AIContextEngine`, Workflow Runtime, Event Pipeline, `RecommendationEngine` e `ExplanationEngine` confirmados preservados integralmente.

---

## 8. Próximo passo

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de prosseguir ao Technical Design (etapa 4).
