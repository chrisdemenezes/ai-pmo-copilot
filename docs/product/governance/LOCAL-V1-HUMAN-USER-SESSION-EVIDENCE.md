# Local V1 Human User Session — Evidence

- **Missão:** FOUNDER DECISION — LOCAL V1 HUMAN USER SESSION (Primeira Validação Funcional Humana da STRATECH V1)
- **Data:** 2026-08-19
- **Facilitador:** Claude (User Research Facilitator / Product Observer / Evidence Recorder)

## 1. Executive Summary

Primeira sessão real de usuário humano da STRATECH V1, conduzida interativamente (o Founder na máquina física Windows, executando ações e narrando em tempo real; o facilitador dando apenas objetivos de tarefa, nunca passo a passo). Ambiente preparado do zero na baseline oficial (`main` @ `990917f`), com um achado operacional real durante o Pre-Session Gate (conflito de porta 5432 com o PostgreSQL nativo do Windows — 2ª ocorrência do mesmo achado de D-213). As 10 tarefas mandatadas foram completadas. Resultado: **1 FAIL real** (Priorização), **1 tarefa parcial com Product Gap conhecido** (Administração — papéis/organizações), **7 PASS WITH FRICTION**, **2 PASS limpos** (Ações, Logout). Intenção de uso = **SIM**. Utilidade percebida = **6,5–7/10**. Nenhuma STOP CONDITION foi atingida — nenhuma falha de tenant isolation, autenticação, corrupção de dados, ou indisponibilidade persistente. Nenhuma correção foi feita durante a sessão.

## 2. Session Metadata

- **Duração:** sessão única e contínua, conduzida via chat com o Founder narrando ações reais na máquina física.
- **Modalidade:** o facilitador não teve acesso visual/direto ao navegador do usuário — toda observação depende da narração em tempo real do próprio usuário (limitação metodológica registrada com transparência; não é observação comportamental direta).
- **Timestamps precisos por tarefa:** não disponíveis (sem acesso a relógio de sistema do navegador do usuário) — a ordem e o conteúdo das interações estão preservados fielmente pela sequência real da conversa.

## 3. User Profile

- **Usuário do teste:** o próprio Founder (Christiano Menezes), autoconfirmado como participante desta sessão específica.
- Papel real na organização: Founder/responsável pela gestão do produto.
- Não é um usuário externo nem um perfil cego — resultado a ser lido com essa lente (viés de proximidade com o produto é menor que um usuário externo real, mas o Founder ainda seguiu o protocolo de exploração livre sem receber passo a passo).

## 4. Pilot Baseline

- Branch: `main`
- SHA: `990917f279411b73c6a481213a541175da5bc0f6` (confirmado idêntico via `git rev-parse HEAD` na máquina física)
- Migration head: `0021` (confirmado via `alembic current`)

## 5. Environment

- Máquina física Windows do Founder (hostname `CRM_Consultoria`), Git Bash (MINGW64).
- PostgreSQL + pgvector via Docker (`pgvector/pgvector:pg16`).
- Backend (`uvicorn`) em `:8000`, frontend (`next dev`) em `:3000`.
- Browser: Chrome/Chromium, janela sem outras sessões corporativas reais (confirmado pelo usuário).
- Dataset: sintético, via `demo/seed_demo_data.py` (6 projetos com análises de status/risco, 6 reuniões com ações, 1 documento indexado) + Enterprise Domain seedado pelas migrations (3 portfólios, 4 programas, 7 projetos).
- Nenhum dado corporativo real utilizado (confirmado explicitamente pelo usuário).

## 6. Pre-session Gate

