# W3-3 EXECUTIVE REPORT — Risk Advisor (Enterprise Agent PoC)

**Wave 3, Epic W3-3**
**Data:** 2026-07-23
**Autor:** Claude / Tech Lead
**Base:** `DOMAIN-BLUEPRINT-RISK-ADVISOR.md` (aprovado, Implementação bloqueada), `TECHNICAL-DESIGN-RISK-ADVISOR.md`, liberado pelo encerramento do Security Hardening Gate (D-045) e pela consolidação da `main` (D-044).

---

## Escopo entregue

Primeiro Enterprise Agent conversacional da plataforma: uma camada de pergunta-e-resposta em linguagem natural sobre os riscos já identificados de um Projeto (`AnalysisRecord` kind="risk"), nunca disparando uma nova análise. Cobre os 2 pontos de decisão que o Blueprint deixou explicitamente pendentes de C-1/C-2: RBAC (reaproveita `intelligence.read`) e organization scope (reaproveita `ProjectSummaryService.list_latest_risks`, já org-escopado desde o Security Hardening Gate).

## Arquivos alterados

**Novos:**
- `docs/architecture/TECHNICAL-DESIGN-RISK-ADVISOR.md`
- `src/agents/risk_advisor/agent.py` + `prompts/advise.md` (+ `__init__.py`)
- `web/app/api/bff/workspace/[projectName]/risk-advisor/route.ts` (+ `.test.ts`)
- `web/components/workspace/risk-advisor-section.tsx` (+ `.test.tsx`)
- `web/lib/hooks/use-ask-risk-advisor.ts` (+ `.test.tsx`)
- `tests/test_risk_advisor_agent.py`

**Modificados:**
- `src/api/routes/intelligence.py` — nova rota `POST /risk-advisor/ask`.
- `tests/test_intelligence_api.py` — nova classe `TestRiskAdvisor` (6 testes).
- `web/lib/workspace/types.ts` — `RiskAdvisorAnswer`/`RiskAdvisorCitedAnalysis`.
- `web/app/workspace/[projectName]/page.tsx` — nova seção wired.
- `web/e2e/mock-backend.mjs` — handler para `/api/risk-advisor/ask`.
- `web/e2e/workspace.spec.ts` — novo teste E2E ponta-a-ponta.

## Migração

Nenhuma (Blueprint §5: nenhuma entidade nova).

## Arquitetura impactada

Nenhuma fora do escopo do Blueprint. Nenhuma permissão nova (reaproveita `intelligence.read`), nenhum provider novo, nenhum registry novo, nenhuma extensão do `PromptRegistry`/`LLMProvider`. Confirma o guarda-corpo da AR-2 e do próprio Blueprint (Seção 14): nenhum framework de orquestração multi-agente, vector store, RAG, ou memória de longo prazo introduzido.

## Testes executados e resultados

| Suíte | Resultado |
|---|---|
| `pytest` (backend, PostgreSQL) | **314 passed** (305 pré-existentes + 9 novos) |
| `ruff check src tests` | Limpo |
| `tsc --noEmit` (frontend) | Limpo |
| `eslint .` (frontend) | Limpo |
| `vitest run` (frontend) | **468 passed** (452 pré-existentes + 16 novos) |
| Playwright E2E — novo teste do Risk Advisor (3 breakpoints) | 3/3 passed |
| Playwright E2E — suíte Workspace completa (spot-check, 3 breakpoints) | 60/63 — as 3 falhas são as mesmas já confirmadas pré-existentes e não relacionadas durante a verificação do Security Hardening Gate (TIP-006/TIP-007, flakiness de ambiente) |

## Critérios de aceite do Blueprint (Seção 16) — confirmação

| Critério | Status |
|---|---|
| Responde apenas com base em `AnalysisRecord` já persistidos do `project_id`/`project_name` em contexto, nunca de outro projeto/organização | ✅ `test_never_sees_risks_from_another_organization` |
| Toda resposta cita a análise de origem (`source_analysis_id`) | ✅ `cited_analyses` na resposta, testado em `test_answers_from_the_latest_risk_analysis_with_citations` |
| RBAC aplicado | ✅ `intelligence.read`, testado em `test_user_with_no_role_is_denied` |
| Organization scope aplicado | ✅ reaproveita `list_latest_risks(organization_id=...)` |
| Pergunta auditada (ator, projeto, texto, timestamp — nunca a resposta completa) | ✅ `test_records_an_audit_entry_without_the_llm_answer` |
| Nenhuma escrita/mutação: somente leitura | ✅ nenhum `save_analysis`/mutação em `ask_risk_advisor` |
| Nenhum framework de orquestração, vector store, RAG, ou memória de longo prazo | ✅ confirmado por inspeção do desenho (agente stateless, sem histórico persistido) |

## Riscos e pendências

Nenhum risco novo. As 3 falhas E2E observadas no spot-check são a mesma flakiness de ambiente já isolada e confirmada pré-existente durante o Security Hardening Gate (via comparação A/B contra a baseline) — não relacionadas a este Epic.

## Confirmação de encerramento

**Epic W3-3 concluído.** Todos os critérios de aceite do Blueprint confirmados item a item. Nenhum Blueprint, Domain Model ou ADR aprovado foi alterado. Per o Epic Ledger da AR-2 (D-039), os 3 Epics originalmente sequenciados para a Wave 3 (W3-1, W3-2, W3-3) estão agora todos resolvidos: W3-1 concluído (D-040), W3-2 adiado por falta de consumidor real (D-041), W3-3 concluído (D-046). Próximo passo: aguardar nova instrução do Founder sobre o restante da Wave 3 (Knowledge Platform e demais Enterprise Agents permanecem bloqueados por Decision Proposal, per D-039/D-042).
