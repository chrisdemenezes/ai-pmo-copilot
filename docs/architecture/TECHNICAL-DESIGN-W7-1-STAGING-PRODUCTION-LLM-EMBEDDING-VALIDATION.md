# Technical Design — W7-1: Staging & Production LLM/Embedding Validation

**Autorização:** "Founder Decision — W7-5 Closure + W7-1 Institutional Opening". W7-5 está formalmente encerrado (D-172, `W7-5-EXECUTIVE-EVIDENCE.md`). Autorizada exclusivamente a abertura institucional do W7-1, e exclusivamente a produção deste Technical Design + Staging Validation Plan. **Nenhum provisionamento, nenhum deployment executado, nenhuma credencial de produção utilizada, nenhuma validação real de LLM/embedding realizada nesta missão.**

Este documento é fundado no que o W7-5 realmente entregou (código e contratos reais, não aspiração) e na definição arquitetural de Staging já registrada em AR-18 §7 (16 características mínimas) e no Production AI Validation Model de AR-18 §8 (7 camadas, aplicadas independentemente a LLM e Embedding). Nenhuma dessas duas seções é redefinida aqui — apenas operacionalizada em um plano executável.

---

## 1. O que o W7-1 herda do W7-5 (grounding real, não assumido)

| Contrato do W7-5 | Onde vive | O que o W7-1 reutiliza |
|---|---|---|
| Configuration Contract | `src/api/startup_config.py`, `web/lib/startup-config.ts` | A validação `staging`/`production` já existe e já falha fechado — W7-1 só precisa *popular* as variáveis reais, não construir um novo mecanismo |
| Readiness | `GET /ready` (`src/main.py`) | Sinal objetivo de "esta instância está apta" — parte do protocolo de validação (§5) |
| Release Identity | `Dockerfile`/`web/Dockerfile` (`GIT_SHA`/`RELEASE_SHA`) | Toda execução de validação real deve citar o `release` observado em `GET /health` de ambos os serviços, para rastreabilidade |
| Deployment Contract | `docker-compose.yml` (`api`/`web`/`database`), `PRI-009` §2 (Build → Validate → Migrate → Deploy → Readiness → Smoke → Promote) | Topologia mínima de staging (§3) é a mesma composição, apontada para um host real |
| Migration Discipline | `docker-compose.yml` (comando `api` desacoplado), `PRI-009` §2 passo 3 | As 20 migrations reais (`0001` a `0020`) rodam como etapa explícita antes do deploy de staging |
| Smoke Test Parametrizável | `web/playwright.config.ts` (`PLAYWRIGHT_BASE_URL`), `web/e2e/smoke.spec.ts` | Executável contra staging assim que ela existir, sem nenhuma mudança de código |

Nada disso precisa ser reconstruído. O W7-1 é a primeira vez que esses contratos são exercitados contra algo que não é `localhost`.

---

## 2. Pergunta 1 — Onde staging será hospedado

**Requisito arquitetural (derivado do que já foi decidido, não inventado agora):** o W7-5 estabeleceu, como decisão institucional explícita, que o deployment é feito via `docker-compose`/Docker puro — sem Kubernetes, sem service mesh, sem plataforma gerenciada introduzida sem necessidade demonstrada (Technical Design W7-5 §4, reafirmado nesta missão). Staging herda essa mesma restrição: **qualquer host que rode Docker + `docker compose` e consiga expor as portas `8000`/`3000`/`5432` (ou equivalentes atrás de um proxy) satisfaz o requisito técnico** — não há dependência de nenhum provedor específico.

**O que este Technical Design pode decidir sozinho:** a topologia (§3) e o fato de não introduzir uma plataforma nova.

**O que este Technical Design não pode decidir sozinho — Founder Decision elevada, não silenciosamente resolvida:** *qual* host real (conta de nuvem já existente, VM própria, provedor a contratar). Este repositório não referencia nenhuma conta de infraestrutura de staging/produção hoje (confirmado: nenhum arquivo de credencial, nenhum `.tfstate`, nenhuma referência a um provedor específico em `docs/`). Três opções, sem escolha forçada:

| Opção | Descrição | Trade-off |
|---|---|---|
| A. VM única self-hosted | Uma máquina (própria ou de um provedor genérico — DigitalOcean/Hetzner/EC2/etc.) rodando `docker compose up`, mesma composição do `docker-compose.yml` atual | Menor custo, menor novidade tecnológica; requer alguém responsável por patch/uptime da VM |
| B. Ambiente gerenciado de containers (ex.: um único serviço tipo Fly.io/Render/Railway, sem orquestração própria) | Mesmas imagens Docker, hospedagem gerida pelo provedor | Menos operação manual; introduz uma dependência de plataforma nova (ainda que não seja Kubernetes) |
| C. Mesma conta/infraestrutura já usada para CI (se existir alguma capacidade de execução persistente lá) | Reaproveita o que já existe | Só é viável se essa capacidade existir e for isolada de produção — não confirmado neste repositório |

**Recomendação do Tech Lead:** Opção A (VM única self-hosted rodando `docker compose`) — é a que introduz zero tecnologia nova além do que o W7-5 já decidiu, e é reversível/trivial de descartar. A escolha final do provedor/conta específico é uma decisão de procurement/infraestrutura do Founder/CTO, não uma decisão de arquitetura de software — **elevada aqui, não decidida silenciosamente**, e não bloqueia a produção deste Technical Design (bloqueia apenas o provisionamento real, que não está autorizado nesta missão de qualquer forma).

---

## 3. Pergunta 2 — Topologia mínima

Staging usa exatamente a mesma topologia de 3 serviços que produção já usa em `docker-compose.yml` — nenhum serviço novo, nenhuma duplicação de arquitetura:

```
┌─────────────┐      ┌─────────────┐      ┌──────────────────────┐
│   web        │ ---> │   api        │ ---> │  database             │
│ (Next.js,    │ BFF  │ (FastAPI/    │ SQL  │  (pgvector/pgvector:  │
│  standalone) │      │  Uvicorn)    │      │  pg16, migrations     │
│  porta 3000  │      │  porta 8000  │      │  0001-0020)           │
└─────────────┘      └─────────────┘      └──────────────────────┘
```

- **Isolamento de rede**: staging roda em um host (ou conta) **distinto** de produção — nunca a mesma instância de banco, nunca o mesmo `docker-compose` project name. Nenhum dado de produção é copiado para staging (AR-18 §7, "banco dedicado... sem dados de produção").
- **Sem serviço adicional**: nenhum load balancer dedicado, nenhum cache distribuído, nenhuma fila de mensagens — nenhuma Capability real hoje depende deles (confirmado: nenhuma dessas dependências aparece em `docker-compose.yml`, `requirements.txt`, ou `package.json`).
- **Acesso controlado**: staging não é publicamente exposto — ambiente de validação interna (AR-18 §7, última linha), consistente com a proibição explícita desta missão de não usar credenciais de produção nem iniciar validação real.

---

## 4. Pergunta 3 — Quais serviços/dependências precisam existir

Derivado diretamente do Configuration Contract (W7-5 Etapa 1) e do Production AI Validation Model (AR-18 §8):

| Dependência | Estado hoje | O que falta para staging |
|---|---|---|
| PostgreSQL + pgvector | Código pronto (`pgvector/pgvector:pg16`, 20 migrations testadas) | Uma instância real, isolada, com as 20 migrations aplicadas do zero (não apenas em CI) |
| LLM provider real (Anthropic) | **Código pronto** — `ProductionLLMProvider` (`src/llm/providers/production_provider.py`), fail-closed sem `ANTHROPIC_API_KEY` por design, camadas 1-2 do Production AI Validation Model já satisfeitas | Uma chave Anthropic real de uso restrito a staging (nunca a chave de produção), e a execução real (camadas 3-7, nunca feitas) |
| Embedding provider real | **Código não existe.** `src/services/knowledge_platform/embedding_provider.py` só implementa `MockEmbeddingProvider` — qualquer `EMBEDDING_PROVIDER` diferente de `"mock"` levanta `EmbeddingProviderConfigError` hoje, deliberadamente (TD-011, ainda aberto) | **Bloqueio real, não contornável por este Technical Design**: um backend de embedding de produção precisa ser *escolhido* (Founder Decision, elevada em AR-18 e ainda não tomada) e *implementado* (código novo) antes de qualquer validação real de embedding poder ocorrer. Ver §7 |
| Frontend (BFF) | Código pronto (W7-5 Etapa 4, `web/Dockerfile`, serviço `web`) | Deploy real apontado ao `api` de staging via `BACKEND_URL` |
| Migrations | Código pronto, 20 migrations testadas em CI (Postgres real) | Execução real fora de CI, como etapa isolada do deploy (`PRI-009` §2 passo 3) |
| Observability mínima | `correlation_id` já estabelecido e reutilizado em 15+ arquivos de domínio/evento/workflow — **mas confirmado ausente** em `ai_foundation/observability.py`, `ai_foundation/audit_integration.py` e `executive_orchestrator/orchestrator.py` (achado original de D-169, nunca corrigido) | Esse gap específico precisa ser fechado antes da validação real de uma Capability de Executive Intelligence ser diagnosticável ponta a ponta em staging (AR-18 §7, "Observability... para permitir diagnóstico") |

