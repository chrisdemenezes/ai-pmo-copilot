# Domain Blueprint — Enterprise Administration

**Wave:** 2 (Enterprise Master Execution Program)
**Status:** Blueprint conceitual — não implementa, não produz código.
**Precondição:** resolve o conflito identificado em `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §9 (Decision Proposal — Enterprise Administration: escopo mínimo vs. completo), ainda pendente de decisão do Founder.

**Regra seguida neste documento:** este Blueprint produz uma **recomendação arquitetural fundamentada**, per o pedido explícito da missão — mas uma recomendação não é uma decisão aprovada. Como o escopo "mínimo" (Épico 5, Release 0.1) já foi formalmente aprovado via EO-016/EO-016A e qualquer expansão dele é, por definição, uma mudança de decisão já aprovada, esta recomendação **permanece um Decision Proposal até ratificação do Founder** — não é aplicada a este documento como fato consolidado.

---

## 0. Correção de escopo — API Keys (D-051, substitui a classificação da Seção 2)

**O Founder emitiu uma decisão arquitetural permanente e retroativa**: uma dependência arquitetural nunca autoriza deixar um Epic previsto pendente; quando uma dependência é encontrada, a resposta é revisar a arquitetura e eliminá-la se for artificial, não esperar por uma decisão futura que ainda não existe. Especificamente sobre API Keys, o Founder determinou o princípio permanente: **componente fundamental nunca pode depender de componente futuro; o inverso (componente futuro consumindo um fundamental) é sempre permitido.**

Sob esse princípio, a classificação original da Seção 2 (API Keys = Nível 3, "pertence à decisão de Integration Hub, Wave 4") está **incorreta** e é revogada por esta seção. O raciocínio original invertia a relação de dependência: nada em "uma organização emite e revoga credenciais de API para autenticar chamadas em nome de um usuário já existente" depende de a STRATECH ter (ou vir a ter) um Integration Hub. É o oposto — um futuro Integration Hub, se e quando existir, seria apenas mais um **consumidor** de uma capacidade de API Keys que já existe hoje, exatamente como qualquer outra rota autenticada.

**Reclassificação: API Keys passa de Nível 3 para Nível 1** (mesmo nível de Usuários/Organizações/Papéis/Auditoria — schema e infraestrutura de autenticação já existentes reaproveitados integralmente, nenhum conceito de domínio novo):

| Sub-área | Nível (revisado) | Grounding | Recomendação |
|---|---|---|---|
| **API Keys** | **1 — fundamental, sem dependência de Integration Hub** | A chave de API autentica **como o usuário que a criou** — reaproveita 100% do RBAC/auditoria já existentes (`AuthenticatedUser`, `require_permission`, `record_audit`); o hashing reaproveita `Argon2PasswordHasher`, já usado para senhas. Nenhum modelo de permissão novo, nenhum provider novo, nenhum registry novo. | Implementar imediatamente como extensão do Épico 5 (Enterprise Administration), não como parte do Integration Hub. Um futuro Integration Hub (Wave 4) consome esta capacidade — não a inversa. |

Isso não reabre nem reclassifica as demais linhas Nível 3 (Workspaces administrativos, Tenant/System Settings) — cada uma delas depende de uma decisão de produto/nome ainda não tomada (colisão de nome com o Workspace de produto; modelo de negócio multi-tenant), o que é uma dependência real de decisão, não uma dependência arquitetural artificial como a que existia para API Keys. A distinção que o Founder traçou é exatamente essa: uma dependência é ilegítima quando é **apenas o resultado de uma decisão arquitetural anterior** (o caso de API Keys); continua legítima quando depende de uma **decisão de produto ainda não tomada** por ninguém, em nenhum documento.

Implementação completa desta correção: ver `AR-4-API-KEYS-REVIEW.md`, `TECHNICAL-DESIGN-API-KEYS.md` e Decision Log D-051.

---

## 0.1 Correção de escopo — Configurações da Organização vs. Tenant/System Settings (D-052)

**Auditoria realizada:** per o mesmo rigor exigido para API Keys, antes de reclassificar o item "Tenant/System Settings" da fila de fechamento (`WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md` §6, item 4), foi feita uma busca exaustiva em **todo** o repositório — todos os Domain Blueprints, Technical Designs, o Business Model Blueprint, Mission Control, Decision Log, CHANGELOG, backlog e roadmap oficiais, código-fonte de `src/` e `web/` — pela pergunta: existe, em algum documento oficial, uma definição concreta do que "Configurações da Organização" deveria conter (idioma, fuso horário, branding, preferências de notificação, comportamentos padrão, configuração regional, feature flags, etc.)?

**Resultado: não existe nenhuma.** Toda ocorrência do termo no repositório é (a) um rótulo solto em uma lista de sub-áreas administrativas, ou (b) uma afirmação explícita de que o escopo ainda não foi definido — a própria linha 50 desta tabela já dizia isso ("o escopo exato — 'configurações de quê?' — precisa de definição de produto antes de Technical Design"); `src/api/routes/administration.py` e `src/database/administration_repository.py` já documentam essa mesma ausência em seus próprios docstrings. Nenhum campo concreto (idioma, timezone, branding, notificação, papel padrão, feature flag) é nomeado em nenhum lugar. O modelo `Organization` (`src/database/models.py`) não tem nenhuma coluna de configuração — só `id`, `name`, `slug`, `created_at`.

**Distinção formal entre dois conceitos que vinham sendo tratados como um só:**

1. **Configurações da Organização** (preferências funcionais do domínio Enterprise Administration) — **sem bloqueio arquitetural e sem bloqueio de modelo de negócio.** O único obstáculo real é a ausência total de um requisito funcional documentado. Implementá-la agora exigiria inventar comportamento de produto (que preferências existem, o que cada uma faz) — proibido pela mesma regra já aplicada em `BUSINESS-MODEL-BLUEPRINT.md` ("não preencha lacunas com suposições"). Uma melhoria de infraestrutura adjacente (ex.: tornar o rate limiting por organização) foi avaliada e **rejeitada explicitamente como suficiente para fechar este item** — é uma melhoria de plataforma, não uma funcionalidade de "Configurações da Organização", e usá-la para encerrar o item violaria a proibição de "usar melhorias de infraestrutura apenas para justificar o encerramento de um Epic".
2. **Tenant/System Settings** (modelo comercial SaaS — planos, billing, configuração isolada por cliente-tenant pagante) — permanece **genuinamente bloqueado**, mas por uma razão diferente de qualquer dependência arquitetural: depende de uma decisão de negócio ainda não tomada por ninguém, em nenhum documento (`BUSINESS-MODEL-BLUEPRINT.md` §2, perguntas 1-7, todas sem resposta). Esta não é uma dependência arquitetural artificial eliminável pelo princípio permanente do D-051 — é uma decisão comercial real, que nenhuma Architecture Review pode substituir.

**Reclassificação formal (substitui as linhas correspondentes da Seção 2):**

| Sub-área | Status formal | Justificativa |
|---|---|---|
| **Configurações da Organização** | **Sem Escopo Funcional Definido** | Nenhum documento oficial (Blueprint, Technical Design, Decision Log, Executive Report, backlog, roadmap) especifica qualquer preferência/campo concreto. Não é um bloqueio de arquitetura nem de modelo de negócio — é ausência de requisito de produto. Permanece fora de escopo até o Founder definir concretamente o que deve conter; não deve ser preenchido com suposições nem com melhorias de infraestrutura reaproveitadas como substituto. |
| **Tenant/System Settings** | **Pendente de Decisão de Negócio (Wave 6 — Business Model Blueprint)** | Depende inteiramente das 7 perguntas sem resposta de `BUSINESS-MODEL-BLUEPRINT.md` §2 — decisão de negócio do Founder, não uma dependência arquitetural corrigível. |

Registrado formalmente em Decision Log D-052. Item 4 do Wave Completion Review retrospectivo fecha como **Governança Concluída** (auditoria completa, escopo esclarecido e documentado), não como Implementado — não há requisito funcional a implementar até que um dos dois status acima mude por decisão do Founder.

---

## 1. O conflito, resumido

| | Escopo aprovado (Épico 5, Release 0.1) | Escopo pedido por esta missão |
|---|---|---|
| Auditoria | Log de mutações de Org/User/Role/Project | Auditoria + Logs + Health como áreas próprias |
| Telas administrativas | Mínimas, sob item de navegação "Administração" | Usuários, Organizações, Workspaces, Convites, Sessões, API Keys, Configurações, Segurança, Tenant Settings, System Settings — 13 sub-áreas |

## 2. Recomendação arquitetural

**Recomendação: faseamento em 3 níveis, não uma dicotomia mínima-vs-completa.** As 13 sub-áreas pedidas não têm todas o mesmo grau de risco/novidade — tratá-las como um bloco único ("completa") força a mesma decisão de escopo para itens que já têm schema pronto (Usuários) e itens que não existem em nenhuma forma na STRATECH hoje (Workspaces multi-organização, API Keys, Tenant/System Settings). A tabela abaixo classifica cada uma:

| Sub-área | Nível | Grounding hoje | Recomendação |
|---|---|---|---|
| **Usuários** | 1 — já aprovado | Schema completo desde Épico 1 (`users`); tela é só CRUD sobre o que já existe | Incluir no Épico 5 como estava aprovado |
| **Organizações** | 1 — já aprovado | Schema completo desde Épico 1 (`organizations`) | Incluir no Épico 5 como estava aprovado |
| **Papéis (Roles/Permissions)** | 1 — já aprovado, dependente do RBAC Blueprint | Schema existe; UI de atribuição depende de RBAC estar aplicado (Wave 2/Épico 3) primeiro | Incluir no Épico 5, sequenciado após RBAC (`DOMAIN-BLUEPRINT-RBAC.md`) |
| **Auditoria (log de mutações)** | 1 — já aprovado | Era o núcleo do Épico 5 original | Incluir como estava aprovado |
| **Sessões (visualização/revogação)** | **Implementado (D-053 — resolve TD-010)** | Corrigido: o store server-side que o Blueprint assumia existir **não existia** (a sessão era um cookie HMAC stateless). Item 5 do Wave Completion Review adicionou a tabela `sessions`, o `session_id` cunhado pelo backend no login, e o enforcement de revogação em `require_permission`. Ver `TECHNICAL-DESIGN-SESSIONS.md`. | Concluído — listagem/revogação reais em `/administracao/sessoes`. |
| **Segurança (política de senha, MFA se aplicável)** | 2 — extensão natural | Argon2/`AuthService` já existem; painel de configuração de política é extensão, não conceito novo | Extensão recomendada, escopo exato a definir em Technical Design |
| **Logs (visualização, não só auditoria de mutação)** | 2 — extensão natural | Logging já existe (`logger.info` em todas as rotas) mas não é agregado nem exposto em UI | Extensão recomendada — agregação de log estruturado, não um sistema de logging novo |
| **Health (status da aplicação)** | 2 — extensão natural, baixo custo | Não existe hoje; é um endpoint de baixo risco (`/health`) comum em qualquer API | Extensão recomendada — implementação trivial, sem impacto em domínio |
| **Configurações (preferências por organização)** | **Sem Escopo Funcional Definido (D-052 — ver §0.1)** | Auditoria exaustiva do repositório (D-052) confirmou: nenhum documento oficial especifica qualquer preferência/campo concreto | Não implementar até o Founder definir o conteúdo concreto — não preencher com suposições nem com melhorias de infraestrutura (ex.: rate limit por organização) usadas como substituto |
| **Workspaces (administração de múltiplos workspaces por organização)** | 3 — conflito de nome, decisão de domínio nova | ⚠️ "Workspace" já é um termo de produto **diferente** — a página `/workspace/{project}` da V1/RC-1 (um workspace por projeto, não um conceito administrável). Introduzir "Workspaces" como unidade administrativa colidiria com esse termo já em produção. | **Não recomendado sem antes resolver a colisão de nome.** Se a necessidade real é "agrupar usuários/projetos sob uma sub-unidade da organização", isso já tem candidato natural no Domain Map (Program/Portfolio, Wave 2) — recomenda-se avaliar se "Workspaces administrativos" não é apenas RBAC com Organization Scope mais granular (Program-level), não uma entidade nova. |
| **Convites** | 3 — não existe, mas já estava no Blueprint v2.0 (Release 0.2, "Convites e Stakeholders") | Zero implementação hoje; mas **já é escopo aprovado** para Release 0.2/Wave 2, só não fechado como Épico ainda | Recomendado incluir — mas como extensão do que já está no Master Roadmap §3.2, não como invenção nova desta missão |
| **API Keys** | 3 — não existe, sem precedente | Nenhuma menção prévia em nenhum Blueprint/ADR. A STRATECH não expõe hoje nenhuma API para consumo de terceiros autenticado por chave — a única autenticação de API é `X-API-Key` do próprio backend para o BFF (`verify_api_key`), um segredo de infraestrutura, não uma feature de produto | **Não recomendado agora.** Requer decisão de produto (a STRATECH expõe API pública para integrações de clientes?) antes de qualquer Technical Design — relacionado à Wave 4 (Integration Hub), não a Administration. |
| **Tenant Settings / System Settings** | **Pendente de Decisão de Negócio (D-052 — ver §0.1)** | Depende inteiramente das 7 perguntas sem resposta de `BUSINESS-MODEL-BLUEPRINT.md` §2 — decisão comercial do Founder, não uma dependência arquitetural corrigível | Aguarda decisão de modelo de negócio (Wave 6); se a resposta for "a STRATECH nunca se torna produto multi-cliente comercial", este item deixa de existir como conceito, não apenas fica adiado. |

## 3. Recomendação consolidada

1. **Nível 1** (Usuários, Organizações, Papéis, Auditoria) — é exatamente o Épico 5 já aprovado. Nenhuma mudança de escopo necessária; prosseguir como estava.
2. **Nível 2** (Sessões, Segurança, Logs, Health, Configurações) — extensão de baixo risco sobre o que já existe; recomenda-se aprovar como ampliação do Épico 5, formalizada por um Decision Proposal simples (não um novo Épico), já que nenhuma delas introduz um conceito de domínio novo.
3. **Nível 3** (Workspaces administrativos, API Keys, Tenant/System Settings) — **não recomendado neste momento.** Cada um depende de uma decisão anterior que ainda não foi tomada: Workspaces precisa resolver a colisão de nome com o Workspace de produto já existente; API Keys pertence à decisão de Integration Hub (Wave 4); Tenant/System Settings depende inteiramente da decisão de modelo de negócio (Wave 6, `BUSINESS-MODEL-BLUEPRINT.md`).
4. **Convites** fica fora dos 3 níveis acima porque já tem outro lar aprovado (Master Roadmap §3.2, Release 0.2/Wave 2, "Convites e Stakeholders") — não deve ser duplicado dentro do Épico 5/Administration.

**Este documento não decide qual opção da matriz A/B/C do `ENTERPRISE-MASTER-EXECUTION-PROGRAM.md` §9 é adotada — apresenta uma recomendação mais granular (por sub-área, não em bloco) para que o Founder decida com mais precisão do que "mínima vs. completa".**

---

## 4. Fundamentado vs. depende do Founder vs. exige definição arquitetural

| Fundamentado (pode virar Technical Design assim que ratificado) | Depende do Founder (Decision Proposal) | Exige definição arquitetural antes de qualquer decisão |
|---|---|---|
| Nível 1 completo (schema já existe) | Adotar Nível 2 como extensão do Épico 5 | Workspaces administrativos (resolver colisão de nome primeiro) |
| Sequenciamento (RBAC antes de Papéis) | — | API Keys (depende de decisão de Integration Hub) |
| — | — | Tenant/System Settings (depende de Business Model Blueprint) |
