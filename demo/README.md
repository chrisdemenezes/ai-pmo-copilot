# DPS-01 — Ambiente de Demonstração

Não é a Release 0.3. Não altera arquitetura, contratos de API ou o AI-PEF. Este
diretório contém orquestração (os mesmos comandos de `README.md` / `web/README.md`,
reunidos para subir com um passo único) e o Demo Mode: um modo de operação da
demonstração que reutiliza exatamente os mesmos endpoints e schemas de produção,
mudando apenas a fonte do texto que o `MockLLMProvider` devolve.

## Passo único

```bash
bash demo/start-demo.sh
```

Na primeira execução, cria `demo/.env` a partir de `demo/.env.example` (gitignored)
com um `SESSION_SECRET` gerado automaticamente. Já vem configurado em Demo Mode —
nenhuma credencial externa é necessária.

Ao concluir:

```bash
bash demo/stop-demo.sh
```

## Checklist de execução da demonstração

1. `bash demo/start-demo.sh` — aguardar as duas mensagens "is up".
2. `python3 demo/seed_demo_data.py` — popula o portfólio fictício do DPS-01
   (Implantação SAP S/4HANA + 5 projetos de apoio) via Demo Mode.
3. Abrir `http://localhost:3000/entrar`, senha em `demo/.env` (`WORKSPACE_PASSWORD`).
4. Abrir `http://localhost:3000/dashboard` — seguir o roteiro do DPS-01, Seção 8.
5. Ao final: `bash demo/stop-demo.sh`.

## Demo Mode

Capacidade adicionada na Sprint 2, classificada como **Demo Capability** (não uma
Feature de produto): um campo opcional e aditivo `response_file` em
`MockLLMProvider` (`src/llm/providers/mock_provider.py`), ligado por uma única
variável de ambiente nova, `MOCK_LLM_RESPONSE_FILE` (`src/llm/providers/factory.py`).
Quando ausente, o comportamento é idêntico ao de antes da Sprint 2 — usado hoje por
todo o restante do repositório (testes, CI, dev local) sem qualquer mudança.

`seed_demo_data.py` escreve o JSON estruturado de cada projeto nesse arquivo antes de
cada chamada real; o backend lê o arquivo a cada requisição e devolve o conteúdo como
se fosse a resposta do modelo. Da agregação em diante (`parse_structured_output`,
`ProjectSummaryService`, o Dashboard) é o mesmo fluxo de produção, sem nenhum atalho.

Nenhum contrato de API mudou, nenhum schema de saída mudou, nenhuma arquitetura
mudou, o `ProductionLLMProvider` não foi tocado. Para rodar a demo contra o Claude
real em vez do Demo Mode, basta trocar `LLM_PROVIDER=anthropic` e preencher
`ANTHROPIC_API_KEY` em `demo/.env` — `seed_demo_data.py` detecta automaticamente e
envia o contexto real em vez de escrever o arquivo de resposta.

## Evidências (Sprint 2, validado nesta máquina em 2026-07-11)

**Testes automatizados:**

```
ruff check src tests            -> All checks passed!
python3 -m pytest               -> 87 passed
```

7 testes novos: 3 em `test_mock_provider.py` (lê o arquivo, lê fresco a cada chamada,
comportamento inalterado quando ausente), 2 em `test_provider_factory.py`
(`response_file=None` por padrão, honra `MOCK_LLM_RESPONSE_FILE` quando definido).

**Seed real, ponta a ponta:**

```
== Implantacao SAP S/4HANA ==
  [status] structured=True health_status=red
  [risk] structured=True risks=4
== Migracao de Data Center ==     [status] structured=True health_status=yellow
== Portal do Cliente 2.0 ==       [status] structured=True health_status=green
== Programa de Governanca de Dados ==  [status] structured=True health_status=green
== Renovacao de Infraestrutura de Rede ==  [status] structured=True health_status=green
== Implantacao de CRM Regional == [status] structured=True health_status=yellow
```

`GET /api/portfolio/summary` e `GET /api/bff/dashboard` (via cookie de sessão real)
retornam exatamente os mesmos 6 registros, byte a byte.

**Dashboard real, capturado via Playwright** (login real, senha real, sessão real):
SAP S/4HANA no topo da distribuição CRÍTICO, 4 riscos identificados; distribuição de
saúde 3 SAUDÁVEL / 2 ATENÇÃO / 1 CRÍTICO; os 6 projetos renderizados na grade —
reproduz exatamente o Ato 2 do DPS-01 (Demo Story, Seção 2).

**Login e Dashboard continuam funcionando ponta a ponta, agora com a cadeia de IA completa, sem nenhuma credencial externa.**
