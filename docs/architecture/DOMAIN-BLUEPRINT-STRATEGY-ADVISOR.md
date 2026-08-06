# Domain Blueprint — Strategy Advisor

**Etapa 2 de 6** do ciclo institucional do Strategy Advisor (oitavo e último Advisor da Wave 5). Produzido sob autorização da Founder Decision que aprovou a Advisor Specification (`ADVISOR-SPECIFICATION-STRATEGY-ADVISOR.md`) com **GO para o Domain Blueprint**, fixando como oficiais: Classe B; responsabilidade permanente de verificar alinhamento entre estratégia declarada e execução observada; proibição permanente de criar/modificar/decidir estratégia ou inferir objetivos inexistentes; e — decisão central desta etapa — que `Portfolio.strategic_objective`/`Program.objective`/`Project.objective` **substituem oficialmente** a hipótese preliminar de AR-8 §4 como a referência arquitetural sobre onde a estratégia declarada reside. Nenhum código escrito nesta etapa.

---

## 0. O que já é oficial (não reaberto aqui)

| Decisão | Origem |
|---|---|
| Classe B, definitivamente | Advisor Specification + Founder Decision |
| Responsabilidade permanente: verificar alinhamento entre estratégia declarada e execução observada — nunca criar estratégia | Founder Decision |
| Permanentemente proibido: criar, modificar, decidir estratégia; inferir objetivos inexistentes | Founder Decision |
| Fonte oficial dos objetivos declarados: `Portfolio.strategic_objective`, `Program.objective`, `Project.objective` — substitui a hipótese preliminar de AR-8 §4 | Founder Decision (item 4) |
| Preservação integral de `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline nesta etapa | Founder Decision |

---

## 1. Executive Summary

Este Domain Blueprint resolve as seis questões que a Founder Decision delegou explicitamente: fonte oficial da estratégia; unidade de alinhamento; composição de evidências; tratamento da ausência de estratégia; cobertura parcial; escopo definitivo da comparação entre estratégia e execução.

**Fonte oficial da estratégia**: confirmada pelo próprio Founder — `Portfolio.strategic_objective`, `Program.objective`, `Project.objective` (todos `String(1000)`, nullable, `src/database/models.py`), resolvidos via `DomainService`, nunca via `gather_context()`/RAG. Nenhuma outra fonte é reconhecida como oficial nesta etapa (documentos estratégicos via RAG permanecem candidatos não decididos, ver §8).

**Unidade de alinhamento**: **três unidades independentes** — Portfolio, Program e Project — cada uma avaliada exclusivamente contra o **seu próprio** campo de objetivo declarado, nunca por herança entre níveis (herdar o objetivo de um Program para um Project sem `objective` próprio seria inferir uma estratégia que o Project não declarou, violando a proibição permanente do item 3). Escolha estrutural, não arbitrária: como `AnalysisRecord` só se associa a `project_id` (mesma restrição já usada para fixar a unidade de composição de PMO/Portfolio/Executive Advisor), a evidência de execução de Program/Portfolio é sempre a **agregação** da evidência de execução dos Projects sob eles — nunca uma evidência própria desses níveis.

**Composição de evidências**: um único conjunto de chamadas `gather_context(kind="status")`/`gather_context(kind="risk")`, uma vez por Project da organização — nunca repetidas por nível. A agregação para Program/Portfolio é uma **releitura** (agrupamento) dessas mesmas evidências já buscadas, nunca uma nova consulta — o volume total de chamadas permanece idêntico ao já aprovado para o Executive Advisor (2 × total de Projects da organização), independentemente de quantos níveis participarem da comparação.

**Tratamento de ausência**: ausência total (nenhuma unidade, em nenhum nível, tem estratégia declarada) aciona `no_evidence()`, zero chamada ao LLM — cenário hoje esperado como comum, já que nenhum dado seed/demo popula esses campos (risco já registrado na Advisor Specification). Ausência por unidade (uma unidade sem `objective`/`strategic_objective`, ou com objetivo declarado mas sem nenhuma evidência de execução) é contada estruturalmente, nunca inferida.

**Cobertura parcial**: síntese permitida quando pelo menos uma unidade, em qualquer nível, for **comparável** (tem estratégia declarada **e** evidência de execução) — com limitação explicitamente declarada sobre as unidades não comparáveis, mesma disciplina já provada em Portfolio/PMO/Executive Advisor.

**Escopo definitivo da comparação**: organizacional (todos os Portfolios/Programs/Projects da organização da sessão, nunca um `portfolio_id` fornecido pelo chamador); a comparação nunca cruza unidades — a execução de um Project nunca é comparada à estratégia declarada de outro Project, Program ou Portfolio que não seja o seu próprio ou o de sua cadeia de pertencimento direta; fontes de execução restritas a `kind="status"`/`kind="risk"` (mesma dupla já aprovada para o Executive Advisor).

**Recomendação: GO para a Architecture Review.**

---

## 2. Modelo de domínio

### 2.1 Três unidades de alinhamento, não uma

Diferente de todos os Advisors anteriores (uma única unidade de composição — sempre Project), o Strategy Advisor opera sobre **três unidades estruturalmente distintas**, porque a estratégia declarada existe em três níveis reais da cadeia Portfolio→Program→Project:

| Unidade | Campo de estratégia declarada | Evidência de execução |
|---|---|---|
| **Portfolio** | `Portfolio.strategic_objective` | Agregação de `kind="status"`/`kind="risk"` de **todos** os Projects sob esse Portfolio (via seus Programs) |
| **Program** | `Program.objective` | Agregação de `kind="status"`/`kind="risk"` de **todos** os Projects sob esse Program |
| **Project** | `Project.objective` | `kind="status"`/`kind="risk"` **diretos** desse Project — única unidade com evidência de execução própria, não agregada |

### 2.2 Por que não há herança entre níveis

Se um Project não tem `objective` próprio mas seu Program tem `objective` declarado, o Strategy Advisor **nunca** atribui o objetivo do Program a esse Project como se fosse dele — isso seria inferir uma estratégia que aquele Project especificamente nunca declarou, violando a proibição permanente do item 3 da Founder Decision ("inferir objetivos inexistentes"). Cada unidade só é avaliada contra o campo que ela mesma declarou.

### 2.3 Projects órfãos (sem Program)

`Project.program_id` é nullable (fato de código, `src/database/models.py`) — Projects migrados da Épico 1 ou criados sem vínculo a um Program real existem hoje. Um Project órfão participa normalmente da unidade **Project** (se tiver `objective` próprio), mas nunca é alcançável por nenhuma agregação de Program/Portfolio, porque não há caminho de traversal até ele a partir de nenhum Portfolio — mesma limitação estrutural já aceita implicitamente por toda resolução de escopo via `list_programs()`/`list_projects()` na plataforma.

### 2.4 O que cada `Evidence` representa

Duas naturezas de `Evidence`, nunca confundidas:

1. **Evidência de estratégia declarada** — um `Portfolio`/`Program`/`Project` com seu campo de objetivo preenchido. Primeira vez em toda a Wave 5 que um objeto de `DomainService` se torna `Evidence` citável, não apenas infraestrutura de resolução de escopo (achado já registrado na Advisor Specification §4/§8, confirmado aqui: o contrato `Evidence` já provou ser genérico o suficiente para isso, mesmo argumento já usado para RAG em AR-8 §4.1). Nomenclatura exata de `source_type`/`source_id` para este caso (ex.: `"portfolio_objective"`/`portfolio.id`) é decisão da Architecture Review, não desta etapa.
2. **Evidência de execução** — um `AnalysisRecord` real (`kind="status"` ou `kind="risk"`), exatamente a mesma natureza já usada por Executive/PMO/Portfolio/Delivery/Risk Advisor.

---

## 3. Fonte oficial da estratégia declarada

Confirmada pela própria Founder Decision (item 4): `Portfolio.strategic_objective`, `Program.objective`, `Project.objective` — três campos `String(1000)` nullable, `src/database/models.py`, resolvidos via `DomainService.list_portfolios()`/`list_programs()`/`list_projects()`, já editáveis pelas telas reais de Portfolio/Program Management desde a Wave 2.

| Fonte | Status |
|---|---|
| `Portfolio.strategic_objective` | Confirmada, oficial |
| `Program.objective` | Confirmada, oficial |
| `Project.objective` | Confirmada, oficial |
| `AnalysisRecord`/objetivos declarados | **Descartada** — não existe nenhum `kind` para isso (achado já registrado na Advisor Specification, ratificado pelo item 4 da Founder Decision) |
| Knowledge Platform/RAG sobre documentos estratégicos oficiais | Fora de escopo desta etapa — candidata não decidida, sem caso de uso real demonstrado ainda (ver §8) |
| `Recommendation`/`Explanation`/respostas de outros Advisors | Proibido permanentemente |

---

## 4. Escopo de resolução

**Organizacional**, via `DomainService.list_portfolios(organization_id)` — mesma disciplina de resolução de escopo já usada por todos os Advisors organizacionais (PMO/Executive), nunca um `portfolio_id` fornecido pelo chamador. Para cada Portfolio, `list_programs(portfolio_id=portfolio.id)`; para cada Program, `list_projects(...)` — exatamente a mesma cadeia de traversal que o `PortfolioEvidenceAssembler` já percorre hoje para um único Portfolio (Domain Blueprint do Portfolio Advisor), aqui repetida para **todos** os Portfolios da organização, nenhum método novo.

A comparação nunca cruza unidades: a execução de um Project nunca é avaliada contra a estratégia declarada de um Program/Portfolio que não seja o seu próprio ancestral direto (via `Project.program_id` → `Program.portfolio_id`) — nunca contra a estratégia de outro Portfolio da mesma organização, nunca contra a de outra organização.

Fontes de execução restritas a `AnalysisRecord`/`kind="status"` e `kind="risk"` — mesma dupla já aprovada para o Executive Advisor, mesmo mecanismo (`evidence[0]`, mais recente, nunca histórico — a mesma justificativa já usada pelo Executive Advisor se aplica aqui: a pergunta é sobre alinhamento **agora**, não sobre trajetória).

---

## 5. Componente de composição

### 5.1 Nome e localização (provisórios, a confirmar no Technical Design)

`StrategyEvidenceAssembler`, `src/agents/strategy_advisor/evidence_assembler.py` — exclusivo do pacote do Advisor, mesmo padrão já estabelecido pelos três `EvidenceAssembler`s existentes. Nunca em `src/services/`.

**Quarto componente de composição Classe B, estruturalmente distinto dos três já existentes** (`PortfolioEvidenceAssembler`, `PMOEvidenceAssembler`, `ExecutiveEvidenceAssembler`) — nenhum dos três lê campos de domínio como `Evidence`, todos leem exclusivamente `AnalysisRecord`. Confirma que a não-generalização (D-124) permanece correta: o gatilho de generalização exige um **quarto consumidor estruturalmente equivalente** a um dos três já existentes, e o `StrategyEvidenceAssembler` não é equivalente a nenhum deles — mistura duas naturezas de `Evidence` (estratégia declarada + execução) que nenhum dos três já existentes mistura.

### 5.2 Responsabilidade

1. Resolver todos os Portfolios da organização (`DomainService.list_portfolios(organization_id)`).
2. Para cada Portfolio, resolver seus Programs (`list_programs(portfolio_id)`); para cada Program, resolver seus Projects (`list_projects(...)`) — mesma traversal já usada pelo `PortfolioEvidenceAssembler`, repetida para todos os Portfolios.
3. Para cada Project da organização, chamar exatamente uma vez `gather_context(kind="status")` e uma vez `gather_context(kind="risk")` — capturar apenas `evidence[0]` de cada (mais recente, nunca histórico). **Nunca repetir essas chamadas por nível** — o mesmo par de resultados por Project alimenta tanto a unidade Project quanto as agregações de Program/Portfolio.
4. Para cada Project com `objective` preenchido: montar a unidade Project (estratégia declarada do Project + sua própria evidência de execução do passo 3).
5. Para cada Program com `objective` preenchido: montar a unidade Program (estratégia declarada do Program + a união da evidência de execução de todos os seus Projects, já obtida no passo 3 — nenhuma nova consulta).
6. Para cada Portfolio com `strategic_objective` preenchido: montar a unidade Portfolio (estratégia declarada do Portfolio + a união da evidência de execução de todos os Projects sob seus Programs, já obtida no passo 3).
7. Calcular cobertura estrutural por nível (§7) — nunca pelo LLM.
8. Entregar a lista consolidada de `Evidence` (estratégia declarada + execução, de todas as unidades comparáveis) ao `AdvisorFramework.run()` — **nunca calcula alinhamento ou desvio em código**: isso é interpretação exclusiva do `StrategyAdvisorAgent`/LLM, sempre fundamentada nas evidências entregues, nunca uma regra determinística de "desvio" (mesma disciplina já aplicada a "nenhum ranking determinístico" no Executive Advisor).

### 5.3 Rota permanece fina

`POST /strategy-advisor/ask` segue exatamente o mesmo formato já estabelecido: injeta dependências, instancia `StrategyEvidenceAssembler`, chama `.assemble()`, instancia o Agent, chama `framework.run()`, mapeia a resposta — nenhuma lógica de composição na rota.

---

## 6. `gather_context_many()` — reafirmação, não reaberta

Mesma decisão já registrada para o Executive Advisor, aplicável aqui sem necessidade de nova análise: duas chamadas explícitas por Project (`kind="status"`/`kind="risk"`), dentro do `StrategyEvidenceAssembler`, resolvem toda a composição — inclusive a agregação multi-nível (§5.2, passos 5-6), que é apenas um reagrupamento em memória das mesmas evidências já buscadas. Nenhuma mudança de `AdvisorFramework`/`AIContextEngine` é necessária ou justificada.

---

## 7. Cobertura estrutural e tratamento de ausência

### 7.1 Contagens conceituais por nível

Para cada nível `L` ∈ {Portfolio, Program, Project}, três contagens estruturais:

| Campo conceitual | Definição |
|---|---|
| `{L}_total` | Todas as instâncias de `L` na organização |
| `{L}_with_declared_strategy` | Instâncias de `L` com o campo de objetivo preenchido |
| `{L}_with_execution_evidence` | Instâncias de `L` com pelo menos uma evidência de execução (direta, para Project; agregada, para Program/Portfolio) |

**Unidade comparável** = instância com **ambas** (`with_declared_strategy` ∩ `with_execution_evidence`) — apenas unidades comparáveis entram no conjunto de `Evidence` entregue ao LLM. Nomes de campo definitivos do modelo de resposta (achatados ou não por nível) são decisão do Technical Design, não desta etapa.

### 7.2 Ausência total

Nenhuma unidade comparável em nenhum nível, em toda a organização → `no_evidence()`, zero chamada ao LLM — mesmo portão anti-alucinação já em produção. Cenário hoje esperado como o mais comum: nenhum script de seed/demo popula `strategic_objective`/`objective` (risco já registrado na Advisor Specification §10.1), portanto a maioria das organizações cairá aqui até que dados reais sejam declarados pelos usuários.

### 7.3 Ausência parcial

Síntese permitida sempre que pelo menos uma unidade, em qualquer nível, for comparável — com **limitação explicitamente declarada** sobre quantas unidades de cada nível não puderam ser avaliadas (sem estratégia declarada, ou sem evidência de execução), usando as contagens estruturais do §7.1 — nunca uma generalização silenciosa para uma unidade sem evidência.

### 7.4 Caso particular: estratégia declarada sem evidência de execução

Uma unidade com objetivo declarado mas **nenhuma** evidência de execução associada (nem direta, nem agregada) não é "sem estratégia" — é "não comparável por falta de execução". Contada separadamente (`{L}_with_declared_strategy` mas fora de `{L}_with_execution_evidence`), nunca tratada como ausência de estratégia.

---

## 8. Questões explicitamente fora de escopo desta etapa (reservadas à Architecture Review)

1. **Nomenclatura exata de `Evidence` para estratégia declarada** — qual `source_type`/`source_id` usar para um Portfolio/Program/Project (§2.4) é decisão de Technical Design, não desta etapa; a Architecture Review deve confirmar a compatibilidade formal com o contrato `Evidence` (já argumentada aqui, não formalmente decidida).
2. **Papel de RAG/documentos estratégicos oficiais** — permanece candidato não decidido (já identificado na Advisor Specification, `WAVE-3-INTEGRATION-BLUEPRINT.md` §6); nenhuma inclusão automática nesta etapa.
3. **Modelo de resposta definitivo** (nomes de campo, achatamento por nível ou não, modelo de citação — `CitedProject`/`ExecutiveCitedEvidence` não se aplicam diretamente, dado que este Advisor cita Portfolios/Programs/Projects, não apenas Projects) — reservado à Architecture Review.
4. **Tratamento de Projects órfãos** (`program_id IS NULL`, §2.3) no modelo de resposta — participam da unidade Project normalmente, mas como isso aparece em cobertura por nível (já que não têm Program/Portfolio ancestral) é decisão de Technical Design.

---

## 9. Limites de atuação (reafirmados, específicos desta Epic)

- Nunca cria, escreve, decide ou altera `strategic_objective`/`objective` — Advisor de leitura, como todos os demais.
- Nunca infere um objetivo declarado a partir de padrões de execução, nem herda o objetivo de um nível ancestral para um nível sem declaração própria (§2.2).
- Nunca calcula alinhamento/desvio deterministicamente em código — sempre interpretação do LLM, fundamentada em evidência (§5.2, passo 8).
- Nunca substitui Executive Advisor (decisão executiva sem referência a estratégia), PMO Advisor (conformidade de processo), Governance Advisor (governança da própria STRATECH) ou Portfolio Advisor (composição/equilíbrio de um portfólio específico) — reafirmação da Advisor Specification §1.4/§6.
- Nunca consome `Recommendation`/`Explanation`/resposta de outro Advisor.
- Nunca afirma tendência histórica — estruturalmente impossível, já que apenas o registro de execução mais recente de cada `kind` chega ao prompt (mesma disciplina do Executive Advisor).

---

## 10. Riscos

| Risco | Natureza | Mitigação registrada |
|---|---|---|
| `strategic_objective`/`objective` não populados por nenhum seed/demo real hoje | Comprovado (já registrado na Advisor Specification §10.1) | Ausência total tratada como cenário legítimo (§7.2), nunca um defeito |
| Primeira vez que `DomainService` (não `AnalysisRecord`) se torna `Evidence` citável | Comprovado (fato de código, nunca exercido antes) | Compatibilidade conceitual com o contrato `Evidence` já argumentada (§2.4); nomenclatura exata reservada à Architecture Review (§8.1) |
| Modelo de três unidades independentes (Portfolio/Program/Project) é mais complexo que qualquer Advisor anterior (um único nível) | Comprovado (decisão desta etapa) | Nenhuma herança entre níveis (§2.2) mantém cada unidade simples e isolada; agregação reaproveita evidência já buscada, sem custo adicional de volume (§5.2, passo 3) |
| Volume de chamadas | Comprovado, mas **não aumentado** em relação ao já aprovado para o Executive Advisor | 2 × total de Projects da organização, independentemente do número de níveis avaliados — mesmo gatilho de performance já aprovado (20+ chamadas sequenciais ou p95 > 3s) |
| Projects órfãos (`program_id IS NULL`) não alcançáveis por agregação de Program/Portfolio | Comprovado (fato de código, §2.3) | Participam normalmente da unidade Project; tratamento em cobertura por nível reservado ao Technical Design (§8.4) |

Nenhum risco listado é bloqueante para a Architecture Review.

---

## 11. Critérios de sucesso

- Toda afirmação de alinhamento/desvio rastreável a uma unidade real (Portfolio/Program/Project) com seu campo de objetivo declarado real e a `AnalysisRecord`(s) real(is) — nenhuma estratégia inventada, nenhuma inferência entre níveis.
- Nenhuma citação de `Recommendation`/`Explanation`/resposta de outro Advisor, em nenhuma circunstância.
- Nenhuma escrita em `strategic_objective`/`objective` ou em qualquer outra entidade de domínio.
- Cobertura estrutural por nível sempre calculada em código, nunca pelo LLM.
- Nenhum cálculo determinístico de alinhamento/desvio em código — sempre interpretação do LLM sobre evidência real.
- Nenhuma chamada ao LLM quando nenhuma unidade, em nenhum nível, for comparável.
- Nenhuma mudança de assinatura em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline exigida por este Blueprint.

---

## 12. Recomendação

**GO para a Architecture Review do Strategy Advisor.**

Resolvido nesta etapa: fonte oficial da estratégia (confirmada pela própria Founder Decision); unidade de alinhamento (três unidades independentes — Portfolio, Program, Project — sem herança entre níveis); composição de evidências (`StrategyEvidenceAssembler`, reaproveitando as mesmas chamadas de execução para todos os níveis, sem custo adicional de volume); tratamento de ausência total e parcial; cobertura estrutural conceitual por nível; escopo definitivo da comparação (organizacional, nunca cruzando unidades).

Reservado à Architecture Review/Technical Design, não decidido aqui: nomenclatura exata de `Evidence`/modelo de resposta/citação; papel de RAG; tratamento fino de Projects órfãos em cobertura.

Retorno obrigatório para Executive Review do Founder. Nenhum trabalho da Architecture Review será iniciado sem nova aprovação explícita.
