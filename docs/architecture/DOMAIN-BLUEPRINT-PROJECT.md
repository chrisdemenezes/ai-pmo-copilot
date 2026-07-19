# Domain Blueprint — Project Domain Closure

**Wave:** 2 (Enterprise Master Execution Program) — corresponde ao Épico 4 (Projeto como entidade real)
**Status:** Blueprint conceitual — não implementa, não produz código.
**Objetivo:** produzir uma única recomendação oficial sobre a unificação (ou não) entre `Project` e `Project Delivery`, encerrando TD-008.

---

## 1. Os 3 conceitos, lado a lado (fato, não interpretação)

| | `Project` (backend real) | `ProjectSummary` | `Project` (domínio DDD) |
|---|---|---|---|
| Onde | `src/database/models.py` | `web/lib/dashboard/types.ts` | `web/lib/domain/project.ts` |
| Origem | Épico 1 | V1/RC-1, via BFF | Capability 03 |
| Persistido? | Sim | Sim (via `analysis_records`) | Não |
| Chave | `id` (integer) | `project_name` (texto livre) | `id` (string), vinculado a `programId` |
| Uso hoje | Apenas membership/organização — nenhuma análise de IA o referencia | Consumido pelo Executive Cockpit ("Projetos", Risk Concentration, Health Distribution) | Consumido pelo Program Execution panel e `/project-delivery` |
| Vínculo a Program | Não tem | Não tem | Tem (`programId` obrigatório) |

Nenhum dos três compartilha ID. Isso é o problema que TD-008 nomeia e que o Épico 4 (nunca iniciado) deveria resolver.

## 2. As duas opções tecnicamente possíveis

### Opção A — Unificar os três em uma única tabela `projects`

Estender o `Project` real do backend (Épico 1) com os campos que `ProjectSummary` e o `Project` de domínio precisam (`program_id`, `sponsor`, `objective`, indicadores de saúde/progresso), migrar `analysis_records.project_name` para referenciar `project_id`, e aposentar tanto `ProjectSummary` quanto a tabela `projects_delivery` temporária proposta no Foundation Technical Design.

**Vantagens:** um único conceito de Project, para sempre — elimina TD-008 de vez, não apenas adia. Análises de IA passam a referenciar a entidade real (pré-requisito da Release 0.3/AI Foundation de qualquer forma).

**Custos/riscos:** é uma migração de dados real sobre `analysis_records` (dados de produção do V1) — maior risco de migração do que criar uma tabela nova vazia. Exige decidir, no mesmo momento, o mapeamento de `project_name` (texto livre, pode ter duplicatas/variações) para `project_id` (chave única) — problema de qualidade de dados, não só de schema (`ADR-V2-003` já registrou que a V2 trata "um projeto por `project_name` distinto, sem fusão automática" — a unificação precisa reconciliar com essa decisão já aprovada, não contradizê-la).

### Opção B — Manter três conceitos, com fronteiras formalizadas (não unificar)

Aceitar que os três servem públicos diferentes (membership organizacional; leitura histórica do V1; domínio DDD de execução) e formalizar as fronteiras com um adaptador de leitura (não de escrita) entre eles, sem migração de dados.

**Vantagens:** zero risco de migração; nenhuma mudança em dado de produção existente; a V1 (`ProjectSummary`) continua intocada, coerente com ADR-V2-001 (evolução incremental, não reescrita).

**Custos/riscos:** TD-008 nunca é resolvido, apenas gerenciado — o risco de um novo engenheiro importar o `Project` errado permanece para sempre, não apenas até o Épico 4.

## 3. Recomendação oficial

**Recomendação: Opção A (unificar), mas faseada — não como uma migração única.**

Justificativa técnica: manter 3 conceitos indefinidamente (Opção B) não é uma arquitetura estável — é uma dívida técnica gerenciada permanentemente, e o próprio objetivo desta missão (Architecture Freeze) pressupõe que o domínio pare de ter ambiguidade estrutural. A Release 0.3 (AI Foundation) **já pressupõe** portar os 3 Accelerators para o `Project` real — ou seja, a unificação vai ser necessária de qualquer forma para a Wave 3 (Enterprise Intelligence) funcionar sobre dados reais, não sobre `project_name` livre. Adiar a unificação apenas move o mesmo trabalho para dentro da Wave 3, com mais pressa e menos tempo de planejamento.

**Faseamento recomendado (para conter o risco de migração de dados real, per a Seção 2, Opção A):**

1. **Fase 1 (Wave 2, junto com Épico 3/RBAC):** estender o `Project` real do backend com os campos de domínio (`program_id`, indicadores) — schema apenas, sem migrar `analysis_records` ainda. `projects_delivery` (nome temporário do Foundation Technical Design §2.9) nunca chega a existir como tabela própria — os campos vão direto na tabela `projects` já existente.
2. **Fase 2 (ainda Wave 2):** migrar o domínio DDD (`web/lib/domain/project.ts`) para ler da API real (já desenhado em `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §1) em vez do array semeado — agora contra a tabela `projects` unificada, não uma tabela temporária.
3. **Fase 3 (Wave 3, quando AI Foundation começar):** migrar `analysis_records.project_name` para `project_id`, com reconciliação explícita de nomes duplicados/variações (respeitando ADR-V2-003 — sem fusão automática, decisão humana por ambiguidade). `ProjectSummary` é aposentado somente após essa fase — nunca antes, para não quebrar o Executive Cockpit em produção.

**Isto substitui a recomendação anterior** (`projects_delivery` como tabela deliberadamente temporária, `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §2.9/§2.16) — a tabela temporária deixa de ser necessária porque a Fase 1 acima vai direto para a tabela unificada. **Este é um ajuste a um documento já produzido nesta mesma linha de trabalho (Foundation Technical Design), não a uma decisão aprovada pelo Founder** — portanto é registrado aqui como recomendação, sujeita à mesma ratificação que o restante deste Blueprint, não aplicada automaticamente ao Technical Design existente.

## 4. Se a recomendação não for aceita

Caso o Founder prefira a Opção B (não unificar), a justificativa técnica que sustenta essa escolha seria: o custo de reconciliar `project_name` duplicado/variado (Fase 3 acima) é maior do que o valor de eliminar TD-008, e a AI Foundation pode continuar operando sobre `project_name` livre por mais tempo do que o planejado. Essa é uma troca legítima — apenas não é a que este documento recomenda, dado que adia indefinidamente um problema já identificado há duas Architecture Reviews (D-019, AR-1) sem um plano de encerramento.

---

## 5. Fundamentado vs. depende do Founder vs. exige definição arquitetural

| Fundamentado | Depende do Founder | Exige definição arquitetural |
|---|---|---|
| Os 3 conceitos e suas diferenças (fato, Seção 1) | Adotar Opção A (recomendada) vs. Opção B | Regra de reconciliação de `project_name` duplicado/variado (Fase 3) — não trivial, precisa de Technical Design própria quando essa fase chegar |
| Faseamento recomendado (Seção 3) | Substituir `projects_delivery` temporário pela tabela unificada direta | |