| Item | Resultado |
|---|---|
| `main` na baseline correta | PASS |
| Working tree limpa | PASS |
| PostgreSQL/pgvector | PASS (após resolução de conflito, ver achado abaixo) |
| Migrations = 0021 | PASS |
| Backend | PASS |
| `/health` | PASS |
| `/ready` | PASS |
| Frontend | PASS |
| Login | PASS (confirmado indiretamente — usuário chegou autenticado ao Dashboard) |
| Dataset sintético | PASS |
| Documents | PASS |
| Navegação Administração → produto | PASS (confirmado durante a Task 9) |
| Logout | PASS (confirmado durante a Task 10) |
| Backup recovery point | NÃO EXECUTADO — julgamento operacional do facilitador: dataset é trivialmente reproduzível via `seed_demo_data.py`, sessão não é destrutiva, não classificado como BLOCKER |
| Browser limpo | PASS (confirmado pelo usuário) |
| Ausência de dados corporativos reais | PASS (confirmado pelo usuário) |

**Achado operacional real durante o Pre-Session Gate (não é achado de produto):** `demo/start-demo.sh` falhou inicialmente porque `demo/.env` foi auto-criado pelo próprio script com `DATABASE_URL` comentada — corrigido manualmente (descomentada). Em seguida, um restart do ambiente expôs um `UnicodeDecodeError` no `psycopg2` — diagnosticado como o serviço nativo do PostgreSQL do Windows ocupando a porta 5432 (Docker Desktop não estava rodando no momento). **Esta é a 2ª ocorrência do mesmo achado já registrado em D-213** ("servico nativo do Windows ocupando porta 5432 acidentalmente"), ainda sem correção permanente no Runbook. O Founder optou por desinstalar o PostgreSQL nativo do Windows como resolução definitiva de sua própria máquina. Nenhuma alteração de código/script foi feita durante a sessão (proibido pelo mandato, Seção 2 e 26) — o Founder perguntou explicitamente sobre uma correção permanente nos scripts, e foi informado de que isso fica para a Pilot Findings Review.

## 7. Tasks

### Task 0 — First Impression (Dashboard, pré-login não observado — usuário já chegou autenticado)

- **Pergunta:** o que o sistema faz, o que chama atenção, significado de Priorização/Decisões/Aprendizados.
- **Resposta:** "sistema de gestão de projetos, que centraliza dados e informações pra uma tomada de decisão". Primeira tela percebida como "um pouco poluída" para um contexto executivo; sugestão de reorganizar itens em submenus.
- **Resultado:** informação registrada, sem PASS/FAIL (não é uma tarefa).

### Task 1 — Executive Orientation

- **Objetivo:** descobrir a situação geral da organização.
- **Completado:** SIM. **Assistência:** NENHUMA.
- **Caminho do usuário:** permaneceu no Dashboard, interpretou os indicadores de saúde de portfólio.
- **Conclusão do usuário:** portfólio "meio comprometido", muitos itens críticos/altos; não conseguiu identificar se estavam atrasados ou no prazo.
- **Resultado:** PASS WITH FRICTION.

### Task 2 — Prioritization

- **Objetivo:** descobrir onde concentrar atenção primeiro.
- **Completado:** NÃO. **Assistência:** BAIXA (esclarecimento do termo "organização" na formulação da tarefa, a pedido explícito do usuário — não foi orientação de navegação).
- **Conclusão do usuário:** "não está claro... teríamos que melhorar o layout, deixar mais claro o que preciso priorizar e definir qual o filtro".
- **Resultado:** **FAIL** — objetivo central da tela não foi alcançado.

### Task 3 — Portfolio / Program / Project

- **Objetivo:** entender a hierarquia.
- **Completado:** SIM. **Assistência:** NENHUMA.
- **Achado de navegação:** menus "Projetos" e "Program Management" separados geram confusão.
- **Explicação da hierarquia pelo usuário:** "portfólio nível um, programa nível dois, projeto nível três, tarefas nível quatro, ações nível cinco" — **conceitualmente correta**, consistente com a arquitetura real do produto.
- **Resultado:** PASS WITH FRICTION (reclassificado a pedido do Founder — correto conceitualmente, mas UI não reforça a hierarquia).

### Task 4 — Project Delivery

