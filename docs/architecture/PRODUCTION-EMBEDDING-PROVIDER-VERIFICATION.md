# Production Embedding Provider — Current Facts Verification

**Autorização:** "Founder Decision — Production Embedding Provider Final Confirmation". `TECHNICAL-DESIGN-PRODUCTION-EMBEDDING-CONTRACT-VECTOR-MIGRATION.md` (D-175) está **APPROVED**, incluindo as 7 decisões arquiteturais nele descritas (contrato `embed(text) -> list[float]` mantido; segundo provider real sem novo registry; dimensão fixa pelo modelo de produção; proveniência mínima; rejeição de zero-padding; troca futura tratada por migration+reembedding; estratégia de cutover do Technical Design). Autorizada exclusivamente uma verificação factual atual, contra documentação oficial dos fornecedores, antes de qualquer registro definitivo do provider. **Nenhum código alterado, nenhuma migration criada, nenhum schema alterado, nenhum staging provisionado, nenhuma credencial usada, nenhuma chamada real às APIs.**

Todos os fatos abaixo vêm de documentação oficial dos fornecedores (`docs.voyageai.com`, `blog.voyageai.com`, `developers.openai.com`/`openai.com`, catálogos oficiais Azure/AWS para Cohere), consultada nesta missão. Fontes completas na seção final.

---

## VOYAGE — CURRENT FACTS

1. **`voyage-multilingual-2` continua disponível?** Sim, ainda listado no catálogo oficial (`docs.voyageai.com/docs/embeddings`) — mas é um modelo de **junho de 2024**, e **não é mais o mais recente nem o mais recomendado** pela própria Voyage AI (achado central, ver item 7).
2. **Dimensionalidade:** fixa em **1024**, sem parâmetro de truncagem/configuração — diferente da geração mais nova (item 7).
3. **Limites de entrada/contexto:** 32.000 tokens.
4. **Suporte multilingual PT/EN:** confirmado — 27 idiomas, incluindo português e inglês explicitamente listados; documentação oficial declara desempenho de retrieval multilíngue superior a "OpenAI v3 large e Cohere multilingual v3" (comparação feita pelo próprio fornecedor, citada aqui como declaração de marketing, não validação independente).
5. **Política de tratamento/retenção de dados (API hospedada pela Voyage):** clientes podem optar por retenção zero-dia (opt-out do uso de dados para treinamento futuro), exigindo conta com forma de pagamento cadastrada e usuário com papel de Admin na organização, alternado manualmente na seção "Terms of Service" do painel da organização. **Achado adicional relevante:** Voyage AI também oferece implantação via **AWS Marketplace e Azure Marketplace**, onde os modelos rodam dentro da própria conta/VPC do cliente — nesse modo, dados declaradamente nunca saem da rede virtual do cliente, endereçando de forma mais forte a preocupação de dados corporativos saindo da infraestrutura própria (opção adicional à recomendação original de D-175, que só considerava a API multi-tenant padrão).
6. **Pricing atual (API padrão, embeddings):** `voyage-multilingual-2` — primeiros 50 milhões de tokens gratuitos por conta, cobrança por token depois (valor exato por token não confirmado nesta busca para este modelo específico legado); `voyage-4` — US$ 0,06/milhão de tokens; `voyage-4-large` — US$ 0,12/milhão de tokens; ambos com os primeiros 200 milhões de tokens gratuitos por conta.
7. **Existência de modelo mais recente/superior:** **Sim, confirmado — achado que altera a recomendação anterior.** A Voyage AI lançou a **família Voyage 4** (`voyage-4`, `voyage-4-large`, `voyage-4-lite`, `voyage-4-nano`) em **15 de janeiro de 2026** — general-purpose e multilíngue (inclui português), dimensão **configurável** (2048/1024/512/256, via Matryoshka representation learning + quantização), mesmos 32.000 tokens de contexto, com "espaço de embedding compartilhado" entre os modelos da própria família Voyage 4 (compatibilidade cruzada declarada entre `voyage-4`/`voyage-4-large`/`voyage-4-lite` — relevante para §7 do Technical Design D-175, potencialmente reduzindo o custo de trocar *entre* variantes da mesma família 4, embora não elimine a necessidade de reembedding ao trocar de geração/provider). Existe ainda um modelo mais novo e mais especializado, **`voyage-context-4`** (29 de junho de 2026) — embeddings contextualizados por chunk com auto-chunking embutido, desempenho declarado ~8,4% superior ao Cohere Embed v4 em benchmarks de retrieval por chunk — mas com um **contrato de API estruturalmente diferente** (processa o documento inteiro e retorna um vetor por chunk, não `embed(um texto) -> um vetor`), o que exigiria redesenhar o pipeline de ingestão além do escopo autorizado nesta missão (manutenção do contrato atual, per D-175). **Não elevado como recomendação agora** — registrado como consideração arquitetural futura, caso a estratégia de chunking da STRATECH seja revisitada.

