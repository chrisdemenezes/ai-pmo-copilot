# Advisor Specification — Governance Advisor (segundo uso do padrão institucional, Classe D)

**Autorização:** "Founder Decision — Próximo Enterprise Advisor da Wave 5" (2026-08-03) — Founder definiu oficialmente o Governance Advisor como o próximo Enterprise Advisor da Wave 5, justificando: a sequência da Wave 5 passa a priorizar reutilização arquitetural e redução de risco; o Governance Advisor reutiliza integralmente a infraestrutura já validada pelo Document Advisor (Knowledge Platform, Document Ingestion, RAG Pipeline, `normalize_rag_evidence()`, `AdvisorFramework`, `RecommendationEngine`, citações rastreáveis, portão anti-alucinação); domínio funcional distinto, infraestrutura praticamente idêntica — validando definitivamente o modelo de múltiplos Advisors sobre a mesma arquitetura. Autorizada a abertura do ciclo institucional de 6 etapas (D-092): **1. Advisor Specification (este documento)** → 2. Domain Blueprint → 3. Architecture Review → 4. Technical Design → 5. Implementação → 6. Executive Review. Nenhum código escrito nesta etapa.

---

## Executive Summary

O Governance Advisor é o **segundo Advisor de Classe D** (RAG como evidência primária, `AR-8` §4) — mesmo modelo arquitetural do Document Advisor, já provado em produção (W5-1, D-096). Seu domínio é distinto: em vez de responder sobre documentos corporativos genéricos, ele responde sobre **os próprios documentos de governança da STRATECH** — Decision Log, Technical Debt Register, Mission Control (`ENTERPRISE-ADVISOR-CATALOG.md` §7). Toda a infraestrutura que ele precisa — Knowledge Platform, Document Ingestion (W5-0), RAG Pipeline, `normalize_rag_evidence()`, `AdvisorFramework`, `RecommendationEngine`, portão anti-alucinação — já existe, já está validada por um segundo consumidor real (o Document Advisor), e não exige nenhuma mudança estrutural conhecida até este ponto. O único achado grounded que este documento levanta, não resolvido aqui, é operacional: os documentos de governança (`DECISION-LOG.md`, `TECHNICAL_DEBT.md`) hoje vivem como arquivos Markdown no repositório, não como `Document`s ingeridos na Knowledge Platform — a ingestão inicial (e sua cadência de atualização) é uma decisão do Domain Blueprint, não uma lacuna arquitetural. Recomendação ao final: **GO para o Domain Blueprint**.

---

## 1. Identidade do Advisor

| Campo | Valor |
|---|---|
| Nome | Governance Advisor |
| Posição no catálogo | `ENTERPRISE-ADVISOR-CATALOG.md` §7 (7º de 8 Advisors) |
| Classe (per AR-8 §4, nascida do código) | **Classe D — Knowledge/Document Intelligence** (RAG como evidência primária) |
| Segundo Advisor da mesma Classe | Document Advisor (já implementado e encerrado, W5-1, D-096) — primeiro e único precedente real de um Advisor de Classe D em produção |

---

## 2. Objetivo e responsabilidade (per catálogo, `ENTERPRISE-ADVISOR-CATALOG.md` §7)

**Objetivo:** apoiar conformidade com a própria governança STRATECH (Decision Log, Technical Debt, Wave Completion Policy).

**Responsabilidade:** verificar se decisões/débitos técnicos/waves seguem o processo de governança declarado (ex.: nenhuma Decision Proposal esquecida, nenhum TD sem classificação) — respondendo perguntas em linguagem natural sobre esses documentos, sempre citando o item real (ex.: "TD-00X sem classificação").

---

## 3. Contrato (nenhum contrato novo — reaproveita `AdvisorContract` já provado pelo Risk Advisor e pelo Document Advisor)

```
class GovernanceAdvisorAgent:
    name = "governance_advisor"
    def advise(self, session: SessionContext, question: str,
               evidence: list[Evidence], rag_context: RagContext | None = None) -> dict:
        ...
```

