# AR-2 — Wave 3 Architecture Review

**Missão:** Architecture Review dedicada à Wave 3 (Enterprise Intelligence), exigida explicitamente antes de qualquer Technical Design (`ARCHITECTURE-FREEZE.md` §2.3/§2.4: "Wave 3 exige uma Architecture Review entre Blueprint e Technical Design"; `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` §5: "recomenda-se que este documento passe por uma Architecture Review dedicada antes de qualquer Technical Design ser iniciada").
**Autorização:** Founder, "AUTORIZAÇÃO — INÍCIO DA WAVE 3" (2026-07-23), aprovando o encerramento da Wave 2 e abrindo a Wave 3 sob o fluxo Architecture Review → Domain Blueprint → Technical Design → Implementation → Testing → Executive Report, por Epic, sem nova autorização entre Epics salvo os 5 gatilhos explícitos do Founder.
**Data:** 2026-07-23.
**Autor:** Claude / Tech Lead.

---

## 1. Auditoria de código (baseline pós Wave 2)

- **Estrutura `src/`:** exatamente `agents/api/database/llm/prompts/services/workflows`, per CLAUDE.md — nenhum desvio, nenhum diretório novo, nenhuma arquitetura paralela introduzida pela Wave 2.
- **Grounding do `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` §0 revalidado linha a linha contra o código real:**
  - `PromptRegistry` (`src/prompts/registry.py`) resolve prompts por caminho de arquivo (`base_path/agent_name/prompts/prompt_name.md`), sem conceito de versão — confirmado, inalterado.
  - `LLMProvider` (`src/llm/providers/base.py`, `Protocol`) + `get_provider()` (`factory.py`) seleciona 1 provider ativo por variável de ambiente (`mock`/`anthropic`) — confirmado, sem multi-model routing.
  - 3 agentes de propósito único (`src/agents/{project_status,risk_review,meeting_intelligence}/agent.py`), cada um uma chamada direta a `LLMProvider` via `PromptRegistry`, sem comunicação entre si, sem framework de orquestração — confirmado.
  - Nenhum `TODO`/`FIXME`/`XXX` órfão encontrado em `src/`, `web/lib/`, `web/app/` (grep completo, zero ocorrências).
- **`AnalysisRecord` (`src/database/repository.py`) já possui `project_id` (FK para `projects.id`) populado em toda escrita desde o Épico 1** (`save_analysis` chama `get_or_create_project_for_name` na mesma transação) — mas toda leitura/filtro (`list_analyses`) e toda a superfície de API/BFF/frontend ainda operam sobre `project_name` (string), e `web/lib/dashboard/types.ts::ProjectSummary` permanece um tipo paralelo ao domínio `Project` real (Capability 03). Isto é exatamente TD-008, Fase 3 — confirmado como ainda aberto, não resolvido silenciosamente por nenhuma Sprint da Wave 2.
- **Nenhuma duplicação, código morto ou arquitetura paralela nova** encontrada além do que já era conhecido e registrado (TD-008).

**Conclusão:** o baseline herdado da Wave 2 está limpo. Nenhum achado desta auditoria exige correção antes da Wave 3 começar.

## 2. Auditoria de consistência de governança

- `ARCHITECTURE-FREEZE.md` já previa exatamente esta etapa ("Wave 3 aguardando Architecture Review") — este documento resolve essa pendência. Per a própria regra do Freeze ("este veredito não é reaberto... deve ser registrado como uma nova entrada de Decision Log"), o Freeze **não é editado retroativamente**; a resolução fica registrada em D-039.
- `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §11 (TD ↔ Wave) lista TD-008 como bloqueante "antes de migrar dados reais de `projects_delivery`" — **premissa desatualizada, não uma nova decisão:** `projects_delivery` nunca foi criada como tabela separada (Fase 1 do `DOMAIN-BLUEPRINT-PROJECT.md`, Opção A, já unificou os campos de domínio na própria tabela `projects` do Épico 1). O gatilho real e atual de TD-008 Fase 3 é "a Wave 3 (AI Foundation) começar" (`TECHNICAL_DEBT.md` TD-008), não a criação de uma tabela que nunca existiu. Correção de premissa registrada aqui, mesmo padrão já usado em D-034/D-035 — nenhum documento é reescrito.
- `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` permanece válido sem alteração — esta Architecture Review não encontrou nenhuma imprecisão em seu conteúdo, apenas o formaliza como precondição cumprida.
- Nenhuma divergência entre Mission Control, CHANGELOG, Decision Log e o estado real do repositório encontrada.

## 3. Verificação de engenharia

Reaproveitada a verificação já executada nesta mesma sessão para o encerramento da Wave 2 (nenhuma mudança de código ocorreu entre aquela verificação e esta revisão — apenas documentação):

| Verificação | Resultado |
|---|---|
| `pytest` (backend, PostgreSQL efêmero) | 281 passed |
| `ruff check src tests` | Limpo |
| `vitest run` (frontend) | 437 passed |
| `tsc --noEmit` | Limpo |
| `eslint .` | Limpo |
| Playwright E2E — `lg`/`md`/`mobile` | 81 testes cada, todos passando |

**Nenhuma correção de engenharia exigida por esta Architecture Review.**

## 4. Epic Ledger — Wave 3 (Enterprise Intelligence)

Organização dos 4 sub-espaços de `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §5 em Epics executáveis, na ordem em que podem ser seguramente iniciados. Cada Epic segue o fluxo completo determinado pelo Founder (Architecture Review própria → Domain Blueprint → Technical Design → Implementation → Testing → Executive Report) — os itens "Pronto para iniciar" abaixo já passaram pela camada de Architecture Review que este documento fornece na Wave 3; um Epic com particularidades adicionais ainda pode exigir sua própria revisão específica no momento do seu Blueprint.

