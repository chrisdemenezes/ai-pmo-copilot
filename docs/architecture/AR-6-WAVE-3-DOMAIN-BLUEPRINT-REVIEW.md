# AR-6 — Architecture Review: Wave 3 Domain Blueprint (Digital PMO Intelligence)

**Escopo:** revisão arquitetural dos 8 entregáveis do Wave 3 Domain Blueprint (`WAVE-3-DOMAIN-BLUEPRINT.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md`, `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md`, `ENTERPRISE-ADVISOR-CATALOG.md`, `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md`, `WAVE-3-INTEGRATION-BLUEPRINT.md`, `WAVE-3-EXECUTION-PLAN.md`), antes de qualquer Technical Design, per o fluxo institucional obrigatório (Domain Blueprint → **Revisão Arquitetural** → Aprovação do Founder → Implementação incremental) e a exigência já registrada em `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §5 de uma Architecture Review (AR-6) como pré-requisito explícito antes de qualquer Technical Design de Knowledge Platform ou dos Advisors restantes.
**Data:** 2026-07-27
**Contexto:** produzido logo após a conclusão do Blueprint (D-063), antes de qualquer implementação de Fase 1.

---

## 1. Consistência com a arquitetura oficial (CLAUDE.md)

| Regra | Verificação |
|---|---|
| Nunca criar arquitetura paralela | ✅ Nenhum novo diretório de topo é proposto. `Enterprise Knowledge Platform` e `Enterprise Advisor Framework` são descritos como subpacotes de `src/services/`, mesma árvore já oficial que hospeda `ai_foundation/`. |
| Nunca duplicar código | ✅ Os Blueprints são explícitos e repetidos em afirmar reuso de `AIContextEngine`, `RecommendationEngine`, `ExplanationEngine`, `render_analyst_prompt`, `SessionContext`, `AIFoundationAudit`, `ObservabilityRecorder`, `PromptRegistry`, `LLMProvider`, `AnalysisRepository` — nenhum componente é reimplementado. |
| Nunca criar novo provider | ✅ `LLMProvider(Protocol)` permanece único; `EmbeddingProvider` é um Protocol **novo**, mas cobre uma capacidade que não existe hoje (embeddings) — não é um segundo provider concorrente com `LLMProvider`, é uma abstração para uma responsabilidade distinta, análoga em forma, não em escopo. |
| Nunca criar novo registry | ✅ `PromptRegistry` permanece único. `AdvisorContract`/registro de Advisors (Advisor Framework §2-3) é um catálogo de contratos de execução, não um Prompt Registry paralelo — nenhum Advisor tem seu próprio prompt fora de `PromptRegistry`. |
| Reutilizar componentes existentes | ✅ Verificado documento a documento (§2 abaixo). |
| SOLID / Dependency Injection | ✅ `KnowledgeRepository`/`VectorRepository`/`EmbeddingProvider` e `AdvisorContract` são todos definidos como Protocol/abstração injetável, mesmo padrão de `AnalysisRepository`/`LLMProvider` já em produção. |

---

## 2. Checagem item a item das diretrizes do Founder (verbatim)

| Diretriz do Founder | Onde é honrada |
|---|---|
| "A Vector Store é um componente de infraestrutura, nunca um domínio de negócio" | `WAVE-3-DOMAIN-BLUEPRINT.md` Princípio 1; `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` inteiro trata a plataforma como infraestrutura, sem nenhum conceito de negócio nomeado dentro dela. |
| "O domínio não poderá depender diretamente da tecnologia utilizada" | Princípio 2 do documento mestre; `KnowledgeRepository`/`VectorRepository` como única porta de acesso, reafirmado em todos os 4 documentos que tocam a Knowledge Platform. |
| "Toda interação deverá ocorrer através de uma abstração" | Idem — nenhum Advisor, rota ou serviço importa `pgvector` diretamente (`DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §2). |
| "A implementação inicial aprovada será pgvector, mantendo a arquitetura preparada para futura substituição" | Explícito em `DOMAIN-BLUEPRINT-ENTERPRISE-KNOWLEDGE-PLATFORM.md` §1.6 e Critério de evolução §5.1 do documento mestre ("nenhum segundo Vector Store... substituição ocorre atrás da abstração já definida"). |
| "O framework será apenas infraestrutura de execução" | `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` §1 (não-escopo explícito: "nenhum Advisor é implementado aqui"). |
| "Os Enterprise Advisors permanecem conceitos do domínio" | `WAVE-3-DOMAIN-BLUEPRINT.md` §3 (Bounded Context "Enterprise Advisors" classificado como domínio, não infraestrutura); `ENTERPRISE-ADVISOR-CATALOG.md` trata cada Advisor como conceito de negócio com objetivo/responsabilidade próprios. |
| "O domínio nunca poderá depender do framework" | Princípio 3 do documento mestre; `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` §2 — o contrato (`AdvisorContract`) é definido pelo Advisor, o Framework apenas o invoca. |
| "Cada Advisor deverá possuir contrato próprio, responsabilidades bem definidas e independência arquitetural" | `AdvisorContract` com `input_schema`/`output_schema` próprios por Advisor (Framework §2); os 8 Advisors do Catálogo têm objetivo/responsabilidade/entradas/saídas/limites distintos, sem superposição de responsabilidade não justificada. |
| "Não implementar nenhum Epic neste momento" | Verificado: nenhum arquivo de código (`src/`, `web/`) foi tocado por esta missão — apenas `docs/` e uma entrada de dados mock (`mission-control-data.ts`, conteúdo textual de governança, não lógica de produto). |
| "Nenhum Advisor deverá ser implementado nesta etapa" | `ENTERPRISE-ADVISOR-CATALOG.md` — todas as 8 entradas são especificação, nenhuma classe/arquivo de Advisor criado. |