---

## 5. Pergunta 4 — Quais secrets/configurações serão necessários

Catálogo derivado diretamente de `collect_startup_config_problems()` (backend) e `collectStartupConfigProblems()` (frontend) — nenhuma variável nova é inventada aqui, apenas populada com valores reais de staging:

| Variável | Camada | Natureza | Fonte em staging |
|---|---|---|---|
| `ENVIRONMENT=staging` | Backend + Frontend | Config | Fixa por definição |
| `DATABASE_URL` | Backend | Segredo (credencial de conexão) | Apontando para o Postgres real de staging, nunca SQLite, nunca o banco de produção |
| `API_KEY` | Backend | Segredo | Valor próprio de staging, nunca reaproveitado de dev ou produção |
| `LLM_PROVIDER=anthropic` | Backend | Config | Fixo |
| `ANTHROPIC_API_KEY` | Backend | Segredo | **Chave própria de staging**, com limite de uso/orçamento monitorável separadamente da chave de produção (quando esta existir) |
| `EMBEDDING_PROVIDER` | Backend | Config | Bloqueado até a decisão de §7 — hoje só `mock` é aceito, que W7-1 não pode usar em staging (proibido pelo próprio Configuration Contract fora do dev) |
| `CORS_ALLOWED_ORIGINS` | Backend | Config | Origem real do frontend de staging |
| `BACKEND_URL` | Frontend | Config | URL real do `api` de staging |
| `SESSION_SECRET` | Frontend | Segredo | Valor próprio de staging |
| `WORKSPACE_PASSWORD` | Frontend | Segredo | Valor próprio de staging, nunca a senha de produção |
| `RELEASE_SHA`/`GIT_SHA` | Backend + Frontend | Metadado (não segredo) | Gerado automaticamente pelo build (`git rev-parse HEAD`) |

**Nenhum secrets manager é introduzido** — decisão já tomada e reafirmada no Technical Design W7-5 (§7, Secrets Boundaries), sem necessidade demonstrada de mudança aqui. Distribuição de segredos reais de staging é responsabilidade operacional de quem provisionar o ambiente (fora do escopo desta missão) — variáveis de ambiente no host escolhido (§2), nunca commitadas, nunca reaproveitadas de `.env` de desenvolvimento (AR-18 §7, "secrets próprios").

---

## 6. Pergunta 5 — Protocolo de validação com LLM + embeddings reais

**Este protocolo é definido aqui, mas não é executado nesta missão.** Ele passa a ser executável no momento em que staging existir (fora do escopo desta missão) e as pré-condições de §4/§7 estiverem satisfeitas.

### 6.1 Validação de LLM real (camadas 3-7 de AR-18 §8, aplicadas a LLM)

1. **Infraestrutura preparada** (camada 3): staging operacional per §2/§3, `ENVIRONMENT=staging` validado no boot (`GET /ready` retorna `200`).
2. **Ambiente disponível** (camada 4): `ANTHROPIC_API_KEY` real de staging configurada; `GET /ready` confirma ausência de problemas de configuração.
3. **Integração configurada** (camada 5): uma chamada de smoke manual e isolada a `ProductionLLMProvider.generate()` (via qualquer rota que já a exercite — ex.: `POST /api/risk-advisor/ask`) com um prompt trivial, confirmando que a chave real responde e que `TokenUsage` é populado.
4. **Execução real** (camada 6): exercitar **uma Capability real de Executive Intelligence ponta a ponta** contra dados reais de staging (não fixtures) — candidato natural: `POST /api/risk-advisor/ask` ou `POST /api/decision-support` (ambos já usam `AdvisorFramework`/`ExecutiveOrchestrator` reais). Critério de sucesso: resposta com citação de evidência real, sem erro, `correlation_id` presente nos logs (sujeito ao fechamento do gap de observability, §4).
5. **Evidência de validação** (camada 7): registrar, neste mesmo diretório de governança, o `release` (`GET /health`), o timestamp, a rota exercitada, o `correlation_id` (ou sua ausência confirmada como gap, se ainda não fechado), e a resposta obtida — nunca "funcionou" sem artefato.

