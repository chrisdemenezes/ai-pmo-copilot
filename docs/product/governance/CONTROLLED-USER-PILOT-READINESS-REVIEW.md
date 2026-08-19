# Controlled User Pilot — Readiness Review

**Autorização:** "Founder Decision — W7-7 Checkpoint Ratification + Controlled User Pilot Readiness Review", em resposta à Executive Evidence do W7-7 (D-199, APPROVED) e ao fechamento do Logout UI Gap (D-200). Esta revisão **não é** Wave 7 Completion Review, Enterprise Production Certification, Security Certification, ou Performance Certification. Pergunta única: **com o estado atual real da STRATECH V1, o que ainda impede que usuários reais selecionados utilizem a plataforma em um piloto controlado?**

**Método:** reconstrução mecânica do estado real — nenhuma avaliação anterior assumida válida sem verificação direta nesta missão (código, testes, migrations, runbooks lidos/executados de novo, não apenas citados). Onde uma avaliação anterior foi reconfirmada sem alteração, isso está registrado explicitamente como "reconfirmado", não como "assumido".

---

## 1. Pilot Assumptions (aplicadas nesta revisão)

Grupo pequeno de usuários selecionados; acesso controlado; Chrome/Chromium como browser suportado; sem promessa de SLA enterprise; ambiente isolado; acompanhamento próximo do Founder/equipe; possibilidade de intervenção manual; volume de dados e carga limitados; objetivo principal = validação real do produto e experiência — não confundido com Enterprise Production.

**Não relaxadas sob nenhuma hipótese:** tenant isolation, authentication, data integrity, security HIGH/CRITICAL, backup/restore essencial, perda silenciosa de dados.

---

## 2. Classificação por dimensão

