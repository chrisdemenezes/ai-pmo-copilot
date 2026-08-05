# Advisor Specification — Strategy Advisor

**Etapa 1 de 6** do ciclo institucional do Strategy Advisor (oitavo e último Advisor da Wave 5). Produzida sob autorização da Founder Decision "Abertura do ciclo institucional do Strategy Advisor", que segue a Founder Decision anterior — "Executive Advisor" (D-124) — que encerrou oficialmente o Executive Advisor e registrou o terceiro padrão consolidado Classe B (`ExecutiveEvidenceAssembler`, ao lado de `PortfolioEvidenceAssembler`/`PMOEvidenceAssembler`). Missão exclusivamente documental — nenhum código escrito, nenhum Technical Design, nenhuma implementação, nenhum trabalho da Etapa 2.

---

## 0. Base institucional já permanente, não redecidida aqui

- **Restrição permanente de "nunca delegação entre Advisors"** (`framework.py`, Fase 3): `AdvisorFramework.run()` executa exatamente um Advisor por chamada, nunca compõe a saída de um Advisor a partir da saída de outro. Fundamenta diretamente a proibição do Founder ("nunca consome respostas de outros Advisors").
- **Três padrões Classe B já consolidados (D-124)**: `PortfolioEvidenceAssembler`, `PMOEvidenceAssembler`, `ExecutiveEvidenceAssembler` coexistem sem generalização automática. O gatilho de generalização (quarto consumidor estruturalmente equivalente com duplicação real e comprovada) permanece a única via para um componente compartilhado — não presumido aqui, avaliado apenas se o Domain Blueprint concluir que a composição do Strategy Advisor coincide estruturalmente com um dos três já existentes.
- **Catálogo original já registrava a intenção geral** (`ENTERPRISE-ADVISOR-CATALOG.md` §3, anterior à abertura formal da Wave 5): "apoiar decisões de alinhamento estratégico entre iniciativas e objetivos organizacionais... avaliar se um conjunto de projetos/programas está alinhado a objetivos declarados (quando existirem no domínio); sinalizar desvio, nunca decidir a estratégia." Usado aqui como ponto de partida histórico, não como decisão vinculante — mesmo tratamento já dado ao catálogo original em toda a Wave 5.
- **`WAVE-3-INTEGRATION-BLUEPRINT.md` §6 já registra** o Strategy Advisor como consumidor do Decision Center (via ingestão de decisões já registradas na Knowledge Platform) — ponto de integração já previsto pela arquitetura antes desta Specification, não uma proposta nova.
- **Achado que corrige a premissa de AR-8 §4 sem reescrevê-lo (D-094 — aplicação prospectiva da governança, não retroativa):** AR-8 §4 classificara preliminarmente o Strategy Advisor como **Classe C — Declarative Intelligence**, citando como fonte "`AnalysisRecord`/objetivos declarados, quando existirem no domínio" e observando que, "mesmo mecanismo da Classe A", hoje cairia sempre em `no_evidence()`. Leitura direta de código (`src/database/models.py`) mostra que essa premissa não se sustenta estruturalmente: **não existe nenhum `kind` de `AnalysisRecord` para objetivos declarados** — os objetivos reais e já em produção desde a Wave 2 são os campos estruturados `Portfolio.strategic_objective` (`String(1000)`, nullable), `Program.objective` (`String(1000)`, nullable) e `Project.objective` (`String(1000)`, nullable), editáveis hoje pelas telas reais de Portfolio/Program Management (`web/app/portfolio-management`, `web/app/program-management`) e resolvidos via `DomainService.list_portfolios()`/`list_programs()`/`list_projects()` — nunca via `gather_context()`. Este achado não decide a classificação por si só (isso é o §3 abaixo) — apenas corrige o fato de código sobre o qual a classificação deve ser fundamentada.

---

## 1. Identidade do Strategy Advisor

### 1.1 Problema estratégico que resolve

Hoje, a STRATECH captura estratégia declarada em três níveis (`Portfolio.strategic_objective`, `Program.objective`, `Project.objective`) e evidência de execução real em `AnalysisRecord` (`kind="status"`, `kind="risk"`) — mas nada na plataforma confronta as duas coisas. Um Portfolio pode ter um objetivo estratégico declarado há meses enquanto os Projects sob ele executam com sinais de status/risco que nunca são verificados contra esse objetivo — o desalinhamento, se existir, só seria percebido manualmente, por quem lembrar de comparar as duas fontes por conta própria.

