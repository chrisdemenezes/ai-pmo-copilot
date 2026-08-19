# Technical Design — Risk Advisor (Epic W3-3)

**Base:** `DOMAIN-BLUEPRINT-RISK-ADVISOR.md` (Blueprint concluído, Implementação bloqueada por 2 dependências — ambas resolvidas: C-1/C-2 fechados pelo Security Hardening Gate, D-045; `main` consolidada, D-044).
**Status:** resolve os critérios de aceite do Blueprint (Seção 16). Nenhum impacto arquitetural fora do escopo do Blueprint encontrado — implementação segue imediatamente após este documento.

---

## 1. Agente

Novo módulo `src/agents/risk_advisor/`, mesmo padrão dos 3 Accelerators existentes (`meeting_intelligence`, `risk_review`, `project_status`):

- `agent.py` — `RiskAdvisorAgent(model_client, prompt_registry)`. Método `advise(question: str, risks: list[dict]) -> dict`, não `analyze()` — este agente nunca produz uma nova análise, apenas sintetiza sobre dados já existentes (Blueprint §4/§6).
- `prompts/advise.md` — reaproveita `PromptRegistry.get("risk_advisor", "advise")` (nenhuma extensão do registry, per Blueprint §7). O prompt recebe a pergunta e os riscos já estruturados (serializados como JSON: descrição, probabilidade, impacto, mitigação, recomendação de escalonamento, `source_analysis_id`, `source_created_at`) e instrui o modelo a responder **exclusivamente** com base nesses dados, citando o(s) `source_analysis_id` usado(s) na resposta.
- Reaproveita `parse_structured_output` (`src/agents/shared/output_parser.py`) — schema de saída: `{"answer": "string", "cited_analysis_ids": [int, ...]}`.
- **Nenhum dado bruto do projeto é enviado ao LLM** — apenas a lista já estruturada de riscos (Blueprint §6, passo 3: "nunca o contexto bruto do projeto").
- **Caso sem riscos identificados:** se `list_latest_risks` não retornar nenhum item para o `project_name`, a rota responde diretamente (`{"answer": "Nenhum risco identificado ainda para este projeto.", "cited_analyses": []}`) **sem chamar o LLM** — evita custo e uma possível alucinação sobre dados inexistentes.

## 2. API (nova rota em `src/api/routes/intelligence.py`, mesmo router)

| Método | Rota | Permissão | Request | Resposta |
|---|---|---|---|---|
| `POST` | `/risk-advisor/ask` | `intelligence.read` | `{"project_name": str, "question": str}` | `{"answer": str, "cited_analyses": [{"source_analysis_id": int, "source_created_at": datetime}]}` |

**Por que `intelligence.read`, não uma permissão nova:** o Risk Advisor é somente leitura (Blueprint §6 passo 5, §16) — não cria, edita nem dispara uma análise. Introduzir uma permissão dedicada (`risk_advisor.ask` ou similar) seria uma nova capacidade de RBAC sem um caso de uso que a justifique (mesmo raciocínio do Epic W3-2/D-041: não construir antecipando um requisito hipotético). Reaproveita exatamente a mesma permissão que já protege `GET /risks/latest`, a fonte de dados deste agente.

- `organization_id` vem de `context.organization.organization_id` (nunca do cliente), mesmo padrão das outras 8 rotas do módulo.
- Resolve os riscos via `ProjectSummaryService.list_latest_risks(organization_id, project_name)` — zero query nova, zero tabela nova (Blueprint §5).
- Auditoria: `repository.administration.record_audit(organization_id, context.user.user_id, "risk_advisor.question_asked", "project", None, {"project_name": ..., "question": question})` — **nunca a resposta do LLM no log** (Blueprint §12), mesma disciplina de allowlist já usada em `USER-MANAGEMENT-EXECUTIVE-REPORT` (nunca senha) e nas 3 rotas de análise deste mesmo Gate (nunca o payload completo).
- Validação: `question` com `min_length=3, max_length=2000` (mesmo padrão de tamanho mínimo/máximo já usado em `project_context`/`transcript`, ajustado à escala de uma pergunta).

## 3. BFF (Next.js)

Nova rota `web/app/api/bff/workspace/[projectName]/risk-advisor/route.ts` — mesmo padrão bespoke das 3 rotas `.../analyze/*` deste mesmo Gate (`readSessionIdentity`/`institutionalHeaders` de `domain-proxy.ts`, timeout de 60s por depender de LLM, mapeamento de erro 429/422/400). `project_name` vem do segmento de rota (já decodificado, mesmo padrão das demais rotas do Workspace); `question` vem do corpo.

## 4. Frontend

Uma seção "Risk Advisor" na Workspace do Projeto (`web/app/workspace/[projectName]/page.tsx`), mesmo padrão visual das seções existentes (Riscos, Comunicação, Ações): campo de pergunta + botão "Perguntar", resposta exibida com citação da(s) análise(s) de origem (data + link para o dialog de detalhe já existente, reaproveitando `Histórico completo`). Sem histórico de conversa persistido (Blueprint §13/§14) — cada pergunta é independente, o campo limpa após a resposta.

## 5. Migração

Nenhuma (Blueprint §5: nenhuma entidade nova, nenhuma tabela nova).

## 6. Testes

- `tests/test_risk_advisor_agent.py` — unidade do agente (parsing, caso sem riscos não chama o LLM, prompt recebe apenas dados estruturados).
- `tests/test_intelligence_api.py` — nova classe `TestRiskAdvisor`: 403 sem permissão, 200 com resposta e citações corretas, isolamento organizacional (pergunta sobre projeto de outra organização não vê os riscos), auditoria registrada sem a resposta do LLM no log.
- BFF: `web/app/api/bff/workspace/[projectName]/risk-advisor/route.test.ts`, mesmo padrão das 3 rotas `.../analyze/*`.
- Frontend: teste de componente da nova seção (loading/pergunta/resposta/erro).

## 7. Fora de escopo (reafirmado do Blueprint §14)

Multi-agent framework, vector store, RAG, memória de longo prazo, orchestration engine, model registry, prompt registry novo, provider router — nenhum necessário; nenhum introduzido.
