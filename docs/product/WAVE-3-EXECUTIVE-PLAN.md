# Wave 3 Executive Plan — Enterprise Intelligence

**Data:** 2026-07-27 · Produzido **após** a conclusão do Wave 2 Closure Review (`WAVE-2-CLOSURE-REPORT.md`, D-062, "Wave 3 Ready" declarado). Este documento é um plano — **nenhum Epic é implementado por ele.**

---

## 0. Estado herdado

A Wave 3 já está parcialmente em execução (aberta em D-039, 2026-07-23):

| Epic | Status | Decisão |
|---|---|---|
| W3-1 — Project Identity Unification (TD-008 Fase 3a) | ✅ Concluído | D-040 |
| W3-2 — AI Platform Foundation → redefinido como Digital PMO Intelligence Foundation | ✅ Concluído | D-041/D-047 |
| W3-3 — Risk Advisor (PoC de Enterprise Agent conversacional) | ✅ Concluído | D-046 |
| Security Hardening Gate (C-1 RBAC, C-2 Tenant Isolation) | ✅ Concluído (bloqueava W3-3, resolvido antes) | D-045 |

**Superseding Decision (D-048):** reverteu o tratamento de Knowledge Platform e dos 7 Enterprise Advisors restantes como "Decision Proposal que não bloqueia o fechamento" — ambos passam a ser **escopo obrigatório** da Wave 3, não mais especulativo.

**2 Decision Proposals do Founder seguem abertas** (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §15), únicas pendências que travam o avanço:
1. **§15.1 — adoção de Vector Store** (Knowledge Platform): decidir se avança e, se sim, qual tecnologia (recomendação técnica não-vinculante: `pgvector` sobre o Postgres já oficial).
2. **§15.2 — framework de orquestração multi-agente** (Enterprise Agents): decidir a forma que os 7 Advisors restantes assumem, informado pelo resultado do PoC do Risk Advisor.

---

## 1. Objetivos da Wave 3

1. Entregar a **Knowledge Platform** (Document Intelligence, Semantic Search, Embeddings, Vector Store, RAG, Context Manager) — hoje 0% implementado, sem ADR/Blueprint aprovado além da referência de Document Intelligence (ADR-V2-005).
2. Entregar os **7 Enterprise Agents restantes** (Executive, Strategy, PMO, Portfolio, Delivery, Governance, Document Advisor), generalizando o padrão provado pelo Risk Advisor.
3. Entregar a camada de **Executive Intelligence** sobre Portfolio/Program/Project (insight de IA, não apenas dados — Decision Intelligence, PMO Intelligence, Governance Intelligence, Executive Briefing).
4. Encerrar a Wave 3 sob os mesmos critérios da Wave Completion Policy (D-048) — sem nenhum item previsto pendente, tratado como Decision Proposal em aberto.

---

## 2. Entregáveis

