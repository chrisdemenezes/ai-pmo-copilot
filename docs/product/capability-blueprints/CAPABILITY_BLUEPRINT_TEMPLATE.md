# Capability Blueprint Template

STRATECH V2 — Product Engineering Framework (EO-021).

> Este arquivo é **apenas o template oficial**. Nenhuma Capability Blueprint real (`CB-NNN-*.md`) foi criada a partir dele nesta EO. Toda Capability Blueprint futura é uma cópia deste template preenchida, seguindo o fluxo Product Vision → Capability Blueprint → Founder Approval → Engineering Order → Technical Design → Implementation → Architecture Review → Merge (`GOVERNANCE_MODEL.md`, Seção 2A).
>
> **Regra central:** toda decisão funcional é tomada aqui, antes da engenharia. Nenhuma Technical Design ou Implementation pode alterar regra de negócio, UX, fluxo ou critério de aceite definidos numa Capability Blueprint aprovada — qualquer inconsistência encontrada durante a engenharia vira uma Engineering Question (EQ), nunca uma decisão unilateral (`GOVERNANCE_MODEL.md`, Seção 5).

---

**Código:** `CB-NNN`
**Nome da Capability:**
**Status:** Draft | Em Aprovação | Aprovada (Founder) | Em Implementação | Implementada
**Programa relacionado (Domain Map):**
**Release/Épico relacionado:**

---

## 1. Executive Summary

*Resumo de uma página: o que esta Capability entrega, para quem, e por quê. Deve ser lido e compreendido isoladamente, sem o resto do documento.*

## 2. Business Vision

*Como esta Capability se conecta à visão estratégica da STRATECH V2 (Blueprint, Master Roadmap). Que diferenciação ela entrega.*

## 3. Business Problem

*O problema de negócio real que motiva esta Capability. Evidência do problema, não apenas afirmação.*

## 4. Target Users

*Personas/perfis que usam esta Capability (referenciar Cockpit-Views-Matrix quando aplicável). O que cada perfil espera obter.*

## 5. User Journey

*Fluxo ponta a ponta do usuário, do gatilho até o resultado. Diagramas (Mermaid) quando ajudarem.*

## 6. Functional Scope

*O que está dentro do escopo desta Capability — lista explícita, não aberta a interpretação.*

## 7. Functional Specification

*Comportamento detalhado, tela a tela / endpoint a endpoint, na granularidade necessária para a engenharia implementar sem tomar decisão funcional própria.*

## 8. Business Rules

*Regras de negócio explícitas, numeradas, testáveis. Esta seção é a que a engenharia nunca pode alterar ou simplificar.*

## 9. Permissions

*Quem pode fazer o quê. Papéis/permissões envolvidos (RBAC, quando aplicável).*

## 10. Information Model

*Entidades, atributos e relacionamentos envolvidos, em nível conceitual — não é o schema técnico (isso é responsabilidade da Technical Design subsequente).*

## 11. UX Principles

*Princípios de experiência que a implementação deve respeitar. Não é o desenho visual em si (isso é artefato de design), mas as regras que a engenharia não pode violar.*

## 12. AI Opportunities

*Onde IA pode ou deve atuar nesta Capability (referenciar AI-Accelerators-Map quando aplicável), e onde deliberadamente não deve.*

## 13. Metrics

*Como o sucesso desta Capability é medido depois de implementada.*

## 14. Future Evolution

*Extensões previstas, mas explicitamente fora do escopo desta Capability Blueprint — não implementar agora, só registrar.*

## 15. Acceptance Criteria

*Critérios objetivos, verificáveis, que determinam quando esta Capability está pronta. Base para o Definition of Done da implementação.*

## 16. Open Questions

*Perguntas funcionais ainda sem resposta no momento da redação. Devem ser resolvidas antes da aprovação do Founder — uma Capability Blueprint com Open Questions não resolvidas não deveria ser aprovada.*

## 17. Dependencies

*Outras Capabilities, Épicos, Releases ou decisões arquiteturais das quais esta Capability depende.*

## 18. Out of Scope

*O que esta Capability explicitamente não faz, para evitar ambiguidade ou scope creep durante a implementação.*