O Strategy Advisor resolve exatamente essa lacuna: verificar, com evidência primária rastreável, se a execução real permanece coerente com a estratégia oficialmente declarada — nunca inventando uma estratégia que não foi declarada, nunca decidindo se um desvio encontrado deve ser corrigido.

### 1.2 Decisão estratégica que apoia

A decisão de **realinhamento** — não a estratégia em si (isso nunca é responsabilidade do Advisor, per §2), mas a decisão de para onde a atenção de quem pode agir sobre estratégia (sponsor, PMO, liderança) deve ir: qual iniciativa está executando fora do que foi declarado, onde a estratégia declarada pode estar desatualizada frente à realidade da execução, e onde risco atual ameaça um objetivo estratégico específico. Sempre evidencia, nunca decide — mesmo limite permanente de todo Enterprise Advisor.

### 1.3 Valor entregue

Hoje, essa verificação de coerência exige que alguém releia manualmente o campo de objetivo declarado de cada Portfolio/Program/Project e o compare, também manualmente, com o estado de execução mais recente — um trabalho que não escala e que tende a não ser feito de forma consistente. O Strategy Advisor entrega essa verificação já pronta, sempre rastreável a `Portfolio.strategic_objective`/`Program.objective`/`Project.objective` e a `AnalysisRecord`s reais, nunca inventada.

### 1.4 Por que existe mesmo após os sete Advisors já implementados

| Advisor existente | O que já resolve | Por que o Strategy Advisor não duplica |
|---|---|---|
| **Executive Advisor** | Síntese de **o que exige atenção da liderança agora**, combinando status e risco, sem referência a nenhuma estratégia declarada | Executive Advisor nunca lê `strategic_objective`/`objective` nem compara execução a estratégia — responde "o que exige decisão agora"; Strategy Advisor responde "o que estamos fazendo continua alinhado com a estratégia declarada" (distinção do próprio Founder, ver §6) |
| **PMO Advisor** | Conformidade de **processo** (staleness, padrões de atraso) em toda a organização, exclusivamente `kind="status"` | PMO Advisor nunca lê objetivo estratégico declarado — sua pergunta é "os processos estão em dia?", nunca "isso está alinhado com o que foi declarado?" |
| **Governance Advisor** | Conformidade da **própria governança da STRATECH** (Decision Log, Technical Debt Register) contra o que já foi decidido institucionalmente | Governance Advisor nunca avalia estratégia de organização cliente — seu domínio é a governança da plataforma em si, nunca `Portfolio.strategic_objective` |
| **Portfolio Advisor** | Composição/equilíbrio de **um portfólio específico**, snapshot de status por Project | Portfolio Advisor nunca lê `strategic_objective` nem compara execução a estratégia — avalia cobertura de status, não alinhamento |
| **Delivery Advisor** | Trajetória temporal de **um único projeto** | Nunca lê objetivo declarado de nenhum nível, nunca compara a estratégia |
| **Risk Advisor** | Narrativa de risco de **um projeto/portfólio específico**, recomendação de mitigação | Nunca confronta risco com objetivo estratégico declarado — mitiga o risco em si, não avalia se ele ameaça uma estratégia |
| **Document Advisor** | Perguntas ad-hoc sobre **documentos institucionais genéricos** já ingeridos | Não é Q&A documental — mesmo que documentos estratégicos venham a participar (§4, aberto), o Strategy Advisor sempre compara, nunca apenas recupera texto |

Nenhum dos 7 Advisors existentes lê `Portfolio.strategic_objective`/`Program.objective`/`Project.objective`, e nenhum compõe uma comparação entre estratégia declarada e evidência de execução — confirmado por leitura de código (nenhuma referência a esses três campos em nenhum dos 7 pacotes de Advisor existentes). A lacuna é real, não presumida.

---

## 2. Papel institucional

O Strategy Advisor representa a camada de **alinhamento estratégico** da plataforma. Sua responsabilidade **não é criar estratégia** — é verificar se as evidências atuais permanecem coerentes com a estratégia oficialmente declarada.

