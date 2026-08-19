# GOVERNANCE ADVISOR — EXECUTIVE EVIDENCE (Wave 5)

**Autorização:** "Founder Decision — Technical Design do Governance Advisor" (veredito **APPROVED — GO para implementação**), encerrando o ciclo institucional de 6 etapas (D-092): Advisor Specification (D-098) → Domain Blueprint (D-099) → Architecture Review AR-10 (D-100) → Technical Design (D-101) → **Implementação, este documento** → Executive Review.

**Escopo confirmado:** exclusivamente o Governance Advisor, seguindo estritamente a estratégia incremental de 4 passos apresentada na Technical Design (D-101). Nenhuma expansão de escopo além do autorizado.

---

## Escopo entregue

1. **`GovernanceAdvisorAgent`** (novo, `src/agents/governance_advisor/`) — implementa `AdvisorContract` sem alteração ao Protocol; prompt dedicado (`prompts/advise.md`) codificando a hierarquia institucional de AR-10 (Decision Log > Technical Debt Register) e o vocabulário fixo dos 5 rótulos de classificação; reaproveita `parse_structured_output` sem duplicação.
2. **Rota `POST /governance-advisor/ask`** (`src/api/routes/intelligence.py`, mesmo arquivo do Risk/Document Advisor) — RBAC via `knowledge.read` (reutilizada, nenhuma migração nova); resposta `{answer, classification, cited_chunks}`.
3. **Classificação institucional (`CONFORME`/`INCONSISTENTE`/`DESATUALIZADO`/`CONFLITANTE`/`SEM EVIDÊNCIA`)** — transmitida exclusivamente via a **primeira linha** de `answer` (per refinamento explícito do Founder nesta autorização: "nenhum texto adicional deverá aparecer nessa primeira linha"), extraída por `_parse_governance_classification()` **na camada HTTP**, nunca no Framework. Fallback explícito `"NÃO CLASSIFICADO"` quando o LLM não segue o formato — nunca uma classificação inventada.
4. **Nenhuma mudança** a `AdvisorFramework`, `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, Workflow Runtime ou Event Pipeline — confirmado por `git diff` vazio nesses arquivos (§ "Arquitetura impactada").
5. **TD-015 mantido inalterado**, per instrução explícita do Founder (item 5 da autorização) — o `GovernanceAdvisorAgent` usa a mesma chave `"cited_analysis_ids"`, sem nenhuma tentativa de renomeá-la.

---

## Arquivos alterados

**Backend — produção**
- `src/agents/governance_advisor/__init__.py`, `agent.py`, `prompts/advise.md` (novos).
- `src/api/routes/intelligence.py` — `GovernanceAdvisorRequest`/`GovernanceAdvisorResponse` (novos); `_parse_governance_classification()` (nova, camada de rota); rota `POST /governance-advisor/ask` (nova); `_governance_advisor_response()` (nova); import de `GovernanceAdvisorAgent`. Reaproveita `CitedChunk` (já definido para o Document Advisor) sem duplicação.

**Backend — testes**
- `tests/test_governance_advisor_agent.py` (novo) — testes unitários do `GovernanceAdvisorAgent.advise()`.
- `tests/test_governance_advisor.py` (novo) — testes de integração via `AdvisorFramework` real (PostgreSQL real): `SEM EVIDÊNCIA` sem chamada ao LLM, citação real com classificação `CONFORME`, isolamento organizacional, e a **evidência obrigatória de conflito Decision Log × Technical Debt Register** (ver seção dedicada abaixo).
- `tests/test_governance_advisor_api.py` (novo) — testes HTTP reais: `SEM EVIDÊNCIA`, citação real, citação inventada descartada, fallback `NÃO CLASSIFICADO` para resposta malformada, RBAC (`knowledge.read`), isolamento organizacional, resposta malformada (502), trilha de auditoria, e a evidência obrigatória de conflito na camada HTTP.

**Governança**
- `docs/product/stratech-v2/DECISION-LOG.md`, `CHANGELOG.md`, `web/lib/mock/mission-control-data.ts` — espelhados (D-102).

---

## Arquitetura impactada

**Nenhuma.** Confirmado por `git diff --stat` vazio em `src/services/advisor_framework/framework.py`, `src/services/ai_foundation/recommendation_engine.py`, `src/services/ai_foundation/explanation_engine.py`, `src/services/ai_foundation/types.py` e `src/services/ai_foundation/context_engine.py` — nenhum desses arquivos foi tocado por esta implementação. `AdvisorFramework.run()` executa o `GovernanceAdvisorAgent` exatamente como já executa o Risk e o Document Advisor. Nenhum arquivo de `src/workflows/` tocado; nenhum `EventPublisher`/`EventDispatcher` envolvido.

---

## Testes executados e resultados

| Suíte | Resultado |
|---|---|
| Backend completo (`pytest`) | **580 passed**, 0 failed (561 pré-existentes + 19 novos desta Epic) |
| Frontend completo (`vitest`) | **503 passed** (69 arquivos) — nenhum arquivo de frontend tocado nesta Epic |
| `ruff check src tests` | Limpo |
| `npx tsc --noEmit` | Limpo |
| `npx eslint .` | Limpo |

---

## Demonstração funcional completa do Governance Advisor

**Fluxo ponta a ponta** (`tests/test_governance_advisor_api.py::TestRealCitationAndClassification::test_answers_with_a_real_citation_and_conforme_classification`): documento real de governança ingerido via `KnowledgeRepository.ingest()`/`.index()` → `POST /governance-advisor/ask` real (HTTP, RBAC `knowledge.read` real, sessão institucional real) → `AdvisorFramework.gather_rag_context()` → `normalize_rag_evidence()` → `AdvisorFramework.run()` (byte-for-byte inalterado) → `GovernanceAdvisorAgent.advise()` → LLM (fake determinístico, respondendo `"[CONFORME]\n..."`) → `RecommendationEngine.build()` → resposta HTTP com `classification: "CONFORME"` e `answer` já limpo do prefixo, citando `document_id`/`chunk_id` reais.

**`SEM EVIDÊNCIA` sem chamada ao LLM** (`TestNoEvidence`): pergunta sem nenhum documento de governança indexado retorna `classification == "SEM EVIDÊNCIA"` sem nunca invocar o provider.

**Citação inventada descartada** (`TestRealCitationAndClassification::test_discards_a_citation_the_model_invented`): o LLM cita um `chunk_id` real e um inventado (`999999`); a resposta HTTP contém exclusivamente o real.

**Robustez do parsing** (`TestRealCitationAndClassification::test_unformatted_answer_falls_back_to_nao_classificado`): resposta sem o prefixo de classificação → `classification == "NÃO CLASSIFICADO"`, `answer` preservado integralmente, nenhuma exceção — nunca uma classificação inventada.

**Isolamento organizacional** (`TestOrganizationalIsolation`): documento de governança indexado pela Organização B nunca é citado/visível para a Organização A.

### Evidência obrigatória de conflito Decision Log × Technical Debt Register (item 4 da autorização)

`tests/test_governance_advisor.py::TestMandatoryConflictEvidence::test_conflicting_decision_log_and_technical_debt_entries_are_classified_conflitante` e `tests/test_governance_advisor_api.py::TestMandatoryConflictEvidence::test_conflicting_documents_are_classified_conflitante_and_both_cited` (camada Framework e camada HTTP, respectivamente) — comprovam exatamente o cenário exigido:

1. **Decision Log:** um fragmento real é ingerido (`"decision-log-fragment.md"`), afirmando "D-050: A retenção de AuditLog é mantida indefinidamente, sem expiração automática."
2. **Technical Debt Register:** um segundo fragmento é ingerido (`"technical-debt-fragment.md"`), afirmando "TD-020: AuditLog expira automaticamente após 90 dias, conforme política de retenção implementada." — **conflito direto e real** com o primeiro.
3. **Governance Advisor identifica o conflito:** ambos os chunks são recuperados pela mesma busca RAG e entregues juntos como `evidence`.
4. **Classifica como `CONFLITANTE`:** a resposta (`explanation.recommendation.answer` / `response.json()["classification"]`) tem exatamente `"CONFLITANTE"` como primeira linha/classificação, aplicando a hierarquia de AR-10 (o texto da resposta declara explicitamente que o Decision Log tem precedência).
5. **Cita ambos os documentos:** `cited_evidence`/`cited_chunks` contém exatamente os dois `chunk_id`s reais, um de cada documento — verificado por `metadata["document_id"]` (camada Framework) e `document_id` (camada HTTP) apontando para os dois documentos distintos ingeridos.

Nota sobre a fixture do teste: os dois documentos usados são fragmentos de teste criados especificamente para simular a estrutura real de uma entrada de Decision Log (`"D-NNN"`) e de Technical Debt Register (`"TD-NNN"`), per a convenção já estabelecida em D-099/AR-10 — os arquivos reais `DECISION-LOG.md`/`TECHNICAL_DEBT.md` do repositório permanecem intocados por esta Epic.

---

## Critérios de aceite da Technical Design (D-101) — confirmação

1. ✅ Reuso integral do `AdvisorFramework` — confirmado, `run()` byte-for-byte inalterado.
2. ✅ Classificação de 5 estados resolvida sem tocar o Framework — prefixo em `answer`, parsing na rota.
3. ✅ Parsing ocorre exclusivamente na camada HTTP — `_parse_governance_classification()` em `intelligence.py`, nunca em `AdvisorFramework`/`AIContextEngine`.
4. ✅ Evidência obrigatória de conflito Decision Log × Technical Debt Register — cumprida em duas camadas (Framework e HTTP).
5. ✅ TD-015 mantido inalterado — confirmado, nenhuma tentativa de renomear `"cited_analysis_ids"`.
6. ✅ `ruff check src tests` limpo; suíte completa verde; testes cobrindo evidência com citação, estado de falha (`SEM EVIDÊNCIA`), isolamento de tenant, citação inválida descartada, e o cenário de conflito mandado.

---

## Riscos residuais (reconfirmados, nenhum bloqueante)

1. **Robustez do prefixo de classificação** — mitigado pelo fallback explícito `"NÃO CLASSIFICADO"`, testado (`test_unformatted_answer_falls_back_to_nao_classificado`).
2. **TD-015** — permanece Deferred; gatilho definitivo (manutenção arquitetural isolada, explicitamente autorizada pelo Founder) registrado em `TECHNICAL_DEBT.md`.
3. **Ingestão dos documentos reais de governança** (`DECISION-LOG.md`/`TECHNICAL_DEBT.md`) na Knowledge Platform de produção — ainda não realizada; permanece pré-requisito operacional, não arquitetural, per D-098/D-099.
4. **Knowledge Version Resolution (D-090)** — já registrada, não agravada.

Nenhum risco bloqueia o encerramento do Epic.

---

## Confirmação de encerramento

Todos os critérios de aceite atendidos. Nenhuma expansão de escopo além do autorizado. **Recomendação: GO para o encerramento do Epic do Governance Advisor.**

Per instrução explícita do Founder: retorno obrigatório para Executive Review antes de qualquer trabalho do próximo Advisor — nenhum código desse Epic foi iniciado ou antecipado.
