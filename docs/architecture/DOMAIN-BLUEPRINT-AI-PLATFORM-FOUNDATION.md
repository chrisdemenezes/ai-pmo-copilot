> **Nota de superação (2026-07-23, D-047):** o Founder redefiniu permanentemente o escopo do Epic W3-2 nesta mesma data, sob uma nova decisão estratégica ("STRATECH é um Executive Decision Operating System"). A avaliação abaixo permanece correta para o escopo que avaliou (Provider Strategy/Model Registry/Model Routing/Prompt Versioning — nenhum consumidor real hoje). O novo escopo do W3-2 ("Digital PMO Intelligence Foundation") foi implementado — ver `DOMAIN-BLUEPRINT-W3-2-Digital-PMO-Intelligence-Foundation.md`, `AR-3-W3-2-DIGITAL-PMO-FOUNDATION-REVIEW.md`, `TECHNICAL-DESIGN-W3-2-DIGITAL-PMO-FOUNDATION.md` e `docs/product/governance/W3-2-DIGITAL-PMO-FOUNDATION-EXECUTIVE-REPORT.md`. Este documento é preservado sem edição além desta nota, per a disciplina de nunca reescrever retroativamente uma decisão já registrada.

# Domain Blueprint — Epic W3-2: AI Platform Foundation

**Wave:** 3, Epic W3-2 (liberado pela AR-2).
**Status:** Blueprint conceitual concluído. **Conclusão: nenhuma implementação justificada nesta passagem — Epic adiado, não cancelado.**

---

## 1. O que foi avaliado

`DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` §1 recomendava um sequenciamento (Provider Strategy → Model Registry → Model Routing → Cost/Token → Observability/Governança → Evaluation Framework) e a AR-2 liberou este Epic para início imediato, sem depender de decisão do Founder. Esta auditoria foi além da recomendação de sequenciamento e verificou, item a item, se existe **hoje** um consumidor real, um requisito concreto ou um débito técnico aberto que justifique construir cada peça — não apenas se ela é tecnicamente segura de construir.

| Sub-área | Consumidor real hoje? | Veredito |
|---|---|---|
| **Provider Strategy** (múltiplos providers, seleção por caso de uso) | **Não.** Os 3 Accelerators usam sempre o mesmo `LLMProvider` resolvido uma vez por `get_provider()`; nenhum caso de uso pede um modelo diferente de outro hoje. | Não justificado — construir "seleção por caso de uso" sem nenhum caso de uso real que precise de seleção é arquitetura especulativa. |
| **Model Registry** | **Não.** Depende do Provider Strategy acima ter um consumidor primeiro. | Não justificado, mesma razão. |
| **Model Routing** | **Não.** Mesma dependência. | Não justificado. |
| **Prompt Versioning** | **Não.** `PromptRegistry` resolve por caminho de arquivo desde a criação do projeto; nenhum prompt jamais precisou de rollback ou de duas versões coexistindo (histórico de commits do repositório não mostra nenhum caso). | Não justificado — nenhuma dor real a resolver. |
| **Cost Management / Token Governance** | **Parcial.** `ProductionLLMProvider.generate()` (`src/llm/providers/production_provider.py:19`) já recebe `message.usage` (tokens de entrada/saída) da API da Anthropic e **descarta esse dado hoje** — nenhum Accelerator tem visibilidade de custo/token. | Gap real, mas **sem nenhum requisito de negócio ou técnico pedindo isso agora** — nenhum problema de custo relatado, nenhum dashboard pedido, nenhum TD aberto sobre isso. |
| **AI Observability / AI Governance** | **Não.** Mesma conclusão do item acima. | Não justificado agora. |
| **Evaluation Framework** | **Não.** Nenhuma suíte de avaliação de qualidade de output de IA existe ou foi pedida. | Não justificado. |

## 2. Por que este Blueprint não avança para Technical Design

CLAUDE.md e a disciplina de engenharia já estabelecida neste projeto ("não fazer mais do que o necessário", "não projetar para requisitos hipotéticos futuros") aplicam-se tanto a código quanto a Blueprints. O próprio `DOMAIN-BLUEPRINT-WAVE-3-ENTERPRISE-INTELLIGENCE.md` já classificava a maioria destes itens como "🔵 Proposta conceitual nova, zero grounding" — este documento confirma, com uma auditoria concreta caso a caso, que "zero grounding" continua verdadeiro para 6 dos 7 sub-itens, e que o único com um gap real (Cost/Token) não tem nenhum requisito ativo puxando sua resolução.

Construir "seleção de múltiplos providers" sem um segundo provider real em uso, ou um "Model Registry" sem nada para catalogar além do único provider já resolvido por `get_provider()`, seria inventar uma abstração para um problema que não existe hoje na STRATECH — exatamente o padrão que este projeto evita em toda a sua história (nenhum registry/provider duplicado foi criado em nenhuma Sprint anterior sem uma necessidade concreta).

## 3. Decisão — Epic W3-2 adiado, não implementado nesta passagem

**Nenhum código é produzido por este Epic.** O Epic Ledger da Wave 3 (`AR-2-WAVE-3-ARCHITECTURE-REVIEW.md` §4) é atualizado para refletir isto: W3-2 passa de "liberado" para "adiado — sem gatilho concreto", e a Wave 3 avança para o Epic W3-3 (Risk Advisor), que tem um entregável concreto e nomeado.

**Gatilho explícito para reabrir W3-2 no futuro** (qualquer um destes, não uma lista exaustiva): (a) o Epic W3-3 (Risk Advisor) ou um Advisor futuro precisar concretamente de um modelo diferente do já configurado; (b) um problema real de custo/latência for relatado, tornando a instrumentação de tokens necessária; (c) o Founder pedir explicitamente visibilidade de custo de IA. Até um desses ocorrer, este Epic permanece registrado como avaliado e adiado — não uma lacuna silenciosa.

## 4. Nenhuma decisão arquitetural ou de negócio foi tomada aqui

Este documento não decide que a STRATECH nunca terá múltiplos providers ou Model Registry — apenas que não há hoje nenhum caso de uso que os justifique. Nenhum Blueprint aprovado foi alterado; nenhum novo Bounded Context foi criado ou descartado.