- `DOMAIN-BLUEPRINT-ENTERPRISE-INTELLIGENCE.md` (revisão/consolidação) + `AR-6-ENTERPRISE-INTELLIGENCE-ARCHITECTURE-REVIEW.md` — pré-requisito explícito já registrado em `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §5 antes de qualquer Technical Design de Knowledge Platform ou dos Advisors restantes.
- Decision Log formalizando as respostas do Founder a §15.1/§15.2 (nunca decidido silenciosamente).
- Technical Design + implementação de Knowledge Platform (se aprovado em §15.1).
- Technical Design + implementação do framework de orquestração + os 7 Advisors restantes (per a decisão de §15.2).
- Camada de Executive Intelligence consumindo Knowledge Platform + Advisors sobre Portfolio/Program/Project.
- Wave 3 Closure Review (mesmo rigor de 7 entregáveis usado nesta Wave 2), ao final.

---

## 3. Ordem recomendada dos Epics

1. **W3-4 — Domain Blueprint + Architecture Review de Enterprise Intelligence.** Pré-requisito estrutural; sem ele, nenhum Technical Design subsequente tem fundamento aprovado.
2. **W3-5 — Resolução das 2 Decision Proposals (§15.1/§15.2).** Governança, não implementação — mas bloqueia tecnicamente os 2 Epics seguintes. Deve ser levada ao Founder o quanto antes, em paralelo ao Blueprint de W3-4 se possível, para não represar o restante da Wave.
3. **W3-6 — Knowledge Platform**, condicionado à aprovação de §15.1. Sequenciado antes dos Advisors restantes porque os Advisors mais avançados (Strategy, PMO, Governance) plausivelmente consomem contexto de conhecimento corporativo (RAG) — construir a plataforma primeiro evita retrabalho nos Advisors.
4. **W3-7 — Framework de orquestração + os 7 Advisors restantes**, condicionado à aprovação de §15.2. Recomenda-se generalizar 1 Advisor adicional (ex.: PMO Advisor, o mais próximo do domínio já implementado) antes de expandir para os 7, replicando a disciplina de "PoC primeiro" já usada com sucesso no Risk Advisor (W3-3).
5. **W3-8 — Executive Intelligence** (Decision/PMO/Governance Intelligence, Executive Briefing) sobre Portfolio/Program/Project — depende de W3-6 e W3-7 já existirem como insumo.
6. **Wave 3 Closure Review** — ao final, mesmo padrão desta Wave 2.

---

## 4. Dependências

- **W3-6 depende de W3-5** (decisão de tecnologia de Vector Store) e de **W3-4** (Blueprint aprovado).
- **W3-7 depende de W3-5** (decisão de framework de orquestração) e de **W3-4**.
- **W3-8 depende de W3-6 e W3-7** — não pode ser implementado sem os insumos de conhecimento e os Advisors que ele consolida.
- **Nenhum Epic desta Wave depende de nada da Wave 2** além do que já está construído (RBAC, Sessions, API Keys, `project_id` como identidade única) — a Wave 2 encerrada é a baseline, não um bloqueador.

---

## 5. Riscos

1. **As 2 Decision Proposals podem represar toda a Wave se não forem resolvidas cedo.** Ambas exigem decisão estratégica do Founder (§15.1/§15.2); recomenda-se levá-las junto com este plano, não depois.
2. **Risco de colisão de nome "Enterprise Memory" com "Executive Memory"** (já sinalizado em `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §5.2) — se Knowledge Platform usar esse termo, uma decisão de nomenclatura explícita é necessária antes do código, mesmo padrão já usado 5 vezes no projeto (D-005/D-009/D-012/D-019/D-055).
3. **Introduzir um framework de orquestração multi-agente é uma decisão de arquitetura de produto nova, sem precedente.** Risco de superengenharia se o desenho não for informado estritamente pelo que o PoC do Risk Advisor já provou funcionar (chamada direta a `LLMProvider` via `PromptRegistry`, sem framework).
4. **Vector Store introduz um tipo de armazenamento novo** — mesmo com `pgvector` (menor risco, reaproveita o Postgres oficial), é uma mudança de infraestrutura que exige seu próprio Technical Design e plano de migração, não uma extensão trivial.

---

## 6. Critérios de conclusão

Idênticos aos já estabelecidos pela Wave Completion Policy (D-048), aplicados à Wave 3:

- 100% dos Epics/Advisors/capacidades originalmente previstos (`ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §5) implementados e funcionais, **ou** formalmente reclassificados como Governança Concluída/Business Pending com auditoria completa (nunca como Decision Proposal silenciosamente adiado).
- 100% dos Domain Blueprints e Technical Designs com implementação correspondente.
- 100% dos Executive Reports publicados.
- Todos os testes (unitário/integração/E2E) aprovados; zero placeholder/TODO/stub.
- Wave 3 Closure Review completo (mesmos 7 entregáveis desta revisão da Wave 2) antes de declarar a Wave encerrada.

---

**Este plano não autoriza nenhuma implementação.** Aguarda aprovação do Founder — inclusive, e principalmente, sobre a sequência e as 2 Decision Proposals (§15.1/§15.2) — antes do início de qualquer Epic.
