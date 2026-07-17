# STRATECH V1 — Encerramento Formal

- **Status:** **APROVADO** — Encerramento institucional da STRATECH V1, aprovado pelo Founder e incorporado à `main` em 17/07/2026. A linha V1 encontra-se em modo manutenção, sob Feature Freeze funcional permanente.
- **Data:** 2026-07-17
- **Revisão Estratégica:** aprovada
- **Merge institucional:** `e14cfa56c076b9bb5b55dcb1c5709e670dcce0d7` (PR #37, Merge Commit)
- **Linha V1:** manutenção · **V2:** implementação bloqueada
- **Pré-condições satisfeitas:** consolidação da `main` (PR #36 mesclado via Merge Commit), validação pós-merge integral, tags de baseline publicadas e validadas.

---

## 1. Baselines oficiais

| Baseline | Tag | Commit | Papel |
|---|---|---|---|
| **Histórica** | `v1.0.0-rc.1` | `c97d37b` | O RC-1 como declarado e encerrado à época (2026-07-17), com o F-01 registrado como known-issue na mensagem da tag. Referência de auditoria; **não recomendada para novas instalações**. |
| **Certificada** | `v1.0.0-rc.2` | `e53c21e3` (merge commit do PR #36) | Árvore integral consolidada na `main`: correção do F-01, relatório de auditoria e proposta de governança inclusos. Todos os gates verdes em ambiente limpo. **Referência oficial para instalação, pilot e manutenção.** |

**Merge commit oficial da consolidação:** `e53c21e3ea3fb234f6c2d06f052be8c8e14e0752` — parents `a1513c95` (main anterior) + `0f0db568` (head da branch de trabalho); 57 commits preservados.

## 2. Composição funcional da V1

Oito Capabilities, todas aprovadas por Executive Review e cobertas por testes:

1. **Análise de Status de Projeto** (Project Status) — análise estruturada com Evidence First
2. **Avaliação de Riscos** (Risk Review)
3. **Meeting Intelligence** — extração de compromissos/decisões de reuniões
4. **Ações** (TIP-008) — compromissos por urgência no Workspace, portfólio e Briefs
5. **Decision Center** (TIP-009) — Executive Decision Queue com sinais de Status e Risco
6. **Portfolio Intelligence** (TIP-010) — Executive Portfolio View em camadas
7. **Executive Memory** (TIP-011) — Mudou/Persistiu/Reapareceu + One Memory Insight Rule
8. **Organizational Intelligence** (TIP-012) — padrões recorrentes (Riscos e Ações), régua de 3+ ocorrências

Plataforma: FastAPI + SQLite/Alembic (backend), Next.js (frontend BFF), autenticação de workspace compartilhada (Nível 1, RFC-001), Demo Mode sem credencial externa, pacote de instalação local multiplataforma.

## 3. Gates de qualidade executados (baseline certificada)

| Gate | Resultado |
|---|---|
| `ruff check src tests` | limpo |
| `pytest --cov`, gate 80% | 114 passed, cobertura 98,91% |
| `alembic upgrade head` / `downgrade base` | limpo nos dois sentidos (banco novo) |
| API real: health + auth fail-closed | 200 / 401 / 200 |
| `tsc --noEmit` | limpo |
| `eslint` | limpo |
| `vitest run` | 400/400 |
| `npm run build` (produção) | limpo |
| `playwright --project=lg` | 67 passed / 1 skip esperado |
| Instalação local (`rc1-local-start.sh`) | executada de ponta a ponta |
| CI (PR #36) | `validate` + `frontend` verdes |

## 4. Known issues residuais

| Item | Severidade | Situação |
|---|---|---|
| 2 vulnerabilidades *moderate* no `npm audit` (postcss transitivo via Next) | Baixa | Pré-existente desde antes do RC-1; correção exige upgrade de Next (mudança de comportamento) — endereçar na janela V2 |
| Condicionante de privacidade e proteção de dados (LGPD) — ver detalhamento abaixo | Alta (condicionante de pilot, não defeito) | Registrada no Product Blueprint §8/§12 e no Pilot Readiness Checklist |
| Scripts Windows (.bat/.ps1) verificados por inspeção + validação de campo, sem cobertura de CI | Baixa | Aceito; CI roda em Linux |
| Autenticação de workspace compartilhada (sem usuário individual, sem RBAC) | Por design na V1 | Limite documentado; resolução é o núcleo da V2 Release 0.1 |

### 4.1 Condicionante de privacidade e proteção de dados (LGPD)

Até a formalização dos controles mínimos de privacidade, segurança e governança de dados, é **proibido** utilizar no Founder Pilot (ou em qualquer uso da linha V1):

- dados pessoais reais (art. 5º, I, LGPD);
- dados pessoais sensíveis (art. 5º, II, LGPD);
- dados identificáveis de clientes;
- dados identificáveis de colaboradores;
- documentos corporativos confidenciais;
- credenciais;
- segredos comerciais;
- dados produtivos não anonimizados.

A baseline certificada (`v1.0.0-rc.2`) **pode** ser utilizada para:

- instalação local;
- demonstração;
- validação técnica;
- testes;
- Founder Pilot com dados sintéticos, anonimizados ou formalmente controlados.

**A existência da tag não autoriza, por consequência automática, piloto externo nem uso de dados reais.** Essas autorizações exigem decisão formal específica do Founder, precedida do endereçamento do gap de LGPD.

## 5. Política de manutenção da V1

1. **A V1 entra em modo manutenção:** nenhuma nova funcionalidade, nenhuma nova Capability, nenhuma mudança de UX — o Feature Freeze declarado na Product Constitution (`b353ab0`) torna-se permanente para a linha V1.
2. **Categorias permitidas:** correção de defeito, correção de segurança, documentação, observabilidade — as mesmas do Feature Freeze do RC-1.
3. **Toda manutenção nasce de branch `fix/` ou `hotfix/`, entra por PR com CI verde e aprovação do Founder**, conforme a Git Governance Policy (quando aprovada).
4. **Dependências:** upgrades apenas por motivação de segurança, nunca por conveniência, sempre com a suíte completa verde antes/depois.

## 6. Critérios objetivos para hotfix

Um hotfix da V1 é justificado somente se **todos** os critérios abaixo forem verdadeiros:

1. Defeito reproduzível na baseline certificada (`v1.0.0-rc.2`) ou em release posterior da linha V1;
2. Afeta usuário real (Founder Pilot ou instalação local) em fluxo funcional, segurança ou integridade de dados — não apenas estética;
3. Sem workaround razoável documentável;
4. Correção possível dentro das categorias permitidas (sem nova funcionalidade);
5. Escopo mínimo demonstrável (diff pequeno, focado, com teste de regressão).

Processo: branch `hotfix/<descricao>` → PR → CI verde → aprovação do Founder → merge → tag `v1.0.0-rc.3` (pré-promoção) ou `v1.0.1` (pós-promoção).

## 7. Regra de Feature Freeze funcional permanente (V1)

**Definição formal:** nenhuma nova funcionalidade, capacidade, evolução de produto ou ampliação de escopo será incorporada à STRATECH V1. Permanecem autorizadas exclusivamente manutenções corretivas, de segurança, documentação e observabilidade, desde que atendam à política formal de manutenção e hotfix (Seções 5 e 6). O congelamento é **funcional** — não impede a manutenção governada; impede a evolução.

| Proibido | Permitido sob governança |
|---|---|
| Nova funcionalidade | Correção de defeito |
| Evolução funcional | Correção de segurança |
| Alteração de arquitetura | Atualização motivada por vulnerabilidade |
| Ampliação de escopo | Documentação |
| Antecipação de recurso da V2 | Observabilidade |
| — | Teste de regressão |

Qualquer necessidade funcional nova pertence à V2 e segue o Blueprint (`922b19e`) e seu processo de releases (0.1–0.5). Nenhuma mudança estrutural pode ser enquadrada como "correção" da V1 — a auditoria de consolidação é o precedente de fiscalização.

## 8. Regra de transição para a V2

1. **Referência arquitetural única:** Enterprise Architecture Blueprint v2.0 (commit `922b19e`) e seus 12 artefatos complementares;
2. **A V2 nasce em branches próprias** (`feature/...` por épico da Release 0.1), a partir da `main` consolidada — nunca da branch histórica de trabalho;
3. **RC-1/V1 permanece intocada como produto:** a V2 evolui o schema por migração (Alembic) preservando os dados de `analysis_records` (ADR-V2-002/003);
4. **Demo Mode e as 8 Capabilities continuam funcionais durante toda a transição** — critério de regressão permanente (Release 0.3 exige a suíte V1 verde);
5. **Nenhum pilot externo na V2** até segurança/segregação/governança mínimas (decisão formal do Founder na abertura do programa).

## 9. Recomendação de promoção futura para `v1.0.0`

Promover `v1.0.0-rc.2` → `v1.0.0` somente quando:

1. Founder Pilot concluído com parecer formal positivo (utilidade, UX, qualidade de análise);
2. Zero defeitos abertos de severidade alta na linha V1;
3. Known issues residuais reavaliados e formalmente aceitos ou resolvidos;
4. Decisão explícita do Founder registrada em documento de promoção.

Dois cenários de alvo para a tag `v1.0.0`:

- **Cenário A — sem alteração após o Founder Pilot:** `v1.0.0` poderá apontar para o mesmo commit de `v1.0.0-rc.2` (`e53c21e3`).
- **Cenário B — com hotfix antes da promoção:** `v1.0.0` deverá apontar para o commit do último hotfix formalmente validado. Nesse cenário, cada hotfix exige, cumulativamente: reprodução do defeito; correção mínima; teste de regressão; CI integralmente verde; validação da instalação; atualização das evidências; e aprovação explícita do Founder.

A tag `v1.0.0` **não** será criada nesta etapa. Enquanto a promoção não ocorrer, `v1.0.0-rc.2` permanece a referência operacional.

## 10. Procedimento canônico de criação e validação de tags anotadas

Procedimento permanente para qualquer tag futura da STRATECH (ex.: `v1.0.0-rc.3`, `v1.0.0`). As tags `v1.0.0-rc.1` e `v1.0.0-rc.2` já foram publicadas e validadas remotamente por este método (alvos confirmados via `git rev-list`). Princípios: nunca usar `git tag -f` às cegas, nunca usar `git push --force`, sempre inspecionar antes de publicar.

**Passos (Bash — Git Bash/Linux/macOS):**

```bash
# 1. Verificar se a tag existe localmente
git tag -l vX.Y.Z-rc.N

# 2. Se existir, inspecionar alvo e mensagem
git show vX.Y.Z-rc.N --no-patch

# 3. Excluir a tag local SOMENTE se estiver incorreta (alvo ou mensagem errados)
git tag -d vX.Y.Z-rc.N

# 4. Criar a tag anotada (sem -f), com a mensagem em arquivo
git tag -a vX.Y.Z-rc.N <SHA-completo-do-commit> -F mensagem.txt

# 5. Confirmar alvo e mensagem antes de publicar
git show vX.Y.Z-rc.N --no-patch

# 6. Publicar (NUNCA usar --force)
git push origin vX.Y.Z-rc.N
```

**Passos equivalentes (PowerShell — Windows):**

```powershell
# 1-3. Verificar, inspecionar e excluir somente se incorreta
git tag -l vX.Y.Z-rc.N
git show vX.Y.Z-rc.N --no-patch
git tag -d vX.Y.Z-rc.N   # somente se incorreta

# 4. Criar a tag anotada (sem -f); a mensagem em arquivo UTF-8
git tag -a vX.Y.Z-rc.N <SHA-completo-do-commit> -F mensagem.txt

# 5-6. Confirmar e publicar (nunca --force)
git show vX.Y.Z-rc.N --no-patch
git push origin vX.Y.Z-rc.N
```

**Validação remota correta:** `git ls-remote --tags origin` retorna, para uma tag anotada, o SHA do **objeto da tag** (não do commit) e, em uma segunda linha terminada em `^{}`, o SHA do commit-alvo dereferenciado. Por isso, a validação final deve dereferenciar explicitamente:

```bash
git fetch --tags origin
git rev-list -n 1 v1.0.0-rc.1   # esperado: c97d37be0b9f117c2e644f34ccfb36a5b2ceb79a
git rev-list -n 1 v1.0.0-rc.2   # esperado: e53c21e3ea3fb234f6c2d06f052be8c8e14e0752
```

**Registro de validação executada (2026-07-17):** ambas as tags publicadas, anotadas, com alvos dereferenciados confirmados exatamente nos SHAs esperados acima. As mensagens publicadas preservam: os commits-alvo, o caráter histórico da `rc.1`, o caráter certificado da `rc.2`, o registro transparente do F-01, e a confirmação de que a V2 é exclusivamente documental. As mensagens foram gravadas deliberadamente em ASCII sem acentuação — objetos de tag Git são imutáveis e a grafia sem acento evita corrupção de codificação entre Windows/Git Bash/Linux; o conteúdo material é o registrado na Seção 1 e no relatório de auditoria.

---

*Documento produzido após a consolidação da `main` (merge commit `e53c21e3`), validação pós-merge integral e publicação das tags de baseline. Aprovado pela Revisão Estratégica do Founder e incorporado institucionalmente à `main` pelo merge commit `e14cfa56` (PR #37) em 17/07/2026 — registro definitivo do encerramento da STRATECH V1.*
