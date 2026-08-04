# AR-11 — Delivery Advisor: Architecture Review

**Autorização:** "Founder Decision — Domain Blueprint do Delivery Advisor" (veredito **APPROVED — GO para a Architecture Review**), reafirmando como definitiva a definição institucional de Classe A/B (D-104) e a fonte oficial do Delivery Advisor (`AnalysisRecord`/`kind="status"`, sem nenhuma segunda fonte estrutural neste Epic), e exigindo que esta revisão analise explicitamente **um único ponto adicional**: se a recência do `AnalysisRecord` deve influenciar a interpretação do Delivery Advisor, avaliado exclusivamente como decisão arquitetural. Preservação integral de `AdvisorFramework`, `AIContextEngine`, Workflow Runtime, Event Pipeline exigida. Nenhum código, nenhum Technical Design produzido aqui.

**Etapa do ciclo institucional:** 3 de 6 (Domain Blueprint concluído D-104 → **Architecture Review, este documento** → Founder Approval → Technical Design → Implementação → Executive Review).

**Método:** toda conclusão é rastreável a código real — `src/database/repository.py::list_analyses`, `src/services/ai_foundation/context_engine.py::gather`, `src/services/advisor_framework/framework.py::run`, `src/agents/risk_advisor/agent.py`.

---

## Executive Summary

Esta Architecture Review resolve o único ponto que o Domain Blueprint deixou para esta etapa (§8.1 do Domain Blueprint): se a recência de um `AnalysisRecord` deve influenciar a interpretação do Delivery Advisor. A resposta, fundamentada em leitura direta de código, é **sim** — mas resolvida inteiramente como **conhecimento de domínio no prompt do `DeliveryAdvisorAgent`** (Technical Design), nunca como lógica nova em `AIContextEngine`/`AdvisorFramework`. `AnalysisRecord.list_analyses()` (`src/database/repository.py:135-166`) já ordena por `created_at.desc()` — a evidência já chega ao Advisor em ordem cronológica decrescente, sem nenhuma mudança de código necessária; o que falta é apenas a instrução de interpretação (o Advisor deve tratar o `AnalysisRecord` de status mais recente como o estado atual, citando registros mais antigos apenas como contexto histórico, nunca como estado presente) — exatamente o mesmo padrão já estabelecido pela hierarquia documental do Governance Advisor (AR-10, D-100): regra de precedência como prompt, nunca como comparador determinístico no Framework. Nenhum achado estrutural novo. Recomendação ao final: **GO para o Technical Design.**

---

## 1. Reafirmação das decisões já permanentes (não redecididas aqui)

- **Classe A definitiva** (D-104): Delivery Advisor permanece Classe A, uma única fonte primária de evidência.
- **Fonte única e oficial** (D-104): `AnalysisRecord`/`kind="status"`, via `AIContextEngine.gather(organization_id, project_name, kind="status")`. Nenhuma segunda chamada estrutural a `kind="risk"`/`"meeting"`/`action_items` está autorizada neste Epic.
- **Fluxo, contrato do `DeliveryAdvisorAgent`, limites de atuação:** idênticos ao já caracterizado no Domain Blueprint (`DOMAIN-BLUEPRINT-DELIVERY-ADVISOR.md` §3/§4/§7) — não reabertos aqui.

---

## 2. Grounding — o que o código real já faz hoje sobre ordenação/recência

Confirmado por leitura direta:

1. **`AnalysisRepository.list_analyses()`** (`src/database/repository.py:135-166`) já executa `.order_by(AnalysisRecord.created_at.desc(), AnalysisRecord.id.desc())` — **sempre**, para qualquer `kind`, sem exceção. Não é uma ordenação especial a criar para o Delivery Advisor; é o comportamento já existente e usado por todo Advisor de Classe A/B/C.
2. **`AIContextEngine.gather()`** (`context_engine.py:19-49`) chama `list_analyses(..., limit=None)` e converte cada `record` em um `Evidence`, **preservando a ordem que o repositório já devolveu** — o primeiro item de `evidence` já é, hoje, o `AnalysisRecord` mais recente. Nenhuma mudança de código necessária para obter essa garantia.
3. **`Evidence.metadata["created_at"]`** já carrega o timestamp de cada registro (mesmo campo usado pelo Risk Advisor) — a informação de recência já está disponível ao Advisor sem nenhuma extensão de contrato.
4. **Padrão já estabelecido pelo Risk Advisor** (`src/agents/risk_advisor/agent.py:34-49`): quando mais de um `AnalysisRecord` de `kind="risk"` existe para o mesmo projeto, `RiskAdvisorAgent.advise()` inclui **todos** no `risks_json` enviado ao modelo, cada um anotado com `source_created_at` — nunca filtra para "apenas o mais recente", deixando a síntese explicitamente ao LLM, mas **sempre com o dado de recência disponível em texto**. Este é o precedente arquitetural direto: recência é informação, não filtro estrutural.
5. **Precedente de tratamento de precedência como conhecimento de domínio, não lógica de Framework:** já decidido para o Governance Advisor (AR-10 §1/D-100) — a hierarquia Decision Log > Technical Debt Register é aplicada exclusivamente no prompt do `GovernanceAdvisorAgent`, nunca em `AIContextEngine`/`AdvisorFramework`. O mesmo princípio se aplica aqui.

**O que NÃO existe e não será inventado por esta revisão:** nenhum filtro em `AIContextEngine.gather()` que descarte `AnalysisRecord`s antigos; nenhum comparador de datas em `AdvisorFramework.run()`; nenhum campo novo em `Evidence` (o timestamp já existe em `metadata["created_at"]`).

---

## 3. Decisão sobre recência do `AnalysisRecord` (o ponto mandatado pelo Founder)

### 3.1 A pergunta concreta

Um projeto pode ter mais de um `AnalysisRecord` de `kind="status"` ao longo do tempo (uma nova análise de status é gerada a cada execução do `project_status` agent). `AIContextEngine.gather(kind="status")` retorna **todos** eles (sem `limit`), cada um um snapshot completo e potencialmente divergente: `health_status` "red" há duas semanas, "green" hoje. Sem uma instrução explícita, o modelo pode citar um `health_status`/`key_findings` antigo como se fosse o estado atual do projeto — um risco real de resposta enganosa, não hipotético.

### 3.2 Duas opções avaliadas

| Opção | Descrição | Avaliação |
|---|---|---|
| **A — Nenhum tratamento especial** | Todos os `AnalysisRecord`s de status entram no prompt sem anotação de recência além do que já existe (`metadata["created_at"]`, hoje não necessariamente incluído no JSON que o Advisor monta) — mesmo padrão bruto do Risk Advisor, sem reforço adicional. | Insuficiente para este domínio: diferente de "risco" (onde múltiplos itens coexistem legitimamente, cada um com seu próprio ciclo de vida), "status de projeto" é uma sequência de snapshots do **mesmo fato** (saúde do projeto) — sem instrução explícita, a ambiguidade entre "qual é o estado atual" é real, não apenas teórica. |
| **B — Recência como conhecimento de domínio no prompt (recomendada)** | O `DeliveryAdvisorAgent` inclui `created_at`/`source_analysis_id` de cada `AnalysisRecord` de status no JSON enviado ao modelo (mesmo padrão já usado por `RiskAdvisorAgent` com `source_created_at`), e o prompt instrui explicitamente: o `AnalysisRecord` de status mais recente (primeiro da lista, já garantido pela ordenação existente de `list_analyses()`, §2.1-§2.2) representa o **estado atual** do projeto; registros mais antigos são citáveis apenas como **contexto histórico/tendência** (ex.: "o projeto estava red há duas semanas, hoje está green"), nunca apresentados como o estado presente sem essa qualificação. | Resolve o risco real (§3.1) sem nenhuma mudança de Framework/`AIContextEngine` — a ordenação necessária já existe (§2.1); o timestamp necessário já existe (§2.3); o único trabalho é textual (prompt), decisão de Technical Design, mesmo mecanismo já provado pela hierarquia do Governance Advisor (§2.5). |

### 3.3 Decisão

