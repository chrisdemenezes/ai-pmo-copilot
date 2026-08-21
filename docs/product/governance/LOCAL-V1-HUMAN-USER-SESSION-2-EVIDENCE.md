# Local V1 Human User Session #2 — Executive Evidence

- **Missão:** FOUNDER DECISION — LOCAL V1 HUMAN USER SESSION #2 (Validação Humana Focada Pós-Pilot Readiness Implementation)
- **Data:** 2026-08-20
- **Baseline SHA:** `d9206eb95f2a9825307b0b684bb4d26a27997f75`
- **Participante:** Founder, atuando novamente como usuário real (facilitador não explicou mudanças previamente, não conduziu para resposta esperada).

## 1. Pre-Session Gate

- `main` local confirmado em `d9206eb95f2a9825307b0b684bb4d26a27997f75`, working tree limpo.
- Stack local (`demo/start-demo.sh`) confirmado no ar (backend :8000, frontend :3000).
- `/health`/`/ready` aceitos por evidência indireta: dados reais renderizando corretamente na primeira tela mostrada, incluindo a nova coluna Prazo.
- Organização/usuário do piloto pré-provisionado tratado como parte do Teste E (ver Seção 6), não como pré-condição bloqueante — os Testes A-D não dependem da organização, e a organização demo padrão foi usada para eles.
- Nenhum BLOCKER técnico encontrado que tenha exigido interromper a sessão.

## 2. Teste A — Priorização

**RESULT:** PASS

**ASSISTANCE REQUIRED:** mínima — 3 perguntas fechadas (sim/não) para obter uma resposta explícita, sem explicar a regra em si.

**USER INTERPRETATION:** o usuário identificou espontaneamente, ao olhar a tela, que a lista está "filtrada por ações necessárias no dia de hoje, ações durante a semana e assim por diante" — descrição correta da sequência de camadas (decisão hoje → decisão esta semana → risco a monitorar → sem sinal de atenção) sem que a regra fosse explicada antes. Persiste, no entanto, forte preferência por um formato Kanban/board em vez de lista — mesmo pedido feito na Session #1, agora com uma 2ª evidência consistente.

## 3. Teste B — Dashboard (dados demonstrativos)

**RESULT:** FAIL

**REAL VS DEMO DATA:** o usuário rolou a página inteira (confirmado explicitamente — "fui até o final... onde fala sobre concentração de riscos, top 5") e declarou, de forma direta, que **não existe** nenhuma indicação na tela que distinga dado real de dado demonstrativo. Isso ocorre apesar de o badge "Dados demonstrativos" (D-219) estar implementado e comprovadamente presente — confirmado visualmente mais tarde, durante o Teste E, quando a mesma seção apareceu com o badge visível na tela do usuário. Achado real: o mecanismo existe, mas não está cumprindo seu objetivo de comunicação na prática (baixa saliência/discoverability), não uma ausência de implementação.

**DENSITY COMPARISON:** ver Teste D.

## 4. Teste C — Indicador de Prazo

**RESULT:** PASS

**USER INTERPRETATION:** o usuário interpretou corretamente o selo "No Prazo" como "o projeto está dentro do prazo estimado", sem assistência. Teste limitado pelo dataset disponível — as únicas linhas visíveis mostravam "No Prazo" uniformemente, sem contraste real com "Atenção"/"Atrasado" (limitação de dados, não do produto).

**Achado adicional (Business Insight):** o usuário notou espontaneamente que "Saúde" e "Prazo" são colunas independentes e questionou como um portfólio pode estar "Crítico" em saúde mas "No Prazo" simultaneamente — sinalizando que a relação entre os dois indicadores não está explicada na tela.

## 5. Teste D — Densidade do Dashboard

**RESULT:** IGUAL à Session #1 (não melhorou, não piorou).

**Justificativa do usuário:** ainda considera necessário deixar mais limpo, com indicadores mais diretos, e mover informação detalhada para um modelo de consulta/pesquisa em vez de expor tudo de uma vez. Reitera pedido de indicadores financeiros (orçado x planejado, horas) — já investigado e explicitamente fora de escopo em D-217 (exigiria novo modelo de dados/decisão arquitetural); registrado novamente como Feature Request, decisão inalterada.

