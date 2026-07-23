# Enterprise Domain Blueprint — Risk Advisor (Epic W3-3)

**Wave:** 3, Epic W3-3 — a única das 8 "Enterprise Agents" liberada como prova de conceito pela AR-2, per a recomendação já registrada em `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` §4 ("Risk Advisor... mais próximo de já existir — é o Accelerator real com uma interface conversacional nova").
**Natureza:** Enterprise Domain Blueprint (não um Technical Design) — define o domínio, papéis, fluxo e critérios de aceite; não define Protocols, contratos de código ou schema (isso é a Technical Design, próxima etapa, condicionada per Seção 15).
**Status:** Blueprint concluído. **Implementação bloqueada** — ver Seção 15.

---

## 1. Propósito executivo

Dar a um executivo (PMO, Portfolio Owner, Program/Project Manager) uma forma de **perguntar em linguagem natural** sobre os riscos já identificados de um Projeto, em vez de apenas ler o resultado estático de uma Avaliação de Riscos already-run. O Risk Advisor não substitui o Accelerator `risk_review` (que continua produzindo a avaliação estruturada) — ele é uma **camada conversacional sobre o que já foi identificado**, respondendo perguntas como "qual o risco mais crítico do Projeto X agora?" ou "algum risco deste projeto já apareceu em outro projeto do mesmo Program?".

## 2. Decisão executiva apoiada

Priorização de atenção: qual risco, entre os já identificados, merece escalonamento ou mitigação imediata — não uma nova avaliação de risco (isso já é o `risk_review`), mas uma síntese/priorização sobre avaliações existentes, em linguagem natural, sob demanda.

## 3. Atores

- **Usuário primário:** qualquer usuário com papel que já tenha acesso de leitura a Riscos hoje (mesma superfície RBAC do Workspace/Dashboard — a decidir exatamente qual permissão na Technical Design, ver Seção 15/Decision Proposal C-1).
- **Sistema:** o próprio Risk Advisor (extensão conversacional do Accelerator `risk_review` existente).
- **Fora de escopo como ator:** nenhum outro Advisor, nenhum sistema externo.

## 4. Entradas e saídas

**Entrada:** uma pergunta em linguagem natural do usuário + o `project_id` do Projeto em contexto (o usuário já está na Workspace de um Projeto específico — não uma pergunta cross-portfolio nesta primeira versão).
**Saída:** uma resposta em linguagem natural, **sempre derivada exclusivamente das avaliações de risco já persistidas** (`AnalysisRecord` com `kind="risk"` para aquele `project_id`, via `ProjectSummaryService.list_latest_risks()` já existente) — nunca uma nova chamada de análise, nunca informação inventada fora desses dados.

## 5. Modelo de domínio

**Nenhuma entidade nova.** O Risk Advisor não introduz um Bounded Context — ele lê o que já existe:
- `Project` (real, DDD, Wave 2) — para resolver o `project_id` em contexto e confirmar organization scope.
- `AnalysisRecord` (kind="risk") — a fonte de verdade dos riscos já identificados, já linkada a `project_id` desde o Epic W3-1.
- Nenhuma tabela nova, nenhuma migração.

## 6. Fluxo decisório

1. Usuário faz uma pergunta na interface conversacional, no contexto de um Projeto.
2. O backend resolve os riscos mais recentes daquele `project_id` (reaproveita `ProjectSummaryService.list_latest_risks(project_name=...)`, ou uma variante por `project_id` — decisão de Technical Design).
3. O prompt enviado ao LLM contém **exclusivamente** os riscos já estruturados (descrição, probabilidade, impacto, mitigação, recomendação de escalonamento) — nunca o contexto bruto do projeto, nunca dados de outro projeto.
4. O LLM sintetiza uma resposta em linguagem natural à pergunta, restrita a esse conjunto de dados.
5. A resposta é devolvida ao usuário; **nenhuma escrita ocorre** (o Risk Advisor é somente leitura — não cria, edita ou dispara uma nova análise).

## 7. Integração entre domínio e LLM

Reaproveita integralmente `LLMProvider` (Protocol existente) + `PromptRegistry` (path-based, existente) — **nenhuma extensão de nenhum dos dois é necessária** para este Epic (ao contrário do que Epic W3-2 teria proposto, e que já foi adiado por falta de caso de uso real; este é precisamente o primeiro caso de uso real, mas não exige multi-provider nem versionamento de prompt — um provider, um prompt novo, mesmo padrão dos 3 Accelerators existentes).

## 8. Explainability