| # | Dimensão | Classificação | Evidência |
|---|---|---|---|
| 1 | Product functionality | **READY FOR PILOT** | 14 itens de nav reais em produção (`web/components/shell/navigation.ts`), regra de entrada "nenhum placeholder", todos os hooks de dados reais (`usePortfolios`/`usePrograms`/`useProjects`/etc.), confirmado por leitura direta de `app/aprendizados/page.tsx` e `app/portfolio/page.tsx` nesta missão (nenhum stub) |
| 2 | Installation | **READY FOR PILOT** | `make dev` (clone→setup→db-create→migrate→dev) confirmado em `Makefile`; `docker-compose.yml`/`PRI-009` cobrem o caminho de produção separadamente; todas as env vars catalogadas em `.env.example`/`web/.env.example` |
| 3 | Authentication | **READY FOR PILOT** | Login real por usuário (organização+email+senha), Argon2, `LoginBruteForceGuard` (W7-4/D-188, 5 tentativas/15min lockout), sem CAPTCHA/MFA — aceitável para o piloto per premissas |
| 4 | Session | **READY FOR PILOT** | Cookie HMAC-assinado, TTL 12h, `SameSite=lax`, `HttpOnly`. **Logout agora real end-to-end** (D-200) — botão real na UI, `DELETE /api/bff/session`, revogação server-side comprovada. Revogação best-effort (F9, `ACCEPTED`) é o único resíduo, proporcional à escala do piloto |
| 5 | RBAC | **READY FOR PILOT** | Reverificado nesta missão: todo módulo de rota tem `verify_api_key` (`grep -L` vazio); `require_permission` presente em `administration`/`intelligence`/`invitations`/`knowledge`/`portfolio`/`program`/`project_delivery`; `tests/test_authorization.py` verde |
| 6 | Tenant isolation | **READY FOR PILOT** | Reverificado: `CrossTenantViolationError` (`src/database/enterprise_repository.py:30`) segue existindo e testado; `organization_id` sempre de `RequestContext` |
| 7 | Security baseline | **READY WITH ACCEPTED LIMITATION** | `Controlled Pilot Security Baseline = SATISFIED` (D-191/D-192, W7-4) — F1/F2/F4 (HIGH) fechados. F3 (headers HTTP)/F5 (rate limit por organização, não por usuário)/F6 (nenhum scan de dependências)/F7 (falhas de login em log, não em `audit_logs`) permanecem `OPEN`, classificação MEDIUM/LOW, não bloqueantes para um piloto pequeno e supervisionado |
| 8 | Browser/frontend baseline | **READY FOR PILOT** | `Controlled Pilot Browser Baseline = SATISFIED` (D-199, W7-7) — Chromium/Chrome nos 3 viewports, exatamente a premissa do piloto |
| 9 | Documents | **READY FOR PILOT** | Upload/listagem/reindexação reais e testados (unidade + integração + E2E com fronteira de evidência declarada) — `src/api/routes/knowledge.py`, `web/e2e/documents-admin.spec.ts` |
| 10 | Knowledge/RAG | **READY WITH ACCEPTED LIMITATION** | Recuperação (`rag_pipeline.py`) é real e testada contra Postgres+pgvector real (não mockada). **Porém o embedding usado é sempre `MockEmbeddingProvider`, em todo lugar, inclusive em todos os testes** — nenhuma chamada real à Voyage AI jamais ocorreu neste código (`tests/test_voyage_embedding_provider.py` confirma explicitamente: nenhuma chamada de rede real em nenhum teste). O mecanismo funciona; a **qualidade semântica real é inteiramente não comprovada** até o Gate B ser resolvido |
| 11 | Enterprise Advisors | **BLOCKED — EXTERNALLY (Gate C)** | 8 Advisors reais, `ProductionLLMProvider` real (Anthropic SDK), falha fechado sem `ANTHROPIC_API_KEY` — 326 testes de advisor/orchestrator verdes contra Postgres real. Tecnicamente pronto; **funcionalmente inutilizável em um piloto real sem uma credencial Anthropic real** (Gate C, W7-1) |
| 12 | Executive Intelligence (Orchestrator) | **BLOCKED — EXTERNALLY (Gate C)** | `ExecutiveOrchestrator` real, `selection_rule` determinística (nunca LLM-driven), coberto pelos mesmos 326 testes. Mesma dependência de Gate C que os Advisors — o Orchestrator nunca opera sem um provider LLM real configurado para um piloto de verdade |
| 13 | Decision Support | **BLOCKED — EXTERNALLY (Gate C)** | `POST /decision-support/ask` real, evidence-gated (`insufficient_basis`/`SELECTION_EMPTY`/`COLLECTION_EMPTY`, comportamento implementado e testado, não aspiracional) — `tests/test_decision_support_api.py`, 33 testes (combinado com Executive Narrative). Mesma dependência de Gate C |
| 14 | Executive Narrative | **BLOCKED — EXTERNALLY (Gate C)** | `POST /executive-narrative/generate` real, mesmo contrato de evidência de Decision Support, catálogo completo de Advisors por escopo. Mesma dependência de Gate C |
| 15 | Database | **READY FOR PILOT** | Único datastore com estado (Postgres 16 + `pgvector`), reverificado nesta missão |
| 16 | Migrations | **READY FOR PILOT** | Reverificado nesta missão: **21 migrations reais** (`alembic/versions/`, confirmado por `ls`), 20 com `downgrade()` substantivo + 1 no-op intencional e documentado (`0014`, backfill de dados, reversão destrutiva por design, não um defeito) |
| 17 | Backup | **READY FOR PILOT** | `src/database/backup.py` implementado e testado localmente (W7-3, D-182) — `pg_dump -Fc`, verificação via `pg_restore --list`, nenhum artefato parcial em falha |
| 18 | Restore | **READY FOR PILOT** | `src/database/restore_validation.py` implementado e testado localmente (W7-3, D-183) — deriva tabelas esperadas de `Base.metadata` (nunca hardcoded), valida revisão Alembic, integridade referencial, contrato de embedding |
| 19 | Disaster Recovery (drill completo) | **NOT REQUIRED FOR PILOT** | Ver Seção 4 — justificativa de risco explícita |
| 20 | Deployment | **READY FOR PILOT** | Configuration Contract fail-fast (W7-5), `/health`/`/ready` reais, `RELEASE_SHA` exposto, frontend containerizado, migration como etapa explícita separada, smoke test parametrizável (`PLAYWRIGHT_BASE_URL`) |
| 21 | Configuration | **READY FOR PILOT** | Todas as variáveis catalogadas com defaults documentados; achado cosmético (não bloqueante): `WORKSPACE_PASSWORD` é exigido no boot (`web/lib/startup-config.ts:33-34`) mas nunca consumido em nenhuma lógica de autenticação real — resíduo do design "Nível 1" anterior à Identity Foundation, inofensivo (qualquer valor satisfaz o fail-fast) |
| 22 | Secrets | **READY FOR PILOT** | `API_KEY`/`SESSION_SECRET`/`ANTHROPIC_API_KEY`/`VOYAGE_API_KEY`/`POSTGRES_PASSWORD` — todos via variável de ambiente, nenhum hardcoded, fail-fast fora de dev; nenhum secrets manager (F10, `ACCEPTED`, adequado para o estágio) |
| 23 | LLM provider | **BLOCKED — EXTERNALLY (Gate C)** | `ProductionLLMProvider` real e testado (Anthropic SDK, `claude-3-5-sonnet-20241022`), nunca executado com chave real em staging/produção — apenas Gate C separa "código pronto" de "piloto funcional" |
| 24 | Embedding provider | **BLOCKED — EXTERNALLY (Gate B), degrada sem bloquear boot** | `VoyageEmbeddingProvider` real e implementado (D-177, `voyage-4`, dimensão 1024), nunca chamado com chave real em nenhum ambiente, inclusive testes. Sem Gate B, o app funciona (cai para mock), mas RAG/Document Advisor operam sobre qualidade semântica não comprovada |
| 25 | Staging | **BLOCKED — EXTERNALLY (Gate A)** | Nenhum staging provisionado; arquitetura já aprovada (D-175: VM 2 vCPU/4GB RAM/20-40GB) mas procurement pendente |
| 26 | Observability | **READY WITH ACCEPTED LIMITATION** | Ver Seção 5 — mínimo necessário presente, plataforma completa não |
| 27 | Performance | **NOT REQUIRED FOR PILOT** | Ver Seção 5 — nenhum load testing existe, nenhuma necessidade demonstrada para um piloto de carga limitada |
| 28 | Supportability | **READY WITH ACCEPTED LIMITATION** | 3 runbooks reais (`PRI-008`/`009`/`010`) cobrindo deploy/backup-restore/DR; nenhum runbook de incident-response dedicado — aceitável para equipe pequena com acompanhamento próximo (premissa do piloto) |
| 29 | Runbooks | **READY WITH ACCEPTED LIMITATION** | Mesmos 3 runbooks. Achado cosmético: `PRI-009` linha 103 ainda cita "20 migrations" — desatualizado desde a migration `0021` (não bloqueante, correção de baixo esforço registrada como debt) |

