# STRATECH V2 — Governance Model

Formaliza como decisões são tomadas, especificadas, revisadas, implementadas e encerradas na STRATECH V2. Este documento é a **fonte primária** do modelo de papéis e do fluxo de estágios — `docs/product/STRATECH_V2_MASTER_ROADMAP.md` (Seção 2, Product Lifecycle) apresenta a mesma informação em formato de painel executivo, derivada deste documento, não o contrário.

> **Nota de institucionalização (EO-018):** este documento formaliza o modelo de 3 papéis já registrado em LL-002 (`LESSONS_LEARNED.md`) e o fluxo de estágios já descrito na Seção 2 do Master Roadmap. Por instrução explícita da EO-018, o Master Roadmap não foi alterado nesta consolidação — como consequência, sua Seção 2 e este documento descrevem o mesmo fluxo em paralelo até que uma EO futura autorize atualizar o Master Roadmap para apontar para este arquivo como fonte primária. Ver "Lacunas" na entrega da EO-018.

---

## 1. Modelo de papéis

Três papéis distintos e independentes, conforme LL-002:

| Papel | Responsabilidade | O que nunca faz sozinho |
|---|---|---|
| **Founder** | Decisões estratégicas, autorização de merge, configuração administrativa do GitHub (rulesets, branch protection) | Não implementa código nem revisa arquitetura de forma independente |
| **Claude / Engineering Lead** | Implementação, testes com evidência real (não apenas leitura de código), execução de CI, parar explicitamente quando um gate não pode ser comprovado | Nunca realiza merge sem autorização explícita (EO-MERGE); nunca comita commits parciais |
| **ChatGPT / Architecture & Product Advisor** | Revisão arquitetural independente de TDS e Pull Requests, emissão de Engineering Orders, recomendação APPROVE / APPROVED WITH OBSERVATIONS / CHANGES REQUESTED / REJECT | Não implementa; sua revisão é sempre anterior à decisão de merge do Founder, nunca a substitui |

