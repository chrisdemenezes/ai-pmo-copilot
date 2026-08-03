# Domain Blueprint — Governance Advisor (etapa 2 de 6 do ciclo institucional)

**Autorização:** "Founder Decision — Governance Advisor Specification" (veredito **APPROVED — GO para o Domain Blueprint**), exigindo que este documento considere explicitamente 4 cenários de governança (§6), sem criar novas regras — o Governance Advisor apenas identifica esses estados e fundamenta cada conclusão exclusivamente em evidências documentais rastreáveis, com o tratamento desses cenários mantido completamente separado da implementação. Determina também: não resolver TD-015 nesta etapa (mantido para a Architecture Review, conforme já registrado em D-095/D-096/D-098); preservar integralmente a arquitetura validada pelo Document Advisor. Nenhum código escrito nesta etapa.

---

## Executive Summary

O Governance Advisor é o segundo Advisor de Classe D da Wave 5 (RAG como evidência primária, `AR-8` §4) — reutiliza, **sem nenhuma alteração**, toda a arquitetura já provada em produção pelo Document Advisor (W5-1, D-096): `AdvisorFramework`, `normalize_rag_evidence()`, `RecommendationEngine`, o portão anti-alucinação, e o mecanismo de citação rastreável (`Evidence.source_id`/`source_label`/`metadata`). Seu domínio funcional é distinto — em vez de responder sobre documentos corporativos genéricos, ele responde sobre **os próprios documentos de governança da STRATECH** (Decision Log, Technical Debt Register, Mission Control), sinalizando 4 estados possíveis (§6): ausência de evidência, documento inconsistente com outra decisão oficial, documento desatualizado em relação ao Decision Log, e documentos conflitantes entre si — todos identificados exclusivamente por citação real, nunca por uma regra nova de comparação automática. Nenhum dos 4 cenários exige um mecanismo novo de Framework: todos são resolvidos pela mesma capacidade já existente de `normalize_rag_evidence()` devolver múltiplos chunks de múltiplos documentos na mesma `RagContext`, deixando a identificação do padrão (ausência/inconsistência/desatualização/conflito) para a camada de domínio do próprio Advisor — exatamente o mesmo princípio que já separa Framework de domínio em todo Advisor existente. Recomendação ao final: **GO para a Architecture Review**.

---

## 0. Escopo e não-escopo deste documento

**Decide:** objetivo/responsabilidade do Governance Advisor (reafirmando o catálogo), modelo arquitetural aplicado (idêntico ao Document Advisor, nenhuma novidade), fontes de evidência, e a caracterização conceitual dos 4 cenários de governança exigidos pelo Founder — o que cada um significa, que tipo de evidência o fundamenta, e por que nenhum exige arquitetura nova.

**Não decide (fica para etapas seguintes, per instrução explícita do Founder):**
- **Architecture Review:** avaliação do gatilho de TD-015 (chave `"cited_analysis_ids"` em `AdvisorFramework.run()`) — não resolvido aqui.
- **Technical Design:** texto literal do prompt do `GovernanceAdvisorAgent`, wording exato de `no_evidence_answer`, `top_k`, nome da rota HTTP, e a forma exata como o prompt orienta o modelo a reconhecer cada um dos 4 cenários (o "tratamento" desses cenários, que o Founder determinou manter separado da implementação).
- **Domain Blueprint anterior (processo, não arquitetura):** quem ingere os documentos de governança na Knowledge Platform e com que cadência — já registrado como achado em aberto na Advisor Specification (D-098), resolvido abaixo (§5) apenas na medida operacional mínima necessária para o Epic avançar, não como automação nova.

---

## 1. Grounding Audit — o que já existe, hoje, em código (reaproveitado sem alteração do Document Advisor)

Confirmado por leitura direta do código já implementado no Epic W5-1 (`src/services/advisor_framework/framework.py`, `src/services/ai_foundation/context_engine.py`, `src/services/ai_foundation/recommendation_engine.py`, `src/agents/document_advisor/agent.py`):