## 6. Teste E — Provisionamento do Piloto

**RESULT:** confirmado operacionalmente, com um achado real de defeito descoberto e contornado (sem alteração de código).

O primeiro boot com `PILOT_ORGANIZATION_NAME=Piloto Externo A` (valor sem aspas) falhou silenciosamente: `demo/start-demo.sh` carrega `demo/.env` via `source` (bash, não um parser de `.env` dedicado), e um valor com espaço não citado quebra esse parsing — a variável nunca foi exportada. Confirmado mecanicamente pelo log do backend: `"Pilot organization bootstrap skipped -- PILOT_ORGANIZATION_NAME/PILOT_ORGANIZATION_ADMIN_EMAIL/PILOT_ORGANIZATION_ADMIN_PASSWORD not set"`, seguido de `"Login failed: organization not found slug=piloto-externo-a"`.

Corrigido apenas no `.env` local do Founder (`PILOT_ORGANIZATION_NAME="Piloto Externo A"`, com aspas) — **nenhuma alteração de código do repositório nesta sessão**. Após a correção local, o boot processou o bootstrap corretamente e o login como `organization_admin` do piloto funcionou. Tenant isolation confirmado visualmente: a organização nova renderizou com todos os contadores zerados (Portfólios/Programas/Projetos/Decisões = 0), sem nenhum dado vazando de "Organização Principal".

**Achado real registrado:** o próprio nome de exemplo usado no Runbook (`docs/operations/LOCAL-V1-PILOT-ORGANIZATION-PROVISIONING-RUNBOOK.md`) contém um espaço e dispara esse defeito — é um gap de robustez/documentação do caminho `demo/start-demo.sh`, não do mecanismo `AuthService.bootstrap_organization()` em si, que funcionou corretamente assim que a variável foi corretamente exportada.

**FOUNDER ACCEPTANCE:** o Founder respondeu inicialmente "sim" à pergunta de aceitação do modelo pré-provisionado, depois corrigiu explicitamente para **ACCEPTABLE WITH LIMITATION** — aceitável para este piloto controlado específico, mas exige que uma tela de criação de organizações passe a existir no roadmap. Isso reforça (não cria) o Product Gap já registrado em D-217.

## 7. Human Scores

| Dimensão | Nota |
|---|---|
| Perceived Value | 8/10 |
| Usability | 8/10 |
| Clarity | 8/10 |
| Navigation | 8/10 |
| Decision Support Potential | 8/10 |
| Trust | 8/10 |
| Intent to Use | **TALVEZ** |

Todas as 6 dimensões numéricas foram confirmadas explicitamente pelo Founder como uniformes em 8/10 (não inferidas). Intent to Use = Talvez, não Sim — o Founder condicionou isso explicitamente à correção dos achados pendentes desta sessão (pedido direto de correção imediata, recusado durante a sessão por regra STOP do mandato, registrado como Next Recommended Action).

## 8. Session #1 → Session #2

| Dimensão | Session #1 | Session #2 |
|---|---|---|
| Priorização | FAIL | PASS |
| Dashboard (dados demonstrativos) | não testado (badge não existia) | FAIL — sem dado comparável de Session #1 |
| Prazo | não existia | PASS — sem dado comparável de Session #1 |
| Clareza/densidade | "está um pouco poluído essa primeira tela" | IGUAL — sem melhora percebida |
| Valor percebido | 6,5–7/10 | 8/10 — melhora |

