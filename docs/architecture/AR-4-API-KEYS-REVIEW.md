# AR-4 — Architecture Review: API Keys (D-051)

**Escopo:** revisão arquitetural da correção de escopo registrada em `DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md` §0 (API Keys reclassificado de Nível 3 "depende de Integration Hub" para Nível 1 "fundamental"), antes da Technical Design, per o fluxo institucional obrigatório (Domain Blueprint → Revisão Arquitetural → Technical Design → Implementação).
**Motivação:** decisão arquitetural permanente do Founder — nenhum Epic previsto pode ficar pendente por depender de uma decisão futura que ainda não existe; dependências criadas apenas por decisão arquitetural anterior devem ser corrigidas, não preservadas.
**Data:** 2026-07-24

---

## 1. A dependência original era real ou artificial?

**Artificial.** A justificativa original (`DOMAIN-BLUEPRINT-ENTERPRISE-ADMINISTRATION.md`, versão anterior à correção) para classificar API Keys como Nível 3 era: "nenhuma menção prévia em nenhum Blueprint/ADR" e "relacionado à Wave 4 (Integration Hub), não a Administration". Nenhum dos dois é uma dependência técnica — são ausência de precedente e uma associação temática, não uma dependência de dados, contrato ou sequenciamento. Não existe nenhum dado, endpoint ou decisão do Integration Hub que uma implementação de API Keys precise consumir. A relação correta é a inversa: um futuro Integration Hub consumiria API Keys (para autenticar chamadas de integrações de terceiros em nome de um usuário), nunca o contrário. Portanto: **componente fundamental (API Keys) não depende de componente futuro (Integration Hub)** — exatamente o princípio permanente que o Founder estabeleceu.

## 2. Consistência com a arquitetura oficial (CLAUDE.md)

| Regra | Verificação |
|---|---|
| Nunca criar arquitetura paralela | ✅ `ApiKey` é um modelo em `src/database/models.py`, ao lado de `AuditLog`; `AdministrationRepository`/`AdministrationService` ganham métodos novos, não uma nova camada. Rotas em `src/api/routes/administration.py`, já a home de Usuários/Organizações/Papéis. |
| Nunca duplicar código | ✅ Autenticação por API Key reaproveita 100% do RBAC (`require_permission`), auditoria (`record_audit`) e hashing (`Argon2PasswordHasher`) já existentes — nenhuma lógica de permissão, auditoria ou hash é reimplementada. |
| Nunca criar novo provider | ✅ Nenhum `LLMProvider`/provider de infraestrutura novo — API Keys não é um conceito de IA. |
| Nunca criar novo registry | ✅ Nenhum registry novo. |
| Reutilizar componentes existentes | ✅ `RequestContext`/`get_request_context`, `AuthenticatedUser`/`OrganizationIdentity`/`SessionIdentity`, `require_permission`, `AdministrationRepository`, `record_audit`, `Argon2PasswordHasher` — todos reaproveitados sem alteração de contrato para os consumidores existentes. |
| SOLID / Dependency Injection | ✅ `AdministrationService` continua recebendo `repository` via construtor; a única nuance é que, em `get_request_context`, a construção do serviço é uma chamada de função direta dentro de um branch condicional (não um `Depends(...)` declarado) — ver Seção 4 sobre por que isso é a escolha correta, não uma violação de DI. |

## 3. Desenho de domínio: API Key autentica como o quê?

**Decisão central do desenho:** uma API Key autentica **como o usuário que a criou**, não como uma identidade própria com seu próprio conjunto de permissões. Isso significa:

- Zero modelo de permissão novo — a chave herda exatamente o RBAC do `created_by_user_id` no momento de cada requisição (não no momento da criação), então revogar um papel do usuário automaticamente restringe o que suas chaves podem fazer, sem nenhuma sincronização adicional.
- Zero Integration Hub necessário para ter valor imediato — uma organização já pode emitir uma chave hoje para automação própria (scripts, CI, integrações internas) contra qualquer rota já protegida por `require_permission`, sem esperar nenhuma decisão de produto futura.
- A alternativa rejeitada (criar um modelo de "Service Account" ou permissões próprias por chave) foi descartada por introduzir exatamente o tipo de arquitetura especulativa que o Founder proibiu — não há hoje nenhum requisito real que peça granularidade de permissão por chave independente do usuário.