- `AdvisorFramework.gather_rag_context(organization_id, query, top_k)` → `RagPipeline.retrieve()` → `KnowledgeRepository.search()` — já filtra por `organization_id`, já ranqueia por similaridade + recência de versão. **Nenhum destes três componentes precisa mudar.**
- `AdvisorFramework.normalize_rag_evidence(rag_context)` — já implementado (D-088/W5-1), já mecânico, já devolve **um `Evidence` por chunk retornado, de qualquer documento da organização** — não há limitação a um único documento por chamada. Isso é exatamente o que os cenários 2-4 (§6) precisam: chunks de documentos diferentes (ex.: um chunk do Decision Log e um chunk do Technical Debt Register) já chegam juntos, na mesma lista `list[Evidence]`, sem nenhuma mudança de código.
- `AdvisorFramework.run()` — portão anti-alucinação (`if not evidence:`) já cobre o cenário 1 (ausência de evidência documental) sem nenhuma mudança: se a busca RAG não retornar nada relevante, `RecommendationEngine.no_evidence()` responde, exatamente como já ocorre para o Document Advisor.
- `RecommendationEngine.build()` já filtra citações por `source_id` presente na evidência entregue — já suporta, sem mudança, uma resposta citando **múltiplos `chunk_id` de documentos diferentes** simultaneamente (é exatamente isso que uma resposta sobre "documentos conflitantes" precisa citar).
- `DocumentIngestionService`/`POST /documents` (W5-0) — já aceita qualquer texto/markdown como `Document`, sem exigir que o conteúdo seja "corporativo" em algum sentido restrito. Ingerir `DECISION-LOG.md`/`TECHNICAL_DEBT.md` como `Document`s usa exatamente essa rota, sem extensão.

**O que NÃO existe e não será inventado por este documento:** nenhum comparador determinístico de "consistência" entre documentos; nenhuma nova regra de negócio em `AIContextEngine`; nenhum campo novo em `Evidence` (confirmado suficiente pelo Technical Design do Document Advisor, D-095); nenhuma automação de sincronização entre o Git e a Knowledge Platform.

---

## 2. Objetivo e responsabilidade (per `ENTERPRISE-ADVISOR-CATALOG.md` §7, reafirmado — não redecidido)

**Objetivo:** apoiar conformidade com a própria governança STRATECH (Decision Log, Technical Debt, Wave Completion Policy).

**Responsabilidade:** verificar se decisões/débitos técnicos/waves seguem o processo de governança declarado, respondendo perguntas em linguagem natural e sinalizando lacunas — sempre citando o item real (ex.: "TD-00X sem classificação"), nunca inventando uma lacuna sem evidência.

**Reafirmado, per catálogo:** não decide política de governança — aplica exclusivamente a política já declarada nos documentos existentes.

---

## 3. Modelo aplicado — Framework-Mediated Evidence Assembly, Classe D (idêntico ao Document Advisor, D-088/AR-9)

```
Rota (POST /governance-advisor/ask, nome definitivo per Technical Design)
  │
  ▼
Montagem de Contexto: framework.gather_rag_context(organization_id, question, top_k)
  │   (apenas gather_rag_context() -- nunca gather_context(), pois não existe
  │    AnalysisRecord de kind="governance")
  ▼
framework.normalize_rag_evidence(rag_context)  -- já implementado, reutilizado sem mudança
  │
  ▼
framework.run(governance_advisor_agent, session, question, evidence, rag_context, no_evidence_answer=...)
  │   (compartilhado, byte-for-byte igual ao Document Advisor -- auditoria, portão
  │    anti-alucinação, RecommendationEngine.build(), ExplanationEngine.explain())
  ▼
GovernanceAdvisorAgent.advise()  -- único componente novo desta Epic
```

Nenhuma etapa deste fluxo diverge do já implementado e testado para o Document Advisor — a única peça nova é o próprio `GovernanceAdvisorAgent` (interpretação de domínio, §6).

---

## 4. Contrato do `GovernanceAdvisorAgent` (nenhum contrato novo)

```
class GovernanceAdvisorAgent:
    name = "governance_advisor"
    def advise(self, session: SessionContext, question: str,
               evidence: list[Evidence], rag_context: RagContext | None = None) -> dict:
        ...
```

Mesma forma exata de `AdvisorContract`, já provada por `RiskAdvisorAgent` e `DocumentAdvisorAgent` — nenhuma alteração ao Protocol.

---

## 5. Fontes de evidência

RAG Pipeline sobre um corpus documental restrito e específico: os documentos de governança da própria plataforma. **Definição do corpus (resolvida aqui, decisão mínima necessária para avançar):** `docs/product/stratech-v2/DECISION-LOG.md` e `docs/architecture/TECHNICAL_DEBT.md` — os dois documentos de governança formais, versionados, e já estruturados em entradas identificáveis (`D-NNN`, `TD-NNN`) que o catálogo (§7) cita como escopo ("Decision Log, Technical Debt, Wave Completion Policy"). `CHANGELOG.md` e os relatórios de Executive Evidence/Wave Closure são espelhos derivados do Decision Log — não fontes primárias adicionais nesta primeira versão do Advisor (achado, não decisão final — a Architecture Review pode ampliar o corpus se necessário).

