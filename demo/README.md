# DPS-01 — Ambiente de Demonstração

Não é a Release 0.3. Não altera arquitetura, contratos de API ou o AI-PEF. Este
diretório contém apenas orquestração: os mesmos comandos (`uvicorn`, `next dev`,
chamadas HTTP aos endpoints reais) que já existem em `README.md` e `web/README.md`,
reunidos para subir com um passo único.

## Passo único

```bash
bash demo/start-demo.sh
```

Na primeira execução, cria `demo/.env` a partir de `demo/.env.example` (gitignored,
como qualquer `.env` no repositório) com um `SESSION_SECRET` gerado automaticamente.
Edite `demo/.env` para definir `ANTHROPIC_API_KEY` — ver "Impedimento conhecido"
abaixo.

Ao concluir:

```bash
bash demo/stop-demo.sh
```

## Checklist de execução da demonstração

1. `bash demo/start-demo.sh` — aguardar as duas mensagens "is up".
2. `python3 demo/seed_demo_data.py` — popula o portfólio fictício do DPS-01
   (Implantação SAP S/4HANA + 5 projetos de apoio). **Requer o impedimento abaixo
   resolvido.**
3. Abrir `http://localhost:3000/entrar`, senha em `demo/.env` (`WORKSPACE_PASSWORD`).
4. Abrir `http://localhost:3000/dashboard` — seguir o roteiro do DPS-01, Seção 8.
5. Ao final: `bash demo/stop-demo.sh`.

## Evidências (Sprint 1, validado nesta máquina em 2026-07-11)

- `GET /health` → `200 {"status":"healthy",...}` — backend real sobe sem Docker/Postgres (SQLite).
- `POST /api/bff/session` com senha correta → `200 {"authenticated":true}`, cookie `workspace_session` setado.
- `GET /api/bff/dashboard` sem cookie → `401 {"error":"unauthenticated",...}` — gate real, confirmado.
- `GET /api/bff/dashboard` com cookie válido, banco vazio → `200 []` — plumbing completo, ponta a ponta.
- `bash demo/stop-demo.sh` → portas 3000 e 8000 liberadas, confirmado com `lsof`.

**Login e Dashboard funcionam ponta a ponta hoje, sem nenhuma alteração de código.**

## Impedimento conhecido (provedor LLM)

A cadeia de análise de IA (`POST /api/projects/analyze`, `/api/risks/analyze`,
`/api/meetings/analyze`) está bloqueada neste ambiente por falta de credencial —
não é uma lacuna de desenvolvimento. Duas evidências reais, capturadas nesta sessão:

**Com `LLM_PROVIDER=anthropic` e sem `ANTHROPIC_API_KEY`** (configuração padrão deste `demo/.env.example`):

```
HTTP 503 {"error":"provider_config_error","detail":"ANTHROPIC_API_KEY is required for production LLM execution."}
```

Este ambiente de execução não possui uma `ANTHROPIC_API_KEY` disponível.

**Com `LLM_PROVIDER=mock`** (o padrão do restante do repositório, usado em dev/CI):

```
POST /api/projects/analyze -> 200, mas model_output = {"structured": false, "raw_output": "mock analysis output"}
GET  /api/portfolio/summary -> latest_health_status: null, open_risks: 0, pending_action_items: 0
```

O `MockLLMProvider` sempre devolve o texto fixo `"mock analysis output"`, que não é
JSON — `parse_structured_output` marca `structured: false`, e `ProjectSummaryService`
ignora registros não estruturados na agregação. O registro é salvo (`total_analyses`
sobe), mas o card do projeto fica sem saúde e sem contagem de riscos. Confirmado nesta
sessão com uma chamada real.

`MockLLMProvider` aceita um campo `response` configurável no construtor, mas
`src/llm/providers/factory.py` sempre instancia `MockLLMProvider()` sem argumentos —
não há hoje nenhuma variável de ambiente que permita injetar uma resposta mock
customizada por chamada.

### Duas saídas possíveis — decisão do Product Owner

1. **Fornecer uma `ANTHROPIC_API_KEY` real** neste ambiente. Zero alteração de
   código; resolve por configuração, como a diretriz da Sprint 1 pede.
2. **Autorizar uma alteração mínima e aditiva** em `src/llm/providers/factory.py`
   para ler um `MOCK_LLM_RESPONSE` opcional do ambiente e repassá-lo ao
   `MockLLMProvider`, preservando 100% do comportamento atual quando a variável não
   está definida. É código de produto — por instrução explícita da Sprint 1,
   qualquer necessidade dessa natureza deve interromper e aguardar autorização em
   vez de ser decidida unilateralmente.

Nenhuma das duas foi executada. `demo/seed_demo_data.py` está pronto e testado contra
ambos os modos de falha — falta apenas a decisão acima para produzir dados
estruturados de verdade.