Fluxo (idêntico, byte-for-byte, ao já implementado para o Document Advisor — `TECHNICAL-DESIGN-DOCUMENT-ADVISOR.md` §4): Rota → Montagem de Contexto (`framework.gather_rag_context(organization_id, question, top_k=5)`, já existente, zero mudança) → `framework.normalize_rag_evidence(rag_context)` (já implementado no W5-1, **reutilizado sem nenhuma alteração** — a própria justificativa de D-088/AR-9 para centralizar esse método em `AIContextEngine` era exatamente evitar duplicação entre Document e Governance Advisor, ambos Classe D) → `AdvisorFramework.run()` (compartilhado, inalterado) → `GovernanceAdvisorAgent.advise()`.

---

## 4. Fonte de evidência (achado grounded, distinto do Document Advisor)

RAG Pipeline é a fonte primária, exatamente como o Document Advisor — porém sobre um **corpus documental diferente e mais restrito**: os documentos de governança da própria plataforma (`DECISION-LOG.md`, `TECHNICAL_DEBT.md`, e possivelmente um snapshot textual de `mission-control-data.ts`/relatórios de encerramento de Wave), não documentos corporativos genéricos de um cliente.

**Pré-requisito operacional, não arquitetural (achado a resolver no Domain Blueprint, não decidido aqui):** hoje esses documentos existem apenas como arquivos versionados no repositório Git — **nenhum deles foi ingerido na Knowledge Platform** via `POST /documents` (W5-0). A infraestrutura de ingestão já existe e já é genérica (aceita qualquer texto/markdown, `DocumentIngestionService`/`KnowledgeRepository.ingest()`); o que falta é a decisão operacional de **quem ingere, quando, e com que cadência de atualização** (a cada novo D-NNN? periodicamente? sob demanda?) — isso é escopo do Domain Blueprint, explicitamente **não resolvido por esta Advisor Specification**. Duas opções preliminares, sem decisão: (a) ingestão manual via a interface administrativa já existente (`/administracao/documentos`), reaproveitada sem nenhuma mudança; (b) uma automação de sincronização (fora de escopo hoje, sem consumidor real que a justifique, per "Grounded before Generalized").

---

## 5. Dependências de infraestrutura (quase todas já prontas e validadas — segunda vez que esta tabela é preenchida)

| Dependência | Status |
|---|---|
| `KnowledgeRepository`/`RagPipeline` (Wave 3 Fase 1/2) | Pronto |
| `AdvisorFramework`/`AdvisorContract` (Wave 3 Fase 3/4) | Pronto |
| `normalize_rag_evidence()` (D-088, implementado no W5-1) | **Pronto e já validado por um segundo consumidor real** (o próprio propósito de tê-lo centralizado) |
| Document Ingestion real (W5-0) | Pronto — mesma rota `POST /documents`, nenhuma extensão necessária |
| Ingestão dos documentos de governança específicos deste Advisor (Decision Log, TD Register) | **Não realizada ainda** — pré-requisito operacional, não arquitetural (ver §4); decisão de processo pertence ao Domain Blueprint |
| `RecommendationEngine`/`ExplanationEngine` | Pronto, inalterado desde o W5-1 |

---

## 6. Limites de atuação (idênticos a todos os Advisors, AR-8 §8 — reafirmados, não redecididos)

- Nunca invocado por `WorkflowRuntime`; nunca registrado como handler de `EventDispatcher`.
- Nunca executa regra de negócio, nunca altera entidade — produz exclusivamente `Explanation`/`Recommendation`.
- Nunca interpreta além do texto do chunk — se a pergunta não tem evidência documental relevante, `no_evidence()`, nunca infere.
- **Específico deste Advisor (per catálogo §7):** não decide política de governança — aplica exclusivamente a política já declarada nos documentos existentes (Decision Log/TD Register/Mission Control), nunca cria uma regra nova nem reinterpreta uma decisão já registrada.

---

