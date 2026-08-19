# Domain Blueprint — Enterprise Memory Model

**Status:** Blueprint subordinado a `WAVE-3-DOMAIN-BLUEPRINT.md` (documento mestre da Wave 3). Nenhum Epic é implementado por este documento.
**Autorização:** decorre da adoção da Enterprise Knowledge Platform (Decisão Estratégica do Founder, 2026-07-27) — o Enterprise Memory Model é a camada de **classificação e ciclo de vida** sobre o conteúdo que a Knowledge Platform já indexa, não uma segunda plataforma de armazenamento.

---

## 0. Checklist de colisão — Enterprise Memory vs. Executive Memory (obrigatório, Princípio 7)

O nome "Enterprise Memory" já foi sinalizado como risco de colisão em `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §5.2, contra o conceito **Executive Memory**, já em produção desde a V1. Esta seção prova, antes de qualquer código, que os dois conceitos não colidem — mesma disciplina de nomenclatura já usada em D-005/D-009/D-012/D-019/D-055.

| | **Executive Memory** (V1, já existe) | **Enterprise Memory Model** (Wave 3, este Blueprint) |
|---|---|---|
| Localização | `web/lib/executive-memory/memory-insights.ts` — puramente frontend | `src/services/` (backend), camada de classificação sobre a Knowledge Platform |
| Estado | Stateless — sem persistência própria | Com ciclo de vida e persistência próprios (memórias classificadas) |
| Mecanismo | Diff exato entre os 2 `AnalysisRecord`s estruturados mais recentes (string matching exato) | Classificação de conteúdo já indexado pela Knowledge Platform (documentos, decisões, ações, lições) em 5 categorias de memória |
| Saída | No máximo 1 insight por sessão ("mudou"/"persistiu"/"reapareceu") | Um modelo de memórias persistentes, consultável por qualquer Advisor via Knowledge Repository |
| Embeddings/Vector Store | Nunca usa | Usa (via Knowledge Platform, nunca diretamente — Princípio 2) |
| Escopo de consumo | UI do Workspace/Dashboard (V1) | Enterprise Advisors (Wave 3), via Advisor Framework |

**Conclusão da checklist:** os dois conceitos não se sobrepõem em mecanismo, camada, persistência ou consumidor. `Executive Memory` permanece intocado — nenhuma migração, nenhuma renomeação, nenhuma extração de lógica dele para este Blueprint. `Enterprise Memory Model` é um conceito novo, de backend, que nunca lê nem escreve em `memory-insights.ts`. Ambos os nomes coexistem deliberadamente porque descrevem coisas genuinamente diferentes — a alternativa (renomear um dos dois) foi avaliada e descartada por não haver ambiguidade real de responsabilidade, apenas similaridade de nome em português.

Esta seção precede e é pré-requisito de qualquer outra parte deste Blueprint — nenhuma implementação futura desta camada pode prosseguir sem revalidar esta checklist se o nome ou o mecanismo de qualquer um dos dois conceitos mudar.

---

## 1. Escopo e não-escopo

**Escopo:** classificar e governar o ciclo de vida de 5 tipos de memória corporativa, todas apoiadas sobre a Enterprise Knowledge Platform (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md`).

**Não-escopo (explícito):**
- Nenhuma indexação, embedding ou Vector Store própria — isso já existe na Knowledge Platform; este Blueprint apenas classifica o que já está lá.
- Nenhuma alteração a `Executive Memory` (V1) — ver §0.
- Nenhum Enterprise Advisor implementado aqui — Advisors **consomem** este modelo (`ENTERPRISE-ADVISOR-CATALOG.md`).

---

## 2. As 5 memórias

### 2.1 Memória documental
Conteúdo bruto ingerido pela Knowledge Platform (documentos, atas, especificações, relatórios). É a memória "de origem" — as demais memórias frequentemente referenciam um `document_id`/`chunk_id` desta, mas nunca a duplicam fisicamente (nenhuma cópia de texto integral fora do Knowledge Repository).

