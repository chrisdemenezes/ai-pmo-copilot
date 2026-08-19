# Domain Blueprint — Convites (Invitations)

**Wave:** 2 (Enterprise Master Execution Program) — Release 0.2, "Convites e Stakeholders" (`STRATECH_V2_MASTER_ROADMAP.md` §3.2 / §4 / §6).
**Item:** 6 do Wave Completion Review retrospectivo (`WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md` §6).
**Status:** aprovado para Technical Design pela Decisão do Founder (item 6), que forneceu a especificação funcional e separou formalmente domínio de infraestrutura.

---

## 0. Origem da especificação e a separação domínio × infraestrutura

Uma auditoria exaustiva de todos os artefatos oficiais (Product Constitution, Permanent Principles, todos os Domain Blueprints e Technical Designs, Business Model Blueprint, Master Roadmap, Decision Logs, Mission Control, CHANGELOG, backlog) estabeleceu dois fatos:

1. **Convites é escopo aprovado, não especulativo:** "Convites e Stakeholders" consta do Master Roadmap como Release 0.2 / Wave 2, status *Planned / 0%* (`STRATECH_V2_MASTER_ROADMAP.md:185,214,245,279`). O `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md:74,83` confirma esse "lar aprovado" e proíbe duplicá-lo dentro do Épico 5. Sob a Wave Completion Policy (D-048), um item previsto e aprovado é **obrigatório**, não adiável.

2. **Nenhum documento define funcionalmente o Convite nem o acopla intrinsecamente a e-mail.** Todos os atributos que uma especificação normalmente carrega — definição da entidade, atores, estados, expiração, permissões, eventos de auditoria — estavam **NÃO ESPECIFICADOS** em qualquer artefato. A única menção a e-mail é uma **suposição do plano de fechamento** (`WAVE-COMPLETION-REVIEW-RETROSPECTIVE.md:90`: "Precisa de envio de e-mail — nenhuma infraestrutura de e-mail existe hoje; decisão de provedor (SMTP/SES/etc.) é pré-requisito"), que descreve e-mail como o **mecanismo de entrega** ("envio de e-mail", "fluxo de convite por e-mail"), nunca como um constituinte do domínio. Nenhum documento diz "um Convite é um link tokenizado por e-mail". Ao contrário: `TECHNICAL-DESIGN-USER-MANAGEMENT.md:12-13` deliberadamente evitou e-mail/token, tratando-os como capacidade separadamente gated.

**Decisão do Founder (item 6), que esta Blueprint materializa:** o domínio "Convites" é um conceito de domínio; e-mail é um mecanismo de notificação. O domínio **não depende** da existência de um provedor SMTP/SES — apenas o *envio automático* do convite dependeria. Portanto, o domínio é implementado integralmente agora, com uma **abstração de notificação** (`NotificationProvider`) e uma implementação `NoOp` padrão (o seam existe, o provedor concreto não) — nenhum provedor específico é escolhido nem implementado. A especificação funcional (aggregate, token, estados Pendente/Aceito/Expirado/Cancelado, API, RBAC, auditoria, UI administrativa) foi fornecida pela própria Decisão do Founder e é registrada abaixo — não inventada por esta Blueprint.

Esta é a mesma disciplina já aplicada em D-051 (API Keys — dependência arquitetural artificial removida) e no Event Foundation (D-049 — `NoOpEventEmitter`: "o seam existe, o barramento ainda não"). O `NoOpNotificationProvider` é o análogo direto.

---

## 1. Definição

Um **Convite (Invitation)** é uma credencial de onboarding, emitida por um administrador, que autoriza uma pessoa ainda-sem-conta a ingressar numa organização com um papel pré-determinado. É um primitivo fundamental de Enterprise Administration, ao lado de Users/Roles/API Keys/Sessions — não um artefato de um sistema de e-mail.

O Convite carrega um **token** de uso único (segredo), entregável por qualquer canal. Enquanto nenhum provedor de notificação automática existir, o token é devolvido uma única vez na criação (como o `plaintext_key` de uma API Key, D-051) e o administrador o entrega manualmente. Quando um `NotificationProvider` real for plugado no futuro, o mesmo token passa a ser enviado automaticamente — sem mudança no domínio.

## 2. Atores e operações

| Operação | Ator | Autorização |
|---|---|---|
| **Criar** convite | Administrador da organização | Permissão `invitations.manage` |
| **Listar** convites | Administrador da organização | Permissão `invitations.manage` |
| **Cancelar** convite | Administrador da organização | Permissão `invitations.manage` |
| **Pré-visualizar** convite (ver org/papel antes de aceitar) | O convidado (posse do token) | O próprio token — nenhuma sessão |
| **Aceitar** convite | O convidado (posse do token) | O próprio token — nenhuma sessão |

Aceitação e pré-visualização são operações **públicas** (o convidado ainda não tem conta/sessão), autenticadas exclusivamente pela posse do token — exatamente como o login não exige `get_request_context`. Toda gestão administrativa (criar/listar/cancelar) exige `invitations.manage`, restrita a `organization_admin`.

## 3. Estados (fornecidos pela Decisão do Founder)

