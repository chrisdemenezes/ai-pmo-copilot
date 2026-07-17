# STRATECH — Proposta Definitiva de Governança Git

- **Status:** PROPOSTA — aguardando aprovação do Founder em etapa própria de governança. **Nenhuma configuração foi aplicada no GitHub.**
- **Origem:** Repository Governance & Main Consolidation Audit (2026-07-17), Seções 10–15, consolidadas e revisadas após a diretriz do Founder sobre Baseline Histórica × Certificada.
- **Escopo:** Branch Protection, CODEOWNERS, estratégia de branches, estratégia de versionamento, política de Pull Requests.

---

## 1. Branch Protection da `main`

Aplicar via Settings → Branches (ou ruleset equivalente), somente após aprovação:

| Regra | Valor | Justificativa |
|---|---|---|
| Pull Request obrigatório | Sim, para toda mudança, inclusive de agentes | Fecha o vetor F-02: sem PR, o CI nunca executa; foi assim que o F-01 atravessou 55 commits invisível |
| Checks obrigatórios | `validate` (backend) e `frontend` | São os dois jobs do `ci.yml`; cobrem lint, testes, cobertura ≥80%, typecheck, build de produção e E2E |
| Force push | Bloqueado | Proteção do histórico compartilhado — princípio já formalizado pelo Founder |
| Exclusão da branch | Bloqueada | Idem |
| Branch atualizada antes do merge | Obrigatória | Garante que os checks rodaram contra o estado real pós-merge |
| Conversas resolvidas antes do merge | Obrigatória | Nenhum apontamento de revisão fica silenciosamente ignorado |
| Revisão aprovadora formal (1 review) | **Adiar** até haver um segundo colaborador humano | Com um único humano, o próprio ato de merge do Founder é a aprovação; exigir review formal agora criaria um passo burocrático sem revisor disponível |

## 2. CODEOWNERS

Criar `.github/CODEOWNERS` com uma única linha, **junto com a ativação da Branch Protection** (antes disso é inócuo):

```
* @chrisdemenezes
```

- Aprovação institucional exclusiva do Founder sobre qualquer arquivo — inclusive arquitetura (`docs/product/`), segurança (`.github/`, `src/api/security.py`) e operação (`scripts/`, runbooks).
- Sem usuários ou equipes inventados. Quando houver segundo colaborador, evoluir para entradas por área (ex.: `docs/product/ @chrisdemenezes` mantido exclusivo).
- Rastreabilidade: combinado com "require review from Code Owners" no futuro (quando review formal for ativado).

## 3. Estratégia de branches

| Branch | Finalidade | Origem | Destino | Duração | Encerramento |
|---|---|---|---|---|---|
| `main` | Estado oficial validado. **Sem commits diretos.** | — | — | permanente | — |
| `feature/<capability>` | Nova capacidade (V2: um épico ou incremento de release) | `main` | PR → `main` | dias–semanas | merge + exclusão |
| `fix/<descricao>` | Correção de defeito | `main` | PR → `main` | horas–dias | merge + exclusão |
| `chore/<descricao>` | Manutenção sem efeito de produto (CI, deps, gitignore) | `main` | PR → `main` | horas–dias | merge + exclusão |
| `docs/<descricao>` | Documentação (ex.: `docs/stratech-v2-blueprint`) | `main` | PR → `main` | dias | merge + exclusão |
| `release/<versao>` | Estabilização de release, quando necessária | `main` | PR → `main` + tag | curta | tag + merge + exclusão |
| `hotfix/<descricao>` | Correção urgente sobre release taggeada | tag ou `main` | PR → `main` (+ cherry-pick para `release/` ativa, se houver) | horas | merge + exclusão |

Regras complementares:

1. **Branches de agentes (Claude ou outros) seguem exatamente o mesmo processo** — mesmo PR, mesmos checks, mesma revisão. O prefixo `claude/` é aceitável como identificação de autoria, mas não confere nenhum atalho.
2. **Proibido manter uma única branch longa para todas as evoluções.** A branch `claude/stratech-permanent-principles-yjnm74` é a última desse padrão; após a consolidação, cada trabalho nasce em branch própria e curta.
3. **Documentação também entra por PR** — pode ser um PR leve, mas passa pelo mesmo portão (checks + aprovação).
4. **Hotfix:** só para defeito que afete usuário da baseline certificada; nasce do ponto mais próximo do defeito, PR com o rótulo `hotfix`, merge após checks verdes, tag `rc.N+1` (pré-1.0) ou `v1.0.x` (pós-1.0).
5. **Release:** branch `release/<versao>` apenas se houver necessidade real de estabilização paralela; enquanto o fluxo for linear, taggear direto na `main` após merge validado.