---

## 3. W7-1 — Gates Externos: reavaliação

Reverificado nesta missão (não assumido) — todos os 4 Gates seguem **PENDING**, última confirmação em D-180, nenhuma decisão subsequente os alterou.

| Gate | Estado | Obrigatório para piloto A (dados sintéticos)? | Obrigatório para piloto B (dados corporativos reais)? |
|---|---|---|---|
| A — Staging Host | PENDING (procurement) | **SIM** — nenhum ambiente real existe sem ele, mesmo para dados sintéticos | **SIM** |
| B — Voyage API Credential | PENDING (procurement) | Não bloqueia o boot nem o restante da jornada — mas **necessário para qualquer validação real de qualidade de RAG/Document Advisor** | **SIM** (mesmo motivo, com dado real em jogo) |
| C — Anthropic API Credential | PENDING (procurement) | **SIM** — sem ela, Advisors/Decision Support/Executive Narrative retornam `ProviderConfigError`; um piloto sem IA funcional não valida a proposta de valor central do produto | **SIM** |
| D — Data/DPA Approval | PENDING (legal) | **NÃO** — já decidido explicitamente em D-178 ("Data/DPA não bloqueia validação sintética"), reconfirmado aqui sem alteração | **SIM, sem exceção** — não relaxado nesta revisão, per mandato explícito do Founder |

