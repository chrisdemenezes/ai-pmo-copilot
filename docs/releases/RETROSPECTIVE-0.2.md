# Retrospective — Release 0.2 (FS-001 — Dashboard Executivo)

Consolidação obrigatória do ciclo de governança AI-PEF para a Release 0.2, autorizada pelo Product
Owner após o Release Review e o Release Decision Record (`docs/releases/RDR-0.2.md`). Não inicia
nenhuma implementação de Release 0.3.

## 1. O que funcionou bem

- **Sequência de portões do AI-PEF percorrida integralmente**, sem pular etapa: Product Review →
  Architecture Review → UX Review → Feature Specification → Technical Implementation Plan →
  Product Owner Approval → Implementação (T1–T9) → Documentação (T10) → Code Review → QA Review →
  Release Review → RDR.
- **Nenhuma capacidade inventada.** Toda afirmação técnica foi verificada contra código real antes
  de ser usada — inclusive a mudança `middleware.ts`→`proxy.ts` do Next.js 16, confirmada em
  `node_modules/next/dist/docs` antes de qualquer linha de código, evitando um erro de
  implementação inteiramente evitável.
- **Achados reais encontrados por 3 mecanismos independentes**, não só testes automatizados:
  revisão de código (Principal Reviewer encontrou o bug de stale-while-revalidate), inspeção visual
  manual em navegador real (QA Review encontrou a inconsistência de rótulo que nenhuma asserção
  automatizada capturaria), e medição empírica (o custo real do retry padrão do TanStack Query só
  ficou claro com números reais, não suposição).
- **Product Hypothesis (ADR-010)** resolveu um defeito estrutural real do próprio framework —
  Product Review, como definido originalmente, era impossível de passar para qualquer Feature
  pré-lançamento — sem enfraquecer o rigor exigido.
- **Push-back bem-sucedido contra escopo prematuro** (ADR-009): a expansão do AI-PEF para 10
  módulos foi recusada por falta de evidência real de uso, evitando dívida de processo.
- **Nenhum status de CI foi presumido** — toda alegação de "verde" neste ciclo foi confirmada
  chamando a API do GitHub Actions diretamente, nunca apenas assumida a partir do push.

## 2. O que não funcionou

- **Atividades estratégicas paralelas (Brand Discovery, Brand Foundation, Direção Visual,
  Executive Resolution da Stratech) interromperam repetidamente o fluxo de implementação.** Mesmo
  quando formalmente não-bloqueantes, fragmentaram o contexto e exigiram pausar/retomar T1–T9
  várias vezes.
- **A ordem dos portões do próprio AI-PEF mudou mais de uma vez ao longo do ciclo** (Product Review
  antes vs. depois de Architecture Review, em momentos diferentes) — sinal de que a v1.0 do
  framework ainda não estava madura antes de ser aplicada à primeira Feature real.
- **A restrição de permissão para criar tags Git só foi descoberta na hora de usá-la**, não
  verificada com antecedência — pendência operacional evitável.