**Regra de independência:** nenhum papel revisa o próprio trabalho como Architecture Review — a revisão de uma TDS ou PR produzida pelo Claude/Engineering Lead é sempre também the ChatGPT/Architecture & Product Advisor (ou, em sua ausência, o próprio Founder atuando explicitamente nesse papel, como ocorreu na Executive Pre-Merge Architecture Review do PR #39).

## 2. Fluxo de estágios (Product Lifecycle) — Foundation Phase (Épicos 1-2)

> Este fluxo foi o utilizado durante a Foundation Phase (Épicos 1 e 2). A partir da EO-021, o fluxo oficial para novo trabalho é o **Product-First** (Seção 2A) — este registro é preservado sem alteração, por ser histórico (regra de governança #6 abaixo).

```mermaid
flowchart LR
    A[Vision] --> B[Programs]
    B --> C[Releases]
    C --> D[Epics]
    D --> E[Engineering Orders]
    E --> F[Architecture]
    F --> G[Implementation]
    G --> H[Pull Request]
    H --> I[Merge]
    I --> J[Release]
    J --> K[GA]
```

| Estágio | O que é | Artefato que governa | Papel responsável |
|---|---|---|---|
| Vision | Visão de produto e diferenciação V1→V2 | `Enterprise-Architecture-Blueprint-v2.0.html` | Founder |
| Programs | Domínios funcionais do Domain Map | Blueprint, Seção 6 | Founder + ChatGPT |
| Releases | Fatias entregáveis de um ou mais Programas | `Release-Roadmap-0.1-to-0.5.html` | Founder |
| Epics | Unidades de trabalho dentro de uma Release | `Release-0.N-Macro-Backlog.html` | Founder autoriza, Claude planeja |
| Engineering Orders | Autorização formal para planejar/especificar/implementar um Épico | `ENGINEERING_ORDERS.md` | Founder |
| Architecture | Especificação técnica detalhada | `technical-design-specs/TDS-EPIC-NN.md`, ADRs quando a decisão for arquitetural | Claude redige, ChatGPT revisa (`ARCHITECTURE_REVIEWS.md`), Founder aprova |
| Implementation | Código, migrations, testes, regressão completa | Commits no branch do Épico | Claude |
| Pull Request | Corpo de trabalho completo, nunca mergeado sem autorização | PR no GitHub (resumo executivo/impacto/riscos/rollback) | Claude abre e mantém, Founder não mergea sozinho |
| Merge | Integração à `main` | Engineering Order de merge (EO-MERGE) em `ENGINEERING_ORDERS.md` | Founder autoriza, Claude executa |
| Release | Fechamento formal de uma fatia de Programas | `docs/releases/RELEASE-0.N.md`, Governance Package | Claude documenta, Founder declara encerrada |
| GA | Encerramento de toda a STRATECH V2 | Critério ainda não ratificado | Founder |

**Regra de não-antecipação:** nenhum estágio pula o anterior — não há Implementation sem Architecture aprovada, não há Merge sem Architecture Review do PR, não há Release declarada sem todos os Épicos daquela Release fechados.

## 2A. Fluxo Product-First (EO-021, oficial a partir da Foundation Phase)

A STRATECH V2 adota um processo **Product-First**: decisões funcionais são tomadas e aprovadas **antes** de qualquer engenharia, consolidadas em uma **Capability Blueprint** (`docs/product/capability-blueprints/`, template em `CAPABILITY_BLUEPRINT_TEMPLATE.md`). Este fluxo substitui, para todo trabalho a partir de agora, a entrada direta de "Epics" no fluxo da Seção 2 — um Épico só recebe uma Engineering Order depois que sua Capability Blueprint correspondente é aprovada pelo Founder.

```mermaid
flowchart LR
    A[Product Vision] --> B[Capability Blueprint]
    B --> C[Founder Approval]
    C --> D[Engineering Order]
    D --> E[Technical Design]
    E --> F[Implementation]
    F --> G[Architecture Review]
    G --> H[Merge]
```

| Estágio | O que é | Artefato que governa | Papel responsável |
|---|---|---|---|
| Product Vision | Visão de produto (inalterada — Blueprint, Master Roadmap) | `Enterprise-Architecture-Blueprint-v2.0.html`, `STRATECH_V2_MASTER_ROADMAP.md` | Founder |
| Capability Blueprint | Documento funcional completo de uma capacidade — as 18 seções do template, decisão funcional consolidada antes da engenharia | `docs/product/capability-blueprints/CB-NNN-*.md` | Claude redige a partir da visão aprovada; Founder decide |
| Founder Approval | Aprovação formal da Capability Blueprint — nenhuma engenharia começa antes disso | Registro em `ENGINEERING_ORDERS.md` | Founder |
| Engineering Order | Autorização formal para especificar/implementar a capacidade aprovada | `ENGINEERING_ORDERS.md` | Founder |
| Technical Design | Especificação técnica — **nunca** altera regra de negócio, UX, fluxo ou critério de aceite da Blueprint aprovada | `technical-design-specs/TDS-EPIC-NN.md` | Claude redige, ChatGPT revisa |
| Implementation | Código, migrations, testes | Commits no branch do Épico | Claude |
| Architecture Review | Revisão técnica independente (não revisita decisão funcional já aprovada) | `ARCHITECTURE_REVIEWS.md` | ChatGPT |
| Merge | Integração à `main`, apenas após EO-MERGE | `ENGINEERING_ORDERS.md` | Founder autoriza, Claude executa |

**Regra central do Product-First:** nenhuma decisão funcional é tomada durante Technical Design ou Implementation. Toda decisão de negócio, UX, fluxo ou critério de aceite já foi tomada e aprovada na Capability Blueprint. Se a engenharia encontrar uma inconsistência, uma lacuna, ou uma decisão funcional não coberta durante a Technical Design ou a Implementation, ela **não decide** — emite uma Engineering Question (Seção 5) e aguarda o Product Board.

## 3. Regras de governança documental (EO-018)

1. Toda Engineering Order relevante é registrada em `docs/governance/ENGINEERING_ORDERS.md` no momento em que é emitida — não apenas resumida em outro documento.
2. Toda Architecture Review é registrada em `docs/governance/ARCHITECTURE_REVIEWS.md` no momento em que a decisão é emitida.
3. Toda TDS de Épico é registrada em `docs/architecture/technical-design-specs/TDS-EPIC-NN.md`, com histórico de revisões dentro do mesmo arquivo (não um arquivo por revisão).
4. Todo débito técnico e toda lição aprendida continuam em `TECHNICAL_DEBT.md`/`LESSONS_LEARNED.md` (registros vivos, inalterados por esta EO).
5. `docs/product/STRATECH_V2_MASTER_ROADMAP.md` nunca é fonte primária de EO/TDS/Architecture Review — é um painel executivo derivado, que referencia os documentos acima.
6. Nenhum documento de governança é editado retroativamente para mudar uma decisão já tomada — correções aparecem como uma nova entrada que referencia a anterior.

## 4. Convenção de ADRs (referência)

Ver `docs/architecture/adr/NORMALIZATION-PLAN.md` para o estado atual (duas convenções coexistindo, uma colisão de numeração não resolvida) e o plano proposto — não executado nesta EO.

## 5. Engineering Questions (EQ) — EO-021

**Quando:** sempre que surgir uma dúvida funcional durante a Technical Design ou a Implementation de uma capacidade — uma inconsistência na Capability Blueprint aprovada, uma decisão de negócio/UX/fluxo não coberta, ou um caso de borda que a Blueprint não previu.

**Regra central:** nenhuma decisão funcional pode ser tomada pela engenharia durante a implementação. Encontrar uma dessas situações não autoriza inferir, simplificar ou assumir — a engenharia **pausa o trabalho relacionado** e emite uma Engineering Question.

**O que uma EQ pode conter:**
- contexto exato onde a dúvida surgiu (Capability Blueprint, seção, Technical Design, ou trecho de código);
- a pergunta funcional em si, formulada de forma objetiva;
- alternativas técnicas identificadas (se houver), cada uma com seu impacto — **sem recomendar uma decisão funcional**, apenas informar trade-offs técnicos;
- o que fica bloqueado até a resposta.

**O que uma EQ nunca contém:** uma decisão já tomada unilateralmente pela engenharia, apresentada como fato consumado.

**Resolução:** o Product Board (hoje, o Founder — Seção 1) responde à EQ; a resposta, uma vez dada, é registrada e passa a fazer parte da Capability Blueprint ou da Technical Design correspondente (nunca como uma edição silenciosa — como toda decisão de governança, a resposta é um registro novo que referencia a pergunta original).

**Registro:** EQs individuais serão registradas em um arquivo próprio (`docs/governance/ENGINEERING_QUESTIONS.md`, mesmo padrão vivo de `TECHNICAL_DEBT.md`/`LESSONS_LEARNED.md`) a partir do momento em que a primeira EQ real for emitida — não criado preventivamente nesta EO, para não registrar uma instância antes de existir uma dúvida real.