- **Objetivo:** entender a execução dos projetos.
- **Completado:** SIM.
- **Achado:** visão geral reflete bem a realidade do projeto/portfólio/programa; falta granularidade ao entrar num projeto específico (análises, riscos, ações não claramente listados em detalhe).
- **Resultado:** PASS WITH FRICTION.

### Task 5 — Actions

- **Objetivo:** descobrir quais ações precisam de acompanhamento.
- **Completado:** SIM.
- **Achado:** conteúdo claro, evidencia bem o que precisa de atenção; layout deveria ser board/Kanban (mesmo tema recorrente).
- **Resultado:** PASS WITH FRICTION (reclassificado a pedido do Founder).

### Task 6 — Decisions

- **Objetivo:** encontrar decisões relevantes.
- **Completado:** SIM (parcial — mais foco em feedback de layout do que em resposta direta sobre utilidade).
- **Achado:** mesmo tema recorrente de layout board/Kanban, refinado depois para "alternância de visualização" (lista ↔ board) como opção do usuário, aplicável a Ações/Decisões/Priorização.
- **Resultado:** PASS WITH FRICTION.

### Task 7 — Learnings

- **Objetivo:** descobrir se a plataforma registra aprendizados recorrentes.
- **Completado:** SIM.
- **Achado positivo forte:** o usuário conectou espontaneamente o conceito de Aprendizados a alimentar as IAs/Advisors do produto com boas práticas e lições aprendidas — alinhado com a intenção arquitetural real (Knowledge Platform / Organizational Intelligence).
- **Fricção:** dados percebidos como "crus"/rasos (possivelmente reflexo do dataset sintético limitado).
- **Resultado:** PASS.

### Task 8 — Documents

- **Objetivo:** descobrir onde colocar um novo documento (`demo/synthetic-document.md`).
- **Completado:** SIM — upload real executado com sucesso, "super simples".
- **Achados:** coluna "Ações" na listagem sem propósito claro; campo "chunks" é terminologia técnica interna exposta sem explicação; expectativa de integração com armazenamento externo (OneDrive/Google Drive/rede interna) e de a IA buscar documentos automaticamente (atas, requisitos, cronogramas).
- **Resultado:** PASS WITH FRICTION.

### Task 9 — Administration

- **Objetivo:** administrar usuários e voltar ao trabalho normal.
- **Completado:** PARCIAL — criou um usuário ("Cristiano Menezes") com sucesso; não encontrou onde atribuir papéis; não encontrou cadastro de organizações.
- **Achado:** **PRODUCT GAP — ORGANIZATION ADMINISTRATION / ONBOARDING** (gap já conhecido institucionalmente, não apresentado como resolvido, conforme instrução explícita do mandato). Pergunta arquitetural legítima levantada sobre isolamento entre organizações e usuários multi-organização — registrada como pergunta/risco, não respondida em detalhe durante a sessão (fora do papel de facilitador).
- **Resultado:** PASS WITH FRICTION / PARTIAL.

### Task 10 — Logout

- **Objetivo:** encerrar a sessão.
- **Completado:** SIM. **Assistência:** NENHUMA.
- **Achado positivo forte:** "muito tranquilo... o menu sair está bem visível, fixo na ferramenta... muito fácil, muito ágil" — validação prática do fix de F6 (sidebar sticky) em uso real.
- **Resultado:** PASS.

## 8. Completion Matrix

| Task | Completado |
|---|---|
| 1. Executive Orientation | SIM |
| 2. Prioritization | NÃO |
| 3. Portfolio/Program/Project | SIM |
| 4. Project Delivery | SIM |
| 5. Actions | SIM |
| 6. Decisions | SIM |
| 7. Learnings | SIM |
| 8. Documents | SIM |
| 9. Administration | PARCIAL |
| 10. Logout | SIM |

**Total: 8/10 completas, 1 parcial, 1 não completada (FAIL).**

## 9. Assistance Matrix

