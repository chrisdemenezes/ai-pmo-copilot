# STRATECH V2 — Product Decision Log

Registro leve e cronológico de decisões de produto/técnicas tomadas durante a execução de Sprints — distinto dos ADRs (`docs/architecture/adr/`), que registram decisões arquiteturais formais e passam por Architecture Review. Aqui ficam decisões de menor porte, tomadas dentro da autonomia técnica já concedida pelo Founder, mas que vale registrar para rastreabilidade.

---

### D-001 — Marca visível renomeada para "STRATECH"

- **Contexto:** produto ainda exibia "AI PMO Copilot" (V1) em sidebar/metadata/style guide.
- **Decisão:** renomear para "STRATECH" em toda a superfície visível, consistente com a visão de produto já usada em toda a documentação da V2.
- **Sprint:** 1, Dia 1.

### D-002 — Novos primitivos de Design System seguem o padrão V1, não um novo

- **Contexto:** Sprint 1 pedia consolidar um Design System; um já existia (RFC-001).
- **Decisão:** estender (Table, Progress, Tooltip, Avatar), nunca recriar. Nenhuma nova convenção visual introduzida.
- **Sprint:** 1, Dia 1.

### D-003 — Dado mock do Executive Cockpit centralizado em um único arquivo

- **Contexto:** Portfolio/Program não são entidades reais ainda (Release 0.2); a Sprint pede mock.
- **Decisão:** todo dado simulado do Cockpit vive em `web/lib/mock/cockpit-data.ts` — quando a Release 0.2/0.3 wire dado real, só esse arquivo (e seus consumidores diretos) muda, não cada componente.
- **Sprint:** 1, Entrega 2.1.

### D-004 — Situação do Portfólio/Programa como grids novos, não retrofit do grid real de Projetos

- **Contexto:** poderia ter reaproveitado `ProjectHealthGrid` genericamente para as 3 entidades.
- **Decisão:** dois componentes novos (`PortfolioSituationGrid`, `ProgramSituationGrid`), mesma forma visual, mas sem generalizar prematuramente uma abstração comum entre 3 formatos de dado ainda em fluxo (2 mock, 1 real) — evita uma abstração errada agora que teria que ser desfeita quando o dado real chegar.
- **Sprint:** 1, Entrega 2.2.

### D-005 — "Riscos" do inventário de portfólio é distinto do Risk Intelligence de IA

- **Contexto:** a Entrega 2.3 pediu "Riscos" como uma das 4 categorias (Demandas/Riscos/Issues/Mudanças); a V1 já tem um "Risk Intelligence" real (análise de IA sobre reuniões/riscos).
- **Decisão:** manter os dois conceitos explicitamente separados — o "Riscos" do Mission Control/Cockpit é um item de trabalho formal de portfólio (com mitigação, dono, status), não a mesma coisa que a saída do agente `risk_review`. Documentado no componente para não confundir o próximo engenheiro.
- **Sprint:** 1, Entrega 2.3.

### D-006 — Mission Control usa dado real estático, não mock

- **Contexto:** diferente do Executive Cockpit (Portfolio/Program simulados, porque não existem), o Mission Control mostra o estado real da governança (Épicos, PRs, débito técnico) — que já existe, só não está exposto via API.
- **Decisão:** popular `mission-control-data.ts` com os fatos reais atuais (lidos manualmente dos artefatos de governança e do GitHub), não dado fictício — deixando claro no código que uma versão futura pode ler isso ao vivo (arquivo ou API), sem mudar a forma dos componentes.
- **Sprint:** 1, Mission Control.

### D-007 — Mission Control atrás da sessão, mas sem RBAC de Founder ainda

- **Contexto:** a diretriz pede um painel "exclusivo do Founder"; RBAC funcional não existe (Épico 3 não iniciado).
- **Decisão:** adicionar a rota ao gate de sessão existente (`proxy.ts`) — exige login, mas não distingue papel. Limitação documentada explicitamente na página, no código e neste log, não ocultada.
- **Sprint:** 1, Mission Control.

### D-008 — Executive Focus calculado a partir de dado real, não mock

- **Contexto:** Executive Focus precisa responder "onde devo concentrar atenção hoje?" de forma confiável para um executivo real.
- **Decisão:** reaproveitar `rankByRisk()` (já usado pelo Risk Concentration Ranking real) em vez de criar um novo cálculo ou usar dado simulado — o painel mais visualmente proeminente do Cockpit é o único, além do Mission Control, que não é mock.
- **Sprint:** 1.4, Entrega 2.4.

### D-009 — "Riscos" do inventário permanece distinto do Risk Intelligence de IA (reforço de D-005)

- **Contexto:** Actions Center/AI Recommendations citam "Multilift" e riscos, criando risco de confundir com o Risk Concentration real.
- **Decisão:** manter a separação de conceitos já registrada em D-005; nenhum texto novo combina os dois modelos de dado.
- **Sprint:** 1.4, Entrega 2.4.

### D-010 — Numeração "2.N" será substituída por Capabilities de produto

- **Contexto:** o Founder recomendou abandonar a sequência "2.4/2.5" e passar a organizar o trabalho por Capability de negócio (Capability 01 — Executive Decision, 02 — Portfolio Intelligence, 03 — Governance, 04 — AI Copilot, 05 — Knowledge Intelligence).
- **Decisão:** registrado como direção aprovada para a próxima Sprint — não aplicado retroativamente a esta Sprint 1 (que mantém "Dia N"/"2.N"/"Sprint 1.4" como já documentado, por não reescrever histórico).
- **Sprint:** 1.4 (decisão para vigorar a partir da Sprint seguinte).

---

## Convenção

Cada decisão ganha um ID sequencial `D-NNN`, contexto, decisão e a Sprint/Entrega em que foi tomada. Não editado retroativamente — uma correção é uma nova entrada.