Nenhuma diretriz do Founder foi violada, relaxada ou reinterpretada de forma a reduzir seu rigor original.

---

## 3. Consistência interna entre os 8 documentos

Verificação cruzada de referências (nomes de arquivo citados vs. arquivos reais) confirmou 100% de correspondência, com **uma inconsistência menor encontrada e corrigida durante esta revisão**: `ENTERPRISE-ADVISOR-CATALOG.md` (seção PMO Advisor) citava `WAVE-3-EXECUTIVE-PLAN.md §3.4` — o plano executivo **superseded**, produzido antes deste Blueprint existir — em vez do plano vigente. Corrigido para `WAVE-3-EXECUTION-PLAN.md §2, Fase 4`, o documento correto e atual que carrega a mesma recomendação (PMO Advisor como segundo candidato de generalização, após o Risk Advisor). Nenhuma outra referência cruzada apresentou drift.

Os 8 documentos são mutuamente consistentes quanto a:
- **Camadas e direção de dependência** — a mesma regra ("nenhuma seta sobe") é reafirmada de forma idêntica em `WAVE-3-DOMAIN-BLUEPRINT.md` §1/§4, `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` §0, e `WAVE-3-INTEGRATION-BLUEPRINT.md` §1, sem nenhuma contradição de sentido de seta entre eles.
- **Fluxo síncrono de resposta de Advisor** — descrito uma vez em `WAVE-3-DOMAIN-BLUEPRINT.md` §5.2 e estendido, sem reescrevê-lo de forma divergente, em `DOMAIN-BLUEPRINT-RAG-ARCHITECTURE.md` §1.
- **Checklist de colisão Enterprise Memory vs. Executive Memory** — definida uma única vez (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §0) e apenas referenciada, nunca duplicada ou reformulada, pelos demais documentos que a citam.
- **Ordem de construção (Fase 1-4)** — idêntica entre `WAVE-3-DOMAIN-BLUEPRINT.md` §6 e `WAVE-3-EXECUTION-PLAN.md` §2, sem divergência de sequência.

---

## 4. Grounding: existe consumidor real hoje?

Parcialmente, por desenho. O único consumidor real e em produção de qualquer infraestrutura de IA hoje é o `RiskAdvisorAgent` via `POST /risk-advisor/ask` — e o Blueprint trata isso corretamente como o **padrão de referência**, não como um caso hipotético: `DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` exige explicitamente que esse mesmo agente seja migrado ao novo contrato **antes** de qualquer Advisor novo ser escrito (Fase 3), e `WAVE-3-EXECUTION-PLAN.md` exige um PoC mínimo (Document Advisor, por depender obrigatoriamente do RAG) antes de expandir a Fase 4. Isso preserva a mesma disciplina de "grounding em consumidor real" que a AR-3 já havia validado para a Foundation em si — o risco de especulação sem consumidor (que já reprovou uma versão anterior do W3-2, D-041) está mitigado pelo desenho de Gates, não apenas por promessa.

---

## 5. Risco de sobre-engenharia

Avaliado e mitigado nos 8 documentos:
- Nenhum Model Registry, Provider Router, Prompt Versioning ou Cost/Token Analytics é introduzido — mesma linha já rejeitada em D-041, reafirmada sem reabertura em `WAVE-3-DOMAIN-BLUEPRINT.md` Princípio 5.
- Nenhuma comunicação assíncrona ou fila entre Advisors é antecipada sem caso de uso comprovado (`DOMAIN-BLUEPRINT-ENTERPRISE-ADVISOR-FRAMEWORK.md` §5, Critério de evolução §9.2).
- O Enterprise Memory Model é desenhado como camada de classificação sobre o que a Knowledge Platform já indexa — não introduz um segundo mecanismo de armazenamento.
- A ordem mandatória de Fases (Foundation → Services → Framework → Advisors) previne a tentação comum de construir Advisors antes da infraestrutura comum existir, que reintroduziria exatamente o duck typing que o Framework existe para eliminar.

Nenhum componente novo cobre um problema hipotético sem uma âncora explícita no domínio já existente ou no padrão já provado pelo Risk Advisor.

---

## 6. Impacto em código existente

**Nenhum.** Esta missão é documentação de arquitetura, integralmente. Nenhum arquivo em `src/` ou `web/` (fora do texto de `mission-control-data.ts`, dado de governança, não lógica) foi alterado. `tsc`, `eslint` e `ruff check src tests` seguem limpos, sem qualquer relação de causa com esta missão (nenhuma mudança de código a validar).

---

## 7. Achados e correções aplicadas nesta revisão

1. **Corrigido:** referência cruzada desatualizada em `ENTERPRISE-ADVISOR-CATALOG.md` (PMO Advisor) apontando ao plano executivo superseded em vez do vigente (`WAVE-3-EXECUTION-PLAN.md`). Sem impacto de arquitetura — apenas precisão documental.
2. **Nenhum outro achado.** Nenhuma violação das diretrizes do Founder, nenhuma arquitetura paralela, nenhuma duplicação de componente, nenhuma dependência invertida entre camadas.

---

## 8. Veredito

**Aprovado para avançar à aprovação do Founder sobre `WAVE-3-EXECUTION-PLAN.md`, sem ressalvas.** Nenhuma Decision Proposal adicional é necessária — as 2 Decisões Estratégicas do Founder já resolvidas (Vector Store/`pgvector`; Framework de Orquestração Multiagente) cobrem integralmente o escopo tecnológico desta Wave. O Blueprint está pronto para servir como documento mestre da Fase 1 assim que o Founder aprovar explicitamente o início da implementação — nenhuma implementação de Epic deve começar antes dessa aprovação.
