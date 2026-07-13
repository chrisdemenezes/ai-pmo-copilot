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

O Capítulo 00 é para preparar uma máquina nova (uma vez só); os Capítulos 1-9 são
o checklist do dia da sessão (repetido a cada rodada, já com a máquina pronta).

## Capítulo 00 — Preparação do Ambiente (uma vez por máquina)

Objetivo: qualquer desenvolvedor ou consultor, sem conhecimento prévio do projeto,
consegue preparar a plataforma numa máquina nova só seguindo esta seção. Passos
validados nesta sequência exata numa máquina Windows real (Git Bash/MINGW64) durante
a preparação da RC-1 -- os erros abaixo são os erros reais encontrados, não
hipotéticos.

### 0.1 Pré-requisitos

| Ferramenta | Versão | Por quê |
|---|---|---|
| Git | qualquer recente | clonar o repositório |
| Python | 3.11+ (CI usa 3.11) | backend (`src/`) |
| Node.js + npm | Node 22 (CI usa 22) | frontend (`web/`) |

Confirmar antes de prosseguir:

```bash
git --version
python3 --version
node --version
npm --version
```

Se qualquer um desses comandos não existir, instalar a ferramenta correspondente
antes de continuar -- nenhum passo abaixo funciona sem os quatro.

### 0.2 Clonar o repositório

```bash
git clone <URL do repositório> ai-pmo-copilot
cd ai-pmo-copilot
```

### 0.3 Instalar o backend (`src/`)

```bash
python3 -m pip install -r requirements.txt
```

Usar sempre `python3 -m pip`, nunca só `pip` -- em máquinas com mais de um Python
instalado (comum no Windows, com o Microsoft Store Python e outras instalações
convivendo), `pip` sozinho pode instalar num interpretador diferente do que
`python3` depois vai usar para rodar o backend, causando `ModuleNotFoundError`
mesmo com a instalação "concluída com sucesso".

**Atenção ao final do log de instalação:** se aparecer um aviso como

```
WARNING: The script uvicorn.exe is installed in 'C:\...\Scripts' which is not on PATH.
```

o comando `uvicorn` não vai ser encontrado depois, mesmo instalado corretamente
(ver Troubleshooting 0.6.2 abaixo).

### 0.4 Instalar o frontend (`web/`)

```bash
cd web
npm install
cd ..
```

Leva 1-2 minutos na primeira vez. Avisos de `npm warn` sobre vulnerabilidades
moderadas ou scripts pendentes de aprovação (`sharp`, `unrs-resolver`) são
conhecidos e não bloqueiam o funcionamento do Demo Mode -- não rodar
`npm audit fix --force` sem necessidade (pode trocar versões de dependências fora
do que já foi testado).

### 0.5 Criar o ambiente (`demo/.env`)

Não precisa criar manualmente -- `demo/start-demo.sh` cria `demo/.env` sozinho a
partir de `demo/.env.example` na primeira execução, com um `SESSION_SECRET`
gerado automaticamente. Já vem em Demo Mode (provider mock, sem custo, sem
credencial externa). Ver Capítulo 5 para a senha padrão gerada.

### 0.6 Verificação inicial

```bash
bash demo/start-demo.sh
```

Esperar as **duas** mensagens `is up` aparecerem (backend e frontend) antes de
digitar qualquer outro comando -- a primeira execução do frontend (Next.js
compilando pela primeira vez) pode levar até 1 minuto. Depois:

```bash
python3 demo/seed_demo_data.py
```

Confirmar que as 6 linhas terminam em `structured=True`. Se sim, a máquina está
pronta -- seguir para o Capítulo 1 nas próximas sessões. Se não, ver 0.7 abaixo.

### 0.7 Troubleshooting básico

Quando `demo/start-demo.sh` não imprimir "is up" para um dos dois serviços, **não
adivinhar** -- olhar o log real primeiro:

```bash
cat demo/logs/backend.log
cat demo/logs/frontend.log
```

Erros já encontrados e suas causas:

| Sintoma | Causa | Correção |
|---|---|---|
| `ModuleNotFoundError: No module named 'httpx'` ao rodar `seed_demo_data.py` | Passo 0.3 não foi rodado, ou foi rodado com `pip` de um Python diferente do `python3` | `python3 -m pip install -r requirements.txt` |
| `backend.log`: `uvicorn: command not found` | `pip install --user` colocou os `.exe` numa pasta fora do PATH (aviso no fim do 0.3) | Adicionar a pasta ao PATH desta sessão de terminal: `export PATH="$PATH:<pasta do aviso, em formato /c/Users/... no Git Bash>"`, depois `bash demo/stop-demo.sh && bash demo/start-demo.sh` de novo |
| `frontend.log`: `./node_modules/.bin/next: No such file or directory` | Passo 0.4 (`npm install` dentro de `web/`) não foi rodado | Rodar 0.4, depois `bash demo/stop-demo.sh && bash demo/start-demo.sh` |
| `seed_demo_data.py` devolve `WinError 10061` / `Connection refused` em todo projeto | Backend não está de pé de verdade, mesmo sem erro visível no terminal | Checar `demo/logs/backend.log` -- normalmente é um dos dois casos acima |
| Comandos colados de uma vez parecem se misturar/corromper no terminal (Git Bash/MINGW) | `start-demo.sh` ainda está no loop de espera (até ~90s) quando o próximo comando é digitado | Rodar um comando por vez, esperando o anterior terminar de imprimir antes do próximo |
| Porta 3000 ou 8000 já em uso / processo antigo travado | Uma sessão anterior não foi encerrada corretamente | `bash demo/stop-demo.sh` antes de tentar `start-demo.sh` de novo |

Se nenhum desses cobrir o problema, esse é o ponto de fazer a pergunta e agir --
o objetivo deste capítulo é eliminar a fricção conhecida, não adivinhar problemas
novos.

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
