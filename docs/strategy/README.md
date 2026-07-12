# STRATECH Strategy

Esta pasta representa a **estratégia permanente da STRATECH** — o segundo
ativo estratégico da empresa, ao lado do código. Não é documentação técnica.

## Por que esta área existe, separada das demais

`docs/` já possui `architecture/`, `engineering/` (implícito em
`technical/`, `development/`), `product/` e `releases/`. Essas pastas
documentam **como a plataforma é construída** e **o que foi entregue em
cada incremento** — elas mudam a cada Feature, a cada TIP, a cada release.

`docs/strategy/` documenta algo diferente: **por que a STRATECH existe e
para onde ela vai.** Isso não muda a cada Feature. Uma Feature pode (e
deve) ser cancelada, adiada ou redesenhada se contradizer o que está aqui —
o inverso nunca acontece. Por isso a separação é estrutural, não
cosmética: misturar as duas coisas na mesma pasta faria a estratégia
parecer tão descartável quanto um TIP, e um TIP parecer tão permanente
quanto a Constitution.

## Por que esta pasta NÃO é documentação técnica

Nada aqui descreve como o sistema funciona, qual endpoint faz o quê, ou
como uma Feature foi implementada — isso é o papel de `architecture/`,
`technical/` e `product/`. Esta pasta descreve **decisões que uma
implementação técnica deve obedecer, nunca decisões que uma implementação
técnica produz.** Nenhum TIP, Executive Progress Report ou Visual Fidelity
Report pertence aqui, mesmo que fale sobre estratégia de produto — o lugar
desses artefatos continua sendo `docs/product/<feature>/`.

## Estrutura

| Diretório | Objetivo |
|---|---|
| `00-product-constitution/` | Os princípios inegociáveis da STRATECH — o nível mais alto, do qual tudo abaixo deriva. Muda com a menor frequência de toda a árvore. |
| `01-product-vision/` | Para onde a STRATECH está indo — o futuro desejado do produto. Deriva da Constitution; não pode contradizê-la. |
| `02-product-principles/` | Princípios operacionais de decisão de produto no dia a dia — mais táticos que a Constitution, mas ainda estratégicos, não técnicos. |
| `03-decision-framework/` | Como as decisões são tomadas — os critérios que operacionalizam Constitution, Vision e Principles em julgamentos concretos (inclui as perguntas do papel de Guardian). |
| `04-capability-map/` | O que a plataforma deve ser capaz de fazer, derivado da Vision — a ponte entre estratégia e produto real, sem descrever implementação. |
| `05-roadmap/` | Sequenciamento no tempo do Capability Map — quando, não como. |
| `06-market/` | Contexto externo: mercado, concorrência, posicionamento competitivo. Input para as decisões acima, não normativo por si só. |
| `07-brand/` | Identidade e voz da STRATECH como empresa — diferente da Baseline Visual do produto, que é um artefato técnico em `product/`. |
| `08-research/` | Pesquisa e evidência (usuário, mercado, validação) que sustenta as decisões registradas nos diretórios acima. |

## Como os documentos se relacionam

```
00-product-constitution   (o que é inegociável)
        │
        ▼
01-product-vision         (para onde vamos)
        │
        ▼
02-product-principles     (como decidimos no dia a dia)
        │
        ▼
03-decision-framework     (o critério formal de decisão)
        │
        ▼
04-capability-map         (o que a plataforma deve fazer)
        │
        ▼
05-roadmap                (quando)
```

`06-market/`, `07-brand/` e `08-research/` não fazem parte dessa cadeia de
derivação vertical — são **insumos horizontais**: alimentam qualquer nível
acima com contexto e evidência, mas não têm autoridade normativa própria.
Um documento em `08-research/` pode motivar uma mudança na Vision; ele não
substitui a Vision.

Em caso de conflito aparente entre dois documentos, o de nível mais alto
nesta cadeia prevalece. Um conflito entre a Vision e o Roadmap é resolvido
a favor da Vision — o Roadmap é corrigido, nunca o contrário.

## Quem pode alterar o quê

- **Founder**: única autoridade que aprova alterações de conteúdo em
  qualquer diretório desta pasta. Nenhuma exceção.
- **Chief Software Architect / Product Guardian**: mantém a estrutura,
  garante que Features não violem o que está aqui, e redige propostas de
  alteração — mas não aprova as próprias propostas.
- **Qualquer Feature, TIP ou automação**: leitura apenas. Nenhuma Feature
  altera esta pasta como efeito colateral de sua implementação, mesmo que
  a mudança pareça óbvia ou pequena.

## Regra permanente

`docs/strategy/` não representa código. Representa decisões permanentes da
empresa. Toda alteração de conteúdo depende de aprovação explícita do
Founder, registrada na própria alteração — nunca implícita, nunca
inferida a partir de uma Feature aprovada em outro contexto.

## Papel de Guardian

Antes de iniciar qualquer Feature, o Guardian verifica:

1. Existe algum princípio da Strategy afetado?
2. Existe conflito com a Product Constitution?
3. Existe conflito com a Product Vision?
4. Existe conflito com o Decision Framework?
5. A Feature melhora alguma decisão do usuário?

Se qualquer resposta for negativa: **interromper, explicar, aguardar
decisão.** Este checklist é normativo assim que os documentos referenciados
existirem — até lá, serve como lembrete de que ele se aplicará.

## Estado atual

Todos os diretórios estão vazios, propositalmente. A estrutura foi criada
antes do conteúdo por decisão do Founder — Product Constitution, Vision,
Roadmap, Decision Framework e Capability Map serão escritos junto ao
Founder, não unilateralmente.
