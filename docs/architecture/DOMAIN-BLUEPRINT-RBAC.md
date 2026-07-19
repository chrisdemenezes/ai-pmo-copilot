# Domain Blueprint — Enterprise RBAC

**Wave:** 2 (Enterprise Master Execution Program) — corresponde ao Épico 3 (Organização e RBAC inicial)
**Status:** Blueprint conceitual — não implementa, não produz código.
**Relação com trabalho já existente:** este documento **formaliza e fecha** o modelo de domínio de RBAC; a implementação-nível-de-código já tem Technical Design produzido em `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4 (Protocols, estrutura de diretórios, contratos, testes). Este Blueprint não substitui aquele documento — resolve as perguntas de **modelo de domínio** que o Technical Design deixou em aberto (§4.15: "se o schema do Épico 3 diferir do assumido, revisar antes da implementação").

---

## 1. Role Model

**Fundamentado, já existe:** `roles` (schema, Épico 1), 4 papéis seed. Nenhuma mudança de schema recomendada — o Role Model é: um usuário tem um ou mais `UserRole` dentro de uma organização (`user_roles` já tem `user_id`); um `Role` agrupa `Permission`s via `role_permissions`.

**Pergunta em aberto que este documento resolve:** o Foundation Technical Design (§4.15) apontou como risco não saber se `user_roles` precisa de `organization_id` próprio (usuário com papéis diferentes em organizações diferentes). **Recomendação:** sim — `user_roles` deve incluir `organization_id`, porque a STRATECH já é multi-tenant desde o Épico 1 e um usuário pertencente a mais de uma organização (caso já implícito no schema de `users`/`organizations`) precisa poder ter um papel distinto em cada uma. Isso é uma **extensão aditiva de schema** (nova coluna/FK), não uma decisão nova de arquitetura — recomenda-se ratificar via Decision Proposal simples antes da migração do Épico 3.

## 2. Permission Model

**Fundamentado, já existe:** `permissions` (schema, Épico 1) + vocabulário `resource.action` já definido em `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4.9 (`portfolio.read`, `program.write`, etc.). Este Blueprint fecha o modelo: toda permissão nomeia exatamente um recurso (um dos Bounded Contexts/domínios: `portfolio`, `program`, `project_delivery`, e futuramente `administration`, `rbac` — meta-permissão para gerenciar papéis) e uma ação (`read`, `write`, e futuramente `approve`/`admin` onde fizer sentido, ex.: `program.approve` já citado no Technical Design).

## 3. Claims

**Recomendação: não adotar.** A STRATECH usa RBAC relacional (papel → permissão), não claims-based auth (onde a identidade carrega um conjunto de claims arbitrários validados por assinatura, tipicamente em um JWT). Introduzir Claims ao lado de Roles/Permissions criaria uma segunda arquitetura de autorização — exatamente o que CLAUDE.md proíbe ("nunca criar novo provider/registry"). Se um caso de uso futuro realmente exigir claims (ex.: federação com um IdP externo que só fala em claims), isso é decisão de ADR própria no momento em que esse caso de uso existir — não uma capability a construir preventivamente agora.

## 4. Policies

**Recomendação: mapear para o vocabulário de permissão existente, não criar mecanismo novo.** "Policy" no pedido da missão provavelmente significa "regra de autorização mais expressiva que um papel simples" (ex.: "usuário só pode aprovar Programs do seu próprio Portfolio"). Isso já é exatamente o papel do **Organizational Scoping** (`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §3) combinado com o Permission Model (Seção 2 acima) — um "Policy" é a combinação de uma permissão (`program.approve`) com um escopo (`organization_id`, e futuramente `portfolio_id` se necessário granularidade menor). Não recomendado introduzir um motor de Policy genérico (ex.: estilo OPA/Rego) sem um caso de uso concreto que o RBAC relacional não resolva.

## 5. Authorization (enforcement)

**Fundamentado, já desenhado:** `PermissionChecker` Protocol + `require_permission()` FastAPI dependency (`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4.4/§4.9). Este Blueprint não altera esse desenho — confirma que ele é suficiente para o Role/Permission/Policy Model definido acima (nenhuma extensão de Protocol necessária).

## 6. Scope Hierarchy

**Fundamentado, formalizado por este documento:** a hierarquia de escopo de autorização segue exatamente a hierarquia de domínio já aprovada (Portfolio → Program → Project), não uma hierarquia paralela:

```
Organization (escopo raiz — todo usuário pertence a exatamente 1+ organizações, via user_roles.organization_id)
  └── Portfolio (escopo de negócio raiz dentro da organização)
        └── Program
              └── Project (Project Delivery)
```

Uma permissão concedida no nível Organization aplica-se a toda a árvore abaixo (ex.: um Administrator organizacional vê todos os Portfolios). Uma permissão granular a um Portfolio específico (se um Papel futuro exigir isso — não existe hoje) seria uma extensão do Organizational Scoping, não um mecanismo novo.

## 7. Tenant Isolation

**Fundamentado, já existe e já tem Technical Design:** `organization_id` como FK raiz + `CrossTenantViolationError` (Épico 1) + `assert_same_organization()` (`PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §3.4). Nenhuma mudança recomendada.

## 8. Workspace Isolation

**Recomendação: não introduzir como conceito de isolamento novo.** "Workspace" na STRATECH é hoje a página `/workspace/{project}` (V1) — uma superfície de UI sobre um Project, não uma unidade de isolamento de dados. Não existe (e não é recomendado criar) um "Workspace" como camada de isolamento **entre** Tenant Isolation (Organization) e o domínio (Portfolio/Program/Project) — isso duplicaria a Scope Hierarchy já definida na Seção 6. Se a necessidade real for "isolar por sub-unidade da organização", o Program já cumpre esse papel na hierarquia existente.

---

## 9. Fundamentado vs. depende do Founder vs. exige definição arquitetural

| Fundamentado (pronto para Technical Design, sem mudança) | Depende do Founder (Decision Proposal simples) | Exige definição arquitetural antes de decisão |
|---|---|---|
| Role Model, Permission Model, Authorization (enforcement), Scope Hierarchy, Tenant Isolation | `user_roles.organization_id` (extensão de schema) | — |
| Recomendação de não adotar Claims | | |
| Recomendação de mapear Policies ao vocabulário existente | | |
| Recomendação de não criar Workspace Isolation | | |

**Conclusão:** este Blueprint fecha o modelo de domínio de RBAC sem exigir nenhuma arquitetura nova além de uma extensão de schema já esperada (`organization_id` em `user_roles`). O Épico 3/Wave 2 RBAC está pronto para Technical Design final (a versão já existente em `PHASE-2-FOUNDATION-TECHNICAL-DESIGN.md` §4 precisa apenas incorporar essa extensão de schema, não ser reescrita).
