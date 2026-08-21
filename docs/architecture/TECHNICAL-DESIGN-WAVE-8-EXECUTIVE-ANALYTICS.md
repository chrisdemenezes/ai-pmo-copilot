# Technical Design — Wave 8: Executive Analytics & Experience Completion

## 1. Contexto

Founder Mandate "STRATECH ENTERPRISE V1.0 — WAVE 8 — EXECUTIVE ANALYTICS &
EXPERIENCE COMPLETION" autoriza completar a camada de analytics/KPI executivo
da V1, reutilizando exclusivamente a arquitetura existente (Domain,
AdvisorFramework/AIContextEngine, APIs, Knowledge Platform).

Reconciliação factual (Phase A) confirmou:

- Portfolio/Program/Project são as únicas tabelas de domínio persistidas;
  Risk/Action/Decision/Learning são derivados de `AnalysisRecord` (JSON),
  sem tabela própria.
- `Project` já tem `approved_budget`/`actual_cost`/`forecast_cost`
  (migração `0022`, Package K) e `progress_percentage` (Integer, nullable,
  sem disciplina formal de WBS/earned-value documentada — é uma estimativa
  manual do PM).
- **Não existe nenhuma série temporal de custo/progresso** — apenas um
  snapshot atual por projeto. EVM formal (CPI/SPI/EAC/ETC/VAC/S-Curve) não
  tem base real para ser calculado hoje sem uma extensão de domínio.
- Executive Intelligence (`AdvisorFramework`, `AIContextEngine`,
  `RecommendationEngine`, `ExplanationEngine`, `ExecutiveOrchestrator`,
  `Synthesis`, `Correlation`) está totalmente implementada; princípios
  permanentes #11–13 (nunca cria conhecimento novo, orquestração
  determinística, escopo explícito) permanecem guardrails vigentes.
- Nenhuma biblioteca de gráficos está instalada no frontend; nenhum
  componente de KPI/gráfico reutilizável existe hoje.

## 2. Founder Decision — EVM Temporal Baseline

Diante do gap de série temporal, o Founder decidiu (verbatim, registrado
aqui por rastreabilidade): **não estimar, inferir ou fabricar Planned Value
histórico a partir do snapshot atual**. A ausência de baseline temporal é um
gap real de domínio, tratado com uma extensão aditiva do modelo — nunca uma
reconstrução retroativa do passado.

### A. Baseline temporal

Nova tabela `project_performance_baselines` — curva de valor planejado
explícita, **autorada por humano** (PM/PMO), nunca inferida ou linearizada
automaticamente pelo sistema:

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | Integer FK `organizations.id` | not null, indexed — mesma disciplina de tenant isolation de toda tabela de domínio |
| `project_id` | Integer FK `projects.id` | not null, indexed |
| `baseline_version` | Integer | not null; 1, 2, 3... por projeto |
| `period_date` | Date | not null; um ponto da curva planejada |
| `planned_progress_percentage` | Numeric(5,2) | not null; 0–100, autorado pelo humano |
| `planned_value` | Numeric(14,2) | not null; **derivado** = `bac_reference × planned_progress_percentage / 100` |
| `bac_reference` | Numeric(14,2) | not null; BAC congelado no momento da criação deste baseline (pode divergir do `Project.approved_budget` atual após um rebaseline) |
| `created_at` | DateTime(tz) | not null |

`UNIQUE(project_id, baseline_version, period_date)`.

### B. Historical performance snapshots

Nova tabela `project_performance_snapshots` — captura periódica do lado
real (actual/earned), **append-only, nunca retroativa**:

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | Integer FK | not null, indexed |
| `project_id` | Integer FK `projects.id` | not null, indexed |
| `snapshot_date` | Date | not null |
| `actual_cost` | Numeric(14,2) | not null; copiado de `Project.actual_cost` no momento da captura |
| `progress_percentage` | Integer | not null; copiado de `Project.progress_percentage` no momento da captura |
| `created_at` | DateTime(tz) | not null |

`UNIQUE(project_id, snapshot_date)` — idempotente: uma captura por projeto
por dia; nova captura no mesmo dia retorna a existente sem sobrescrever.

Mecanismo de captura: endpoint explícito acionado por humano
(`POST /projects-delivery/{project_id}/performance-snapshots`), grava um
`AuditLog` (`action="project_performance_snapshot.captured"`, reutilizando
a tabela de auditoria genérica já existente — nenhuma tabela de auditoria
nova). **Nenhum scheduler/cron/Event Pipeline é criado nesta missão** — uma
captura automática periódica exigiria nova infraestrutura de integração,
fora do escopo autorizado agora; fica registrada como próximo passo natural,
não como débito oculto.

### C. Cálculo de PV(t)