| Task | Assistência |
|---|---|
| 1 | Nenhuma |
| 2 | Baixa (esclarecimento de termo, a pedido do usuário) |
| 3 | Nenhuma |
| 4 | Nenhuma |
| 5 | Nenhuma |
| 6 | Nenhuma |
| 7 | Nenhuma |
| 8 | Nenhuma |
| 9 | Nenhuma |
| 10 | Nenhuma |

**Sem assistência: 9/10. Com assistência baixa: 1/10 (Task 2, esclarecimento de vocabulário da própria tarefa, não de navegação do produto). Sem assistência alta em nenhuma tarefa.**

## 10. Navigation Findings

- Menus "Projetos" e "Program Management" separados geram confusão sobre a hierarquia (Task 3).
- Decision Support e Narrativa Executiva deveriam estar em menu/submenu dedicado à IA, não embutidos no Dashboard.
- Sugestão recorrente (3 ocorrências independentes — Priorização, Ações, Decisões): alternância de visualização lista ↔ board/Kanban.
- Sugestão de menu mais compacto/granular (submenus sob itens principais).

## 11. UX Findings

- Dashboard percebido como "poluído" para o nível executivo esperado.
- Tema visual "muito escuro" — pedido de tema mais claro e revisão tipográfica.
- Coluna "Ações" em Documentos sem propósito claro.
- Campo técnico "chunks" exposto sem explicação ao usuário final.
- Logout: **positivo** — claro, rápido, botão fixo e visível.

## 12. Information Architecture Findings

- Hierarquia Portfolio → Program → Project entendida corretamente pelo usuário mesmo sem explicação prévia — mas a navegação atual não reforça essa hierarquia visualmente.
- Falta de granularidade ao entrar num projeto específico (Project Delivery) — análises/riscos/ações não claramente listados em detalhe.
- Decision Support/Narrativa Executiva misturados ao Dashboard, quando o usuário esperaria uma área dedicada de interação com IA.

## 13. Product Defects

Nenhum defeito de produto real (bug) foi encontrado durante a sessão observada — todos os achados são de UX/IA/Product Gap/Feature Request, não de comportamento incorreto do sistema.

## 14. Product Gaps

- **PRODUCT GAP — ORGANIZATION ADMINISTRATION / ONBOARDING**: sem UI para atribuir papéis a usuários criados nem para cadastrar novas organizações (achado já conhecido institucionalmente, reafirmado nesta sessão).
- Falta de indicadores financeiros (previsto vs. realizado, desvio de custo) no Dashboard.
- Falta de sinalização de prazo (atrasado/no prazo) nos indicadores de saúde do portfólio.

## 15. Feature Requests

1. Alternância de visualização (lista ↔ board/Kanban) em Ações, Decisões, Priorização.
2. Indicadores financeiros e de prazo tipo "semáforo" no Dashboard, alinhados a práticas de mercado de PMO/VMO.
3. Tema visual mais claro, revisão de tipografia, menu mais compacto/granular.
4. Menu dedicado para interação com IA (Decision Support/Narrativa Executiva fora do Dashboard).
5. Integração com armazenamento externo (OneDrive/Google Drive/rede interna) para Documents.
6. IA buscando/indexando documentos automaticamente (atas, requisitos, cronogramas) em vez de só upload manual.

## 16. Business Insights

- Usuário conectou espontaneamente Aprendizados/Learnings a "abastecer as IAs do produto com as melhores práticas" — validação orgânica da intenção arquitetural do Knowledge Platform.
- Pedido de pesquisa de mercado sobre KPIs/metodologias usadas por PMOs e VMOs líderes, para cruzamento com o produto — registrado como direção de pesquisa futura, não executado nesta sessão (fora de escopo).
- Visão do produto como "assessor, analista de projetos" que "vai operar o escritório de projetos" — percepção de valor overall positiva e alinhada à proposta original do produto.

## 17. User Quotes

