# Domain Blueprint — Wave 3: Enterprise Intelligence

**Wave:** 3 (Enterprise Master Execution Program)
**Status:** Blueprint conceitual — não implementa, não produz código. Precondição para que a Wave 3 deixe de estar "sem Blueprint" (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §5).
**Natureza deste documento:** diferente dos Domain Blueprints CB-001/002/003 (que precediam a implementação de algo já decidido em detalhe), este Blueprint precede a **primeira decisão de arquitetura** de uma área inteiramente nova. Por isso, cada seção classifica explicitamente o que é reaproveito de algo real, o que é uma proposta conceitual nova (precisa de Architecture Review antes de virar Technical Design) e o que é uma pergunta em aberto que este documento não resolve.

**O que este documento NÃO faz:** não define Protocols, contratos, schemas ou código (isso é Technical Design, próxima etapa, per o fluxo Blueprint → Technical Design → Decision Validation → Sprint Planning → Implementation). Não altera Product Constitution, Foundation Architecture, Foundation Technical Design, Enterprise Master Execution Program, Decision Logs ou Technical Debt Register.

---

## 0. O que já é real hoje (não proposto, já existe)

| Componente | Onde |
|---|---|
| 3 agentes de propósito único: Project Health, Risk Intelligence, Meeting Intelligence | `src/agents/project_status/`, `risk_review/`, `meeting_intelligence/` |
| `PromptRegistry` | `src/prompts/registry.py` |
| `LLMProvider` (interface) + seleção de 1 provider ativo | `src/llm/providers/base.py`, `factory.py` |
| AI-Accelerators-Map (taxonomia de referência, 12 Accelerators, 3 construídos) | `docs/product/stratech-v2/` |
| Contrato "toda ação crítica de IA exige validação humana por padrão" | ADR-V2-007 |
| "Riscos" de portfólio ≠ Risk Intelligence de IA (dois conceitos, deliberadamente separados) | D-005/D-009 |
| "Executive Memory" (insights Mudou/Persistiu/Reapareceu) — já em produção, V1 | Workspace/Dashboard |

Estes são os únicos alicerces reais sobre os quais a Wave 3 pode ser construída sem inventar nada. Tudo abaixo que não estiver marcado "✅ Real" é proposta conceitual, não decisão.

---

## 1. AI Platform

| Sub-área | Classificação | Proposta conceitual |
|---|---|---|
| **Prompt Registry** | ✅ Real | `PromptRegistry` já cumpre este papel — reaproveitar, não recriar. |
| **Provider Strategy** | 🟡 Parcial (existe seleção de 1 provider) | Evoluir `LLMProvider`/`factory.py` de "1 provider ativo por configuração" para "múltiplos providers registrados, seleção por caso de uso" — **extensão** do Protocol existente, não um segundo mecanismo. Reaproveita o padrão Protocol já usado em `CredentialVerifier`/`IdentityResolver`. |
| **Model Registry** | 🔵 Proposta nova | Catálogo de modelos disponíveis por provider (nome, custo, limites, capacidades) — consumido pelo Provider Strategy acima para decidir roteamento. Não existe hoje nem como conceito. |
| **Model Routing** | 🔵 Proposta nova | Regra que decide qual modelo atende qual chamada (ex.: por Accelerator, por custo-alvo, por criticidade). Depende do Model Registry existir primeiro. |
| **Prompt Versioning** | 🔵 Proposta nova | `PromptRegistry` hoje resolve prompts por caminho de arquivo (`base_path="src/agents"`), sem conceito de versão explícita. Adicionar versionamento é uma extensão aditiva ao Registry existente — não um Registry novo (CLAUDE.md: nunca criar novo registry). |
| **Cost Management, Token Governance** | 🔵 Proposta nova | Nenhuma medição de custo/token existe hoje em nenhum Accelerator. Pré-requisito: instrumentação nos 3 agentes existentes antes de generalizar. |
| **AI Observability, AI Governance** | 🔵 Proposta nova | Sem grounding hoje — nenhum log estruturado de decisão de IA existe além do que `AnalysisRepository` já persiste (payload da análise, não metadados de governança de IA). |
| **Evaluation Framework** | 🔵 Proposta nova | Nenhuma suíte de avaliação de qualidade de output de IA existe hoje (os testes atuais — `test_meeting_agent.py`, `test_risk_review_agent.py`, `test_project_status_agent.py` — testam integração/contrato, não qualidade de resposta). |