Função-degrau sobre os pontos reais definidos no baseline ativo (maior
`baseline_version` do projeto): PV(t) = `planned_value` do ponto com
`period_date` mais recente ≤ t. Fora de
`[baseline_start_date, baseline_end_date]` (implícitos como
min/max `period_date` do baseline ativo) ou sem baseline definido → **N/A**.
Nunca interpola valores entre dois pontos autorados.

### D. Cálculo de EV

**Não assumido automaticamente como `BAC × progress_percentage`.**
`progress_percentage` é um campo manual do PM, sem disciplina formal de
WBS/earned-value documentada em nenhum artefato de domínio. EV é calculado
como `bac_reference (do baseline ativo) × snapshot.progress_percentage / 100`
mas **rotulado explicitamente em toda API/UI como "Valor Agregado (estimado
a partir do progresso reportado)"** — nunca apresentado como um EV
certificado/auditado. Sem baseline ativo para o projeto → EV = N/A (nunca
cai silenciosamente para `Project.approved_budget` atual, o que quebraria a
consistência com o PV que está sendo comparado).

### E. Série histórica de AC

= sequência ordenada de `project_performance_snapshots.actual_cost` por
`snapshot_date`. Vazia para todo projeto existente até a primeira captura;
acumula estritamente prospectivamente a partir daí. Nunca reconstruída
retroativamente.

### F. Versionamento de baseline

`baseline_version` inteiro, imutável por versão — mesma disciplina de
"nova linha, nunca UPDATE" já usada por `DocumentVersion`/`AnalysisRecord`.
Baseline "atual" para cálculo de KPI ao vivo = maior `baseline_version` do
projeto. Versões antigas permanecem consultáveis (auditoria de como o plano
mudou), mas não participam do cálculo corrente.

### G. Comportamento de rebaseline

Rebaseline = inserir um novo conjunto de linhas com
`baseline_version = max_atual + 1`. **Nunca toca**
`project_performance_snapshots` — o realizado não muda ao se replanejar.
Grava `AuditLog` (`action="project_performance_baseline.rebaselined"`,
`details={previous_version, new_version}`).

### H. Projetos existentes sem histórico

Zero linhas em ambas as tabelas hoje, para todo projeto pré-existente. Toda
métrica da família EVM (PV, EV, CPI, SPI, EAC, ETC, VAC) retorna um "N/A"
tipado com motivo (`no_baseline_defined`, `no_snapshot_captured`,
`baseline_missing_bac_reference`) — nunca zero, nunca fabricado. CV/SV
herdam a mesma propagação de N/A (dependem de EV). A variância de
orçamento simples já existente (Package K:
`approved_budget − actual_cost`) permanece **inalterada e sem regressão** —
é uma métrica separada, mais simples, não afetada por este novo conceito.
S-Curve só é renderizada quando existe pelo menos um baseline **e** pelo
menos um snapshot para o projeto; caso contrário, exibe
"Dados históricos insuficientes" — nunca uma curva fabricada/interpolada.

## 3. Fórmulas EVM adotadas

```
BAC = bac_reference (congelado no baseline ativo)
PV(t) = função-degrau sobre period_date/planned_value do baseline ativo
EV = bac_reference × snapshot.progress_percentage / 100  [rotulado "estimado"]
AC = snapshot.actual_cost

CPI = EV / AC           (N/A se AC nulo ou zero)
SPI = EV / PV           (N/A se PV nulo ou zero)
CV  = EV - AC
SV  = EV - PV
EAC = AC + (BAC - EV) / CPI    (N/A se CPI indisponível)
ETC = EAC - AC
VAC = BAC - EAC
```

Toda métrica é `Optional[Decimal]` + um `reason` explícito quando ausente
— nunca `0`, nunca um valor fabricado.

## 4. Impacto arquitetural

- 2 tabelas novas, puramente aditivas (nenhuma coluna/tabela existente
  alterada). Migração `0023`, padrão idêntico ao de `0016`
  (`op.create_table`, índices, FKs, downgrade completo).
- Novo `PerformanceRepository` (mesmo padrão de construção por
  `session_factory` de `EnterpriseRepository`/`DomainRepository`,
  composto em `AnalysisRepository.__init__` como `.performance`).
- Novo módulo determinístico puro `src/services/executive_analytics/metrics_engine.py`
  — nenhuma chamada a LLM, nenhuma dependência de IA.
- Novos endpoints em `project_delivery.py` (mesmo router já registrado em
  `src/main.py`, nenhum novo registro de rota).
- Nenhuma mudança em RBAC, tenant model, Advisors, Evidence Gate,
  ExecutiveOrchestrator, Synthesis, Correlation.
- Pacote I (Organização) permanece ARCHITECTURAL DECISION REQUIRED,
  inalterado, fora de escopo.