- "está um pouco poluído essa primeira tela"
- "não está claro o que seria... descubra como está a situação geral da organização" (sobre a formulação da Task 1)
- "não consegui visualizar se estão em atraso, se estão em dia"
- "aqui a gente poderia melhorar o layout, poderia trazer em formato de como é utilizado no Scrum"
- "Não, ela não está claro. A gente teria que melhorar o layout, deixar mais claro o que preciso priorizar"
- "portfólio nível um, programa nível dois, projeto nível três, tarefas nível quatro, ações nível cinco"
- "este quadro de ações sim está claro, fica bem evidente o que precisa ser feito"
- "Bastante interessante essa tela... utilize essa esse menu pra abastecer as IAs do produto"
- "cheguei a fazer, super simples" (upload de documento)
- "não vi aonde eu cadastro os papéis... criação de organizações, ainda está muito muito simples"
- "foi muito tranquilo... o menu sair está bem visível, fixo... muito fácil, muito ágil"
- "Sim, de forma geral [a STRATECH] faz parte da minha rotina de trabalho... ele é um assessor, um analista de projetos"
- "hoje a nota eu diria que está entre seis e meia e sete... entendo que a ferramenta já estaria usual pro usuário final"

## 18. Executive Intelligence Expectations

Sem avaliar qualidade real de IA (Anthropic/Voyage indisponíveis nesta sessão — fronteira respeitada). O usuário localizou Decision Support e Narrativa Executiva no Dashboard e expressou:

- Esperaria perguntar sobre status atual e propostas de tomada de decisão baseadas nas análises.
- Esperaria que a IA colaborasse com a análise, trouxesse pontos de atenção e sugestões rápidas de decisão/redirecionamento.
- Considera o conceito "contributivo" para tomada de decisão.
- Acredita que essas funcionalidades deveriam estar num menu/submenu dedicado à IA, não dentro do Dashboard.

Não foi solicitado ao usuário avaliar a qualidade real de uma resposta de IA (mecanismo técnico presente, conteúdo real de IA indisponível).

## 19. Value Assessment

- **Descrição em uma frase:** "sistema de gestão de projetos que centraliza dados e informações pra tomada de decisão" (inicial) / "um assessor, um analista de projetos... vai operar o escritório de projetos e trazer insights importantes pra tomada de decisão" (final).
- **Funcionalidade mais valiosa:** Ações (Task 5, PASS limpo) e o conceito de Aprendizados alimentando IA (Task 7, PASS com insight espontâneo).
- **Funcionalidade menos clara:** Priorização (Task 2, FAIL).
- **Ficou sem saber o que fazer:** sim, brevemente na Task 2 (formulação da tarefa, termo "organização").
- **Esperava e não encontrou:** atribuição de papéis e cadastro de organizações em Administração (Task 9).
- **Intenção de uso:** **SIM**.
- **O que precisaria mudar para uso regular:** melhorias visuais, reorganização de menus, indicadores financeiros/prazo.
- **Uma única coisa a adicionar:** não coletado como pergunta isolada — refletido nos Feature Requests (Seção 15).

## 20. Scores

| Métrica | Valor | Observação |
|---|---|---|
| Perceived Value | 6,5–7/10 | Coletado explicitamente |
| Usability | NÃO COLETADO NUMERICAMENTE | Fricção qualitativa recorrente em layout/menus |
| Clarity | NÃO COLETADO NUMERICAMENTE | Priorização = FAIL de clareza; outras telas = fricção |
| Navigation | NÃO COLETADO NUMERICAMENTE | Múltiplos achados de fricção de navegação |
| Decision Support Potential | NÃO COLETADO NUMERICAMENTE | Percepção qualitativa positiva ("contributivo") |
| Trust | NÃO COLETADO | Sessão fechada antes desta pergunta específica ser respondida isoladamente |
| Intent to Use | **SIM** | Coletado explicitamente |

Nota: por instrução do próprio mandato ("os scores são indicadores qualitativos... não métricas estatísticas"), os itens não coletados numericamente não foram inventados — registrados honestamente como não coletados.

## 21. Top Positive Findings