**Recomendação de sequenciamento (proposta, não decisão):** Provider Strategy (extensão) → Model Registry → Model Routing → Cost/Token → Observability/Governance → Evaluation Framework. Nenhum destes deve começar sem uma Technical Design própria — este Blueprint apenas nomeia o espaço.

## 2. Knowledge Platform

| Sub-área | Classificação | Proposta conceitual |
|---|---|---|
| **Enterprise Knowledge Base, Semantic Search, Embeddings, Vector Store, RAG Strategy** | 🔵 Proposta nova, zero grounding | Nenhum destes existe em nenhuma forma na STRATECH hoje — nem como schema, nem como dependência instalada, nem como ADR. Introduzir um Vector Store é adicionar um novo tipo de armazenamento à arquitetura (hoje só Postgres/SQLite via SQLAlchemy) — decisão de infraestrutura que precisa de ADR próprio antes de Technical Design. |
| **Context Manager** | 🔵 Proposta nova | Conceito de "gerenciar contexto entregue ao LLM" não existe hoje — cada agente monta seu próprio `transcript`/`project_context` diretamente na request (`intelligence.py`). Generalizar isso é razoável, mas ainda não desenhado. |
| **Enterprise Memory** | ⚠️ **Risco de colisão de nome, sinalizado explicitamente** | Já existe "Executive Memory" em produção (V1) — insights "Mudou/Persistiu/Reapareceu" computados no Workspace/Dashboard, sem Vector Store, sem RAG. "Enterprise Memory" (Knowledge Platform, este Blueprint) e "Executive Memory" (já real) **devem permanecer conceitos distintos e nomeados de forma inconfundível** — mesma disciplina de D-005/D-009/D-012/D-019. Este Blueprint não resolve o nome final; apenas exige que, quando esta capability for desenhada, um nome diferente de "Executive Memory" seja escolhido antes de qualquer código. |

**Dependência explícita:** Knowledge Platform inteiro depende de uma decisão de infraestrutura (Vector Store) que não pode ser tomada por este Blueprint — é uma decisão de ADR, com implicações de custo/operação que pertencem ao Founder.

## 3. Executive Intelligence

| Sub-área | Classificação | Proposta conceitual |
|---|---|---|
| **Portfolio/Program/Project Intelligence** | 🟡 Parcial | Os 3 domínios já existem como entidades DDD (Wave 2, Capabilities 01-03). "Intelligence" aqui significa uma camada de insight de IA **sobre** esses domínios — ainda não existe, mas tem onde se apoiar (o domínio real já modelado). |
| **Risk Intelligence** | ✅ Real, mas hoje é um Accelerator isolado (`risk_review`), não integrado ao domínio Project | Portar para consumir o `Project` real (DDD) é o trabalho já nomeado na Release 0.3/AI Foundation do Master Roadmap — não uma invenção nova. |
| **Executive Decision Intelligence, PMO Intelligence, Governance Intelligence** | 🔵 Proposta nova | Nenhum existe. Mapeiam conceitualmente para o Programa "Executive Intelligence" já aprovado no Blueprint v2.0 (Cockpit views, indicadores, alertas) — mas nenhum desses 3 nomes específicos foi definido antes deste documento. |

**Cuidado de nomenclatura, mesma disciplina do resto do projeto:** "PMO Intelligence" e "Governança Intelligence" não podem ser confundidos com a governança de **processo de engenharia** já existente (EO→ADR→Architecture Review→PR→merge, LL-002) — são camadas de IA sobre o domínio de produto, não sobre o processo de desenvolvimento. Distinção registrada aqui preventivamente.