| Estado | Significado | Como é determinado |
|---|---|---|
| **Pendente** | Emitido, aguardando aceitação | Não aceito, não cancelado, `expires_at` no futuro |
| **Aceito** | O convidado criou sua conta a partir dele | `accepted_at` preenchido (terminal) |
| **Expirado** | Passou da validade sem aceitação | `expires_at` no passado, não aceito, não cancelado |
| **Cancelado** | Revogado por um administrador antes da aceitação | `cancelled_at` preenchido (terminal) |

O estado é **derivado** dos timestamps (`accepted_at`, `cancelled_at`, `expires_at`), não armazenado como coluna mutável — assim "Expirado" nunca requer um job de fundo que vire um flag; um convite fica Expirado por decurso de tempo, calculado na leitura. Transições terminais (Aceito, Cancelado) são one-way. Apenas um convite **Pendente** pode ser aceito ou cancelado; qualquer outra transição é rejeitada.

## 4. Expiração

Um Convite Pendente expira automaticamente. A **duração** é um default de implementação (não um comportamento de produto especificado por nenhum documento) — `INVITATION_TTL` = 7 dias, configurável. Justificativa: o estado "Expirado" nomeado pela Decisão do Founder exige que uma validade exista; a duração concreta é uma escolha de implementação sensata (mesma natureza do TTL de 12h de uma Sessão), documentada no Technical Design, não uma suposição de requisito de negócio.

## 5. Modelo de dados

`invitations` (nova tabela, migração 0013):

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | int PK | |
| `organization_id` | FK organizations.id | escopo de tenant |
| `email` | str | e-mail do convidado (a conta a criar) |
| `role_name` | str | papel concedido na aceitação (deve existir no catálogo) |
| `invited_by_user_id` | FK users.id | quem emitiu |
| `token_prefix` | str | primeiros caracteres do token, exibidos para diferenciar convites (não secreto) |
| `hashed_token` | str | Argon2 do token — nunca reexposto após a criação |
| `created_at` | datetime | |
| `expires_at` | datetime | `created_at + INVITATION_TTL` |
| `accepted_at` | datetime? | terminal |
| `cancelled_at` | datetime? | terminal |

Reaproveita 100% da infraestrutura existente: hashing via `Argon2PasswordHasher` (já usado para senhas e API Keys), auditoria via `AdministrationRepository.record_audit`, criação de usuário via `EnterpriseRepository.create_user_in_session` + `assign_role_in_session` (a mesma composição atômica de `AdministrationService.create_user`). Nenhum provider novo, nenhum registry novo, nenhum modelo de permissão novo.

## 6. RBAC

Nova permissão `invitations.manage` (gerir convites — criar/listar/cancelar), atribuída apenas a `organization_admin`, semeada na migração 0013 — mesmo padrão de `api_keys.manage` (D-051) e `sessions.manage` (D-053). As rotas públicas de pré-visualização/aceitação não exigem permissão (o token é a autorização).

## 7. Auditoria

Cada mutação é auditada via o mecanismo genérico já existente (`audit_logs`): `invitation.created`, `invitation.accepted`, `invitation.cancelled`. O `details` nunca inclui o token nem o hash — apenas `email`/`role_name`/`token_prefix`. A aceitação também gera o `user.created` já existente (a criação de usuário reaproveita o caminho auditado de User Management).

## 8. Notificação — a abstração, não um provedor

`NotificationProvider` (Protocol): `notify_invitation_created(invitation, plaintext_token) -> None`. Implementação padrão `NoOpNotificationProvider` (apenas loga que um envio ocorreria — "o seam existe, o provedor não"). Nenhum SMTP/SES/SendGrid é escolhido ou implementado. Quando o modelo de comunicação for decidido pelo Founder (uma decisão de negócio de Wave 6/Integration Hub), um provedor concreto implementa o mesmo Protocol sem tocar no domínio. Até lá, o convite é **plenamente funcional**: o token é devolvido uma vez na criação para entrega manual.

## 9. O que NÃO está no escopo (não inventar)

- Escolha de provedor de e-mail (SMTP/SES/etc.) — decisão de negócio, permanece pendente; não bloqueia o domínio.
- "Reset de senha"/"recuperação" — capacidade distinta, fora deste escopo (mesma fronteira que `TECHNICAL-DESIGN-USER-MANAGEMENT.md` já traçou).
- Reenvio automático, lembretes, templates de e-mail — pertencem ao provedor concreto futuro, não ao domínio.
- "Stakeholders/sponsors/atores externos" como papéis distintos — o Convite concede um papel **já existente** no catálogo RBAC; expandir o conjunto de papéis é trabalho separado do Roadmap (expansão de RBAC), não deste item.

## 10. Fundamentado vs. depende do Founder

| Fundamentado (implementado agora) | Depende de decisão de negócio futura (não bloqueia) |
|---|---|
| Aggregate, token, estados, expiração, API, RBAC, auditoria, UI administrativa, abstração `NotificationProvider` | Escolha do provedor de notificação concreto (SMTP/SES/…) e políticas de onboarding/comunicação associadas |