- **O achado de segurança mais sério (Achado #1) só apareceu no Code Review**, não em nenhuma etapa
  anterior — TIP-001 não continha nenhum item explícito de checklist de segurança para rotas de
  autenticação/sessão.
- **O comportamento de retry do TanStack Query nunca foi considerado em nenhum artefato de
  arquitetura antes da implementação** — um gap de especificação (RFC-001/FS-001), não apenas de
  código.

## 3. Achados por etapa e papel

| Etapa | Papel | Achado |
|---|---|---|
| Product Review | Chief Product Officer Advisor | 2 de 5 perguntas sem métrica histórica — resolvido via Product Hypothesis (ADR-010) |
| Architecture Review | Chief Product Architect | Technical Adaptation: `middleware.ts`→`proxy.ts` (Next.js 16) |
| UX Review | Principal UX Architect | 4 ajustes de layout, decisão de escopo de W3–W5, rótulo/tooltip de "Riscos identificados" |
| Implementação (T8) | Principal Software Engineer | Kill switch prometido em TIP-001 §7 estava ausente — implementado ao ser descoberto |
| Implementação (T8, achado por Reviewer) | Principal Reviewer | Dashboard descartava dado válido em falha de poll em background |
| Code Review | Principal Reviewer | 5 achados — 1 Alto (segurança, sem rate limiting no login), 3 Médio/Baixo (defesa em profundidade, validação de schema, exceção não tratada), 1 já conhecido |
| QA Review | Product Quality Architect | Inconsistência de rótulo de status entre widgets (só visível por inspeção manual) |

## 4. Decisões tomadas com base em evidência

- **ADR-009** (framework evolutivo) — nenhum ciclo completo real existia antes do pedido de
  expansão do AI-PEF; decisão de reter a expansão até haver evidência.
- **ADR-010** (Product Hypothesis) — impossibilidade lógica de métrica histórica pré-lançamento.
- **`retry: false`** — medição empírica real (7,9s/40,2s com retry padrão vs. 0,7s/8,9s sem).
- **Aceitação de risco do Achado #1** — decisão explícita e escopada (interno/piloto), não omissão;
  registrada com condição obrigatória para a próxima Release.

## 5. Desvios entre documentação e implementação

- FS-001 §9/§16 continuaram descrevendo a sessão Nível 1 e a rota BFF como "não implementada"/"a
  construir" muito depois de ambas estarem prontas — só corrigido na Revisão 5 (T10). Desvio de
  rastreabilidade, não de comportamento real do sistema.
- TIP-001 §7 (rollback) prometia um kill switch de emergência que não existia até T8 — a lacuna
  entre o que o plano afirmava e o que o código continha só foi fechada no Mid Sprint Review.

## 6. Eficácia dos gates do AI-PEF

| Portão | Eficácia |
|---|---|
| Product Review | Seria ineficaz sem ADR-010; hoje eficaz |
| Architecture Review / UX Review | Eficazes — geraram decisões reais, não formalidades vazias |
| Technical Implementation Plan | Parcialmente eficaz — não antecipou o achado de segurança nem a lacuna do kill switch |
| Code Review | Muito eficaz — encontrou o único achado crítico que nenhum portão anterior capturou |
| QA Review | Eficaz — validação manual encontrou o que asserção automatizada não captura |
| RDR (não previsto na v1.0 original, sugerido durante este ciclo) | Eficaz — deve ser formalizado |

## 7. Melhorias obrigatórias para a Release 0.3

1. Mitigação do Achado #1 (rate limiting de login) — já é condição obrigatória do RDR-0.2, não uma
   melhoria opcional.
2. TIP deve incluir, a partir de agora, um item explícito de checklist de segurança para qualquer
   Feature que envolva rota de autenticação/sessão — não descoberto ad-hoc em Code Review.
3. Criar a tag `v0.2` manualmente (pendência operacional já registrada).

## 8. Riscos aceitos e condições de encerramento

- **Achado #1 (Segurança, Alto):** aceito exclusivamente para uso interno/piloto controlado da
  Stratech. Não se estende a produção pública ou clientes externos. Condição de encerramento:
  mitigação completa (rate limiting, limitação por IP, janela configurável, testes,
  documentação) antes de qualquer ambiente além desse escopo.
- **4 achados de backlog técnico não-bloqueantes:** defesa em profundidade da rota BFF, validação
  de schema em runtime, exceção não tratada quando `SESSION_SECRET` está ausente, `aria-live`
  ausente — nenhum bloqueia a Release 0.2.
- **Suíte E2E não integrada ao CI oficial:** backlog técnico da próxima Release, não bloqueante
  para FS-001 (decisão já registrada).

## 9. Plano de ações priorizado

| Ação | Responsável | Prioridade | Prazo |
|---|---|---|---|
| Mitigar Achado #1 (rate limiting no login) | Principal Software Engineer | **Crítica** | Antes de qualquer deploy além de interno/piloto |
| Criar a tag `v0.2` manualmente no GitHub | Product Owner | Baixa | Pendência operacional, sem prazo definido |
| Integrar a suíte E2E ao GitHub Actions CI | Principal Software Engineer | Média | Release 0.3 |
| Adicionar checklist de segurança ao template de TIP do AI-PEF | Chief Product Architect | Média | Antes do início de FS-002 |
| Formalizar o RDR como portão oficial do AI-PEF | Chief Product Architect | Média | Antes do início de FS-002 |
| Resolver os 4 achados de backlog técnico do Code Review | Principal Software Engineer | Baixa | Release 0.3 ou posterior |

## 10. Recomendação objetiva sobre ajustes no AI-PEF

**Incorporar ao processo:**
- **Release Decision Record como portão oficial** (após Release Review, antes de Retrospective) —
  validado nesta release por uso real, não especulação; template já existe (`RDR-0.2.md`).
- **Checklist mínimo de segurança no template de TIP**, aplicável a qualquer Feature que crie rota
  de autenticação, sessão ou credencial — o achado mais sério desta release só foi pego por um
  Code Review cuidadoso, não por processo que garantisse isso.

**Não incorporar ao processo agora:**
- A expansão do AI-PEF para os 10 módulos propostos anteriormente (Governança de IA, Checklists
  genéricos de compliance, taxonomia completa de Knowledge Base, papéis adicionais como Security
  Architect) — permanece sem evidência real de necessidade além desta única release. ADR-009
  continua válido: nenhum desses itens é promovido sem um ciclo real que o exija.
- Um portão formal separado de "Security Review", distinto de Code Review — considerado, mas sem
  evidência suficiente (1 achado em 1 release) para justificar um novo portão dedicado ainda; manter
  como recomendação a observar, não decisão.

## Addendum — atualização do AI-PEF executada (ADR-011)

Após aprovação desta Retrospective, o Product Owner autorizou uma atualização restrita do AI-PEF
com origem exclusiva nesta seção 10 — nenhuma mudança adicional. Executada como **ADR-011**:
checklist de segurança condicional adicionado ao Template de Technical Implementation Plan; Release
Decision Record formalizado como critério de saída obrigatório do Portão 10 (Release Review) já
existente — sem gate novo, sem papel novo. AI-PEF agora versionado em
`docs/product/ai-pef/AI-PEF.html` (v1.1), commit `16d84f1`, primeira vez que o framework entra em
controle de versão do repositório.
