# External Gates Resolution Checklist — Controlled User Pilot

**Autorização:** "Founder Decision — Controlled User Pilot: External Gates Resolution + W7-1 Real Execution Authorization" — Gate Check executado (D-202): Gates A, B, C = `NOT AVAILABLE` no ambiente desta sessão. Per a STOP Rule mandatada (Seção 4), nenhuma execução real do protocolo W7-1 foi iniciada. Este documento é exclusivamente o que falta prover/configurar — **reaproveita integralmente os contratos já aprovados, nenhuma arquitetura nova proposta.**

---

## Por que nenhum dos 3 Gates está disponível nesta sessão

Esta sessão do Claude Code roda em um **container isolado e efêmero** (ambiente de execução remota), recriado do zero a cada sessão — não é, e nunca foi proposto como, o host de staging real da STRATECH. Nenhuma credencial de aplicação (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`) está presente neste ambiente. Isso é esperado e correto: essas credenciais nunca devem viver em um container efêmero de agente — elas pertencem exclusivamente ao host de staging real, provisionado e mantido pelo Founder/equipe de infraestrutura.

---

## GATE A — Staging Host

**Status:** `NOT AVAILABLE`

**O que já existe (reutilizável, sem redesenho):**
- Arquitetura aprovada (Founder Decision, D-175): VM Linux dedicada, 2 vCPU, 4 GB RAM, 20-40 GB storage inicial, Docker + Docker Compose.
- `docker-compose.yml`/`docker-compose.override.yml` (W7-5) já implementam a topologia de 3 serviços (`api`/`web`/`database`), com PostgreSQL não exposto publicamente por padrão.
- `docs/operations/PRI-009-production-deployment-runbook.md` já documenta a sequência completa de deploy (backup → build com `GIT_SHA` → `alembic upgrade head` → `docker compose up` → confirmação de revisão).

**O que o Founder precisa prover:**
1. Uma VM Linux real (2 vCPU / 4 GB RAM / 20-40 GB, per D-175) — provedor específico é decisão de procurement, não técnica.
2. Docker + Docker Compose instalados na VM.
3. Um endereço/URL alcançável (IP público ou DNS) para a sessão de validação técnica acessar.
4. Acesso SSH (ou equivalente) para que a execução do Deployment Contract (Seção 7 do mandato) possa rodar contra essa VM.
5. Confirmação de que a VM está isolada de qualquer ambiente de produção real (nenhum está provisionado hoje — apenas confirmação de intenção).

---

## GATE B — Voyage API Credential

**Status:** `NOT AVAILABLE`

**O que já existe (reutilizável, sem redesenho):**
- `VoyageEmbeddingProvider` (`src/services/knowledge_platform/embedding_provider.py`) implementado e testado — model `voyage-4`, dimensão 1024 (Founder Decision, D-177).
- Migration `0021` já aplica o schema `vector(1024)` + campos de proveniência de embedding.
- `EMBEDDING_PROVIDER=voyage` já é a única mudança de configuração necessária — nenhum código pendente.

**O que o Founder precisa prover:**
1. Uma conta Voyage AI (ou confirmação de que a conta Anthropic já dá acesso à Voyage, se aplicável ao acordo comercial vigente).
2. Uma `VOYAGE_API_KEY` real, válida, com cota suficiente para a validação técnica (documento sintético único de teste — volume mínimo).
3. Confirmação de que a chave será fornecida através de um mecanismo seguro (variável de ambiente na VM de staging, nunca em texto no chat, nunca commitada).

---

## GATE C — Anthropic API Credential

**Status:** `NOT AVAILABLE`

**O que já existe (reutilizável, sem redesenho):**
- `ProductionLLMProvider` (`src/llm/providers/production_provider.py`) implementado e testado — SDK oficial `anthropic`, model `claude-3-5-sonnet-20241022` (configurável via `MODEL_NAME`).
- Falha fechada já implementada: sem `ANTHROPIC_API_KEY`, o boot falha fora de `dev` (Configuration Contract, `src/api/startup_config.py`).
- `LLM_PROVIDER=anthropic` já é a única mudança de configuração necessária — nenhum código pendente.

**Nota de esclarecimento (não uma ambiguidade a resolver, apenas um registro):** o ambiente desta sessão do Claude Code tem sua própria infraestrutura de proxy para as chamadas de modelo da própria sessão (`ANTHROPIC_BASE_URL`) — isso é inteiramente distinto da credencial de aplicação que a STRATECH precisa, e não foi e não deve ser reaproveitado para essa finalidade.

**O que o Founder precisa prover:**
1. Uma `ANTHROPIC_API_KEY` real, válida, com cota suficiente para a validação técnica (volume mínimo: Advisors representativos + Decision Support + Executive Narrative, algumas dezenas de chamadas).
2. Confirmação de que a chave será fornecida através de um mecanismo seguro (variável de ambiente na VM de staging, nunca em texto no chat, nunca commitada).

---

## GATE D — Data/DPA Approval

**Status:** `NOT APPROVED` (não exigido para esta fase, per decisão do próprio Founder — a validação técnica inicial usa exclusivamente dado sintético/controlado)

**Nenhuma ação necessária agora.** Gate D só se torna um pré-requisito se/quando o Founder decidir enviar dado corporativo real à Anthropic ou à Voyage AI — o que não é o escopo desta fase de validação técnica. Esta regra não foi e não será relaxada.

---

## Sequência recomendada de resolução (sem redesenho, apenas ordem prática)

1. Provisionar a VM de staging (Gate A) — pré-requisito físico para tudo o resto.
2. Obter `ANTHROPIC_API_KEY` (Gate C) e `VOYAGE_API_KEY` (Gate B) em paralelo — nenhuma depende da outra.
3. Configurar as 3 credenciais + demais variáveis já catalogadas em `.env.example`/`web/.env.example` diretamente na VM de staging (nunca em texto no chat, nunca commitadas).
4. Confirmar ao Founder Decision seguinte que os 3 Gates estão `AVAILABLE` — a partir daí, a execução real do protocolo W7-1 (Seções 6-22 do mandato) pode prosseguir exatamente como já autorizado, sem nova autorização de escopo.

---

## O que este documento explicitamente não é

Não é uma proposta de arquitetura nova. Não é uma alteração de contrato de deployment, embedding, ou LLM. Não é uma execução simulada ou substituta do protocolo W7-1. É exclusivamente a lista do que falta ser provido externamente para que a execução real, já autorizada, possa começar.