### 6.2 Validação de embedding real (camadas 3-7, aplicadas a embedding) — **bloqueada até §7 ser resolvido**

Idêntica em estrutura à validação de LLM, mas **não pode começar pela camada 3** porque a camada 1 (código) não existe hoje. Uma vez o backend de produção escolhido e implementado (§7):

1. **Infraestrutura preparada**: `EMBEDDING_PROVIDER=<backend-escolhido>` aceito por `get_embedding_provider()` sem levantar `EmbeddingProviderConfigError`.
2. **Ambiente disponível**: credencial real do backend de embedding (se aplicável) configurada em staging.
3. **Integração configurada**: uma chamada de smoke isolada a `embed()` com um texto trivial, confirmando dimensão do vetor (`KNOWLEDGE_EMBEDDING_DIM`) e resposta real do backend.
4. **Execução real**: `POST /documents` com um documento real (não fixture) seguido de `POST /api/document-advisor/ask` com uma pergunta real sobre esse documento — exercita ingestão (embedding na escrita) e RAG (embedding na leitura + busca vetorial `pgvector`) de ponta a ponta.
5. **Evidência de validação**: mesmo padrão de registro do item 6.1.5.

### 6.3 Readiness e Smoke Test como parte do protocolo

Antes de qualquer validação de LLM/embedding: `GET /ready` deve responder `200` (readiness verde, W7-5 Etapa 2) e `npx playwright test e2e/smoke.spec.ts` com `PLAYWRIGHT_BASE_URL`/`SMOKE_BACKEND_URL`/`SMOKE_LOGIN_*` apontados para staging deve passar (W7-5 Etapa 6) — ambos já implementados, nenhuma mudança de código necessária para executá-los contra staging quando ela existir.

---

## 7. Bloqueio explícito, elevado e não resolvido por este Technical Design

**Backend de embedding de produção não está escolhido.** Esta é a mesma questão que AR-18 já elevou como Founder Decision e que D-171 absorveu formalmente em W7-1 (TD-011 → W7-1). Este Technical Design **não a resolve** — apenas confirma, com grounding em código real (`embedding_provider.py`), que:

- nenhuma implementação de produção existe hoje, apenas `MockEmbeddingProvider`;
- a validação real de embedding (§6.2) está estruturalmente bloqueada até essa escolha ser feita e implementada;
- a validação real de LLM (§6.1) **não depende** dessa escolha e pode prosseguir independentemente, uma vez staging exista — confirma a paralelização já identificada em AR-18 §16 ("validação de LLM e de embedding podem correr em paralelo uma vez o ambiente existir").

Este Technical Design não inventa uma resposta para essa Founder Decision. Ela precisa ser tomada antes da Etapa de validação real de embedding (não antes da Etapa de validação de LLM, nem antes deste próprio documento).

---

## 8. O que não foi feito nesta missão (verbatim das restrições do Founder)

- Nenhum staging foi provisionado.
- Nenhum deployment foi executado.
- Nenhuma credencial de produção foi utilizada.
- Nenhuma validação real com LLM ou embeddings reais foi iniciada.
- Nenhuma infraestrutura foi escolhida de forma definitiva — apenas requisitos e opções, com a escolha final do host real elevada ao Founder (§2).
- Nenhum backend de embedding de produção foi escolhido (§7) — permanece Founder Decision aberta.

---

## 9. Critérios de encerramento deste Technical Design

1. ✅ Grounding real no que o W7-5 entregou (§1), sem re-derivar contratos já existentes.
2. ✅ As 5 perguntas mandatadas respondidas (§2-§6), incluindo elevação explícita (não silenciosa) de duas decisões que este documento não pode tomar sozinho: host real de staging (§2) e backend de embedding de produção (§7).
3. ✅ Protocolo de validação de LLM e de embedding definidos com critério de sucesso e evidência exigida, prontos para execução futura — nenhum executado agora.
4. ✅ Nenhuma ação proibida executada.

**Veredito: GO para que o Founder decida o host de staging (§2).** A validação de embedding real permanece bloqueada até a Founder Decision de §7 ser tomada. Nenhum provisionamento, deployment ou validação real inicia automaticamente. Retornando obrigatoriamente para Executive Review.
