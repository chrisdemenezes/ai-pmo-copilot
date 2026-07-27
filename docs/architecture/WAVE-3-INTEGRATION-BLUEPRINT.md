# Wave 3 Integration Blueprint

**Status:** Blueprint subordinado a `WAVE-3-DOMAIN-BLUEPRINT.md`. Nenhum Epic é implementado por este documento.
**Objetivo:** definir, em nível de Blueprint (não de Technical Design), como a Enterprise Knowledge Platform e os Enterprise Advisors se integram aos 10 domínios/módulos já existentes, preservando a regra de dependência unidirecional ("nenhuma seta sobe", `WAVE-3-DOMAIN-BLUEPRINT.md` §1) — os módulos existentes nunca importam Knowledge Platform/Advisor Framework diretamente; a integração ocorre sempre por leitura de metadados (Knowledge Platform lendo do domínio) ou por consumo opt-in de um Advisor (o domínio nunca é obrigado a chamar um Advisor).

---

## 1. Princípio de integração único

Para todos os 10 pontos abaixo, o mesmo padrão se aplica:

```
Módulo existente (Portfolio/Program/Project/...)
  ──produz metadado/evento──> Enterprise Knowledge Platform (ingestão, indexação)
  <──consome via Advisor (opt-in, síncrono, resposta a uma pergunta)── Enterprise Advisor
```

Nenhum módulo existente é alterado estruturalmente para "servir" a Knowledge Platform — a ingestão lê o que já existe (via os mesmos repositórios/serviços já implementados), nunca exige um novo campo obrigatório em uma entidade já em produção sem o mesmo rigor aditivo-primeiro de TD-008.

---

## 2. Portfolio

- **O que a Knowledge Platform ingere:** metadados de portfólio (nome, composição de programas/projetos) como contexto de escopo para Semantic Search — não o conteúdo de portfólio em si, que já é dado estruturado, não documento.
- **Advisor que consome:** Portfolio Advisor, Executive Advisor.
- **Regra:** leitura via `AnalysisRepository`/repositórios de Portfolio já existentes — nenhum acesso direto a tabela por um componente da Knowledge Platform.

## 3. Program

- **O que a Knowledge Platform ingere:** mesma lógica do Portfolio, um nível abaixo — metadados de programa como contexto de escopo.
- **Advisor que consome:** Portfolio Advisor, PMO Advisor.
- **Regra:** idêntica à do Portfolio — leitura via serviço/repositório existente.

## 4. Project

- **O que a Knowledge Platform ingere:** metadados de projeto (`project_id`, nome via `Project.name`/`analysis_display_name`) como escopo de ingestão de documentos relacionados a um projeto específico.
- **Advisor que consome:** Delivery Advisor, Risk Advisor (já existe), PMO Advisor.
- **Regra:** todo documento com escopo de projeto referencia `project_id` (nunca `project_name` como chave — mesma disciplina definitiva de TD-008 Etapa 4b: nome nunca volta a ser identidade).

## 5. Executive Dashboard

- **O que consome:** Executive Advisor sintetiza (nunca recalcula) os mesmos sinais já exibidos no Dashboard (V1) em linguagem natural.
- **Regra:** o Dashboard continua sendo a fonte de verdade visual; o Executive Advisor nunca introduz uma métrica que o Dashboard não exiba — qualquer nova métrica nasce no Dashboard primeiro (domínio), nunca no Advisor.

## 6. Decision Center

- **O que a Knowledge Platform ingere:** decisões já registradas (Decision Center/Decision Log) como memória de decisões (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §2.3) — ingestão lê o registro existente, nunca duplica o armazenamento da decisão.
- **Advisor que consome:** Governance Advisor, Executive Advisor, Strategy Advisor.
- **Regra:** a Knowledge Platform nunca se torna uma segunda fonte de verdade para decisões — ela indexa para busca semântica, o Decision Center permanece o sistema de registro.

## 7. Actions

- **O que a Knowledge Platform ingere:** ações abertas/fechadas como contexto operacional (memória operacional, `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §2.2, quando vinculadas a uma sessão de Advisor) ou como evidência estruturada (via `AIContextEngine`, já existente, sem mudança).
- **Advisor que consome:** Delivery Advisor, PMO Advisor.
- **Regra:** ações continuam sendo lidas via os serviços já existentes (`list_action_items` etc.) — a Knowledge Platform não reimplementa esse acesso.

## 8. Risks

- **O que consome:** Risk Advisor (já existe, inalterado) continua usando exclusivamente a Foundation; RAG é uma extensão **opcional** futura caso o Risk Advisor precise de contexto documental além de `AnalysisRecord` — não obrigatória nesta Wave.
- **Regra:** nenhuma mudança ao comportamento já provado em produção do Risk Advisor é implícita nesta integração — qualquer extensão é aditiva e opt-in.

## 9. Lessons Learned (Organizational Learnings)

- **O que a Knowledge Platform ingere:** lições aprendidas já registradas, como memória de aprendizados (`DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §2.4) — mesma regra do Decision Center: ingestão lê o registro existente, nunca duplica.
- **Advisor que consome:** PMO Advisor, Governance Advisor, Document Advisor (busca livre).

## 10. Workspace

- **O que a Knowledge Platform NUNCA faz:** ler ou escrever em `Executive Memory` (`web/lib/executive-memory/`) — ver checklist de colisão obrigatória, `DOMAIN-BLUEPRINT-ENTERPRISE-MEMORY-MODEL.md` §0. O Workspace continua servindo Executive Memory (V1) exatamente como hoje, sem qualquer dependência da Knowledge Platform.
- **O que pode integrar:** um Advisor pode ser oferecido como uma ação adicional dentro do Workspace (ex.: "perguntar ao Document Advisor sobre este projeto") — decisão de UI/Technical Design, não deste Blueprint; a arquitetura não impede, mas também não implementa isso agora.

## 11. AI Intelligence Layer (Digital PMO Intelligence Foundation)

- **Regra central, já estabelecida no documento mestre (Princípio 4):** a Foundation nunca é substituída. Toda integração de Knowledge Platform/Advisors com a Foundation ocorre por extensão aditiva — RAG como segunda fonte de `Evidence`, Advisor Framework invocando `AIContextEngine`/`RecommendationEngine`/`ExplanationEngine`/`render_analyst_prompt` exatamente como o Risk Advisor já faz.
- **Nenhum dos 10 pontos de integração acima cria um segundo caminho de composição de prompt, um segundo `PromptRegistry` ou um segundo `LLMProvider`.**

---

## 12. Critérios de evolução

1. **Toda nova ingestão de um módulo existente na Knowledge Platform é read-only em relação a esse módulo** — a ingestão nunca grava de volta no domínio; se um Advisor precisar produzir uma ação sobre um módulo existente (ex.: criar uma ação a partir de uma recomendação), essa escrita segue os serviços de domínio já existentes, nunca um caminho novo.
2. **Nenhum módulo existente passa a depender da Knowledge Platform ou de um Advisor para funcionar** — toda integração é consumida de forma opt-in; remover a Knowledge Platform inteira não pode quebrar Portfolio/Program/Project/Dashboard/Decision Center/Actions/Risks/Lessons Learned/Workspace.
3. **Toda nova integração segue o mesmo par ingestão-leitura → consumo-opt-in definido em §1** — nenhuma exceção ad-hoc por módulo.
