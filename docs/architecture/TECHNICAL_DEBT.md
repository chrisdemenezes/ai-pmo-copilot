# STRATECH — Technical Debt Register

Registro vivo de débitos arquiteturais conhecidos. Cada item tem origem, status e o gatilho que exige sua resolução — nenhum item aqui é corrigido automaticamente por esta entrada; a correção é um trabalho futuro separado, autorizado individualmente quando seu gatilho ocorrer.

---

## TD-001 — SQLite Foreign Keys não aplicadas pelo motor

- **Origem:** PR #39 (Épico 1 — Enterprise Foundation Schema)
- **Status:** Aberto
- **Descrição:** O SQLite não aplica constraints de FK por padrão; nenhuma conexão desta aplicação executa `PRAGMA foreign_keys=ON`. Todas as FKs declaradas nos modelos/migração (`organizations`, `users`, `projects`, etc.) são estruturalmente corretas mas não são impostas pelo motor em tempo de execução no caminho SQLite (o caminho Postgres, se usado em produção, aplica FKs por padrão).
- **Evidência:** comprovado por execução real durante a Executive Pre-Merge Architecture Review — um `DELETE FROM organizations` com usuários e projetos filhos executa sem erro.
- **Resolver antes de:** qualquer fluxo de exclusão (organização, usuário ou projeto) ser exposto por API ou UI.

## TD-002 — Delete Policy indefinida (RESTRICT vs. CASCADE)

- **Origem:** PR #39 (Épico 1 — Enterprise Foundation Schema)
- **Status:** Aberto
- **Descrição:** Nenhuma FK possui `ondelete` definido; nenhum `relationship()` ORM com cascade existe. Combinado com TD-001, uma exclusão real hoje produziria órfãos silenciosos em vez de RESTRICT (bloquear) ou CASCADE (propagar) — nenhuma das duas é a política atual; a política atual é "nenhuma".
- **Decisão pendente:** escolher RESTRICT ou CASCADE por relação (ex.: excluir Organização deveria bloquear se houver Projetos, ou excluir em cascata?) é uma decisão de produto/arquitetura, não apenas técnica.
- **Resolver antes de:** o primeiro endpoint `DELETE` de qualquer entidade da Enterprise Foundation (candidato natural: Épico 5 — Auditoria e administração mínima).

## TD-003 — Convenção de sessão do Repository inconsistente

- **Origem:** PR #39 (Épico 1 — Enterprise Foundation Schema)
- **Status:** Planejado
- **Descrição:** `EnterpriseRepository` mistura dois padrões: a maioria dos métodos abre sua própria sessão (`with self._session_factory() as session`), mas dois métodos (`get_or_create_default_organization`, `get_or_create_project_for_name`) recebem uma sessão externa para participar da transação do chamador. Funciona e está documentado via docstring, mas não há convenção de nome (ex.: sufixo `_in_session`) que distinga os dois grupos à primeira vista.
- **Resolver durante:** o Épico RBAC (Épico 3), quando a classe crescer com novos métodos de escrita e o risco de uso incorreto do padrão errado aumentar.

---

## Convenção de uso deste registro

- Novo débito identificado por qualquer revisão (arquitetural, de segurança, de código) ganha um ID sequencial `TD-NNN` aqui, com origem (PR/commit), status (`Aberto` / `Planejado` / `Resolvido`) e o gatilho explícito de resolução.
- Nenhum item é resolvido silenciosamente: a resolução de um TD é um commit/PR próprio que referencia o ID e atualiza o status para `Resolvido`, com a data e o PR de resolução.
- Este documento não substitui ADRs — um TD pode motivar um ADR futuro quando sua resolução envolver decisão arquitetural (como é o caso de TD-002).