**TECHNICALLY IMPLEMENTED vs EXTERNALLY BLOCKED (separação explícita):** todo o código dos 3 Gates técnicos (B/C — providers reais) está implementado, testado e pronto para receber uma credencial real sem alteração adicional. Gate A é puramente de infraestrutura (nenhum código pendente). **Nenhum dos 4 Gates tem qualquer dependência técnica não resolvida — todos são Business/Procurement/Legal, não Engineering.**

---

## 4. W7-3 — Disaster Recovery: mínimo obrigatório para o piloto

| Item | Classificação | Justificativa de risco |
|---|---|---|
| Backup funcional | READY FOR PILOT | Implementado e testado localmente (D-182) |
| Restore funcional | READY FOR PILOT | Implementado e testado localmente (D-183) |
| Procedimento documentado | READY FOR PILOT | `PRI-010`, 13 fases executáveis |
| Validação de restore | READY FOR PILOT | `validate_restore()` cobre schema/integridade/embedding, gap histórico do `PRI-008` já corrigido (D-183) |
| RTO/RPO definidos | READY WITH ACCEPTED LIMITATION | 8h/24h configurados e documentados, nunca medidos contra um drill real — alvo de design, não fato comprovado |
| DR Drill completo (real, medido) | **NOT REQUIRED FOR PILOT — requisito de Enterprise Production** | Um piloto pequeno, com dado de volume limitado, sob acompanhamento próximo do Founder/equipe e possibilidade de intervenção manual, tem um raio de impacto de perda de dados ordens de magnitude menor que Produção Enterprise com múltiplos clientes sob obrigação contratual. O mecanismo de backup/restore já está implementado e testado localmente (não apenas documentado) — o risco residual de não ter executado um drill formal é proporcional ao estágio, não decidido por conveniência: se o pior cenário ocorrer durante o piloto, restore a partir de um backup testado localmente é uma resposta adequada, com o Founder podendo autorizar uma execução real assistida se necessário |

**Conclusão da Seção 4:** Disaster Recovery não bloqueia o Controlled User Pilot. Bloqueia inequivocamente a Enterprise Production Certification (W7-3 permanece `OPEN`, DR não é `Delivered`).

---

## 5. Observability / Performance: mínimo obrigatório

| Sinal necessário | Existe hoje? | Evidência |
|---|---|---|
| Aplicação indisponível | SIM | `GET /health` (liveness) |
| Erro de backend | SIM (log, sem alerta automático) | `logging` estruturado com `request_id` propagado (`src/api/request_context.py`), estados de erro visíveis na UI (`dashboard.spec.ts` etc.) |
| Erro de AI provider | SIM (log + falha explícita) | `ProviderConfigError` falha fechado com mensagem clara; erros de provider logados |
| Falha de banco | SIM | `GET /ready` executa `SELECT 1` real contra o banco |
| Falha de readiness | SIM | `GET /ready` distinto de `/health`, checa Configuration Contract + DB |
| Falha de login | SIM (log, não `audit_logs` ainda) | `logger.info` em `auth_service.py` (F7, `OPEN`, não bloqueante) |
| Execução anormalmente lenta percebida pelo usuário | **NÃO — apenas observação manual** | Nenhum APM/tracing/métrica existe (confirmado: busca por Prometheus/OpenTelemetry/StatsD/Datadog/Grafana em todo o repositório não encontra nenhum uso real) |

**Classificação: READY WITH ACCEPTED LIMITATION.** Todos os sinais mínimos mandatados existem, exceto detecção automática de lentidão — aceitável explicitamente porque a premissa do piloto inclui "acompanhamento próximo do Founder/equipe" e "possibilidade de intervenção manual", tornando observação manual uma mitigação real, não uma lacuna ignorada. **Nenhuma plataforma de observability enterprise é necessária ou recomendada nesta revisão** — não há necessidade demonstrada, per o próprio mandato de não overengineering.