## 4. Ponto técnico de Dependency Injection: por que uma chamada direta, não `Depends(...)`

`get_request_context` é resolvido pelo FastAPI em **toda** rota autenticada, em **todo** teste que usa `TestClient`. Declarar `AdministrationService` como um parâmetro `Depends(...)` nessa função forçaria sua construção (incluindo uma conexão real ao banco via `AnalysisRepository`) em toda chamada, mesmo nas ~12 suítes de teste existentes que nunca enviam `X-Stratech-Api-Key` e nunca fizeram override dessa dependência — risco real de regressão em massa, não hipotético. A correção: `build_repository()`/`AdministrationService(...)` são chamados como função Python simples **dentro do `if x_stratech_api_key:`**, portanto só executam quando o header está de fato presente. O único custo é que esse caminho específico não é interceptável via `app.dependency_overrides` (mitigado no único teste que precisa disso via `build_repository.cache_clear()` + `DATABASE_URL` de teste). Isso não é uma exceção ao DI — é a aplicação correta de "injetar apenas o que o caminho de execução realmente precisa".

## 5. Checagem item a item da lista de proibições do Founder

Vector Store, pgvector, embeddings, RAG, Knowledge Platform, Executive Memory permanente, Multi-Agent Framework, planejamento autônomo, reflexão autônoma, auto-execução, agentes colaborativos, Integration Hub especulativo, implementação provisória — **nenhum aparece em nenhum componente deste desenho.** Em particular, nenhum "Integration Hub mínimo" ou stub foi criado para acomodar API Keys — a capacidade é definitiva e completa por si só.

## 6. Grounding: existe consumidor real hoje?

Sim, imediato — qualquer organização que precise automatizar chamadas à API da STRATECH hoje (scripts internos, CI, integrações ponto-a-ponto) tem uma necessidade real e presente de autenticação sem sessão de navegador, resolvida integralmente por esta capacidade, sem depender de nenhum Integration Hub futuro.

## 7. Impacto em código existente

- `src/api/identity_context.py::get_request_context` — aditivo: um novo header opcional (`X-Stratech-Api-Key`), alternativo aos 3 headers de sessão já existentes. Nenhuma rota existente muda sua própria assinatura de `Depends(...)`; todas ganham suporte a API Key "de graça".
- Nenhuma migração de dado existente — `alembic/versions/0011_api_keys.py` só cria a tabela nova `api_keys` e semeia a permissão `api_keys.manage` (restrita a `organization_admin`).
- Nenhuma mudança de contrato HTTP em rotas pré-existentes.
- `web/proxy.ts` — correção adicional, não relacionada a API Keys em si: `/administracao` nunca esteve no `config.matcher`, gap pré-existente (visitante não autenticado podia carregar o shell da página; as chamadas BFF já eram bloqueadas). Corrigido para toda a seção Administração, não só a nova página.

## 8. Risco de sobre-engenharia

Avaliado e mitigado: o desenho inteiro é CRUD + hash + uma verificação de credencial adicional sobre infraestrutura que já existe — nenhum componente novo de arquitetura, nenhuma abstração introduzida além do necessário para o caso real (uma organização emite/revoga chaves; uma chave autentica como seu criador).

## 9. Veredito

**Aprovado para Technical Design, sem ressalvas.** A dependência original de Integration Hub era incorreta e fica formalmente removida por esta revisão — API Keys é fundamental, Nível 1, sem dependência de nenhum componente futuro. Nenhuma Decision Proposal adicional é necessária: a decisão do Founder (revogação retroativa do desenho anterior + princípio permanente de não-dependência de componente futuro) já autoriza a implementação completa e imediata.