Não foi inventada evolução onde não há dado comparável (Dashboard/dados demonstrativos e Prazo são capacidades novas desta missão, sem baseline em Session #1).

## 9. Findings

**BLOCKER:** nenhum.

**HIGH:**
1. Badge "Dados demonstrativos" implementado e presente na tela, mas não percebido espontaneamente pelo usuário mesmo após rolar a página inteira duas vezes — falha de comunicação prática (UX/UI, discoverability).
2. Bootstrap da organização do piloto falha silenciosamente quando `PILOT_ORGANIZATION_NAME` contém espaço sem aspas, carregado via `source` em `demo/start-demo.sh` — o próprio exemplo do Runbook dispara o defeito (Product Defect / gap de robustez de documentação).

**MEDIUM:**
- Organization Administration UI (tela de criação de organizações) reforçada como necessária pelo Founder antes de expandir o modelo além deste piloto controlado (Product Gap já conhecido, D-217).

**LOW / OBSERVATION:**
- Fricção operacional ao editar `.env` no Windows (Git Bash + editor de texto) — conteúdo de heredoc colado como texto literal em vez de executado, exigindo correção manual. Registrado como observação ambiental, não defeito de produto.
- Relação entre indicadores "Saúde" e "Prazo" não explicada na tela quando os dois divergem.

**POSITIVE:**
- Sequência de camadas de Priorização descrita corretamente pelo usuário sem explicação prévia.
- Selo "No Prazo" interpretado corretamente sem assistência.
- Valor percebido subiu de 6,5–7/10 (Session #1) para 8/10 (Session #2).
- Tenant isolation confirmado visualmente correto na nova organização do piloto.

## 10. Categorização

**PRODUCT DEFECTS:** bootstrap do piloto quebra com nome de organização contendo espaço (Runbook/`demo/start-demo.sh`).

**UX/UI FINDINGS:** baixa saliência do badge "Dados demonstrativos".

**INFORMATION ARCHITECTURE:** relação entre Saúde e Prazo não explicada.

**PRODUCT GAPS:** Organization Administration UI (reforço de D-217, não um novo gap).

**FEATURE REQUESTS:** Kanban/board para Priorização (recorrente, 2ª sessão); indicadores financeiros (recorrente, já fora de escopo); modelo de consulta/pesquisa para informação detalhada do Dashboard.

**BUSINESS INSIGHTS:** usuários podem esperar uma explicação da relação entre Saúde e Prazo quando os dois indicadores divergem.

## 11. Experience Gates

| Gate | Resultado |
|---|---|
| G1 — Priorização = PASS | SATISFIED |
| G2 — Dados demonstrativos claramente distinguíveis | NOT SATISFIED |
| G3 — Indicador de prazo compreensível | SATISFIED |
| G4 — Provisionamento pré-piloto operacionalmente aceitável | SATISFIED WITH LIMITATION |
| G5 — Zero BLOCKER | SATISFIED |
| G6 — Zero HIGH que impeça execução das tarefas centrais | SATISFIED (os 2 HIGH não bloquearam nenhuma tarefa central) |
| G7 — Usuário demonstra compreensão do modelo de valor da STRATECH | SATISFIED |
| G8 — INTENT TO USE = SIM ou justificadamente positivo | NOT SATISFIED (Talvez, condicionado a correções pendentes) |

## 12. Gates Finais

- **CONTROLLED EXTERNAL PILOT TECHNICAL GATE:** SATISFIED (herdado de D-221, revalidado nesta sessão, sem regressão).
- **CONTROLLED EXTERNAL PILOT EXPERIENCE GATE:** NOT SATISFIED (G2 e G8 não satisfeitos).
- **GO/NO-GO FOR CONTROLLED EXTERNAL PILOT:** CONDITIONAL GO — pronto tecnicamente, mas a experiência real revelou 2 achados HIGH não resolvidos e uma intenção de uso condicional. Recomenda-se uma nova Founder Decision para um ciclo mínimo de correção focado nesses 2 achados, seguido de reavaliação de G2/G8 antes de autorizar o piloto externo.

## 13. Recommended Next Action

Founder Executive Review desta evidência → nova Founder Decision explícita para (a) autorizar um ciclo mínimo de implementação focado nos 2 achados HIGH (saliência do badge "Dados demonstrativos"; robustez do Runbook/mecanismo de bootstrap para nomes de organização com espaço), e (b) decidir se uma nova validação humana curta é necessária antes do piloto externo, ou se o Founder aceita prosseguir com base na evidência já coletada. Nenhuma implementação foi feita nesta sessão — inclusive o pedido direto do Founder de corrigir os achados imediatamente foi recusado durante a sessão, por regra STOP explícita do mandato.
