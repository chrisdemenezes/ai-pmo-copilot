# AR-10 — Architecture Review do Governance Advisor (etapa 3 de 6)

**Autorização:** "Founder Decision — Domain Blueprint do Governance Advisor" (veredito **APPROVED — GO para a Architecture Review**), exigindo uma avaliação adicional: verificar explicitamente a hierarquia de autoridade entre os documentos institucionais, para que o Governance Advisor seja capaz de identificar qual documento possui precedência quando houver conflito documental — **definida apenas arquiteturalmente, nenhuma implementação nesta etapa**. Determina também: manter TD-015 para decisão **nesta** Architecture Review (não mais uma postergação vaga); preservar integralmente `AdvisorFramework`, `AIContextEngine`, Event Pipeline, Workflow Runtime. Nenhum código escrito.

---

## Executive Summary

Esta revisão resolve os dois pontos mandatados pelo Founder sem introduzir nenhuma arquitetura nova e sem tocar em nenhum dos quatro componentes que o Founder determinou preservar integralmente. A hierarquia de autoridade documental (§1) é definida como um **fato de domínio**, não um mecanismo de Framework — exatamente a mesma disciplina já aplicada aos 4 cenários de governança do Domain Blueprint (D-099): a regra de precedência é conhecimento que pertence ao prompt do `GovernanceAdvisorAgent` (Technical Design), nunca um comparador determinístico em `AIContextEngine`/`AdvisorFramework`. A decisão sobre TD-015 (§2) é explícita, não uma nova postergação disfarçada: **TD-015 permanece Deferred nesta Epic**, porque resolvê-lo exigiria alterar `AdvisorFramework.run()` — o que esta mesma autorização do Founder determina preservar integralmente nesta revisão. A resolução é redefinida como uma mudança isolada de manutenção de Framework, nunca bundlada à entrega de um Advisor específico. Recomendação ao final: **GO para o Technical Design.**

---

## 1. Análise da hierarquia documental (avaliação adicional exigida pelo Founder)

### 1.1 Documentos institucionais em jogo e sua natureza real (grounded, não inventada)

| Documento | Natureza (confirmada pela própria convenção do repositório) |
|---|---|
| `docs/product/stratech-v2/DECISION-LOG.md` | **Fonte primária e canônica.** Convenção explícita no próprio arquivo: "Cada decisão ganha um ID sequencial `D-NNN`... **Não editado retroativamente — uma correção é uma nova entrada.**" É o único documento append-only e sequencial desta lista. |
| `docs/architecture/TECHNICAL_DEBT.md` | **Subordinado ao Decision Log.** Cada entrada (`TD-NNN`) carrega um campo `Origem` que sempre aponta para a decisão/Domain Blueprint que a originou; mudanças de `Status` são sempre "per D-NNN" (ex.: TD-012 tem uma "Nota de atualização (D-090, Epic W5-0)"; este próprio AR resolve TD-015 citando esta revisão). Reflete o estado corrente de um débito, mas sua autoridade deriva sempre de uma decisão já registrada no Decision Log. |
| `CHANGELOG.md` | **Espelho do Decision Log**, redigido para leitura humana. Toda entrada termina com "**Decision Log:** D-NNN" — nunca a fonte primária. |
| `web/lib/mock/mission-control-data.ts` (`RECENT_DECISIONS`/`PRODUCT_PULSE_TODAY`/`ENTERPRISE_PROGRAM_WAVES`) | **Espelho do Decision Log**, para o painel do Founder. Mesma relação de subordinação do CHANGELOG — nunca fonte primária, sujeito a resumo/paráfrase. |
| Domain Blueprint / Architecture Review / Technical Design / Executive Evidence (por Epic) | **Documentos de trabalho, não fonte de autoridade por si só.** Cada um só se torna vinculante quando uma "Founder Decision" o aprova — e essa aprovação é o que vira uma entrada no Decision Log. O texto de um Technical Design pode ser mais detalhado que sua entrada no Decision Log, mas se os dois divergirem, a entrada do Decision Log (que registra exatamente o que o Founder decidiu, inclusive condições/ressalvas) prevalece. |

### 1.2 A regra de precedência (já implícita em D-094, generalizada aqui)

O Founder já estabeleceu, em D-094 ("regra institucional permanente de aplicação prospectiva da governança"), o princípio de que decisões evoluem prospectivamente e permanecem válidas **até serem explicitamente revogadas**. Generalizando esse princípio já decidido para uma regra de precedência documental completa:

1. **O Decision Log é sempre a fonte de autoridade mais alta.** Qualquer conflito entre o Decision Log e qualquer outro documento (Technical Debt Register, Mission Control, CHANGELOG, ou o próprio corpo de um Domain Blueprint/Architecture Review/Technical Design) é resolvido a favor do Decision Log.
2. **Dentro do próprio Decision Log, a entrada `D-NNN` mais recente que trata explicitamente do mesmo tema prevalece** sobre uma entrada anterior — mas apenas quando há tratamento explícito; per D-094, o silêncio de uma entrada posterior sobre um tema **não revoga** uma decisão anterior sobre esse tema (uma decisão nunca "expira" implicitamente).
3. **O Technical Debt Register é subordinado ao Decision Log** — sua entrada mais atual sobre um débito reflete a última decisão do Founder registrada no Decision Log sobre aquele débito (exatamente o padrão já usado nas "Notas de atualização" de TD-012 e nesta própria revisão para TD-015, §2).
4. **Mission Control e CHANGELOG nunca são fonte primária** — são espelhos derivados, sujeitos a erro de transcrição; em caso de divergência com o Decision Log, o Decision Log corrige.
5. **Um documento de Epic (Domain Blueprint/AR/TD) só é autoritativo na medida em que uma "Founder Decision" registrada no Decision Log o aprovou** — inclusive com as condições/ressalvas que essa aprovação impôs (ex.: este próprio AR-10 só é válido pelas condições que a "Founder Decision — Domain Blueprint do Governance Advisor" impôs, registradas como entrada futura no Decision Log).

### 1.3 Como o Governance Advisor aplica essa hierarquia — definição arquitetural, não implementação

Per exigência explícita do Founder ("essa regra deverá ser apenas definida arquiteturalmente"), a decisão aqui é **onde** essa regra vive, não o texto exato que a implementa:

- A hierarquia (§1.2) é **conhecimento de domínio**, da mesma natureza que os 4 cenários de governança já caracterizados no Domain Blueprint (D-099) — pertence ao prompt do `GovernanceAdvisorAgent` (Technical Design), **nunca** a um comparador determinístico novo em `AIContextEngine`/`AdvisorFramework`. Esta é a mesma disciplina já estabelecida para os cenários 6.2/6.3/6.4 do Domain Blueprint: o Framework nunca decide qual documento "vence" — apenas entrega, sem alteração, os chunks de ambos os documentos conflitantes (`normalize_rag_evidence()`, já suficiente, confirmado em §1 do Domain Blueprint); a **interpretação de qual documento tem precedência é feita pelo próprio Advisor**, aplicando a regra de domínio (§1.2) ao decidir sua resposta.
- **Nenhum campo novo em `Evidence`** é necessário para isso: `source_label` (já existente, ex. `"Document {document_id} / Chunk {chunk_id}"`) mais o `source_name` com que o documento foi ingerido (ex. `"DECISION-LOG.md"` vs. `"TECHNICAL_DEBT.md"`) já são suficientes para o modelo, orientado pela regra de precedência no prompt, identificar de qual documento cada chunk citado provém e aplicar a hierarquia. Confirma-se, portanto, que **nenhuma mudança a `Evidence`/`normalize_rag_evidence()`/`AdvisorFramework`/`AIContextEngine` é necessária** para satisfazer esta exigência do Founder.
- **Decisão explícita, não implementação:** a Architecture Review autoriza o Technical Design a escrever, no prompt do `GovernanceAdvisorAgent`, a regra de precedência de §1.2 como instrução textual ao modelo — nenhum código é escrito aqui, apenas a decisão arquitetural de que essa regra existe, é fixa (não descoberta pelo modelo), e onde ela mora (prompt do Advisor, não Framework).

---

## 2. Decisão sobre TD-015 (exigida nesta etapa, não mais uma postergação)

### 2.1 Contexto

TD-015 registra que `AdvisorFramework.run()` lê a chave literal `"cited_analysis_ids"` do output do modelo — nome herdado do Risk Advisor, anterior ao rename de `Evidence` (D-088). O gatilho de resolução registrado (D-095/D-096) era exatamente "o segundo Advisor baseado em RAG (Governance Advisor ou equivalente)" — este é esse momento.

### 2.2 Por que TD-015 **não será resolvido nesta Epic** — decisão explícita, com justificativa, não uma nova postergação vaga

Resolver TD-015 exigiria renomear a chave lida por `model_output.get("cited_analysis_ids")` dentro de `AdvisorFramework.run()` (`framework.py:98`) para algo genérico (ex.: `"cited_source_ids"`), e atualizar os prompts dos **três** Advisors que a consomem (Risk, Document, e o novo Governance). Isso é, por definição, **uma alteração a `AdvisorFramework.run()`** — exatamente o componente que esta mesma autorização do Founder determina **preservar integralmente** nesta Architecture Review. As duas exigências (resolver TD-015 agora vs. preservar `AdvisorFramework.run()` integralmente nesta revisão) são estruturalmente incompatíveis dentro do mesmo Epic — a decisão explícita desta revisão é priorizar a preservação do Framework, per instrução textual mais específica do Founder para esta etapa.

### 2.3 Decisão

