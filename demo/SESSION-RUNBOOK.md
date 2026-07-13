# RC-1 — Runbook das 5 Sessões Reais de Validação

Runbook operacional curto para o facilitador. Não é um novo framework nem uma nova
automação — reúne, em ordem, os comandos que já existem em `demo/start-demo.sh`,
`demo/seed_demo_data.py` e `demo/stop-demo.sh` (verificado antes de escrever este
documento: os três scripts já cobrem tudo que uma automação precisaria cobrir; os
únicos passos abaixo sem um script dedicado -- reset do SQLite e checklist de saúde
-- são um único comando existente reaproveitado, não algo novo).

Usar junto com (não substituir): Protocolo de Validação, Instrumento de Captura
(Validation Report) e o roteiro do DPS-01 -- todos já existentes fora deste
repositório, referenciados em `docs/releases/ADR-012-founder-decision-release-0.3.md`.
Este runbook cobre só a parte técnica (subir/resetar/encerrar o ambiente); o
protocolo de observação da sessão em si vem desses documentos.

## 1. Iniciar o Demo Mode

```bash
bash demo/start-demo.sh
```

Aguardar as duas mensagens `is up` (backend e frontend). Na primeira execução cria
`demo/.env` a partir de `demo/.env.example` com um `SESSION_SECRET` gerado — já em
Demo Mode, nenhuma credencial externa necessária.

## 2. Resetar o SQLite (rodar sempre antes de semear, para começar do zero)

O banco do Demo Mode é o arquivo `ai_pmo_copilot.db` na raiz do repositório
(`src/database/repository.py`, padrão `sqlite:///./ai_pmo_copilot.db`, criado
relativo ao diretório de onde o `uvicorn` roda -- a raiz, conforme
`demo/start-demo.sh`). Não existe endpoint de reset; apagar o arquivo é o reset:

```bash
bash demo/stop-demo.sh
rm -f ai_pmo_copilot.db ai_pmo_copilot.db-wal ai_pmo_copilot.db-shm
bash demo/start-demo.sh
```

## 3. Semear os dados

```bash
python3 demo/seed_demo_data.py
```

Popula o portfólio fictício (Implantação SAP S/4HANA + 5 projetos de apoio) via
Demo Mode. Confirmar que as 6 linhas terminam com `structured=True` antes de
prosseguir -- se alguma vier `structured=False`, repetir o passo 2 e tentar de novo
antes de chamar o participante.

## 4. URLs da aplicação

| | |
|---|---|
| Login | `http://localhost:3000/entrar` |
| Dashboard | `http://localhost:3000/dashboard` |
| Backend (health) | `http://localhost:8000/health` |

## 5. Credencial de demonstração

Senha do workspace: `demo-local-password` (`WORKSPACE_PASSWORD` em `demo/.env`,
copiado de `demo/.env.example` na primeira execução do passo 1 -- confirmar que
não foi alterada antes da sessão).

## 6. Checklist de saúde (rodar antes de chamar o participante)

```bash
curl -sf http://localhost:8000/health && echo "backend OK"
curl -sf http://localhost:3000/entrar > /dev/null && echo "frontend OK"
```

Depois, abrir `http://localhost:3000/entrar` no navegador da sessão, logar, e
confirmar que o Dashboard carrega os 6 projetos fictícios antes de chamar o
participante. Isso não é um passo técnico novo -- é o mesmo dry-run que este Review
já executou contra o backend real.

## 7. Sequência exata da demonstração

O participante percorre a jornada oficial da RC-1, sem roteiro técnico -- só a
pergunta que ele quer responder sobre o projeto:

```
Login
  -> Dashboard
    -> Projetos
      -> Workspace de um projeto
        -> Analisar Projeto
          -> escolher aquilo que deseja compreender
            -> executar uma análise
              -> receber o Executive Brief
                -> compreender o próximo passo
                  -> voltar ao Dashboard e perceber os impactos
```

Regras de condução durante a rodada (Founder, registradas na aprovação do RC-1
Readiness Review): não explicar uma tela antes que o participante tente
compreendê-la; não perguntar "você gostou?"; registrar tempo até compreensão,
primeiro elemento que atrai atenção, perguntas/confusões/hesitações, e o momento em
que o participante verbaliza utilidade real; classificar cada observação como
evidência, não como decisão de produto. Nenhum texto, componente ou fluxo deve ser
alterado entre participantes.

## 8. Procedimento de encerramento

```bash
bash demo/stop-demo.sh
```

Atualizar somente o Validation Report existente com as observações da sessão -- não
produzir documento adicional, não implementar melhorias, não abrir Feature
Specification.

## 9. Restaurar o ambiente antes da sessão seguinte

Repetir os passos 2 e 3 (parar, apagar o `.db`, subir de novo, semear de novo) para
que o próximo participante encontre exatamente o mesmo estado inicial dos demais.
Não pular este passo entre sessões -- o SQLite é um arquivo persistente e o
histórico acumula silenciosamente se não for resetado (achado registrado no RC-1
Readiness Review).

## Interrupção por defeito crítico

Só um defeito crítico que impeça a continuidade da jornada justifica interromper
uma rodada. Nesse caso: parar, registrar evidência, classificar a severidade, e
aguardar decisão do Founder antes de qualquer correção.