**É expressamente proibido, permanentemente:**
- criar estratégia;
- escrever estratégia;
- decidir estratégia;
- alterar estratégia;
- recomendar mudança estratégica sem evidência;
- consumir `Recommendation` de outro Advisor;
- consumir `Explanation` de outro Advisor;
- atuar como orquestrador de Advisors;
- consolidar respostas previamente produzidas por outro Advisor;
- executar regras de negócio;
- interpretar além da evidência disponível.

**Toda análise deverá partir exclusivamente de estratégias previamente registradas** — nunca uma estratégia inferida a partir de padrões de execução, nunca uma estratégia sugerida pelo próprio Advisor na ausência de uma declaração real. Se nenhuma estratégia estiver declarada para o escopo avaliado, o Advisor nunca a inventa — reporta a ausência como tal (mesmo portão anti-alucinação já em produção em todos os Advisors). **Este princípio torna-se permanente.**

---

## 3. Classificação arquitetural

**Classe B**, determinada nesta etapa — não uma repetição automática da nota preliminar de AR-8 §4 (Classe C), pelas razões abaixo, aplicando exclusivamente as definições permanentes já vigentes na plataforma (D-104).

**Justificativa rigorosa, per D-104:** a fronteira entre Classe A e Classe B não é a quantidade de assuntos na resposta — é a **cardinalidade de fontes primárias de evidência independentes** que a montagem de contexto do Advisor consulta. A própria identidade definida pelo Founder nesta Founder Decision (§2 acima: "verificar se **as evidências atuais** permanecem coerentes **com a estratégia oficialmente declarada**") exige estruturalmente, no mínimo, duas fontes independentes:

1. uma fonte de **estratégia declarada** (candidatas identificadas no §4 — nunca decidido aqui qual exatamente);
2. uma fonte de **evidência de execução atual** (`AnalysisRecord`, já usada por 6 dos 7 Advisors existentes).

Comparar as duas coisas é, por definição, compor duas fontes primárias independentes — o que satisfaz Classe B por si só (D-104), **independentemente de qual par exato de fontes o Domain Blueprint venha a decidir**. Isso vale mesmo se a fonte de estratégia declarada acabar sendo RAG (Classe D em outros Advisors) em vez de um campo de domínio estruturado — a composição de **qualquer** fonte de estratégia declarada com **qualquer** fonte de execução já é, estruturalmente, Classe B.

**Sobre a nota preliminar de AR-8 §4 (Classe C):** essa nota foi escrita antes de qualquer Domain Blueprint do Strategy Advisor existir, assumindo uma única fonte ("mesmo mecanismo da Classe A"), citando `AnalysisRecord` como a origem dos objetivos declarados — premissa que o achado do §0 já mostrou não se sustentar estruturalmente (os objetivos reais vivem em `Portfolio.strategic_objective`/`Program.objective`/`Project.objective`, nunca em `AnalysisRecord`). Não se propõe reescrever AR-8 (D-094) — apenas fundamentar, nesta Specification, a classificação correta a partir da definição institucional permanente (D-104) e da identidade real que o próprio Founder define para este Advisor.

A observação de fundo de AR-8 permanece válida, apenas deslocada de nível: como `strategic_objective`/`objective` são campos nullable e hoje não populados por nenhum dado seed/demo real (§10.1), é plenamente esperado que, para muitos Portfolios/Programs/Projects, a fonte de estratégia declarada retorne vazia — cenário legítimo de cobertura parcial ou ausência, nunca um bug, mesma disciplina já aplicada a `no_evidence()`/cobertura parcial em todos os Advisors Classe B anteriores.

### 3.1 Fontes primárias que participarão da composição (identificação, não implementação)

Confirmadas como candidatas reais (ver §4, não decidido qual exatamente participa): fonte de estratégia declarada — `Portfolio.strategic_objective`/`Program.objective`/`Project.objective` (campos de domínio estruturados) e/ou documentos estratégicos oficiais via RAG; fonte de execução — `AnalysisRecord`/`kind="status"` e/ou `kind="risk"`. Nenhum mecanismo de composição (nome de componente, assinatura, local no código, exatamente quais `kind`s/campos) é decidido aqui.

---

## 4. Fontes primárias de evidência (reais, hoje, no código)