## 4. Enterprise Advisors

**Aviso mais forte desta seção:** nenhum destes 8 Advisors tem qualquer precedente arquitetural na STRATECH. Não existe hoje nenhum framework de orquestração multi-agente — os 3 agentes reais são chamadas diretas e isoladas a `LLMProvider` via `PromptRegistry`, sem comunicação entre si, sem memória compartilhada, sem roteamento. Definir "responsabilidades" para 8 Advisors sem esse framework existir seria descrever comportamento de um sistema que não tem fundação — por isso esta seção define apenas o **papel conceitual** de cada um (o que cada Advisor responderia, se existisse), não como eles seriam construídos:

| Advisor | Papel conceitual (proposta) | Reaproveita |
|---|---|---|
| Executive Advisor | Síntese executiva cross-domínio (portfolio + risco + governança) para o perfil C-level | Nenhum agente hoje cobre múltiplos domínios — todos são de escopo único |
| PMO Advisor | Perguntas operacionais de PMO (status agregado, gargalos) | Se apoiaria em Program/Project Intelligence (Seção 3) |
| Portfolio Advisor | Perguntas sobre saúde/composição do Portfolio | Se apoiaria no domínio `Portfolio` (Wave 2) já real |
| Delivery Advisor | Perguntas sobre execução de Projects | Se apoiaria no domínio `Project`/`ProjectDelivery` (Wave 2) |
| Governance Advisor | Perguntas sobre conformidade/débito técnico/decisões pendentes | Se apoiaria em Decision Log/Technical Debt Register — mas estes são documentos Markdown hoje, não uma fonte de dados consultável por IA |
| Strategy Advisor | Perguntas de alinhamento estratégico Portfolio↔objetivos | Sem grounding específico hoje |
| Risk Advisor | Superfície conversacional sobre o já-existente `risk_review` Accelerator | ✅ Mais próximo de já existir — é o Accelerator real com uma interface conversacional nova |
| Document Advisor | Perguntas sobre documentos referenciados (Document Intelligence, Release 0.4) | Depende de Document Intelligence existir primeiro — hoje não existe |

**Pré-requisito explícito para qualquer Advisor sair do papel:** um framework de orquestração multi-agente (que "Advisor" hoje pressupõe implicitamente) não está desenhado em nenhum documento da STRATECH. Este Blueprint não o desenha — recomenda que a primeira Technical Design da Wave 3 escolha **um único Advisor** (candidato natural: Risk Advisor, por já ter um Accelerator real por trás) como prova de conceito, antes de generalizar para os outros 7.

---

## 5. O que este Blueprint resolve vs. o que continua em aberto

| Resolvido por este documento | Continua em aberto (Founder / Architecture Review) |
|---|---|
| Nomeação e organização do espaço-alvo da Wave 3 em 4 sub-áreas | Se/quando um Vector Store é adotado (decisão de infraestrutura, ADR próprio) |
| Reaproveitamento explícito do que já é real (Prompt Registry, Provider factory, 3 Accelerators) | Framework de orquestração multi-agente (pré-requisito de qualquer Advisor) |
| Sinalização preventiva de 2 riscos de colisão de nome ("Enterprise Memory" vs. "Executive Memory"; "PMO/Governance Intelligence" vs. governança de processo) | Qual Advisor é o primeiro a ganhar Technical Design |
| Sequenciamento recomendado dentro de AI Platform | Cost Management/Token Governance — nenhuma medição existe para calibrar isso ainda |

**Este Blueprint não substitui uma Architecture Review formal.** Por ser a primeira decisão de arquitetura de uma área inteiramente nova (diferente de CB-001/002/003, que formalizavam algo já falado em Blueprints anteriores), recomenda-se que este documento passe por uma Architecture Review dedicada antes de qualquer Technical Design ser iniciada — mesma disciplina já usada para AR-1.