### 2.2 Memória operacional
Estado de execução corrente relevante a um Advisor ou a uma sessão — análogo em papel a `SessionContext` (Foundation, já existente), mas persistido através de sessões, não apenas durante uma única chamada. Vida curta a média; não é histórico de longo prazo.

### 2.3 Memória de decisões
Referencia decisões já tomadas no domínio (Decision Center, Decision Log da própria governança STRATECH) — nunca reimplementa o armazenamento de uma decisão, apenas classifica/indexa a decisão já existente como um tipo de memória consultável por um Advisor via RAG.

### 2.4 Memória de aprendizados
Referencia Lições Aprendidas (Organizational Learnings) já existentes no domínio — mesmo princípio de 2.3: classifica e torna consultável, nunca duplica o armazenamento original.

### 2.5 Memória organizacional
A camada mais ampla — padrões, convenções e conhecimento tácito recorrente através de múltiplos projetos/programas de uma mesma organização, emergente da consolidação das memórias 2.1–2.4 ao longo do tempo, sempre escopada por `organization_id` (Princípio 6, nunca cross-tenant).

---

## 3. Relacionamento entre memórias

```
Memória documental (origem, Knowledge Platform)
   ├─ referenciada por ──> Memória operacional (contexto de execução corrente)
   ├─ referenciada por ──> Memória de decisões (aponta a Decision Log/Decision Center)
   ├─ referenciada por ──> Memória de aprendizados (aponta a Lessons Learned)
   └─ consolidada em ────> Memória organizacional (padrões emergentes, longo prazo)
```

Nenhuma seta é bidirecional; a memória organizacional nunca é editada diretamente — ela emerge da consolidação das demais, nunca é uma entrada manual própria.

---

## 4. Ciclo de vida

1. **Captura** — uma memória nasce sempre a partir de um evento de domínio já existente (nova ingestão na Knowledge Platform, nova decisão registrada, nova lição aprendida, nova sessão de Advisor) — nunca um input direto e solto do usuário sem origem rastreável.
2. **Classificação** — o Enterprise Memory Model atribui o evento a uma ou mais das 5 categorias (§2).
3. **Consulta** — um Advisor, via Advisor Framework, consulta uma ou mais memórias como evidência adicional (mesmo padrão de citação real, nunca inventada, já aplicado por `RecommendationEngine.build()`).
4. **Consolidação** — memórias operacionais/documentais recorrentes ao longo do tempo podem ser promovidas a memória organizacional; esta promoção é auditável (quem, quando, com base em quê).
5. **Expiração** — memória operacional expira conforme o ciclo de vida da sessão que a originou; memória documental segue a política de retenção da Knowledge Platform (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.12); memória de decisões/aprendizados nunca expira enquanto a decisão/lição de origem existir (governança, não infraestrutura, decide a expiração).

---

## 5. Governança

- Toda promoção a memória organizacional é registrada de forma auditável — mesmo padrão de `AIFoundationAudit.record_question()`, nunca uma escrita silenciosa.
- Nenhuma memória é fonte de verdade paralela — cada uma referencia sua origem no domínio (Decision Log, Lessons Learned, Knowledge Platform); se a origem for corrigida ou removida, a memória correspondente reflete isso, nunca preserva um estado divergente.
- A classificação de uma memória é revisável por decisão de governança (mesmo padrão de reclassificação já usado no Wave 2 Closure Review para Technical Debt) — nenhuma categoria é permanente por acidente de implementação inicial.

---

## 6. Critérios de evolução

1. **Nenhuma sexta categoria de memória** sem revisão explícita deste Blueprint e aprovação do Founder.
2. **Nenhuma duplicação de armazenamento** — toda nova memória referencia uma origem já existente no domínio ou na Knowledge Platform, nunca introduz uma tabela de conteúdo bruto paralela.
3. **Revalidar §0 sempre que `Executive Memory` (V1) ou este modelo mudarem de nome ou mecanismo.**
4. **Toda consulta de memória por um Advisor é escopada por `organization_id`, sem exceção** (Princípio 6, documento mestre).