**Ingestão (achado operacional, resolvido no nível mínimo, per §0):** os dois documentos serão ingeridos via a rota já existente `POST /documents` (W5-0), manualmente, pela mesma interface administrativa (`/administracao/documentos`) já usada para qualquer outro documento — **nenhuma automação de sincronização Git↔Knowledge Platform é criada por este Blueprint.** A cadência de reingestão (a cada novo `D-NNN`? periodicamente?) é uma decisão operacional de uso da plataforma, não uma decisão arquitetural — e herda, sem agravar, o risco já registrado e aceito em D-090 (Knowledge Version Resolution: chunks de versões antigas permanecem pesquisáveis após reingestão).

---

## 6. Fluxos — os 4 cenários de governança exigidos pela autorização do Founder

Os quatro cenários abaixo são caracterizados **conceitualmente** — o que cada um significa e que evidência o fundamenta — sem prescrever a implementação (prompt/código), que fica para o Technical Design, per instrução explícita do Founder. Em nenhum dos quatro casos o Governance Advisor cria uma regra de governança nova: ele apenas relata o que já está expresso nos documentos, com citação obrigatória.

### 6.1 Ausência de evidência documental

Nenhum chunk relevante é retornado pela busca RAG para a pergunta feita. Mecanismo: idêntico ao já provado para Risk/Document Advisor — `AdvisorFramework.run()`'s `if not evidence:` → `RecommendationEngine.no_evidence(...)`. **Nenhum componente novo.** O `no_evidence_answer` de domínio (texto exato da mensagem) é decisão de Technical Design.

### 6.2 Documento existente, porém inconsistente com outra decisão oficial

A busca RAG retorna chunks relevantes de **mais de um documento** (ex.: um chunk do Decision Log e um chunk do Technical Debt Register) cujo conteúdo, lido em conjunto, expressa posições diferentes sobre o mesmo tema. `normalize_rag_evidence()` já entrega ambos os chunks na mesma `evidence: list[Evidence]`, cada um com `source_label`/`metadata["document_id"]` distintos — a **identificação da inconsistência é interpretação de domínio do próprio `GovernanceAdvisorAgent`** (mesma natureza de trabalho que `RiskAdvisorAgent` já faz ao sintetizar múltiplos riscos, ou que `DocumentAdvisorAgent` faz ao sintetizar múltiplos chunks) — nunca do Framework. A resposta deve citar **ambos** os chunks envolvidos, nunca escolher silenciosamente um lado.

### 6.3 Documento existente, porém desatualizado em relação ao Decision Log

Caso específico do cenário 6.2: um documento de governança (ex.: uma entrada mais antiga de Technical Debt, ou um snapshot de Mission Control) não reflete uma decisão **mais recente** já registrada no Decision Log. Distinto — e não deve ser confundido — do risco já registrado em D-090 (Knowledge Version Resolution, que trata de múltiplas *versões do mesmo documento* reingerido): aqui o "desatualizado" é entre **documentos diferentes**, um dos quais é sempre o Decision Log (fonte de verdade cronológica, por ser append-only e sequencial — `D-NNN` crescente). A evidência que fundamenta essa conclusão são sempre pelo menos dois chunks citados: o do documento desatualizado e o da entrada do Decision Log que o supera.

### 6.4 Documentos conflitantes entre si

Generalização dos cenários 6.2/6.3: dois ou mais chunks retornados, de documentos diferentes, cujo conteúdo se contradiz diretamente, sem que um deles seja necessariamente o Decision Log. Mesma exigência: citação de todos os chunks conflitantes, nunca resolução silenciosa a favor de um.

**Ponto comum aos quatro cenários (garantia estrutural, não nova):** em todos os casos, `RecommendationEngine.build()` já garante que nenhuma citação aparece na resposta sem estar presente na `evidence` efetivamente entregue (mesmo portão que já descarta citação inventada, provado em W5-1) — a "fundamentação exclusivamente em evidências documentais rastreáveis" exigida pelo Founder é, portanto, **já estrutural**, não uma garantia nova a construir.

---

## 7. Limites de atuação (idênticos a todos os Advisors, `AR-8` §8 — reafirmados, não redecididos)

