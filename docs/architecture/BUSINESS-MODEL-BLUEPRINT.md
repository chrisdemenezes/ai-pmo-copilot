# Business Model Blueprint — Wave 6 (Productization)

**Wave:** 6 (Enterprise Master Execution Program)
**Status:** **Não é um Blueprint de arquitetura técnica.** É um documento de elicitação de decisão — nomeia exatamente as perguntas de modelo de negócio que precisam ser respondidas pelo Founder antes que qualquer arquitetura de Productization possa existir.

---

## 1. Por que este documento não define Licenciamento, SaaS, Planos, Billing, Marketplace, White Label, Feature Flags, Enterprise/Community Edition

A instrução desta missão foi explícita: **"Não preencha lacunas com suposições."** Aplicando essa regra com o mesmo rigor usado nos outros 4 Blueprints desta missão, a conclusão é a seguinte:

Todos os documentos fundacionais da STRATECH revisados nesta e nas missões anteriores — Product Constitution (V1), Enterprise Architecture Blueprint v2.0, Master Roadmap, todos os Decision Logs (D-001 a D-030), todos os ADRs (V2-001 a V2-009) — descrevem a STRATECH **exclusivamente como uma plataforma de PMO**, evoluindo de single-tenant (V1) para multi-organização (V2). **Em nenhum lugar, em nenhum documento aprovado, a STRATECH é descrita como um produto comercial vendido a múltiplos clientes externos com cobrança.** "Multi-tenant" na STRATECH, até hoje, significa "isolamento de dados entre organizações dentro de uma mesma instalação" (Épico 1) — não "modelo de negócio SaaS com planos e billing".

Escrever um Business Model Blueprint com Licenciamento/Planos/Billing/Marketplace/White Label/Enterprise-vs-Community Edition definidos exigiria **inventar uma estratégia comercial inteira** que nenhum documento autorizou, incluindo decisões que não são arquiteturais (são de negócio, de precificação, de estrutura legal, de go-to-market) e que pertencem exclusivamente ao Founder. Fazer isso violaria diretamente a instrução desta missão e o princípio "não alterar o domínio de negócio" já estabelecido na missão anterior (Enterprise Master Execution Program §0).

**Este documento, portanto, não é um Blueprint de arquitetura — é o formulário de perguntas que precede um.**

## 2. As perguntas que precisam ser respondidas antes de qualquer arquitetura de Productization

Nenhuma destas perguntas tem resposta hoje em nenhum documento da STRATECH:

1. **A STRATECH se torna um produto comercial vendido a múltiplos clientes externos, ou permanece uma plataforma interna/de cliente único licenciada por instalação?** Toda a arquitetura de Wave 6 depende desta resposta antes de qualquer outra.
2. **Se comercial: qual a unidade de cobrança?** Por organização, por usuário, por uso (ex.: chamadas de IA), por módulo/Capability? Nenhum indício em nenhum documento.
3. **Existe uma edição gratuita/open-source (Community Edition)?** Se sim, qual a fronteira exata entre o que é gratuito e o que é pago — Product Constitution não faz essa distinção hoje (V1 não tinha conceito de edição alguma).
4. **White Label é para revendedores/parceiros, ou para clientes finais rotularem a própria instância?** São arquiteturas muito diferentes (multi-tenant com tema por organização vs. builds/distribuições separadas).
5. **Marketplace de quê?** Não há hoje conceito de "extensão"/"plugin"/"conector de terceiros" instalável na STRATECH — Integration Hub (Wave 4, já aprovado) é sobre a STRATECH se conectar a sistemas externos, não sobre terceiros publicarem extensões para a STRATECH. Um Marketplace pressupõe o segundo conceito, que não existe em nenhum Blueprint.
6. **Feature Flags — para qual finalidade?** Rollout gradual de features (prática de engenharia, ortogonal a modelo de negócio) é uma coisa; gating de features por plano pago (prática comercial) é outra. A missão lista "Feature Flags" dentro de "Business Model", sugerindo a segunda — mas isso só faz sentido depois que "Planos" (pergunta 2) existir.
7. **Se a resposta à pergunta 1 for "não" (a STRATECH não vira produto comercial multi-cliente):** então Licensing/Billing/Marketplace/White Label/Subscription não são necessários **nunca**, e a Wave 6 deveria ser removida do Enterprise Master Execution Program, não apenas adiada. Este documento não presume que a resposta é "sim".

## 3. O que é seguro afirmar hoje, sem depender dessas respostas

| Item | Situação |
|---|---|
| **Versioning, Release Management** | ✅ Já existe como processo de engenharia (EO→ADR→Architecture Review→PR→merge, LL-002) — independente da resposta às perguntas de negócio acima. Não faz parte da lacuna. |
| **Multi-tenancy (isolamento de dados)** | ✅ Já existe (Épico 1) e continua existindo de qualquer forma, independente do modelo de negócio — é uma decisão de arquitetura técnica já tomada, não uma decisão comercial. |
| Todo o resto desta Wave | ❌ Não planejável até a Seção 2 ser respondida. |

## 4. Recomendação

**Não produzir nenhuma arquitetura de Productization até o Founder responder às 7 perguntas da Seção 2.** Nenhuma suposição foi usada para preencher esta lacuna, conforme a instrução explícita da missão. Recomenda-se que a Wave 6 permaneça no Enterprise Master Execution Program como um placeholder nomeado (não removida, porque a decisão de removê-la também pertence ao Founder), mas **explicitamente fora do escopo de qualquer Architecture Freeze** — ver Seção final deste conjunto de Blueprints.

---

## 5. Fundamentado vs. depende do Founder vs. exige definição arquitetural

| Fundamentado | Depende do Founder (decisão de negócio, não de arquitetura) | Exige definição arquitetural |
|---|---|---|
| Versioning/Release Management (já existe) | As 7 perguntas da Seção 2, todas | Nenhuma — não há o que desenhar antes das perguntas serem respondidas |
| Multi-tenancy técnico (já existe, independente do modelo comercial) | | |