Toda resposta do Risk Advisor deve citar de qual(is) `AnalysisRecord` (por `source_analysis_id` e data) a informação foi extraída — mesmo padrão já usado em `ActionItemResponse`/`LatestRiskItemResponse` (`source_analysis_id`, `source_created_at`). Nenhuma resposta pode apresentar uma síntese sem a referência à análise de origem, para que o executivo possa sempre verificar a fonte.

## 9. Nível de confiança

Per ADR-V2-007 ("toda ação crítica de IA exige validação humana por padrão"), o Risk Advisor é uma ferramenta de **síntese informativa, não uma recomendação de decisão automática** — não há "nível de confiança" numérico a ser exibido nesta primeira versão (nenhum Accelerator hoje expõe isso); a explainability da Seção 8 cumpre o papel de permitir a verificação humana.

## 10. RBAC

**Decisão pendente, registrada como parte da Decision Proposal C-1 do Repository Audit (`REPOSITORY-AUDIT-WAVE-3.md`, `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §16):** hoje, nenhuma rota de `intelligence.py` (de onde `list_latest_risks` é servido) aplica RBAC. O Risk Advisor **não deve** ser implementado sobre essa mesma lacuna — precisa, no mínimo, de uma permissão de leitura (`intelligence.read` ou equivalente, a decidir na Technical Design, após o Founder decidir C-1).

## 11. Organization scope

Mesma lacuna: `AnalysisRecord` não tem `organization_id` (achado C-2 do Repository Audit). O Risk Advisor **não deve** ser implementado enquanto essa lacuna não for resolvida — do contrário, a resposta do Advisor poderia synthesize riscos de um Projeto de outra organização, exatamente o vazamento já identificado.

## 12. Auditoria

Cada pergunta feita ao Risk Advisor deve ser registrada no audit log (`audit_logs`, mesmo padrão de `administration_service.py`) com: ator, `project_id`, pergunta (texto), timestamp — nunca a resposta completa do LLM no log (consistente com a disciplina já usada: nenhum dado potencialmente sensível é persistido além do necessário).

## 13. Interface conversacional

Um painel de chat simples dentro da Workspace do Projeto (`web/app/workspace/[projectName]`, ou equivalente por `project_id` per a Fase 3b futura de TD-008) — sem histórico persistente de conversa nesta primeira versão (cada pergunta é independente, sem memória entre perguntas), consistente com "nenhuma memória de longo prazo" (explicitamente fora de escopo, Seção 14).

## 14. Explicitamente fora de escopo

Per a instrução direta do Founder: multi-agent framework; vector store; RAG; memória de longo prazo; orchestration engine; model registry; prompt registry novo (reaproveita o existente); provider router. Nenhum destes é necessário para o Risk Advisor conforme desenhado (Seções 5-7) — confirma que o guarda-corpo exigido pela AR-2 ("nenhum framework de orquestração multi-agente sendo introduzido") é cumprido por este desenho.

## 15. Riscos e dependências — Implementação bloqueada

**Este Blueprint não avança para Technical Design/Implementação ainda.** Duas dependências, ambas fora do controle deste Epic:

1. **Decision Proposal C-1/C-2 do Repository Audit** (`REPOSITORY-AUDIT-WAVE-3.md`, `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §16): o Risk Advisor herdaria diretamente a ausência de RBAC e de organization scope de `intelligence.py`/`AnalysisRecord` se implementado antes dessas lacunas serem resolvidas — construir a interface conversacional sobre uma rota sem controle de acesso **agravaria** o problema, não o resolveria. Aguardando decisão do Founder.
2. **Consolidação da `main`** (PR #45, aguardando CI + aprovação) — per a própria instrução do Founder, a Implementação de qualquer Epic novo pressupõe a `main` já atualizada.

**Nenhum código foi produzido por este Epic.** Este Blueprint fica pronto para a Technical Design assim que as 2 dependências acima forem resolvidas.

## 16. Critérios de aceite (para quando a Implementação for autorizada)

- Responde apenas com base em `AnalysisRecord` já persistidos (kind="risk") do `project_id` em contexto, nunca de outro projeto/organização.
- Toda resposta cita a análise de origem (`source_analysis_id`).
- RBAC aplicado (per decisão do Founder em C-1).
- Organization scope aplicado (per decisão do Founder em C-2).
- Pergunta auditada (ator, projeto, texto, timestamp — nunca a resposta completa).
- Nenhuma escrita/mutação: somente leitura.
- Nenhum framework de orquestração, vector store, RAG, ou memória de longo prazo introduzido.