### Epic W3-1 — Project Identity Unification (TD-008, Fase 3) — **Pronto para iniciar**

Reconciliar `analysis_records.project_name` com `project_id` como chave primária de fato em toda a superfície (API, BFF, frontend); aposentar `web/lib/dashboard/types.ts::ProjectSummary` em favor do domínio `Project` real (Capability 03/`web/lib/domain/project.ts`). Não introduz Bounded Context novo (o domínio `Project` já existe desde a Wave 2); não depende de nenhuma decisão do Founder. **Pré-requisito de fato para qualquer "Intelligence" sobre Projects** (Epic W3-3) — não é possível construir uma camada de insight de IA confiável sobre um dado ainda chaveado por string legada.

### Epic W3-2 — AI Platform Foundation — **Avaliado e adiado (D-041), sem gatilho concreto**

O Domain Blueprint deste Epic (`DOMAIN-BLUEPRINT-AI-PLATFORM-FOUNDATION.md`) auditou cada sub-área item a item e encontrou **zero consumidor real hoje** para Provider Strategy/Model Registry/Model Routing/Prompt Versioning/Evaluation Framework, e nenhum requisito ativo para Cost/Token/Observability (apesar de um gap real: `ProductionLLMProvider.generate()` descarta `message.usage` da Anthropic hoje). Construir qualquer uma dessas peças agora seria arquitetura especulativa sem caso de uso, contra a disciplina "não fazer mais do que o necessário" (CLAUDE.md). **Nenhum código produzido.** Adiado até um gatilho concreto existir (ver Blueprint §3) — não removido do Ledger, apenas fora de ordem de execução por ora.

### Epic W3-3 — Executive Intelligence: Risk Advisor (prova de conceito de um único Enterprise Agent) — **Pronto para iniciar, com revisão de escopo obrigatória no próprio Blueprint**

Porta o Accelerator `risk_review` (já real) para consumir o domínio `Project` real (depende de W3-1 concluído) e adiciona uma interface conversacional sobre ele — candidato explicitamente recomendado pelo próprio Blueprint da Wave 3 ("mais próximo de já existir — é o Accelerator real com uma interface conversacional nova"). **Condição de guarda-corpo:** o Domain Blueprint deste Epic deve provar que nenhum framework de orquestração multi-agente está sendo introduzido (nenhuma comunicação entre agentes, nenhuma memória compartilhada nova, nenhum roteamento) — caso o desenho não caiba nessa restrição, o Epic para antes da implementação e volta como Decision Proposal ao Founder (gatilho "necessidade de alteração arquitetural significativa"), em vez de decidir isso silenciosamente.

### Bloqueado — Knowledge Platform (Vector Store, Embeddings, RAG, Semantic Search, Context Manager, "Enterprise Memory")

**Não iniciado nesta Wave sem decisão prévia do Founder.** Adotar um Vector Store introduz um tipo de armazenamento novo (hoje: só Postgres/SQLite via SQLAlchemy) — decisão de infraestrutura com implicação de custo/operação, que o próprio `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` já identificava como pertencente exclusivamente ao Founder. Corresponde diretamente ao gatilho de parada "decisão estratégica dependente do Founder". Ver Decision Proposal em `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §15 (nova seção, aditiva).

### Bloqueado — Enterprise Agents (os 7 Advisors além do Risk Advisor)

**Não iniciado nesta Wave sem decisão prévia do Founder.** Generalizar de um único Advisor (W3-3) para os 8 nomeados no Blueprint exige um framework de orquestração multi-agente que não tem precedente arquitetural na STRATECH hoje — corresponde ao gatilho de parada "necessidade de alteração arquitetural significativa" e, dependendo do desenho, "criação de novos Bounded Contexts". Ver Decision Proposal em `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §15.

## 5. Veredito

**Baseline aprovado para a Wave 3 começar.** Nenhuma correção de código ou de documentação foi necessária além das correções de premissa registradas na Seção 2 (não uma reabertura de decisão, apenas atualização de um dado factual). Autorizados a prosseguir imediatamente, sem nova autorização do Founder: Epic W3-1 e Epic W3-2, em paralelo ou em sequência. Epic W3-3 prossegue condicionalmente à sua própria revisão de escopo no momento do Blueprint. Knowledge Platform e o framework de Enterprise Agents permanecem bloqueados, aguardando decisão do Founder (Decision Proposal registrada, não silenciosamente adiada).
