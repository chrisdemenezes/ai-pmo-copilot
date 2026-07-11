# ADR-012 — Founder Decision: Release 0.3 Opened Ahead of Validation Sprint Completion

**Tipo:** Founder Decision (exceção deliberada de governança, não uma mudança permanente do AI-PEF)
**Escopo:** Exclusivamente a Release 0.3. Não altera o AI-PEF v1.1, não substitui o ADR-009, não
revoga o critério de formalização da Platform Initiative (Seção 0 do Platform Blueprint v1.0).
**Responsável pela decisão:** Founder / Product Owner
**Data:** 2026-07-11

## Contexto

A fase de Validation Sprint estabeleceu, em duas instruções explícitas do Product Owner (papéis
Chief Product Researcher e Chief Product Scientist), que a Release 0.3 só poderia ser aberta após a
conclusão de cinco sessões reais de validação com usuários e a consolidação de um Product Discovery
Report único, produzido a partir dessas sessões.

No momento desta decisão, zero sessões reais haviam sido concluídas — o trabalho realizado até aqui
foi exclusivamente a instalação e validação técnica do ambiente de demonstração (Demo Mode) na
máquina do Founder, etapa anterior à primeira sessão real.

## Problema

Abrir o planejamento da Release 0.3 agora, sem as cinco sessões concluídas, contraria literalmente
as duas condições registradas pelo próprio Product Owner nesta mesma sessão de trabalho. O Chief
Product Architect sinalizou esse conflito explicitamente antes desta decisão ser tomada.

## Alternativas consideradas

1. **Manter o gate — aguardar as 5 sessões e o Product Discovery Report antes de qualquer
   planejamento de Release.** Preserva a condição original sem exceção.
2. **Escrever o Release Plan como exercício especulativo, sem validade até o gate ser cumprido.**
   Produz o documento, mas o mantém sem efeito prático.
3. **Autorização explícita do Founder, com registro formal da exceção (esta decisão).** Abre a
   Release 0.3 agora, mas exige que a decisão seja documentada com o mesmo rigor de um ADR — não
   como uma substituição silenciosa do processo.

## Decisão

Adotada a alternativa 3. O Founder exerce sua autoridade para abrir a Release 0.3 antes da conclusão
da Validation Sprint, com a seguinte reconfiguração explícita:

- As cinco sessões de validação **continuam obrigatórias**, mas passam a ocorrer **em paralelo** ao
  desenvolvimento da Release 0.3, alimentando continuamente o Validation Report.
- O **Product Discovery Report deixa de ser condição de abertura** da Release 0.3 e passa a ser
  **condição obrigatória de encerramento** da Release 0.3 e de priorização da Release 0.4.
- A justificativa registrada pelo Founder: o produto atingiu um nível de maturidade (Release 0.2
  concluída, AI-PEF v1.1 consolidado, Demo Mode operacional, Dashboard funcional, frontend e backend
  integrados, direção visual definida, Platform Blueprint v1.0 aprovado) que reduz o risco de abrir
  uma release de natureza predominantemente de **Experience Platform / UX**, preservando
  integralmente arquitetura, backend, contratos de API e funcionalidades existentes — nenhuma
  Feature classificada como "Visão" no Platform Blueprint será implementada nesta release.

## Consequências

- **Positivas:** a Release 0.3 pode começar sem bloquear no calendário de agendamento das 5 sessões;
  o desenvolvimento visual e a validação real passam a se retroalimentar continuamente, em vez de
  serem sequenciais.
- **Negativas / risco aceito:** o backlog da Release 0.3 é definido com evidência de maturidade
  técnica, não com evidência de comportamento real de usuário. Se as sessões, quando ocorrerem,
  revelarem que a direção da Release 0.3 não responde à dor real do usuário, parte do trabalho
  visual já em andamento pode precisar de retrabalho — risco explicitamente aceito pelo Founder, não
  ignorado.
- Este ADR não estabelece precedente automático. Releases futuras continuam sujeitas às condições de
  validação vigentes no momento, salvo nova decisão de mesma natureza, igualmente registrada.

## Critérios de revisão

- Ao final da Release 0.3, o Product Discovery Report (agora condição de encerramento, não de
  abertura) deve mostrar se as decisões visuais tomadas sem validação prévia se sustentam com
  usuários reais.
- Se, durante as sessões paralelas, um sinal recorrente contradizer uma decisão já implementada da
  Release 0.3 (ex.: confusão repetida com uma tela específica), essa decisão deve ser revisitada
  antes do encerramento da release, não esperar até a Release 0.4.
- A abertura da Release 0.4 permanece condicionada ao Product Discovery Report completo — sem
  exceção adicional automática.

## Referências

- Protocolo de Validação: artefato publicado nesta sessão (Chief Product Researcher)
- Instrumento de Captura (Validation Report): artefato publicado nesta sessão (Chief Product
  Scientist)
- Platform Blueprint v1.0: artefato publicado nesta sessão (Chief Platform Architect)
- AI-PEF v1.1: `docs/product/ai-pef/AI-PEF.html`, ADR-009 (princípio evolutivo)
