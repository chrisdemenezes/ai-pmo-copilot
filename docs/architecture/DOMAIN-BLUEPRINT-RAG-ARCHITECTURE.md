# Domain Blueprint — RAG Architecture

**Status:** Blueprint subordinado a `WAVE-3-DOMAIN-BLUEPRINT.md`. Nenhum Epic é implementado por este documento.
**Relação com os demais Blueprints:** detalha o **RAG Pipeline**, já introduzido como componente de infraestrutura em `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.8, e estende o fluxo síncrono já definido em `WAVE-3-DOMAIN-BLUEPRINT.md` §5.2. Este documento não redefine Vector Store, Embeddings ou Indexação (já definidos na Knowledge Platform) — foca em **como a evidência recuperada se torna parte de uma resposta confiável de Advisor**.

---

## 0. Não-escopo

Este Blueprint não define: Document Ingestion/Parsing/Chunking/Embeddings/Vector Store (Knowledge Platform §1.1–1.6), classificação de memória (Enterprise Memory Model), ou contratos de Advisor (Advisor Framework). Define apenas a mecânica de recuperação → ranking → composição de contexto → grounding → resposta.

---

## 1. Pipeline completo

```
Pergunta do usuário
  → Query Embedding (EmbeddingProvider, mesma abstração da Knowledge Platform)
  → Semantic Search (KnowledgeRepository.search, escopado por organization_id)
  → Ranking (§3)
  → Context Assembly (§4) — combina chunks recuperados + evidência da Foundation (AIContextEngine)
  → Grounding check (§5) — descarta qualquer chunk que não sustente uma citação real
  → render_analyst_prompt (Foundation, reaproveitado, nunca duplicado)
  → LLMProvider.generate(...)
  → RecommendationEngine.build(...) — cita chunk_id/document_id reais, ou no_evidence()
  → ExplanationEngine.explain(...)
  → AIFoundationAudit.record_question(...)
```

Este pipeline **estende** o fluxo de 9 passos já provado por `POST /risk-advisor/ask` (`WAVE-3-DOMAIN-BLUEPRINT.md` §5.2) — os passos de Query Embedding/Semantic Search/Ranking/Context Assembly/Grounding são inseridos **antes** da composição do prompt, nenhum passo já existente da Foundation é removido ou substituído.

---

## 2. Recuperação semântica

Delegada inteiramente à Knowledge Platform (`Semantic Search`, §1.7 daquele Blueprint) — este documento não reimplementa a busca vetorial, apenas consome seu resultado (`list[ScoredChunk]`). A única responsabilidade própria do RAG Pipeline nesta etapa é decidir **quantos** chunks recuperar (`top_k`) e com qual limiar mínimo de score — parâmetros de Technical Design, não deste Blueprint, mas sempre configuráveis, nunca hardcoded por Advisor.

---

## 3. Ranking

Os chunks recuperados por similaridade vetorial são reordenados antes da composição de contexto, considerando (quando disponível): recência da versão do documento (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.10), relevância ao `organization_id`/escopo da pergunta (projeto/portfólio, quando aplicável), e o score de similaridade original. O ranking nunca reordena por autoridade do documento de forma implícita — se uma fonte deve pesar mais que outra (ex.: Decision Log vs. documento genérico), isso é uma política explícita e auditável, não uma heurística escondida no código.

---

## 4. Contexto

O RAG Pipeline nunca é a única fonte de contexto de uma resposta — ele é combinado com o que `AIContextEngine.gather()` já produz (evidência estruturada de `AnalysisRecord`), formando um único conjunto de `Evidence` (tipo já existente na Foundation, `types.py`) antes de `render_analyst_prompt`. Isso preserva o Princípio 4 do documento mestre: a Foundation nunca é substituída, apenas recebe uma segunda fonte de evidência.

Limite de tamanho de contexto (quantos chunks + quanta evidência estruturada cabem em um prompt) é decisão de Technical Design; a regra arquitetural fixa aqui é: **quando há mais evidência do que cabe, corta-se por relevância (ranking, §3), nunca por ordem arbitrária.**

---

## 5. Grounding

Nenhuma citação em uma resposta de Advisor pode referenciar um chunk que não foi de fato recuperado e incluído no contexto enviado ao `LLMProvider`. O grounding check ocorre em dois pontos:
1. **Antes do prompt:** apenas chunks que sobreviveram ao ranking (§3) entram no contexto.
2. **Depois da resposta:** `RecommendationEngine.build()` (mesmo guard-rail já usado para `analysis_id`) verifica que toda citação de `chunk_id`/`document_id` na resposta gerada corresponde a um chunk realmente incluído no contexto — caso contrário, a citação é descartada e, na ausência de qualquer evidência válida, a resposta cai em `no_evidence()`.

Este é o mesmo anti-hallucination guard já provado pelo Risk Advisor, estendido a uma segunda classe de evidência (chunk documental, não apenas `AnalysisRecord`).

---

## 6. Políticas de atualização

O RAG Pipeline nunca serve conteúdo de uma versão de documento já superada silenciosamente — toda recuperação lê da versão mais recente não expirada (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.10/§1.11). Se uma atualização incremental estiver em andamento no momento de uma consulta, a consulta usa a última versão consolidada disponível — nunca um estado parcialmente reindexado.

---

## 7. Estratégia de indexação (relevante ao RAG, não à Knowledge Platform em si)

A granularidade de chunking (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.3) é dimensionada para o caso de uso de RAG: chunks pequenos o suficiente para uma citação precisa (nunca "o documento inteiro" como evidência), grandes o suficiente para preservar contexto local sem fragmentar uma afirmação ao meio. Este é um parâmetro de Technical Design compartilhado entre os dois Blueprints, não uma decisão exclusiva de um ou de outro.

---

## 8. Qualidade das respostas

Critérios de qualidade de uma resposta baseada em RAG, nesta ordem de prioridade:
1. **Honestidade sobre ausência de evidência** — `no_evidence()` é sempre preferível a uma resposta plausível sem citação real (mesmo padrão já validado pelo Risk Advisor em produção).
2. **Rastreabilidade** — toda afirmação factual é rastreável a um `chunk_id`/`document_id` ou a um `analysis_id`, nunca a "conhecimento geral" do modelo.
3. **Escopo correto** — nenhuma resposta mistura evidência de organizações diferentes (Princípio 6).
4. **Atualidade** — evidência de uma versão de documento expirada nunca é preferida sobre uma versão vigente quando ambas estão disponíveis (§6).

---

## 9. Critérios de evolução

1. **Nenhuma mudança de ranking ou de grounding reduz o rigor de citação já estabelecido pelo Risk Advisor** — qualquer ajuste é uma extensão aditiva, nunca um relaxamento do guard-rail.
2. **Parâmetros de recuperação (`top_k`, limiar de score, tamanho de contexto) são configuráveis, nunca hardcoded por Advisor** — mudar um parâmetro não deve exigir alterar código de um Advisor específico.
3. **Toda nova fonte de evidência além de `AnalysisRecord` e chunks documentais** (ex.: uma futura terceira fonte) passa pelo mesmo tratamento de `Evidence` unificado (Foundation) — nunca um caminho de composição de prompt paralelo.
