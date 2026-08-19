# Advisor Specification — Document Advisor (primeiro uso do novo padrão institucional)

**Autorização:** "Founder Decision" (2026-07-30) — encerramento oficial do Epic W5-0 e autorização do ciclo institucional do Epic W5-1 (Document Advisor), com uma mudança de processo recomendada pelo Founder para toda a Wave 5: o ciclo passa a ter 6 etapas, inserindo a **Advisor Specification** como etapa nova antes do Domain Blueprint — **1. Advisor Specification (este documento) → 2. Domain Blueprint → 3. Architecture Review → 4. Technical Design → 5. Implementação → 6. Executive Review.**

**Propósito deste documento (e do padrão que ele inaugura):** uma Advisor Specification é uma folha de especificação curta e objetiva — identidade, contrato, fonte de evidência, limites, dependências, critérios de sucesso de um Advisor — preenchida **antes** do Domain Blueprint, para que toda decisão que já pode ser resolvida por grounding direto em código (per o método já disciplinado nesta Wave) seja capturada em um único lugar padronizado, evitando que cada Domain Blueprint futuro reabra do zero perguntas cuja resposta já é estrutural. **Não substitui** o Domain Blueprint (que continua sendo o documento de desenho completo) nem a Architecture Review — é a camada anterior, mais enxuta, que os alimenta.

---

## 0. Achado de sequenciamento — não decidido unilateralmente, apresentado para confirmação do Founder

Grounding direto no histórico institucional desta Wave: o **Domain Blueprint do Document Advisor já existe** (`DOMAIN-BLUEPRINT-DOCUMENT-ADVISOR.md`, D-087) e a **Architecture Review já existe** (`AR-9-DOCUMENT-ADVISOR-ARCHITECTURE-REVIEW.md`, D-088), ambos aprovados pelo Founder antes desta mudança de processo ser anunciada. Juntos, eles já resolveram, com evidência de código:

- objetivo, responsabilidade, modelo aplicado (Framework-Mediated Evidence Assembly, Classe D);
- contrato genérico e aditivo de `Evidence` (`source_type`/`source_id`/`source_label`/`content`/`metadata`);
- confirmação de `normalize_rag_evidence()` como função puramente mecânica;
- separação do Document Ingestion como Epic habilitador (W5-0, já encerrado).

**O que ainda não existe:** o Technical Design do Document Advisor propriamente dito (prompt, schema exato da rota `/document-advisor/ask`, `no_evidence_answer` de domínio, decisão de `top_k`) — essa é a próxima peça real em aberto.

Este documento (§1-§8 abaixo) **consolida, no novo formato padronizado, o que D-087/D-088 já decidiram** — não redecide nada, não contradiz nada, não introduz nenhuma arquitetura nova. A pergunta que fica para o Founder confirmar: **as etapas 2 (Domain Blueprint) e 3 (Architecture Review) do novo ciclo de 6 já estão satisfeitas pelos documentos existentes (D-087/D-088), avançando diretamente para a etapa 4 (Technical Design)? Ou o Founder deseja que Domain Blueprint e Architecture Review sejam reescritos no formato do novo padrão antes de prosseguir?** Nenhuma das duas opções é assumida aqui.

---

## 1. Identidade do Advisor

| Campo | Valor |
|---|---|
| Nome | Document Advisor |
| Posição no catálogo | `ENTERPRISE-ADVISOR-CATALOG.md` §8 (8º de 8 Advisors; Risk Advisor já implementado como referência) |
| Classe (per AR-8 §4, nascida do código) | **Classe D — Knowledge/Document Intelligence** (RAG como evidência primária) |
| Segundo Advisor da mesma Classe | Governance Advisor (ainda não especificado) |

---

## 2. Objetivo e responsabilidade (per catálogo, D-087)

**Objetivo:** responder perguntas em linguagem natural sobre o conteúdo de documentos corporativos já ingeridos (via W5-0), citando sempre `document_id`/`chunk_id` reais.

**Responsabilidade:** Advisor de referência para uso **primário** do RAG Pipeline — nunca infere além do que o documento diz; sem evidência documental relevante, retorna `no_evidence()`, nunca alucina.

---

## 3. Contrato (nenhum contrato novo — reaproveita `AdvisorContract` já provado pelo Risk Advisor)

```
class DocumentAdvisorAgent:
    name = "document_advisor"
    def advise(self, session: SessionContext, question: str,
               evidence: list[Evidence], rag_context: RagContext | None = None) -> dict:
        ...
```

Fluxo (D-087 §3, D-088 §2/§3): Rota → Montagem de Contexto (chama apenas `framework.gather_rag_context()`, nunca `gather_context()` — não existe `AnalysisRecord` de `kind="document"`) → `framework.normalize_rag_evidence(rag_context)` (novo método aprovado em D-088, ainda não implementado — pertence ao Technical Design desta Epic) → `AdvisorFramework.run()` (compartilhado, byte-a-byte igual ao Risk Advisor) → `DocumentAdvisorAgent.advise()`.

---

## 4. Fonte de evidência