1. Logout — claro, rápido, botão fixo e visível (validação prática do fix F6).
2. Ações — tela clara, evidencia bem o que precisa de atenção.
3. Hierarquia Portfolio/Program/Project entendida corretamente sem explicação prévia.
4. Aprendizados — conexão espontânea e correta com alimentar as IAs do produto.
5. Upload de documentos — "super simples".

## 22. Top Frictions

1. Priorização — objetivo da tela não alcançado (FAIL real).
2. Dashboard — "poluído", falta indicadores financeiros/semáforo de desvio de prazo.
3. Menus fragmentados (Projetos vs. Program Management); Decision Support/Narrativa deveriam ter menu próprio.
4. Administração — sem cadastro de papéis nem de organizações (Product Gap conhecido).
5. Terminologia técnica exposta sem explicação ("chunks", coluna "Ações" em Documentos).

## 23. Top Product Gaps

1. Organization Administration/Onboarding (papéis, criação de organizações).
2. Indicadores financeiros (previsto vs. realizado, desvio de custo).
3. Sinalização de prazo (atrasado/no prazo) nos indicadores de saúde.

## 24. Top Requests

1. Alternância de visualização lista ↔ board/Kanban (Ações/Decisões/Priorização).
2. Menu dedicado de IA (Decision Support/Narrativa fora do Dashboard).
3. Integração com armazenamento externo + IA buscando documentos automaticamente.
4. Tema visual mais claro, tipografia revisada, menu mais compacto.
5. Pesquisa de mercado sobre KPIs/metodologias de PMOs e VMOs líderes.

## 25. Risks

- Priorização (uma tela central para a proposta de valor do produto — ajudar a decidir onde focar) falhou em comunicar seu objetivo. Isso é um risco real para a percepção de valor em uma sessão com usuário externo (não-Founder).
- O gap de Organization Administration já era conhecido institucionalmente e permanece — risco de bloquear onboarding real de múltiplas organizações no piloto controlado.
- Achado operacional (conflito de porta 5432 nativo/Docker) é a 2ª ocorrência do mesmo problema — risco de fricção recorrente em qualquer nova revalidação Windows até ser corrigido permanentemente.

## 26. Pilot Implications

Os achados desta sessão são consistentes com a fronteira de IA declarada (mecanismo técnico presente, conteúdo real de IA não avaliado) e não revelam nenhum problema de segurança, isolamento de dados ou integridade — apenas oportunidades reais de UX/IA/Product Gap. Isso é compatível com prosseguir a validação (mais sessões), mas não com avançar automaticamente para um Controlled User Pilot com usuários externos sem revisar ao menos a Priorização (FAIL) e a organização visual do Dashboard.

## 27. Recommendation

Tratar os achados desta sessão na **Pilot Findings Review** (Founder Executive Review), triando cada um como Decision Proposal antes de qualquer implementação. Nenhuma correção foi feita durante esta sessão, por mandato explícito.

## 28. GO/NO-GO for User Session #2

**GO**, condicionado à Pilot Findings Review ter ocorrido antes — nenhuma STOP CONDITION foi atingida, o ambiente está estável, e os achados são de produto/UX (esperados e desejáveis nesta fase), não de defeitos bloqueantes.

## 29. GO/NO-GO for Controlled User Pilot Progression

**NO-GO** por ora — a Task 2 (Priorização) falhou em comunicar seu objetivo central, e o Product Gap de Organization Administration permanece sem solução, ambos relevantes antes de expor o produto a usuários externos reais em um piloto controlado.

## 30. Recommended Next Actions

1. Founder Executive Review desta evidência.
2. Pilot Findings Review — triagem formal de cada achado (Product Gap/Feature Request/UX) em Decision Proposals.
3. Considerar corrigir permanentemente o conflito de porta 5432 nativo/Docker no Windows (2ª ocorrência do achado de D-213) antes da próxima sessão física.
4. Nenhuma implementação, nenhum roadmap novo, nenhuma User Session #2 iniciada automaticamente — aguardando nova Founder Decision.