- Nunca invocado por `WorkflowRuntime`; nunca registrado como handler de `EventDispatcher`.
- Nunca executa regra de negócio, nunca altera entidade — produz exclusivamente `Explanation`/`Recommendation`.
- Nunca interpreta além do texto dos chunks — se a pergunta não tem evidência documental relevante, `no_evidence()`, nunca infere.
- **Específico deste Advisor (catálogo §7, reafirmado aqui per instrução do Founder):** nunca decide política de governança nova — mesmo ao identificar inconsistência/desatualização/conflito (§6), o Advisor apenas relata o que os documentos já dizem, nunca resolve o conflito, nunca recomenda qual documento deveria prevalecer além de citar que o Decision Log é a fonte cronológica mais recente (§6.3).

---

## 8. Riscos e decisões que ficam para a Architecture Review/Technical Design (não bloqueiam este Blueprint)

1. **TD-015 (gatilho chegou, não resolvido aqui, per instrução explícita do Founder)** — a chave literal `"cited_analysis_ids"` em `AdvisorFramework.run()` permanece com vocabulário do Risk Advisor; a Architecture Review deve decidir se, com este segundo consumidor real confirmado, vale renomeá-la. Nenhuma decisão tomada neste documento.
2. **Definição exata do corpus** (§5) — Decision Log + Technical Debt Register resolvidos aqui como mínimo necessário; a Architecture Review pode ampliar (ex.: incluir Mission Control) se justificado por um caso de uso real.
3. **Cadência de reingestão dos documentos de governança** — decisão operacional, não arquitetural; Technical Design deve apenas confirmar que nenhuma automação é necessária nesta Epic.
4. **Wording exato do `no_evidence_answer` e dos 4 cenários no prompt** — Technical Design, per determinação do Founder de manter a implementação separada deste Domain Blueprint.
5. **`top_k`** — herdado do Document Advisor (default 5), ainda sem dado real de uso de nenhum dos dois Advisors de Classe D — Technical Design.
6. **Knowledge Version Resolution (D-090)** — já registrada, não resolvida, não agravada por este Advisor.

Nenhum risco listado bloqueia o avanço para a Architecture Review.

---

## 9. Fora de escopo (explícito)

- Qualquer mecanismo automático de correção/reconciliação entre documentos de governança conflitantes — o Advisor relata, nunca corrige.
- Qualquer nova regra de governança, política de classificação de TD, ou critério de encerramento de Wave — o Advisor aplica o que já existe, nunca cria.
- Ingestão automática/sincronizada entre o Git e a Knowledge Platform.
- Ampliação do corpus documental além de Decision Log + Technical Debt Register (decisão da Architecture Review, se necessária).
- Qualquer alteração a `AdvisorFramework.run()`, Workflow Runtime, Event Pipeline, ou à lógica de `RecommendationEngine` — arquitetura do Document Advisor preservada integralmente, per instrução explícita do Founder.

---

## 10. Critérios de sucesso do Epic (per catálogo §7 + os 4 cenários desta autorização)

1. Nenhuma lacuna de governança sinalizada sem citação real ao(s) documento(s) de governança correspondente(s).
2. Os 4 cenários (§6) são reconhecíveis nas respostas do Advisor quando aplicáveis, cada um fundamentado em citação real — nunca uma alegação de inconsistência/desatualização/conflito sem os chunks que a evidenciam.
3. `no_evidence()` funciona sem chamada ao LLM quando não há evidência documental relevante — mesmo padrão já provado.
4. Nenhuma citação inventada sobrevive à resposta — mesmo portão já provado (`RecommendationEngine.build()`).
5. Isolamento organizacional preservado — nenhum documento de governança de uma organização aparece para outra (estrutural, já garantido por `organization_id`-scoping em `KnowledgeRepository.search()`).

---

## 11. Recomendação GO/NO-GO para a Architecture Review

**GO.** Toda a infraestrutura necessária já existe e já foi validada por um segundo consumidor real (Document Advisor, W5-1) — este Domain Blueprint não identifica nenhum achado que exija mudança estrutural. Os 4 cenários exigidos pelo Founder foram caracterizados conceitualmente, com evidência de que cada um é resolvido pela capacidade já existente de `normalize_rag_evidence()`/`RecommendationEngine.build()` operarem sobre múltiplos chunks de múltiplos documentos — nenhuma regra nova, nenhum comparador determinístico, nenhuma alteração ao Framework. O único ponto que a Architecture Review deve avaliar explicitamente, per instrução do Founder, é o gatilho de TD-015 — não resolvido aqui.

---

## 12. Próximo passo

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de prosseguir à Architecture Review (etapa 3).
