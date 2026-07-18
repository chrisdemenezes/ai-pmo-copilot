# STRATECH V2 — Engineering Orders Register

Registro cronológico e append-only de todas as Engineering Orders (EOs) e decisões de engenharia equivalentes emitidas pelo Founder desde o início do STRATECH V2. Uma vez emitida, uma EO não é reescrita retroativamente — correções a uma EO anterior aparecem como uma nova entrada que referencia a anterior, nunca como edição da entrada original.

> **Nota de institucionalização (EO-018):** este documento consolida, a partir do histórico de conversa desta engenharia, as EOs emitidas até aqui. Datas anteriores a 2026-07-18 são ancoradas pelos commits/PRs correspondentes (única fonte objetiva disponível) quando a data exata da emissão da ordem em si não estava disponível para reconstrução — ver observação em cada entrada.

---

### EO-008 — Diagnóstico de encerramento do Épico 1

- **Objetivo:** diagnóstico técnico previamente à formalização do encerramento do Épico 1 (Schema Foundation).
- **Data:** 2026-07-17 (ancorada por PR #39, merge commit `4dcf7e886467e86c37524bd0fb46f70b70a7778c`).
- **Status:** Executada.
- **Artefatos relacionados:** PR #39.

### EO-010 — Encerramento do Épico 1

- **Objetivo:** autorizar o encerramento formal do Épico 1 (Schema Foundation) após validação técnica.
- **Data:** 2026-07-17.
- **Status:** Executada.
- **Artefatos relacionados:** PR #39, `RELEASE-0.1.md`.

### EO-011A — Preparar Governance Package GP-001

- **Objetivo:** autorizar a preparação do Governance Package GP-001 (encerramento formal do Épico 1: ADR, Technical Debt, Release Notes, Lessons Learned).
- **Data:** 2026-07-17.
- **Status:** Executada.
- **Artefatos relacionados:** PR #40, `docs/architecture/ADR-V2-004-schema-foundation-integrated.md`, `TECHNICAL_DEBT.md` (TD-001/002/003), `RELEASE-0.1.md`, `LESSONS_LEARNED.md` (LL-001/002).

### EO-012 — Merge Authorization Execution (PR #39)

- **Objetivo:** autorizar a execução do merge do PR #39 (Épico 1) após CI verde e verificação de `mergeable_state`.
- **Data:** 2026-07-17.
- **Status:** Executada.
- **Artefatos relacionados:** PR #39, merge commit `4dcf7e886467e86c37524bd0fb46f70b70a7778c`.

### EO-015 — Authorized to Implement (Épico 2)

- **Objetivo:** autorizar a implementação completa do Épico 2 (Identity Foundation) conforme a TDS Rev. 2, aprovada em AR-002. Define regras de escopo (não implementar Épicos 3/4/5), gate de qualidade obrigatório pré-PR, e formato do relatório final.
- **Data:** 2026-07-18.
- **Status:** Executada.
- **Artefatos relacionados:** `docs/architecture/technical-design-specs/TDS-EPIC-02.md`, `docs/governance/ARCHITECTURE_REVIEWS.md` (AR-002), PR #41.

### EO-015 — Scope Confirmation: Approved to Proceed

- **Objetivo:** autorizar, dentro do Épico 2, três alterações de superfície não previstas literalmente na TDS mas necessárias para implementar o contrato `{email,password}` aprovado: campo de e-mail em `/entrar`, atualização de 9 specs E2E, e handlers `POST /api/auth/login`/`logout` no mock backend do Playwright. Lista restrições explícitas (sem registro de usuário, sem recuperação de senha, sem RBAC).
- **Data:** 2026-07-18.
- **Status:** Executada.
- **Artefatos relacionados:** `web/app/entrar/page.tsx`, `web/e2e/*.spec.ts`, `web/e2e/mock-backend.mjs`.

### EO-015 — Organizational Identity Scope Correction

- **Objetivo:** corrigir o contrato de login para resolver o usuário por **organização + e-mail + senha**, não por busca global de e-mail entre organizações. Exige verificação de schema antes de qualquer migration nova, com instrução explícita de parar e aguardar autorização caso uma migration fosse necessária.
- **Data:** 2026-07-18.
- **Status:** Executada. Migration `0004_organization_slug` autorizada após relatório pré-schema (Opção B escolhida pelo Founder).
- **Artefatos relacionados:** `alembic/versions/0004_organization_slug.py`, `src/services/identity/auth_service.py`, `web/app/api/bff/session/route.ts`, `web/app/entrar/page.tsx`, PR #41.

### Engineering Decision — Regression Gate (Baseline Defects, Épico 2)

- **Objetivo:** classificar as 3 falhas E2E pré-existentes (TD-004/005/006) como Baseline Defect após reprodução comprovada contra o baseline anterior ao Épico 2, autorizando a abertura do PR #41 sem bloquear por essas falhas.
- **Data:** 2026-07-18.
- **Status:** Executada.
- **Artefatos relacionados:** `TECHNICAL_DEBT.md` (TD-004/005/006), PR #41.

### PR #41 — Monitoring Authorization

- **Objetivo:** autorizar o monitoramento automático do PR #41 (CI, mergeability, comentários, reviews), com regras explícitas do que pode ser decidido automaticamente e o que exige autorização do Founder. Proíbe merge em qualquer circunstância.
- **Data:** 2026-07-18.
- **Status:** Em vigor.
- **Artefatos relacionados:** PR #41.

### PR #41 — Role Transition (Release Manager)

- **Objetivo:** transicionar o papel de execução de "Implementador" para "Release Manager" do PR #41, com o objetivo de preservar estabilidade até a decisão de Architecture Review. Define categorias de classificação de comentários (A/B/C/D) e reforça a proibição de merge sem EO-MERGE.
- **Data:** 2026-07-18.
- **Status:** Em vigor. PR #41 em estado READY FOR ARCHITECTURE REVIEW.
- **Artefatos relacionados:** PR #41.

### EO-016 — Master Roadmap (Program Management Office)

- **Objetivo:** autorizar a criação de `docs/product/STRATECH_V2_MASTER_ROADMAP.md` como referência executiva de planejamento da STRATECH V2 (Vision, Programas, Épicos, Releases, Capability Matrix, Maturity Model, Definition of Done, Governance Dashboard, Future Roadmap). Explicitamente documental — proíbe implementação de código.
- **Data:** 2026-07-18.
- **Status:** Executada — primeira versão produzida.
- **Artefatos relacionados:** `docs/product/STRATECH_V2_MASTER_ROADMAP.md`.

### EO-016A — Revisão do Master Roadmap

- **Objetivo:** refinar o Master Roadmap com Executive Dashboard, Product Lifecycle, Capability Tree, agrupamento Platform Foundation/Business Platform, progresso consolidado por Release e indicador global de maturidade. Duas etapas: aprovação com observações (refinamento pedido), depois aprovação final autorizando commit/push/atualização do PR #41.
- **Data:** 2026-07-18.
- **Status:** Executada. Commit `9b739ae`.
- **Artefatos relacionados:** `docs/product/STRATECH_V2_MASTER_ROADMAP.md`, PR #41.

### EO-016B — Release Closure Preparation

- **Objetivo:** produzir o "Release 0.1 Readiness Report" — checklist de todos os artefatos de governança exigidos para o encerramento formal da Release 0.1, com recomendação READY/NOT READY TO CLOSE. Explicitamente sem commit, push ou merge.
- **Data:** 2026-07-18.
- **Status:** Executada. Recomendação emitida: **NOT READY TO CLOSE** (apenas Épico 1 de 6 fechado; Épico 2 em PR aberto; Épicos 3-6 não iniciados).
- **Artefatos relacionados:** nenhum arquivo criado (relatório entregue apenas em texto de resposta).

> **Nota:** a avaliação de governança documental realizada em 2026-07-18 ("Architecture Assessment da Governança Documental") foi reclassificada como **AA-001** (Architecture Assessment) por decisão de AR-004 — mantida fora deste registro de Engineering Orders, por não ser uma ordem do Founder e sim uma avaliação arquitetural.

### EO-018 — Governance Institutionalization

- **Objetivo:** implementar a estrutura documental definitiva de governança (este registro, `ARCHITECTURE_REVIEWS.md`, `GOVERNANCE_MODEL.md`, `technical-design-specs/TDS-EPIC-02.md`, e um plano de normalização — não execução — da estrutura de ADRs), eliminando a dependência do histórico de conversa como fonte primária de decisões.
- **Data:** 2026-07-18.
- **Status:** Em execução — este conjunto de documentos, aguardando aprovação antes de commit.
- **Artefatos relacionados:** todos os arquivos listados acima nesta EO.

### EO-MERGE-001 — Merge Authorization (Épico 2)

- **Objetivo:** autorizar a conclusão do Épico 2 — merge do PR #41 à `main`, exclusão da branch `feature/v2-r01-epic2-identity-foundation`, e atualização dos artefatos de Release/Master Roadmap/governança refletindo o encerramento. Autorizado após AR-003 (`APPROVED WITH OBSERVATIONS`).
- **Data:** 2026-07-18.
- **Status:** Executada — merge realizado (commit `ef760ee426f58eb3dad48f7d3eb3ed248308107d`). Exclusão da branch **não executada**: nenhuma ferramenta de exclusão de branch disponível nesta sessão e `git push --delete` rejeitado (HTTP 403) pelo proxy do repositório — requer ação do Founder (botão "Delete branch" no GitHub, ou concessão de escopo adicional).
- **Artefatos relacionados:** PR #41, `docs/releases/RELEASE-0.1.md`, `docs/product/STRATECH_V2_MASTER_ROADMAP.md`, `docs/governance/ARCHITECTURE_REVIEWS.md` (AR-003).