---

## OPENAI — CURRENT FACTS (verificação sintética)

- **Modelo atual:** `text-embedding-3-large` permanece o modelo mais capaz da OpenAI para embeddings (nenhum modelo mais novo encontrado na documentação oficial consultada).
- **Dimensão:** 3072 nativa, truncável via parâmetro `dimensions` (Matryoshka) — único ponto onde a documentação oficial confirma essa flexibilidade de forma inequívoca desde o lançamento original (achado já presente na análise anterior, D-175, reconfirmado aqui).
- **Contexto:** 8.191 tokens — confirmado, inalterado.
- **Pricing:** US$ 0,13/milhão de tokens (API padrão); US$ 0,065/milhão via Batch API.
- **Conclusão:** continua tecnicamente competitivo, mas sem a vantagem de conta já compartilhada com `LLM_PROVIDER=anthropic` (critério já decisivo na comparação de D-175, inalterado).

---

## COHERE — CURRENT FACTS (verificação sintética)

- **Achado que corrige a análise anterior:** o modelo multilíngue atual da Cohere não é mais `embed-v3` (usado como referência em D-174/D-175) — é **`embed-v4`**, multimodal (texto + imagem), com **1536 dimensões**, também configurável via Matryoshka (256/512/1024/1536).
- **Suporte multilingual:** 100+ idiomas, com desempenho declarado superior em scripts não-latinos (árabe, hindi, japonês, chinês) frente à OpenAI — português/inglês cobertos como parte do suporte geral de 100+ idiomas.
- **Contexto:** 128.000 tokens — maior que Voyage (32K) e OpenAI (8.191).
- **Pricing:** US$ 0,12/milhão de tokens (texto); US$ 0,47/milhão de tokens de imagem.
- **Conclusão:** tecnicamente competitivo e com contexto maior, mas a natureza multimodal do `embed-v4` (otimizado também para imagem/documentos escaneados) é uma capacidade que a STRATECH não tem caso de uso para hoje (`DocumentIngestionService` só aceita texto/markdown, per Technical Design W5-0) — não muda a recomendação, mas é um dado atualizado relevante caso a plataforma amplie para ingestão de PDFs/imagens no futuro.

---

## Impacto sobre a recomendação de D-175

A recomendação original (`voyage-multilingual-2`) está **desatualizada pela própria documentação oficial da Voyage AI** — não por preferência, por evidência: `voyage-multilingual-2` é um modelo de junho de 2024, sucedido por uma geração inteira mais nova (`voyage-4`, janeiro de 2026) que (a) inclui suporte multilíngue equivalente (incl. português), (b) adiciona dimensão configurável (recurso que `voyage-multilingual-2` não tem), e (c) é ativamente promovido pelo próprio fornecedor como a linha atual recomendada para uso geral/multilíngue, com `voyage-multilingual-2` mantido apenas por compatibilidade retroativa. Mantendo a recomendação anterior por inércia seria contrariar exatamente a instrução do Founder.

**Elevado, não decidido silenciosamente:** troca do modelo recomendado dentro do mesmo provider — de `voyage-multilingual-2` para `voyage-4` (ou `voyage-4-large`, se a prioridade for qualidade máxima sobre custo). Isso **não muda a recomendação de provider** (continua Voyage AI, pelas mesmas razões já registradas em D-175 — parceria oficial com a Anthropic), mas muda o modelo exato e, com ele, a dimensão vetorial que deve orientar a migration.

---

## RECOMMENDATION — Voyage / OpenAI / Cohere