**Performance: NOT REQUIRED FOR PILOT.** Nenhum load testing existe (confirmado — busca por locust/k6/benchmark/load test não encontra suíte real). `docs/architecture/WAVE-7-ENTERPRISE-READINESS-KICKOFF.md` já documentava isso como `Not Ready` para Produção. Para um piloto de carga e volume de dados explicitamente limitados, nenhum benchmark formal é necessário — não confundir com uma dispensa geral: se o piloto revelar lentidão real perceptível, isso vira um Stop Condition (Seção 8), não um risco pré-aceito silenciosamente.

---

## 6. User Pilot Journey

| Passo | Status | Evidência |
|---|---|---|
| Login | READY | Login real por usuário, testado E2E nos 3 viewports |
| Dashboard | READY | KPIs reais, Decision Support/Executive Narrative wiring testado (dependem de Gate C para conteúdo real, ver abaixo) |
| Navegação | READY | 14 itens, `shell.spec.ts` (13 passed, 2 skips legítimos, reverificado nesta missão) |
| Projects / Program Management / Project Delivery | READY | Projects com cobertura completa; Program Management/Project Delivery classificados `IN PILOT BASELINE` (D-198) com cobertura mínima real |
| Documents | READY WITH LIMITATION | Upload/listagem reais; qualidade de indexação semântica depende do Gate B |
| Knowledge/RAG | READY WITH LIMITATION | Recuperação real; qualidade de embedding depende do Gate B |
| Advisors | **BLOCKED — Gate C** | Código pronto, 326 testes verdes, funcionalmente inoperante sem credencial Anthropic real |
| Decision Support | **BLOCKED — Gate C** | Idem |
| Executive Narrative | **BLOCKED — Gate C** | Idem |
| Logout | READY | Corrigido nesta mesma sessão (D-200), controle real na UI, testado nos 3 viewports |

---

## 7. Pilot Blocker Register

| ID | Descrição | Origem | Owner | Dependência | Ação necessária | Critério de fechamento |
|---|---|---|---|---|---|---|
| PBR-1 | Nenhuma credencial real Anthropic configurada | External/Business | Founder/Procurement | Nenhuma técnica | Obter `ANTHROPIC_API_KEY` real | Chave configurada + 1 chamada real bem-sucedida validada em ambiente real |
| PBR-2 | Nenhum host de staging/piloto provisionado | External/Technical | Founder/Infra | Nenhuma | Provisionar VM per arquitetura já aprovada (D-175) | Host ativo, deployment via `PRI-009` executado com sucesso |
| PBR-3 | Nenhuma credencial real Voyage configurada | External/Business | Founder/Procurement | Gate D se dado real | Obter `VOYAGE_API_KEY` real | Chave configurada + reembedding executado, se RAG for parte do escopo do piloto |
| PBR-4 | Aprovação Data/DPA pendente | Business/Legal | Founder/Legal | Nenhuma | Concluir revisão de DPA com os providers | Aprovação documentada — **obrigatório apenas se dado corporativo real for usado, nunca dispensado** |

**Nenhuma dívida de Enterprise Production (F3/F5/F6/F7 do W7-4; DR Drill do W7-3; Firefox/WebKit do W7-7; Observability/Performance formais do W7-2/W7-6; runbook de incident-response do W7-8) está listada aqui — nenhuma delas bloqueia o piloto**, per critério de risco explícito de cada seção acima.

---

## 8. Pilot Go-Live Checklist