| Fonte | Onde existe hoje | Justificativa para o Strategy Advisor |
|---|---|---|
| **`Portfolio.strategic_objective`** | `src/database/models.py` (`String(1000)`, nullable), resolvido via `DomainService.list_portfolios(organization_id)`/`get_portfolio()`, já editável pela UI real de Portfolio Management | Fonte mais direta e já em produção de estratégia declarada no nível mais alto da cadeia Portfolio→Program→Project |
| **`Program.objective`** | Mesmo arquivo, mesmo padrão (`String(1000)`, nullable), resolvido via `DomainService.list_programs()`, editável pela UI de Program Management | Estratégia declarada no nível de Program — pode divergir do Portfolio (ex.: Program com objetivo mais tático dentro da mesma estratégia de Portfolio) |
| **`Project.objective`** | Mesmo arquivo, mesmo padrão (`String(1000)`, nullable), resolvido via `DomainService.list_projects()` | Estratégia declarada no nível mais granular — candidato, não decidido se participa (ver §8) |
| **`AnalysisRecord`/`kind="status"`** | `AIContextEngine.gather(organization_id, project_name, "status")`, já usado por Delivery/Portfolio/PMO/Executive Advisor | Evidência de execução real — sem ela não há o que comparar contra a estratégia declarada |
| **`AnalysisRecord`/`kind="risk"`** | Mesmo `gather()`, já usado por Risk/Executive Advisor | Permite responder diretamente a "os riscos atuais ameaçam objetivos estratégicos?" (exemplo do próprio Founder, §5) |
| **Knowledge Platform / RAG sobre documentos estratégicos oficiais** (candidata, não decidida) | `KnowledgeRepository`/`RagPipeline`, já usado por Document/Governance Advisor (Classe D); `WAVE-3-INTEGRATION-BLUEPRINT.md` §6 já registra o Strategy Advisor como consumidor do Decision Center via Knowledge Platform | Se a organização mantiver planejamento estratégico formal (OKRs, planos, atas de comitê estratégico) como documento ingerido, essa seria uma segunda via de "estratégia declarada", complementar ou alternativa aos campos de domínio — decisão reservada ao Domain Blueprint |
| **`DomainService` (Portfolio/Program/Project)** | Já usado por Portfolio/PMO/Executive Advisor para **resolver o escopo** — nunca como conteúdo citado até hoje | Papel duplo em aberto aqui, distinto de todo Advisor anterior: continua resolvendo escopo (quantos Portfolios/Programs/Projects existem), **mas também é o candidato mais direto a fonte citável de estratégia declarada** (`strategic_objective`/`objective`) — primeira vez que um objeto de `DomainService` poderia se tornar `Evidence` citável, não apenas infraestrutura de escopo; achado registrado, não resolvido aqui (ver §8) |

**Nunca**: `Recommendation`, `Explanation`, resposta de outro Advisor — confirmado, nenhuma dessas três aparece na tabela acima, porque nenhuma é uma fonte primária real.

---

## 5. Escopo de atuação

O Strategy Advisor deverá responder perguntas estratégicas como (exemplos que caracterizam o domínio, não uma lista de funcionalidades a implementar, per instrução explícita do Founder):

- a execução permanece alinhada à estratégia?
- existem iniciativas sem alinhamento estratégico?
- os riscos atuais ameaçam objetivos estratégicos?
- existem conflitos entre execução e estratégia declarada?
- quais decisões estratégicas merecem atenção?

Cada uma dessas perguntas, quando respondida, deve permanecer rastreável a `Portfolio.strategic_objective`/`Program.objective`/`Project.objective` reais e a `AnalysisRecord`s reais (e, se decidido pelo Domain Blueprint, a chunks de RAG reais) — nunca a uma estratégia inventada, nunca a uma inferência sem uma declaração real por trás.

---

## 6. Relação com os demais Advisors

**Distinção central, per a própria recomendação estratégica do Founder:**

```
Executive Advisor
  ↓
  decisão executiva — "o que exige atenção da liderança agora?"

Strategy Advisor
  ↓
  alinhamento estratégico — "o que estamos fazendo continua alinhado
  com a estratégia oficialmente declarada?"
```