**Opção B — recência tratada como conhecimento de domínio no prompt do `DeliveryAdvisorAgent`.** Regra a ser detalhada em Technical Design (texto exato do prompt, não decidido aqui): o `AnalysisRecord` de status mais recente é a fonte do estado atual; registros mais antigos permanecem citáveis, mas exclusivamente como histórico/tendência, nunca substituindo o mais recente na resposta sobre o estado presente. Nenhuma mudança a `AIContextEngine.gather()`, `AdvisorFramework.run()`, ou ao contrato `Evidence` — a ordenação e o timestamp necessários já existem em produção (§2).

---

## 4. Preservação confirmada (não apenas alegada)

Nenhuma linha de `AdvisorFramework`, `AIContextEngine`, Workflow Runtime, ou Event Pipeline precisa mudar para esta decisão — confirmado pelo grounding (§2): a ordenação por recência e o timestamp por registro já existem hoje, para todo `kind`, sem exceção. A decisão desta revisão é inteiramente de conteúdo de prompt (Technical Design), a mesma natureza de mudança já aplicada pela hierarquia documental do Governance Advisor (AR-10) sem tocar o Framework.

---

## 5. Riscos residuais

1. **Wording exato da instrução de recência no prompt** — decisão de Technical Design; risco de a instrução ser ambígua o suficiente para o modelo ainda confundir histórico com estado atual — mitigação: teste explícito com dois `AnalysisRecord`s de status divergentes (um antigo "red", um recente "green") comprovando que a resposta reflete o mais recente e cita o antigo apenas como histórico, se mencionado.
2. **`no_evidence_answer`/`top_k`/nome definitivo da rota HTTP** — já registrados no Domain Blueprint (§8), não agravados por esta revisão.
3. **TD-015** — não incide neste Advisor (Classe A via `gather_context()`, não `normalize_rag_evidence()`).
4. **Volume de `AnalysisRecord`s de status por projeto ao longo do tempo** — `gather()` usa `limit=None`; se um projeto acumular um histórico muito longo, o JSON enviado ao prompt cresce sem limite. Risco de baixo impacto imediato (mesmo padrão já aceito pelo Risk Advisor para `kind="risk"`), registrado para o Technical Design avaliar um `limit` explícito se necessário — não bloqueante para este Epic.

Nenhum risco listado bloqueia o avanço para o Technical Design.

---

## 6. Critérios de sucesso (reafirmados do Domain Blueprint, per catálogo §6)

1. Nenhuma afirmação sobre atraso/bloqueio sem um `AnalysisRecord` de status real como evidência.
2. Nenhuma resposta apresenta um `AnalysisRecord` de status desatualizado como se fosse o estado atual do projeto, quando um registro mais recente existe — critério novo desta revisão, decorrente de §3.
3. `no_evidence()` funciona sem chamada ao LLM quando não há `AnalysisRecord` de `kind="status"` relevante.
4. Nenhuma citação inventada sobrevive à resposta (`RecommendationEngine.build()`, já estrutural).
5. Isolamento organizacional preservado (`organization_id`/`project_id`-scoping em `AIContextEngine.gather()`, já estrutural).
6. Nenhuma segunda consulta estrutural a outro `kind` (Classe A, D-104).

---

## 7. Recomendação GO/NO-GO para o Technical Design

**GO.** O único ponto mandatado por esta revisão — recência do `AnalysisRecord` — foi resolvido com evidência de código: a ordenação e o timestamp necessários já existem em produção, sem exceção, para todo `kind` (§2); a decisão (Opção B, §3.3) é inteiramente de conteúdo de prompt, aplicando o mesmo princípio já validado pela hierarquia documental do Governance Advisor (AR-10) — precedência como conhecimento de domínio, nunca lógica de Framework. `AdvisorFramework`, `AIContextEngine`, Workflow Runtime e Event Pipeline confirmados preservados integralmente, sem necessidade de nenhuma mudança.

---

## 8. Próximo passo

Per instrução do Founder: nenhum código escrito nesta etapa. Retorno obrigatório para Executive Review antes de prosseguir ao Technical Design (etapa 4).
