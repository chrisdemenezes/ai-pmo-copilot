# STRATECH — Lessons Learned (Governança de Repositório)

Registro vivo de lições operacionais extraídas da execução real da governança — não de teoria. Cada entrada documenta o que aconteceu, por que aconteceu, e a mudança de prática (se houver) resultante.

---

## LL-001 — Nome de required status check deve corresponder exatamente ao nome do job, não a uma string composta

- **Quando:** Consolidação do PR #39 (STRATECH V2, Épico 1), 2026-07-17.
- **O que aconteceu:** Após a Branch Protection/Ruleset da `main` ser configurada para exigir os checks `validate` e `frontend`, o PR #39 ficou preso em `mergeable_state: blocked` mesmo com ambos os jobs reais (`CI / validate`, `CI / frontend`) concluídos com sucesso. O diagnóstico (obtido apenas por captura de tela da UI do GitHub, já que a API de leitura de rulesets não estava acessível à sessão do agente) revelou um required check pendente chamado literalmente **`validate frontend`** — uma única string, sem correspondência com nenhum job real do workflow (que reporta dois checks separados: `validate` e `frontend`). Esse requisito nunca seria satisfeito, pois nenhum workflow jamais reporta um status com esse nome exato.
- **Causa-raiz:** ao configurar "Required status checks" na interface do GitHub, os dois nomes de check foram inseridos como uma única entrada de texto em vez de duas entradas separadas.
- **Correção:** o Founder corrigiu a configuração da ruleset diretamente na interface do GitHub, separando os dois requisitos. O `mergeable_state` do PR mudou de `blocked` para `clean` imediatamente após a correção, sem qualquer nova alteração de código ou commit.
- **Mudança de prática adotada:** ao configurar required status checks em qualquer ruleset futura da STRATECH, verificar imediatamente após salvar — abrindo um PR de teste ou revisando um PR já aberto — que o `mergeable_state` reflete `clean` quando os checks reais estão verdes. Não presumir que a configuração da UI foi salva como pretendido apenas pela ausência de erro visível.
- **Limitação de ferramenta observada:** a sessão do agente não teve acesso de leitura à API de rulesets/branch protection nem a navegador para inspecionar a UI diretamente — o diagnóstico definitivo só foi possível com uma captura de tela fornecida manualmente pelo Founder. Isso é aceitável como processo (o Founder é o único responsável por configurações administrativas do GitHub, por decisão da própria governança), mas vale registrar como um limite estrutural do modelo agente+humano: verificações de configuração administrativa sempre exigirão a participação ativa do Founder.

## LL-002 — Modelo de governança oficial adotado: humano decide e configura, agente implementa e verifica

- **Quando:** Consolidação da V1 (PRs #36-38) e abertura da V2 (PR #39), julho de 2026.
- **O que foi estabelecido:** Ao longo de toda a consolidação da V1 e da abertura do Épico 1 da V2, o modelo operacional que emergiu — e que se mostrou robusto na prática — foi:
  - **O Founder** decide o que é aprovado, autoriza cada merge individualmente (nunca por autorização geral antecipada), e é o único a aplicar configurações administrativas do GitHub (branch protection, rulesets, CODEOWNERS ativado).
  - **O agente** implementa, testa com evidência real (execução, não apenas leitura de código), audita de forma independente antes de merges estruturais, e **para explicitamente** sempre que uma condição de pré-merge não está clara ou não pôde ser verificada — nunca presume "provavelmente está certo".
  - Toda mudança estrutural (schema, CI, governança) passa por PR mesmo quando o autor é o próprio agente; **nenhum commit direto na `main`** ocorreu em nenhum momento desta consolidação.
  - Bloqueios (como o LL-001) são reportados com a evidência exata disponível — e, quando a ferramenta do agente não alcança a evidência necessária (ex.: UI do GitHub, rulesets), isso é declarado explicitamente em vez de simulado ou presumido.
- **Por que isso importa:** este modelo permitiu avançar com velocidade real (3 PRs de V1 + 1 PR de V2 fundacional em uma única sessão de trabalho) sem nunca sacrificar rastreabilidade, auditabilidade ou a autoridade decisória do Founder. Nenhum merge ocorreu sem autorização explícita; nenhuma configuração de risco (tags, branch protection, exclusão de branch) foi executada pelo agente sem que a permissão da própria plataforma a autorizasse ou o Founder a executasse diretamente.
- **Recomendação de continuidade:** manter este modelo para os Épicos 2-6 e para a Release 0.2+ — em particular, manter a prática de revisão arquitetural independente antes de qualquer merge que introduza schema novo, e manter o registro de débito técnico (`TECHNICAL_DEBT.md`) como parte obrigatória de todo PR estrutural, não apenas do primeiro.