| Advisor | Visão | Altitude | Como o Strategy Advisor complementa, sem sobrepor |
|---|---|---|---|
| **Executive Advisor** | Organização, execução+risco combinados, sem referência a estratégia declarada | Executiva (decisão) | Strategy Advisor nunca responde "o que exige atenção agora" — responde apenas sobre coerência com o que foi declarado, mesmo quando lê as mesmas fontes de execução (`status`/`risk`) |
| **PMO Advisor** | Organização, conformidade de processo (staleness) | Executiva (processo) | Strategy Advisor nunca avalia staleness — avalia alinhamento com estratégia, dimensão ortogonal a "os dados estão atualizados?" |
| **Governance Advisor** | Conformidade da própria governança STRATECH | Meta-institucional | Strategy Advisor nunca avalia a governança da plataforma — avalia a estratégia da organização cliente |
| **Portfolio Advisor** | Um portfólio, composição/equilíbrio | Tática | Strategy Advisor pode operar sobre o mesmo Portfolio, mas nunca avalia balanceamento — avalia se a execução observada condiz com `strategic_objective` |
| **Delivery Advisor** | Um projeto, trajetória temporal | Operacional | Strategy Advisor nunca narra a trajetória de um projeto isolado |
| **Risk Advisor** | Um projeto/portfólio, narrativa de risco e mitigação | Operacional/tático | Strategy Advisor nunca recomenda mitigação — usa o mesmo `kind="risk"` (se decidido) apenas para avaliar ameaça a um objetivo declarado |
| **Document Advisor** | Um documento por vez, sob demanda | Consulta pontual | Strategy Advisor nunca é uma interface de busca documental |

**Ausência completa de sobreposição confirmada**: nenhum dos 7 Advisors lê `strategic_objective`/`objective`, e nenhum compõe uma comparação entre estratégia declarada e evidência de execução — a pergunta que o Strategy Advisor responde é estruturalmente distinta da de todos os demais, mesmo quando compartilha a mesma fonte bruta de execução (`kind="status"`/`kind="risk"`) com Executive/PMO/Portfolio/Risk Advisor, exatamente como esses já convivem hoje sem sobreposição consumindo os mesmos `kind`s.

---

## 7. Limites de atuação

### 7.1 Limites permanentes de todo Enterprise Advisor (reafirmados, não específicos desta Epic)

- Nunca decide — apenas recomenda/evidencia, para quem decide.
- Nunca escreve no domínio (sem `create`/`update`/`delete` em nenhuma entidade).
- Sempre escopado por `organization_id` da sessão autenticada — nunca um parâmetro cross-tenant.
- Portão anti-alucinação (`RecommendationEngine.build()`/`no_evidence()`) — nenhuma citação sem `Evidence` real por trás.
- Nunca invocado por Workflow Runtime nem registrado como handler de Event Pipeline.
- `AdvisorFramework.run()` executa exatamente um Advisor por chamada — nunca delegação entre Advisors (§2).

### 7.2 Limites específicos do Strategy Advisor

- **Nunca cria estratégia** — se nenhum `strategic_objective`/`objective` estiver declarado para o escopo avaliado, o Advisor reporta a ausência, nunca infere um objetivo a partir de padrões de execução.
- **Nunca modifica estratégia** — nenhuma escrita em `Portfolio.strategic_objective`/`Program.objective`/`Project.objective`, em nenhuma circunstância; é um Advisor de leitura, como todos os demais.
- **Nunca executa regra de negócio** — não decide se um desvio encontrado é aceitável ou exige correção, apenas evidencia o desvio.
- **Nunca consome respostas de outros Advisors** — reafirmação explícita (mesmo que outro Advisor já tenha avaliado a mesma evidência bruta, o Strategy Advisor sempre lê a fonte primária diretamente, nunca a interpretação de outro Advisor sobre ela).
- **Nunca interpreta além da evidência** — nenhuma inferência de intenção estratégica não declarada explicitamente em `strategic_objective`/`objective` ou em documento estratégico real.
- **Nunca recomenda mudança estratégica sem evidência** — qualquer sinalização de possível desatualização da estratégia declarada deve ser fundamentada em evidência de execução real, nunca uma opinião do modelo sobre se a estratégia em si está correta.

---

## 8. Questões arquiteturais abertas (reservadas ao Domain Blueprint, não decididas aqui)

