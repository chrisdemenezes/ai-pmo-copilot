# Enterprise Advisor Catalog

**Status:** Blueprint subordinado a `WAVE-3-DOMAIN-BLUEPRINT.md`. **Nenhum Advisor deste catálogo é implementado nesta etapa** — este documento cataloga objetivo, responsabilidade, entradas, saídas, limites de atuação, integrações, dependências e critérios de sucesso de cada um dos 8 Enterprise Advisors, para uso como referência da Fase 4 (implementação individual, após Framework e Foundation existirem — `WAVE-3-DOMAIN-BLUEPRINT.md` §6).

Todos os 8 Advisors compartilham:
- O mesmo contrato (`AdvisorContract`, `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` §2).
- A mesma infraestrutura de execução (Advisor Framework) e de evidência/prompt/observabilidade/auditoria (Digital PMO Intelligence Foundation).
- O mesmo anti-hallucination guard (`RecommendationEngine.build()`/`no_evidence()`) — nenhum Advisor cita o que não pode evidenciar.
- O mesmo escopo obrigatório por `organization_id` (Princípio 6, documento mestre).

---

## 1. Risk Advisor (já existe — referência de padrão)

- **Objetivo:** apoiar decisões de mitigação de risco em um projeto com recomendações fundamentadas em evidência real.
- **Responsabilidade:** responder perguntas sobre risco de um projeto/portfólio, citando `AnalysisRecord`s reais.
- **Entradas:** pergunta do usuário + `organization_id` + escopo (projeto/portfólio, resolvido via `resolve_scope_id`).
- **Saídas:** `Recommendation` + `Explanation` (Foundation), sempre com citação real ou `no_evidence()`.
- **Limites de atuação:** não decide, apenas recomenda; nunca cita o que não está em `AnalysisRecord`.
- **Integrações:** `POST /risk-advisor/ask` (já em produção).
- **Dependências:** Foundation (`AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, `render_analyst_prompt`) — já implementado, é o próprio padrão de referência para os demais 7.
- **Critérios de sucesso:** já provados em produção (W3-3) — citação sempre real, resposta honesta quando não há evidência.

---

## 2. Executive Advisor

- **Objetivo:** sintetizar o estado executivo de um portfólio/organização para liderança sênior (visão consolidada, não operacional).
- **Responsabilidade:** compor um resumo executivo (Executive Briefing) a partir de sinais já existentes (Portfolio Intelligence, Decision Center, riscos, ações) — nunca recalcula esses sinais, apenas os sintetiza.
- **Entradas:** `organization_id` + escopo de portfólio/organização; opcionalmente um período de referência.
- **Saídas:** narrativa executiva estruturada, citando as fontes reais consolidadas (mesma disciplina de citação do Risk Advisor).
- **Limites de atuação:** não substitui o Executive Dashboard já existente (V1) — consome os mesmos dados, apresenta em linguagem natural; nunca inventa uma métrica que o Dashboard não exibe.
- **Integrações:** Executive Dashboard, Decision Center, Portfolio Intelligence.
- **Dependências:** Advisor Framework, Foundation; Knowledge Platform apenas se precisar de contexto documental (RAG opcional, não obrigatório para este Advisor).
- **Critérios de sucesso:** toda afirmação executiva rastreável a um dado real do domínio; nenhuma alucinação de métrica.

---

## 3. Strategy Advisor

- **Objetivo:** apoiar decisões de alinhamento estratégico entre iniciativas e objetivos organizacionais.
- **Responsabilidade:** avaliar se um conjunto de projetos/programas está alinhado a objetivos declarados (quando existirem no domínio); sinalizar desvio, nunca decidir a estratégia.
- **Entradas:** `organization_id` + escopo de portfólio/programa + (quando existente) objetivos estratégicos declarados.
- **Saídas:** `Recommendation`/`Explanation` apontando alinhamento ou desvio, com citação real.
- **Limites de atuação:** não cria objetivos estratégicos por conta própria; opera apenas sobre o que já está declarado no domínio.
- **Integrações:** Portfolio, Program, Decision Center.
- **Dependências:** Advisor Framework, Foundation, Knowledge Platform (RAG sobre documentos estratégicos, quando existentes).
- **Critérios de sucesso:** nenhuma recomendação estratégica sem uma referência real a um objetivo ou projeto existente.

---

## 4. PMO Advisor

- **Objetivo:** apoiar a função de PMO (Project Management Office) com visão consolidada de conformidade e saúde de processo entre projetos.
- **Responsabilidade:** identificar padrões de processo (atrasos recorrentes, ausência de atualização, lacunas de governança) através de múltiplos projetos de uma organização.
- **Entradas:** `organization_id` + escopo organizacional/portfólio.
- **Saídas:** `Recommendation`/`Explanation` sobre saúde de processo, citando os projetos reais envolvidos.
- **Limites de atuação:** não avalia conteúdo de risco de projeto individual (isso é o Risk Advisor) — foco em processo e conformidade, não em conteúdo de risco.
- **Integrações:** Portfolio, Program, Project, Actions, Governança (RBAC/conformidade já existente).
- **Dependências:** Advisor Framework, Foundation; é o primeiro candidato à generalização de um segundo Advisor (recomendado em `WAVE-3-EXECUTIVE-PLAN.md` §3.4, por ser o mais próximo do domínio já implementado).
- **Critérios de sucesso:** padrões identificados sempre referenciam projetos/dados reais; nenhuma generalização sem evidência de múltiplos projetos.

---

## 5. Portfolio Advisor

- **Objetivo:** apoiar decisões de composição e priorização de portfólio.
- **Responsabilidade:** avaliar equilíbrio, dependências e sobreposição entre projetos/programas dentro de um portfólio.
- **Entradas:** `organization_id` + `portfolio_id`.
- **Saídas:** `Recommendation`/`Explanation` sobre composição de portfólio, citando programas/projetos reais.
- **Limites de atuação:** não decide alocação de orçamento ou prioridade — apenas evidencia trade-offs para quem decide.
- **Integrações:** Portfolio, Program, Project, Portfolio Intelligence (já existente, Wave 2).
- **Dependências:** Advisor Framework, Foundation.
- **Critérios de sucesso:** toda recomendação de composição rastreável a projetos/programas reais do portfólio avaliado.

---

## 6. Delivery Advisor

- **Objetivo:** apoiar a execução operacional de um projeto (entrega, cronograma, bloqueios).
- **Responsabilidade:** sintetizar o estado de entrega de um projeto a partir de ações, riscos e histórico de análise já existentes.
- **Entradas:** `organization_id` + `project_id`.
- **Saídas:** `Recommendation`/`Explanation` sobre risco de entrega, citando `AnalysisRecord`s/ações reais.
- **Limites de atuação:** não decide replanejamento — evidencia o estado atual para quem decide.
- **Integrações:** Project, Actions, `AnalysisRecord` (via Foundation).
- **Dependências:** Advisor Framework, Foundation.
- **Critérios de sucesso:** nenhuma afirmação sobre atraso/bloqueio sem uma ação ou análise real como evidência.

---

## 7. Governance Advisor

- **Objetivo:** apoiar conformidade com a própria governança STRATECH (Decision Log, Technical Debt, Wave Completion Policy).
- **Responsabilidade:** verificar se decisões/débitos técnicos/waves seguem o processo de governança declarado (ex.: nenhuma Decision Proposal esquecida, nenhum TD sem classificação).
- **Entradas:** `organization_id` (escopo organizacional da governança) + documentos de governança já existentes (Decision Log, Technical Debt, Mission Control).
- **Saídas:** `Recommendation`/`Explanation` sinalizando lacunas de governança, citando o item real (ex.: "TD-00X sem classificação").
- **Limites de atuação:** não decide política de governança — aplica a política já declarada nos documentos existentes.
- **Integrações:** Decision Log, Technical Debt, Mission Control, Wave Closure Reports.
- **Dependências:** Advisor Framework, Foundation, Knowledge Platform (RAG sobre os documentos de governança, via ingestão desses mesmos documentos).
- **Critérios de sucesso:** nenhuma lacuna sinalizada sem citação real ao documento de governança correspondente.

---

## 8. Document Advisor

- **Objetivo:** responder perguntas sobre o conteúdo de documentos corporativos ingeridos pela Enterprise Knowledge Platform.
- **Responsabilidade:** é o Advisor de referência para uso direto do RAG Pipeline — recupera e sintetiza conteúdo documental sob pergunta livre.
- **Entradas:** pergunta do usuário + `organization_id` + escopo opcional (projeto/portfólio/documento).
- **Saídas:** `Recommendation`/`Explanation` citando `document_id`/`chunk_id` reais (nunca um resumo sem origem rastreável).
- **Limites de atuação:** não interpreta além do que o documento diz — se a pergunta não tem evidência documental, retorna `no_evidence()`, nunca infere.
- **Integrações:** Enterprise Knowledge Platform (RAG Pipeline, Semantic Search, Knowledge Repository) — é o Advisor mais diretamente acoplado à Knowledge Platform.
- **Dependências:** Advisor Framework, Foundation, Knowledge Platform (obrigatória, ao contrário dos demais Advisors onde RAG é opcional).
- **Critérios de sucesso:** toda resposta cita um chunk/documento real; nenhuma resposta sem evidência documental correspondente é apresentada como fato.

---

## Nota final

Nenhum destes 8 Advisors é implementado por este documento. A ordem recomendada de implementação (Fase 4, após Framework/Foundation prontos) é responsabilidade de `WAVE-3-EXECUTION-PLAN.md`, informada pela proximidade de cada Advisor ao domínio já existente (PMO Advisor como segundo candidato mais próximo, após o Risk Advisor já provado).