**Voyage AI** — recomendação mantida como provider, pelas mesmas razões já registradas em D-175 (parceria oficial reconhecida pela Anthropic, cujo SDK/família de conta já está em uso no código para `LLM_PROVIDER=anthropic`) e reforçada por dois achados novos desta verificação: (1) a geração atual (`voyage-4`) elimina a limitação de dimensão fixa que a comparação original apontava contra Voyage e a favor da OpenAI; (2) a opção de implantação via AWS/Azure Marketplace, com dados nunca saindo da VPC do cliente, endereça de forma mais forte a preocupação de tratamento de dados corporativos do que a recomendação original havia registrado.

## MODEL — modelo exato recomendado

**`voyage-4`** (não `voyage-multilingual-2`) — equilíbrio entre qualidade de retrieval e custo (US$ 0,06/milhão de tokens, 200 milhões de tokens gratuitos por conta), suporte multilíngue incluindo português, dimensão configurável. **`voyage-4-large`** (US$ 0,12/milhão) é a alternativa de maior qualidade, se a prioridade do Founder for precisão máxima acima de custo — ambas as opções permanecem dentro da mesma família/provider, então a escolha entre elas é uma decisão de custo-benefício, não arquitetural.

## VECTOR DIMENSION — dimensão exata que deverá orientar a migration

**1024** — o valor default recomendado pelo próprio fornecedor para `voyage-4`/`voyage-4-large`, equilibrando qualidade de retrieval e custo de armazenamento; consistente com a dimensão que `voyage-multilingual-2` já usava (facilita qualquer comparação futura), e sem necessidade demonstrada de otimizar para 512/256 (economia de armazenamento) ou 2048 (qualidade máxima) na escala atual da STRATECH (nenhum índice ANN existe ainda, per D-175 §3.2 — armazenamento não é uma restrição ativa hoje).

## DATA/DPA — Founder/Legal approval required: **YES**

Mesmo com a opção de retenção zero-dia (API padrão) ou implantação em VPC própria (AWS/Azure Marketplace), o uso de qualquer serviço de terceiro para processar texto de documentos corporativos exige aprovação formal de tratamento de dados/DPA antes de qualquer uso com conteúdo real — decisão de procurement/legal, não arquitetural, não decidida por esta verificação.

## GO/NO-GO — para registrar o provider como decisão definitiva

**NO-GO nesta missão** — per instrução explícita do Founder, o provider não é registrado como aprovado antes do Executive Review. Esta verificação entrega os fatos atuais e eleva a mudança de modelo (`voyage-multilingual-2` → `voyage-4`) para decisão do Founder, junto da aprovação de dados/DPA já pendente desde D-175.

---

## O que não foi feito nesta missão (verbatim das restrições do Founder)

Nenhum código alterado. Nenhuma migration criada. Nenhum schema alterado. Nenhum staging provisionado. Nenhuma credencial utilizada. Nenhuma chamada real às APIs de embedding realizada.

---

## Fontes consultadas

- [Text Embeddings — Voyage AI](https://docs.voyageai.com/docs/embeddings)
- [The Voyage 4 model family: shared embedding space with MoE architecture](https://blog.voyageai.com/2026/01/15/voyage-4/)
- [voyage-context-4: stop worrying about chunking with our best-performing model](https://blog.voyageai.com/2026/06/29/voyage-context-4/)
- [voyage-3-large: the new state-of-the-art general-purpose embedding model](https://blog.voyageai.com/2025/01/07/voyage-3-large/)
- [Pricing — Voyage AI](https://docs.voyageai.com/docs/pricing)
- [FAQ — Voyage AI](https://docs.voyageai.com/docs/faq)
- [Contextualized Chunk Embeddings — Voyage AI](https://docs.voyageai.com/docs/contextualized-chunk-embeddings)
- [text-embedding-3-large Model — OpenAI API](https://developers.openai.com/api/docs/models/text-embedding-3-large)
- [Vector embeddings — OpenAI API](https://developers.openai.com/api/docs/guides/embeddings)
- [New embedding models and API updates — OpenAI](https://openai.com/index/new-embedding-models-and-api-updates/)
- [Cohere Embed v4 — Azure AI Catalog](https://ai.azure.com/catalog/models/embed-v-4-0)
- [Cohere Embed v4 — Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-embed-v4.html)