1. **Quais níveis da cadeia participam como fonte de estratégia declarada** — apenas `Portfolio.strategic_objective` (nível mais alto), ou também `Program.objective`/`Project.objective`? Não presumido.
2. **Como um campo de domínio se torna um `Evidence` citável** — nenhum Advisor até hoje usou um objeto de `DomainService` como conteúdo citado (sempre resolução de escopo); o contrato `Evidence` é genérico o suficiente (mesmo argumento já usado para RAG em AR-8 §4.1), mas a questão de que `source_type`/`source_id` usar para um Portfolio/Program/Project (nunca um `AnalysisRecord`) é uma decisão real de Technical Design, não decidida aqui.
3. **Papel de RAG/documentos estratégicos oficiais** — se os campos de domínio já são suficientes como fonte de estratégia declarada, ou se documentos institucionais formais (via Knowledge Platform, já antecipados em `WAVE-3-INTEGRATION-BLUEPRINT.md` §6) são necessários como fonte adicional ou alternativa; não presumido nem a favor nem contra.
4. **Qual evidência de execução participa** — `kind="status"` apenas, `kind="risk"` também (mesma dupla do Executive Advisor), ou uma composição diferente? Reservado ao Domain Blueprint.
5. **Escopo de resolução** — organizacional (como PMO/Executive Advisor) ou por Portfolio específico (como Portfolio Advisor)? Os exemplos do próprio Founder ("existem iniciativas sem alinhamento estratégico?") sugerem uma leitura organizacional, mas isso não é decidido nesta etapa.
6. **Quarto componente de composição vs. reaproveitamento** — dado que já existem três padrões Classe B consolidados (D-124), avaliar se a composição do Strategy Advisor é estruturalmente distinta o suficiente para justificar um quarto componente (`StrategyEvidenceAssembler`, nome provisório) ou se coincide, por acaso, com um já existente — não presumido, sujeito ao mesmo gatilho de generalização já registrado (quarto consumidor estruturalmente equivalente).
7. **Tratamento de cobertura parcial de estratégia declarada** — ex.: Portfolio tem `strategic_objective` preenchido mas nenhum de seus Programs/Projects tem `objective`; como isso se reflete em cobertura estrutural (contagens análogas às já estabelecidas em Portfolio/PMO/Executive Advisor) é decisão do Domain Blueprint.

Nenhuma dessas sete questões é resolvida aqui — cada uma exige leitura de código adicional e ponderação própria do Domain Blueprint.

---

## 9. Critérios de sucesso