RAG Pipeline (`RagPipeline.retrieve()` → `KnowledgeRepository.search()`) é a **única e primária** fonte — não suplementar, ao contrário das Classes A/B/C. Cada `ScoredChunk` retornado é envelopado em um `Evidence(source_type="document_chunk", source_id=chunk.chunk_id, ...)` (contrato definitivo, D-088 §2.2/§2.3) antes de alcançar `AdvisorFramework.run()`.

**Pré-requisito de infraestrutura, já satisfeito:** W5-0 (Document Ingestion) entrega o caminho real de dados — sem ele, este Advisor sempre cairia em `no_evidence()` por falta de conteúdo indexado, não por falha de arquitetura (achado original de D-087/D-088, resolvido pelo encerramento do W5-0, D-091/D-092).

---

## 5. Dependências de infraestrutura (todas já prontas e validadas)

| Dependência | Status |
|---|---|
| `KnowledgeRepository`/`RagPipeline` (Wave 3 Fase 1/2) | Pronto |
| `AdvisorFramework`/`AdvisorContract` (Wave 3 Fase 3/4) | Pronto |
| `document.indexed` → `EventDispatcher` → `WorkflowRuntime` (Wave 4, W4-4) | Pronto, revalidado no encerramento do W5-0 |
| Document Ingestion real (W5-0) | **Encerrado (D-092)** — documentos reais agora entram na plataforma via `POST /documents` |
| `normalize_rag_evidence()` em `AIContextEngine`/`AdvisorFramework` | Aprovado (D-088), **não implementado ainda** — Technical Design desta Epic |

---

## 6. Limites de atuação (idênticos a todos os Advisors, AR-8 §8 — reafirmados, não redecidido)

- Nunca invocado por `WorkflowRuntime`; nunca registrado como handler de `EventDispatcher`.
- Nunca executa regra de negócio, nunca altera entidade — produz exclusivamente `Explanation`/`Recommendation`.
- Nunca interpreta além do texto do chunk — se a pergunta não tem evidência documental, `no_evidence()`, nunca infere.

---

## 7. Riscos/decisões herdadas do ciclo do W5-0, ainda não resolvidas (não redecididas aqui)

1. Nomenclatura `source_type`/`source_id` já resolvida (D-088) — mas a implementação real do rename em `types.py`/`context_engine.py`/`risk_advisor/agent.py` ainda não ocorreu (pertence ao Technical Design).
2. `gather_memory` ainda não existe — não necessário para este Advisor hoje.
3. Chunks de versões antigas de um documento reingerido continuam pesquisáveis via RAG — Decision Proposal "Knowledge Version Resolution" (D-090), não resolvida, não bloqueante para este Advisor.
4. TD-014 (`confidence` em `Evidence`) — Deferred, não necessário para este Advisor hoje.
5. `no_evidence_answer` de domínio (mensagem "nenhum documento relevante encontrado", não a genérica de risco) — decisão de Technical Design.
6. `top_k` (`RagPipeline.retrieve()` default 5) — não validado para um Advisor onde RAG é fonte única — decisão de Technical Design.

---

## 8. Critérios de sucesso (per catálogo)

Toda resposta cita um chunk/documento real; nenhuma resposta sem evidência documental correspondente é apresentada como fato.

---

## 9. Template reutilizável — campos que toda Advisor Specification futura deve preencher

Para os 6 Advisors restantes (Executive, Strategy, PMO, Portfolio, Delivery, Governance), a mesma estrutura de 8 seções acima deve ser repetida:

1. **Identidade** — nome, posição no catálogo, Classe (A/B/C/D, per AR-8), Advisors irmãos da mesma Classe.
2. **Objetivo e responsabilidade** — do catálogo, sem reescrever.
3. **Contrato** — confirmar que reaproveita `AdvisorContract` sem alteração; descrever o fluxo Rota → Montagem de Contexto → `AdvisorFramework.run()` → `Advisor.advise()` específico da Classe.
4. **Fonte de evidência** — qual(is) chamada(s) a `gather_context()`/`gather_rag_context()`/futuro passthrough; se agregada (Classe B), quantas chamadas e como compostas.
5. **Dependências de infraestrutura** — tabela de pré-requisitos, com status real (pronto/pendente), nunca hipotético.
6. **Limites de atuação** — sempre os mesmos 3 (não invocado por workflow/evento; nunca regra de negócio; nunca infere além da evidência) — reafirmados, nunca redecididos por Advisor.
7. **Riscos/decisões herdadas** — o que já foi resolvido arquiteturalmente vs. o que fica para o Technical Design daquele Advisor especificamente.
8. **Critérios de sucesso** — do catálogo.

Uma Advisor Specification **nunca** introduz uma abstração nova no Framework/Foundation — se um achado durante seu preenchimento exigir mudança estrutural (como o `normalize_rag_evidence()` desta), isso é registrado como achado a resolver na Architecture Review correspondente, exatamente como ocorreu aqui.

---

## 10. Próximo passo

Aguarda confirmação do Founder sobre o achado do §0 (sequenciamento) antes de prosseguir para a etapa 4 (Technical Design) ou reabrir as etapas 2/3 no novo formato.
