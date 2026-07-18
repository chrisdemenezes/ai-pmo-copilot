# ADR Tree — Normalization Plan (Proposal, Not Executed)

> Por instrução explícita da EO-018 ("NÃO renumerar ADRs nesta EO"), este documento **propõe** um plano de normalização — nenhum ADR é renumerado, movido ou reescrito aqui. Nenhuma ação abaixo é executada até uma Engineering Order futura autorizar explicitamente.

## Estado atual

Duas convenções de armazenamento coexistindo, sem reconciliação:

1. **`docs/product/stratech-v2/Architecture-Decision-Log.html`** — companion do Blueprint, contém 7 decisões embutidas: `ADR-V2-001` a `ADR-V2-007` (ex.: ADR-V2-004 = "4 papéis no Release 0.1, não os 14 do RBAC de referência").
2. **`docs/architecture/ADR-V2-004-schema-foundation-integrated.md`** — arquivo avulso, único ADR do V2 armazenado como arquivo individual, decidindo um assunto completamente diferente ("integração do schema do Épico 1 ao `main` via PR #39").

**Colisão:** ambos reivindicam o ID `ADR-V2-004`, com conteúdos diferentes. Sinalizada desde o encerramento do GP-001 (Épico 1), nunca resolvida.

## Problema

- Duas convenções de armazenamento (log HTML embutido vs. arquivo `.md` avulso) para o mesmo tipo de artefato.
- Um ID duplicado, ambíguo para qualquer referência futura a "ADR-V2-004".
- Nenhum índice único que aponte para todos os ADRs do V2 independentemente de onde estão armazenados.

## Plano proposto (para autorização futura)

1. **Convenção única:** adotar arquivo-por-ADR sob `docs/architecture/adr/`, o padrão já iniciado pelo arquivo avulso existente — não o padrão de log HTML embutido.
2. **Migração de conteúdo:** transcrever as 7 decisões de `Architecture-Decision-Log.html` para arquivos individuais (`docs/architecture/adr/ADR-V2-001-....md` a `ADR-V2-007-....md`), preservando o conteúdo, sem reinterpretar nenhuma decisão.
3. **Resolução da colisão:** o Founder decide qual dos dois conteúdos que hoje reivindicam `ADR-V2-004` mantém o número e qual é renumerado para o próximo ID livre (`ADR-V2-008`, assumindo que 001-007 permanecem como estão). Nenhuma das duas opções é escolhida unilateralmente aqui.
4. **`Architecture-Decision-Log.html`** passa a ser um índice de leitura (lista + link para cada arquivo), deixando de ser a fonte primária do conteúdo de cada ADR — mantendo seu valor como o companion navegável do Blueprint aprovado, sem duplicar o conteúdo que passaria a viver nos arquivos individuais.
5. **Doravante:** toda nova decisão arquitetural do V2 nasce diretamente como arquivo em `docs/architecture/adr/`, nunca como entrada nova em `Architecture-Decision-Log.html`.

## Fora deste plano

Nenhuma decisão sobre RBAC, schema, ou qualquer conteúdo técnico dos ADRs é revisitada — este plano trata exclusivamente de **onde e como** os ADRs são armazenados, não do que decidem.