- Toda afirmação de alinhamento/desalinhamento é rastreável a um `strategic_objective`/`objective` real e a um `AnalysisRecord` real (e, se decidido, a um documento estratégico real via RAG) — nenhuma estratégia inventada, nenhuma inferência sem declaração real.
- Nenhuma citação de `Recommendation`/`Explanation`/resposta de outro Advisor como evidência, em nenhuma circunstância.
- Nenhuma escrita em `strategic_objective`/`objective` ou em qualquer outra entidade de domínio, em nenhuma circunstância.
- Ausência de estratégia declarada para o escopo avaliado é reportada como tal, nunca preenchida por inferência — mesmo portão anti-alucinação já em produção em todos os Advisors.
- Cobertura (quantos Portfolios/Programs/Projects têm estratégia declarada, quantos têm evidência de execução, quantos têm ambos) sempre estrutural, nunca calculada pelo LLM — mesmo padrão já provado em Portfolio/PMO/Executive Advisor.
- Nenhuma chamada ao LLM quando não há evidência primária suficiente para sintetizar (mesmo portão anti-alucinação).
- Nenhuma mudança de assinatura ou comportamento em `AdvisorFramework`/`AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/Workflow Runtime/Event Pipeline exigida por esta Specification.

---

## 10. Riscos

### 10.1 Comprovados (fato de código, confirmado nesta etapa)

- `Portfolio.strategic_objective`/`Program.objective`/`Project.objective` são campos nullable, e nenhum script de seed/demo real da plataforma os popula hoje — confirmado por busca de código. Isso significa que, na prática atual, é esperado que o Strategy Advisor caia legitimamente em cobertura zero ou parcial na maioria das organizações — cenário correto, não um defeito, mesma disciplina já validada para cobertura zero/parcial em todos os Advisors Classe B anteriores.
- Nenhum Advisor até hoje usou um objeto de `DomainService` (Portfolio/Program/Project) como fonte de `Evidence` citável — até agora, `DomainService` sempre serviu exclusivamente para resolução de escopo. Isso é fato de código, não uma barreira arquitetural (o contrato `Evidence` já provou ser genérico o bastante para RAG em AR-8 §4.1), mas é uma extensão de uso ainda não exercida na prática, comprovadamente diferente de tudo que já existe.

### 10.2 Hipóteses (plausíveis, não confirmadas — a resolver no Domain Blueprint)

- Reaproveitar um dos três `EvidenceAssembler`s já existentes pode não se aplicar, dado que nenhum deles hoje lê campos de domínio como evidência (todos leem exclusivamente `AnalysisRecord`) — hipótese registrada, não assumida como verdadeira nem falsa; poderia haver uma forma de composição que reaproveite parte do padrão sem reaproveitar o componente inteiro.
- Inclusão de documentos estratégicos via RAG poderia criar sobreposição de altitude com Document/Governance Advisor, ou com o próprio Decision Center já registrado em `WAVE-3-INTEGRATION-BLUEPRINT.md` §6 — hipótese registrada, não assumida.

### 10.3 Riscos futuros (fora do escopo desta Epic, registrados por transparência)

- A Wave 6 — Executive Intelligence consumirá os 8 Enterprise Advisors, incluindo o Strategy Advisor (§11) — a classificação e os limites definidos aqui devem permanecer estáveis o suficiente para servir de insumo a essa Wave futura, mas nenhuma decisão da Wave 6 é antecipada ou presumida nesta Specification.

---

## 11. Relação com a Wave 6 — Executive Intelligence

Per `web/lib/mock/mission-control-data.ts` (`ENTERPRISE_PROGRAM_WAVES`, Wave 6) e `WAVE-3-INTEGRATION-BLUEPRINT.md` §5/§11 (já referenciado desde D-071): a Wave 6 — Executive Intelligence **consome os 8 Enterprise Advisors** da Wave 5, e seu status atual é explicitamente "depende estruturalmente da Wave 5 estar completa". O Strategy Advisor é, hoje, o único dos 8 Advisors ainda não concluído.

**Avaliação explícita, sem decidir roadmap:** o Strategy Advisor representa a última dependência arquitetural nomeada para o encerramento completo da Wave 5, e portanto a última dependência estrutural conhecida para a Wave 6 poder iniciar — confirmado por leitura direta de Mission Control e do Integration Blueprint, não uma inferência desta Specification. Nenhuma decisão sobre o que a Wave 6 fará com os 8 Advisors, sobre seu escopo, ou sobre quando ela deve iniciar é tomada ou antecipada aqui — apenas a dependência arquitetural em si é identificada, exatamente como pedido pelo Founder.

---

## 12. Regras permanentes — confirmação de aderência

Esta Specification usa exclusivamente arquitetura, código e documentos reais já citados (`src/database/models.py`, `DomainService`, `AIContextEngine`, `ENTERPRISE-ADVISOR-CATALOG.md`, `WAVE-3-INTEGRATION-BLUEPRINT.md`, `AR-8-WAVE-5-ENTERPRISE-ADVISOR-MODEL-REVIEW.md`, Mission Control) — nenhuma abstração nova proposta, nenhuma mudança a `AdvisorFramework`/`AIContextEngine`/Workflow Runtime/Event Pipeline/`RecommendationEngine`/`ExplanationEngine`, nenhuma infraestrutura nova criada, nenhuma generalização de componente existente antecipada.

---

## 13. Recomendação

**GO para o Domain Blueprint.**

Identidade, papel institucional (verificação de coerência, nunca criação de estratégia — princípio permanente), classificação (Classe B, determinada e justificada rigorosamente per D-104, corrigindo a premissa factual da nota preliminar de AR-8 §4 sem reescrevê-la), domínio de responsabilidade, fontes primárias candidatas e confirmadas (incluindo o achado de que `Portfolio.strategic_objective`/`Program.objective`/`Project.objective` — não `AnalysisRecord` — são a fonte real de estratégia declarada), limites, relação com os 7 Advisors existentes, avaliação da dependência estrutural da Wave 6, e riscos residuais estão todos definidos. Sete questões arquiteturais permanecem explicitamente reservadas ao Domain Blueprint (§8), nenhuma decidida ou presumida nesta etapa.

Retorno obrigatório para Executive Review do Founder. Nenhum trabalho da Etapa 2 (Domain Blueprint) será iniciado sem nova aprovação explícita.