**TD-015 permanece Deferred.** Não é uma postergação repetida sem critério — é a conclusão correta dada a restrição desta própria autorização. **Gatilho de resolução revisado (mais específico que o anterior):** uma mudança de manutenção **isolada e explicitamente autorizada pelo Founder**, nunca bundlada à entrega funcional de um Advisor específico — nem deste Epic (Governance Advisor), nem de um terceiro Advisor futuro. A razão de isolar: um rename em `AdvisorFramework.run()` afeta simultaneamente três Advisors já em produção (Risk, Document, Governance) — misturá-lo com a entrega de funcionalidade nova de um Advisor aumentaria o raio de impacto de um commit sem necessidade, violando a mesma disciplina de mudança mínima já seguida em toda esta Wave.

---

## 3. Confirmação das preservações exigidas pelo Founder (verificadas, não apenas alegadas)

| Componente | Confirmação |
|---|---|
| `AdvisorFramework` (incl. `run()`) | **Preservado integralmente.** Nenhuma mudança avaliada por esta revisão o exige — a hierarquia documental (§1) e os 4 cenários do Domain Blueprint (D-099) são resolvidos inteiramente na camada de prompt do Advisor, nunca no Framework. TD-015 (§2) permanece explicitamente fora do escopo desta Epic exatamente para preservar `run()` intacto. |
| `AIContextEngine` (incl. `normalize_rag_evidence()`) | **Preservado integralmente.** Já devolve `Evidence` de múltiplos documentos (confirmado em D-099 §1) — suficiente para a hierarquia de precedência sem nenhuma extensão. |
| Event Pipeline | **Preservado integralmente.** O Governance Advisor não publica nem consome eventos, mesma confirmação já feita para o Document Advisor. |
| Workflow Runtime | **Preservado integralmente.** O Governance Advisor nunca é invocado por workflow, nunca se registra como handler — mesma restrição permanente (`AR-8` §8), reafirmada. |

---

## 4. Riscos residuais

1. **A regra de precedência (§1.2) depende inteiramente da qualidade do prompt do Technical Design** — se o prompt não expressar a hierarquia com clareza, o modelo pode citar o documento de menor precedência sem indicar isso. Mitigação: o Technical Design deve incluir um teste explícito de precedência (documento A e documento B conflitantes, resposta deve identificar o de maior precedência per §1.2). Não bloqueante — é exatamente o tipo de verificação já feita para os 4 cenários do Domain Blueprint.
2. **TD-015 permanece aberto por mais um ciclo** — não bloqueante; decisão explícita e justificada (§2.3), não uma omissão.
3. **Ingestão dos documentos de governança** (achado já registrado em D-098/D-099) — ainda não realizada; segue sendo pré-requisito operacional do Technical Design/Implementação, não desta revisão.
4. **Definição exata do corpus documental** — mantida como Decision Log + Technical Debt Register (D-099); esta revisão não a amplia (Mission Control/CHANGELOG permanecem fora do corpus ingerido, apesar de mencionados na hierarquia de precedência para completude conceitual em §1.1).
5. **Knowledge Version Resolution (D-090)** — já registrada, não resolvida, não agravada.

Nenhum risco listado bloqueia o avanço para o Technical Design.

---

## 5. Critérios de sucesso (reafirmados do Domain Blueprint, D-099 §10 — mais um específico desta revisão)

1. Nenhuma lacuna de governança sinalizada sem citação real ao(s) documento(s) correspondente(s).
2. Os 4 cenários de governança (D-099 §6) reconhecíveis nas respostas quando aplicáveis, cada um fundamentado em citação real.
3. **Novo, desta revisão:** quando dois documentos citados conflitarem, a resposta deve identificar explicitamente qual possui precedência institucional, per a hierarquia de §1.2 — nunca uma resolução silenciosa ou arbitrária.
4. `no_evidence()` funciona sem chamada ao LLM quando não há evidência relevante.
5. Nenhuma citação inventada sobrevive à resposta.
6. Isolamento organizacional preservado.

---

## 6. Recomendação GO/NO-GO para o Technical Design

**GO.** A hierarquia de autoridade documental foi definida arquiteturalmente (§1) sem exigir nenhuma mudança a `AdvisorFramework`, `AIContextEngine`, Event Pipeline ou Workflow Runtime — todos confirmados preservados integralmente (§3). TD-015 recebeu uma decisão explícita, não uma nova postergação vaga: permanece Deferred nesta Epic, com justificativa estrutural clara e um gatilho de resolução mais específico (§2.3). Nenhum risco residual (§4) bloqueia o avanço. O Technical Design deve detalhar: o texto exato do prompt incorporando a hierarquia de precedência (§1.3) e os 4 cenários (D-099 §6); o `no_evidence_answer` de domínio; `top_k`; o teste explícito de precedência (§4.1).

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de prosseguir ao Technical Design (etapa 4).