## 4. Estratégia de versionamento

Duas classes de baseline (diretriz do Founder, 2026-07-17):

- **Baseline Histórica** — registra o estado **como foi declarado à época**, com known-issues documentados na mensagem da tag. Fidelidade histórica; nunca reescrita.
- **Baseline Certificada** — primeiro commit com **todos** os gates verdes verificados em ambiente limpo. Referência de instalação, pilot, manutenção e hotfix.

Progressão proposta:

| Tag | Commit | Classe | Quando |
|---|---|---|---|
| `v1.0.0-rc.1` | `c97d37b` | Histórica | Após aprovação da etapa de governança (pós-merge) |
| `v1.0.0-rc.2` | commit da correção C-1 | Certificada | Idem |
| `v1.0.0` | a definir | Certificada | Após validação do Founder Pilot |
| `v2.0.0-alpha.1` | a definir | Certificada | Primeira implementação **real** da Release 0.1 da V2 — nunca por documentação |

Racional do `rc.2` (em vez de `rc.1+certified`): semver não ordena build metadata (`+...`) de forma confiável entre ferramentas; um RC que recebeu defect fix é semanticamente um novo candidato; e a gramática fica uniforme (defect fix sobre RC ⇒ `rc.N+1`).

Definições operacionais: **commit** = unidade de mudança · **branch** = linha de trabalho móvel · **tag** = nome imutável de um commit (sempre anotada, com mensagem-manifesto) · **release** = tag + notas publicadas · **baseline** = tag com papel de referência de auditoria (Histórica) ou de operação (Certificada) · **release candidate** = versão completa sob validação final, congelada exceto defect fix.

## 5. Política de Pull Requests

1. **Todo PR referencia sua origem de governança** (Capability, épico da V2, achado de auditoria, hotfix) no corpo.
2. **Corpo mínimo:** contexto · resumo das mudanças · testes executados com resultado · riscos · itens fora de escopo · estratégia de rollback. (PRs de documentação: versão reduzida — contexto, resumo, links verificados.)
3. **Método de merge padrão: merge commit** — preserva o histórico decisório; squash apenas para PRs triviais de um único assunto onde os commits intermediários não carregam informação (decisão caso a caso, nunca padrão); rebase merge proibido (reescreve SHAs que os documentos de governança citam).
4. **CI verde é pré-condição inegociável** — nenhum merge com checks falhando, nem "temporariamente".
5. **Aprovação formal do Founder** para: mudanças estruturais de arquitetura, segurança, CI/CD, modelo de dados, e qualquer coisa que toque a delimitação V1/V2. Na prática atual (um humano), todo merge é do Founder.
6. **Convenção de commits obrigatória (novos commits):** Conventional Commits com escopo — `feat(actions):`, `fix(auth):`, `docs(rc1):`, `test:`, `refactor:`, `chore:`, `ci(frontend):`, `build:`, `perf:`, `security:`. Uma intenção por commit; sem segredos; teste acompanha mudança de comportamento; docs atualizadas quando necessário; breaking change marcado com `!` e explicado no corpo. **Os 55 commits históricos não são renomeados nem reescritos.**
7. **PRs de agentes:** mesmo fluxo, mesma exigência de evidência; o agente nunca faz o próprio merge.

## 6. Ordem de adoção proposta

1. Aprovação desta política (etapa de governança própria);
2. Merge do PR de consolidação da V1 (já preparado, aguardando aprovação);
3. Ativação da Branch Protection + criação do CODEOWNERS (mesmo ato);
4. Criação das tags `v1.0.0-rc.1` (Histórica) e `v1.0.0-rc.2` (Certificada);
5. Exclusão da branch `claude/stratech-permanent-principles-yjnm74` (após validação da `main` e autorização);
6. Daqui em diante, todo trabalho novo nasce em branch curta própria sob esta política.