## 7. Riscos/decisões herdadas do ciclo do Document Advisor, ainda não resolvidas (não redecididas aqui)

1. **TD-015 (chave literal `"cited_analysis_ids"` em `AdvisorFramework.run()`) — o gatilho de resolução registrado (D-095/D-096) era exatamente "o segundo Advisor baseado em RAG (Governance Advisor ou equivalente)". Este é esse momento.** Achado explicitamente apresentado, não decidido unilateralmente aqui: a Architecture Review deste Advisor deve avaliar se, agora que o segundo consumidor real existe, vale renomear a chave para algo genérico (ex.: `"cited_source_ids"`) em uma mudança isolada a `AdvisorFramework.run()`, ou se permanece Deferred por mais um ciclo. Nenhuma decisão tomada nesta Advisor Specification.
2. **Ingestão dos documentos de governança** (§4/§5) — decisão de processo (não arquitetural) pertence ao Domain Blueprint.
3. **Knowledge Version Resolution** (D-090, Decision Proposal ainda não resolvida) — se os documentos de governança forem reingeridos (nova versão do Decision Log após cada D-NNN), este Advisor herda o mesmo comportamento não resolvido (chunks de versões antigas continuam pesquisáveis) — não bloqueante, mesmo risco já aceito para o Document Advisor.
4. **`no_evidence_answer` de domínio** (mensagem própria, ex. "nenhuma referência de governança relevante encontrada" — não a genérica de risco nem a do Document Advisor) — decisão de Technical Design.
5. **`top_k`** (default 5, herdado do Document Advisor, ainda não validado com uso real de nenhum dos dois Advisors de Classe D) — decisão de Technical Design, mesmo risco já registrado para o Document Advisor.
6. **Definição exata do corpus** (§4: quais documentos exatos compõem "os documentos de governança") — decisão do Domain Blueprint, não desta Specification.

---

## 8. Critérios de sucesso (per catálogo §7)

Nenhuma lacuna de governança sinalizada sem citação real ao documento de governança correspondente (mesma disciplina de citação já provada pelo Risk Advisor e pelo Document Advisor — nenhuma resposta sem evidência rastreável é apresentada como fato).

---

## 9. Riscos identificados (consolidado)

| Risco | Bloqueante? | Onde resolver |
|---|---|---|
| TD-015 — trigger de resolução chegou | Não | Architecture Review |
| Documentos de governança ainda não ingeridos | Não (é passo do próprio Domain Blueprint) | Domain Blueprint |
| Knowledge Version Resolution (D-090) ainda aberta | Não | Já registrada, decisão futura fora desta Epic |
| `no_evidence_answer`/`top_k` de domínio não definidos | Não | Technical Design |
| Definição exata do corpus documental | Não | Domain Blueprint |

Nenhum risco listado bloqueia a abertura do Domain Blueprint.

---

## 10. Template reutilizável — nenhuma alteração ao já registrado em D-093 §9

A estrutura de 8 campos por Advisor Specification (Identidade, Objetivo/Responsabilidade, Contrato, Fonte de evidência, Dependências de infraestrutura, Limites de atuação, Riscos/decisões herdadas, Critérios de sucesso) permanece válida e é aplicada aqui sem modificação — confirmando, na prática, que o template funciona para um segundo Advisor real, não apenas hipoteticamente.

---

## 11. Recomendação GO/NO-GO para o Domain Blueprint

**GO.** Toda a infraestrutura necessária já existe e já foi validada por um segundo consumidor real (Document Advisor, W5-1). Nenhum achado desta Advisor Specification bloqueia o avanço — o único ponto a resolver (ingestão dos documentos de governança) é uma decisão de processo do próprio Domain Blueprint, não uma lacuna arquitetural como a que motivou o W5-0. O achado sobre TD-015 é explicitamente reservado para a Architecture Review, não decidido aqui.

Per instrução do Founder: nenhuma implementação iniciada; retorno obrigatório para Executive Review antes de prosseguir ao Domain Blueprint (etapa 2).