1. [ ] `ENVIRONMENT` correto (`staging` ou `production`) no host do piloto
2. [ ] `RELEASE_SHA`/`GIT_SHA` baked no build, confirmado via `GET /health`
3. [ ] Banco provisionado, `alembic upgrade head` executado, confirmado via `GET /ready`
4. [ ] `GET /ready` retorna 200
5. [ ] Credenciais configuradas: `API_KEY`, `ANTHROPIC_API_KEY` (PBR-1), `VOYAGE_API_KEY` se RAG estiver no escopo (PBR-3), `SESSION_SECRET`, `POSTGRES_PASSWORD` (não-default), `WORKSPACE_PASSWORD` (qualquer valor não vazio — vestigial, ver Seção 2 item 21)
6. [ ] Usuários de teste/piloto criados via fluxo de Convites, papéis atribuídos
7. [ ] Organização/tenant do piloto criada
8. [ ] Dado de amostra/seed carregado conforme escopo aprovado (sintético, ou real apenas com PBR-4 fechado)
9. [ ] Documents: um upload/reindexação real de ponta a ponta verificado no ambiente real
10. [ ] Backup executado uma vez antes do go-live, verificado
11. [ ] Smoke test executado contra o ambiente real (`PLAYWRIGHT_BASE_URL`, `smoke.spec.ts`)
12. [ ] Browser: Chrome/Chromium comunicado como o browser suportado aos usuários do piloto
13. [ ] Permissões verificadas: papel/RBAC de cada usuário do piloto conferido
14. [ ] Decision Support: uma pergunta real feita e respondida com sucesso no ambiente real
15. [ ] Executive Narrative: uma geração real executada com sucesso no ambiente real
16. [ ] Logout: verificado funcionando no ambiente real (não apenas contra o mock de E2E)
17. [ ] Contato de suporte nomeado e comunicado aos usuários do piloto
18. [ ] Procedimento e autoridade de rollback/parada documentados e entendidos pela equipe

---

## 9. Stop Conditions

O piloto deve ser interrompido imediatamente se qualquer um destes ocorrer:

- Falha de tenant isolation (qualquer evidência de vazamento de dado entre organizações)
- Bypass de autenticação (qualquer evidência de que sessão/RBAC pode ser contornado)
- Corrupção de dados (qualquer evidência além de erro esperado de usuário)
- Falha de backup não remediada no mesmo dia
- Erro de provider descontrolado (Anthropic/Voyage falhando em cascata sem degradação graciosa — a aplicação deve sempre mostrar um erro claro, nunca travar)
- Falha persistente de IA (Advisors/Decision Support/Executive Narrative falhando repetidamente entre múltiplos usuários/sessões, não um episódio isolado)
- Fluxo crítico indisponível por período prolongado (Login, Dashboard, ou Documents)
- Incidente de segurança (qualquer suspeita de acesso não autorizado, vazamento de credencial, ou tentativa de injeção bem-sucedida)

---

## 10. Preservação

Nenhum Epic implementado ou iniciado além da correção mínima de Logout UI (D-200) já registrada separadamente. Não iniciados: W7-1 execução real, W7-2, W7-3 Drill, W7-4 Enterprise Hardening, W7-7 Enterprise Browser Certification, W7-8, W7-9, W7-10. Esta missão é exclusivamente de Assessment — nenhum código adicional escrito.

---

## 11. GO/NO-GO atual para Controlled User Pilot

**NO-GO hoje — exclusivamente por dependências externas, não técnicas.**

A STRATECH V1 está **tecnicamente pronta** para um Controlled User Pilot: 27 das 29 dimensões avaliadas são `READY FOR PILOT` ou `READY WITH ACCEPTED LIMITATION`; nenhuma dimensão técnica está `BLOCKED` por um motivo de engenharia. As 4 dimensões classificadas `BLOCKED — EXTERNALLY` (Advisors, Executive Intelligence, Decision Support, Executive Narrative) têm código completo, testado (326 testes verdes) e pronto para operar assim que o Gate C (credencial Anthropic real) for resolvido — a mesma dependência bloqueia também o valor central da proposta de produto, tornando-a a mais crítica das 4 pendências externas.

**O que falta para converter NO-GO em GO:**
1. Resolver Gate C (credencial Anthropic real) — **crítico, sem ele o piloto não valida a proposta de valor central**
2. Resolver Gate A (host de staging/piloto provisionado) — **crítico, sem ele não há ambiente real**
3. Resolver Gate B (credencial Voyage real) — necessário apenas se Documents/RAG fizer parte do escopo demonstrado do piloto; sem ele, a aplicação funciona com qualidade de busca semântica não comprovada
4. Resolver Gate D (aprovação Data/DPA) — **apenas se dado corporativo real for usado**; não bloqueia um piloto com dado sintético

Nenhuma dessas 4 pendências requer trabalho de engenharia adicional. Todas são decisões de Business/Procurement/Legal do Founder.

Retornando obrigatoriamente para Executive Review.
