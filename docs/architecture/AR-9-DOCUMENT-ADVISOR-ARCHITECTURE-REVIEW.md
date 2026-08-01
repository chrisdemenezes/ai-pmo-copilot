# AR-9 — Document Advisor: Architecture Review (Document Ingestion + Contrato Genérico de Evidência)

**Autorização:** "Founder Decision — Document Advisor Architecture Review" (2026-07-30). Veredito do Founder sobre `DOMAIN-BLUEPRINT-DOCUMENT-ADVISOR.md`: **APPROVED CONDITIONALLY** — prosseguir para Architecture Review, resolvendo obrigatoriamente dois pontos antes de qualquer Technical Design: (1) Document Ingestion; (2) contrato genérico de evidências (rejeitando `chunk_id` dentro de `source_analysis_id`).

**Etapa do ciclo institucional:** 2 de 8 (Domain Blueprint concluído D-087 → **Architecture Review, este documento** → Founder Approval → Technical Design → ...). **Nenhum código, nenhuma migração, nenhum Technical Design produzido aqui**, per restrição explícita do Founder.

**Método:** toda conclusão é rastreável a código real — `src/services/ai_foundation/types.py`, `context_engine.py`, `recommendation_engine.py`, `explanation_engine.py`, `src/services/advisor_framework/framework.py`, `src/agents/risk_advisor/agent.py`, `src/services/knowledge_platform/knowledge_repository.py`, `src/database/models.py` (`AuditLog`, `Document`, `DocumentVersion`, `Chunk`), `src/workflows/document_indexed_workflow.py`, `src/api/dependencies.py::build_event_publisher()`.

---

## 0. Achados de grounding adicionais desta revisão (base para as duas decisões abaixo)

1. **`document.indexed` já está integralmente conectado ao Event/Workflow Pipeline em produção**, sem nenhuma mudança necessária: `build_event_publisher()` (`src/api/dependencies.py:30-43`) já registra `document_indexed_workflow.register(dispatcher, runtime)` — no momento em que qualquer chamador real invocar `KnowledgeRepository.index()`, o evento é publicado, despachado, e o `WorkflowRuntime` já rastreia a execução em `workflow_executions` (Epic W4-4, D-082). Nenhum trabalho de Event Pipeline resta para o Document Ingestion — apenas o caminho HTTP até `ingest()`/`index()`.
2. **`AuditLog` (`src/database/models.py:357-377`) já é o mecanismo de auditoria genérico da plataforma** (`action`/`entity_type`/`entity_id`/`details`, vocabulário `resource.verb`), reaproveitado sem alteração por `AIFoundationAudit.record_question()` (via `repository.administration.record_audit()`). O Document Ingestion reaproveita o mesmo mecanismo — nenhum novo sistema de auditoria.
3. **`sanitize_error()` (`src/workflows/execution_tracking.py:28-32`) já existe como função reaproveitável e independente de workflow** — `f"{type(exc).__name__}: {exc}"[:limite]`, nunca stack trace, nunca payload. Reaproveitável tal como está para o tratamento de erro do Document Ingestion.
4. **`KnowledgeRepository.get_document()`/`list_versions()` (`knowledge_repository.py:160-186`) já existem e já são tenant-scoped** — ambos retornam `None`/`[]` se `document.organization_id != organization_id`, mesmo padrão de isolamento já usado por `AnalysisRepository`. Cobrem a maior parte da "consulta de status" sem nenhum código novo no repositório; falta apenas um `chunk_count` por versão (extensão aditiva pequena, nível Technical Design).
5. **`Evidence.kind` (`src/services/ai_foundation/types.py`) não é lido em nenhum ponto downstream hoje** — confirmado por busca exaustiva (`grep -rn "\.kind\b" src/`): o único uso é `AnalysisRecord.kind`/`record.kind` (objetos ORM, não o dataclass `Evidence`). Nenhum Advisor, `RecommendationEngine` ou `ExplanationEngine` lê `evidence.kind`. **Isso significa que renomear/reestruturar este campo é seguro — zero comportamento observável depende dele hoje.**
6. **`RecommendationEngine.build()` é a única função que lê `Evidence.source_analysis_id`**, e o faz de forma estritamente posicional: `by_id = {item.source_analysis_id: item for item in evidence}`. Nenhuma outra função do Foundation/Framework acessa esse campo diretamente (confirmado por busca em `src/services/ai_foundation/`, `src/services/advisor_framework/`, `src/agents/risk_advisor/`).

Estes seis achados delimitam exatamente a superfície de mudança necessária — nenhuma suposição além deles.

---

## 1. Ponto 1 — Document Ingestion

### 1.1 Decisão: W5-0 (Epic habilitador) — não capability interna do Document Advisor

**Recomendação: Opção A — W5-0.**

| Critério | W5-0 (Epic habilitador separado) | Capability interna do Epic do Document Advisor |
|---|---|---|
| **Coesão de domínio** | Document Ingestion é Knowledge Platform (upload, storage, indexação, status, auditoria) — mesmo bounded context de `KnowledgeRepository`, nenhuma dependência de LLM/Advisor Framework | Mistura dois bounded contexts no mesmo Epic (Knowledge Platform + Advisor Framework), dificultando rastreabilidade de qual componente falhou |
| **Testabilidade/critério de entrega** | Critério de saída objetivo e independente de LLM: documento enviado → indexado → `document.indexed` publicado → pesquisável via RAG. Nenhuma dependência de comportamento de modelo de linguagem | Critério de saída do Epic ficaria condicionado a dois tipos de falha simultâneos (falha de ingestão vs. falha de síntese do Advisor), dificultando o Executive Review |
| **Dependência estrutural** | Document Advisor (W5-1) depende de W5-0 já estar completo e testado — sequenciamento explícito, sem ambiguidade | Dependência implícita dentro do mesmo Epic, risco de o Advisor ser "implementado" sem nunca ter sido exercitado com dado real |
| **Precedente institucional** | Mesmo padrão já usado nesta plataforma: Event Foundation (W4-1) antes do Workflow Runtime (W4-4) que o consome; Security Hardening Gate antes da continuação do trabalho de Advisors na Wave 3; Sessões (Item 5) antes de Convites (Item 6) | Não há precedente de uma capability de infraestrutura habilitadora entregue "dentro" do Epic que a consome nesta plataforma |
| **Diretriz do Founder (Wave 5 Kickoff)** | "Não otimizar para velocidade... arquitetura suficientemente sólida para que os sete Advisors sejam implementados sem revisões estruturais posteriores" — Document/Governance Advisor (ambos Classe D) reaproveitam o mesmo W5-0, nenhuma reconstrução necessária para o Governance Advisor futuro | Otimiza para menos cerimônia institucional às custas de reusabilidade para o próximo Advisor da Classe D |

**Justificativa consolidada:** Document Ingestion não é uma responsabilidade do Document Advisor — é uma responsabilidade da Knowledge Platform que o Document Advisor (e, no futuro, o Governance Advisor, também Classe D) consome. Tratá-la como Epic habilitador (W5-0) produz um artefato reutilizável antes do primeiro consumidor, exatamente o padrão institucional já validado nesta plataforma, com um critério de entrega funcional limpo e verificável sem depender de comportamento de LLM.

### 1.2 Fluxo funcional completo (W5-0 → W5-1)

```
Usuário autenticado (RBAC: permissão de escrita em conhecimento, ex. knowledge.document.write --
  nome definitivo é decisão de Technical Design, seguindo o padrão resource.verb já
  estabelecido em src/api/authorization.py)
   │
   ▼
POST /documents  (organization_id extraído do contexto de autenticação, nunca do payload --
  mesma disciplina de tenant isolation de toda rota administrativa existente)
   │
   ▼
KnowledgeRepository.ingest(organization_id, source_name, text, project_id=None)
   -- ZERO mudança de assinatura -- cria Document (se novo) + sempre uma nova DocumentVersion
   │  auditoria: AuditLog "document.uploaded" (reaproveita AIFoundationAudit/record_audit)
   ▼
KnowledgeRepository.index(document_id, correlation_id=context.request_id)
   -- ZERO mudança de assinatura -- chunking + embeddings + persiste Chunk rows
   │
   ├── sucesso ──► publica document.indexed (já acontece hoje, zero mudança)
   │                  │
   │                  ▼
   │              EventDispatcher (W4-1, inalterado) ──► WorkflowRuntime (W4-4, já registrado
   │                  em build_event_publisher(), inalterado) ──► workflow_executions rastreado
   │                  │
   │                  ▼
   │              auditoria: AuditLog "document.indexed" (reaproveita o mesmo mecanismo)
   │                  │
   │                  ▼
   │              chunk pesquisável via RagPipeline.retrieve() ──► Document Advisor (W5-1)
   │
   └── falha (ex.: EmbeddingProvider indisponível) ──► exceção original re-lançada ao chamador
                     (mesma disciplina de W4-4: nunca engolida) │
                     auditoria: AuditLog "document.index_failed" com sanitize_error(exc)
                     (reaproveita src/workflows/execution_tracking.py::sanitize_error, sem
                     duplicação) │
                     Document/DocumentVersion permanecem persistidos (ingest() já commitou
                     independentemente) -- estado "ingerido, não indexado" é de primeira
                     classe, nunca escondido -- retry possível re-chamando index()

GET /documents/{id}  -- consulta de status, reaproveitando get_document()/list_versions()
  (já tenant-scoped, já existentes) + chunk_count por versão (extensão aditiva pequena)
  → "ingerido" (versão existe, 0 chunks) | "indexado" (chunks > 0) | "falhou" (auditoria mostra
  document.index_failed mais recente sem document.indexed subsequente)

Interface mínima -- mesmo padrão de página administrativa já usado por Convites/Sessões/API
  Keys: formulário de envio + lista de documentos com status/chunk_count visíveis.
```

**Cobertura explícita dos 9 requisitos do Founder:** usuário autenticado ✓ (RBAC `require_permission`); organization scope ✓ (extraído do contexto, nunca do payload); Document/DocumentVersion ✓ (`ingest()`, zero mudança); ingestão ✓; indexação ✓ (`index()`, zero mudança); consulta de status ✓ (`get_document()`/`list_versions()` + chunk_count aditivo); auditoria ✓ (`AuditLog` reaproveitado); tratamento de erro ✓ (exceção nunca engolida + `sanitize_error()` reaproveitado + estado parcial de primeira classe); interface mínima ✓ (mesmo padrão administrativo já usado 3 vezes nesta plataforma).

### 1.3 Fora de escopo (reafirmado, sem mudança em relação ao Domain Blueprint)

Gestão documental completa, workflow de aprovação, OCR avançado, conectores externos, edição colaborativa, políticas complexas de retenção, automações documentais genéricas — nenhum destes é tocado por W5-0.

---

## 2. Ponto 2 — Contrato genérico de evidências

### 2.1 O problema, confirmado concretamente (não apenas teoricamente)

`RecommendationEngine.build()` hoje usa `Evidence.source_analysis_id` como única chave de correspondência de citação (achado §0.6). Usar `chunk_id` dentro desse campo funcionaria (`int` compatível), mas violaria a própria semântica do nome do campo — um chunk de documento não é um `AnalysisRecord`, exatamente como o Founder apontou. Esta revisão concorda integralmente e propõe a evolução aditiva abaixo.

### 2.2 Contrato definitivo recomendado

```python
@dataclass(frozen=True)
class Evidence:
    """One already-persisted, verifiable fact an Enterprise Advisor can cite.

    Generic across source systems (AR-9/D-088): `source_type` identifies
    which repository produced this fact (e.g. "analysis_record",
    "document_chunk"), `source_id` is that source's own primary key --
    never reinterpreted across types. `content` remains opaque to the
    Foundation on purpose -- only the Advisor that requested this evidence
    knows how to interpret it. `metadata` carries auxiliary, source-specific
    facts (created_at, document_id, score, ...) without inventing a new
    top-level field per future source_type.
    """
    source_type: str
    source_id: int
    source_label: str
    content: dict
    metadata: dict = field(default_factory=dict)
```

Campos exatamente conforme o mínimo mandatado pelo Founder (`source_type`, `source_id`, `source_label`, `content`, `metadata`) — nenhum campo especulativo adicional.

**Onde foram os campos antigos:**
- `source_analysis_id` → `source_id` (generalizado; para `AnalysisRecord`, continua sendo `record.id`; para chunk, é `chunk.chunk_id`).
- `kind` → **removido como campo de topo** (achado §0.5: nunca lido downstream) — quem ainda precisar da classificação de domínio (ex.: "risk") a encontra em `metadata["kind"]`, sem perda de informação, sem campo morto no contrato.
- `source_created_at` → movido para `metadata["created_at"]` — continua disponível para quem lê (`RiskAdvisorAgent` hoje monta `source_created_at` no JSON do prompt; passa a ler de `metadata["created_at"]`), mas deixa de ser um campo de primeira classe obrigatório para toda fonte futura que talvez não tenha essa noção.
- `summary` → `content`, per nomenclatura mandatada pelo Founder — mesma semântica opaca de sempre.

### 2.3 Uso concreto pelos dois produtores (Risk Advisor inalterado em comportamento; Document Advisor novo)

```python
# AIContextEngine.gather() -- AnalysisRecord (Risk Advisor e demais Classes A/B/C)
Evidence(
    source_type="analysis_record",
    source_id=record.id,
    source_label=f"AnalysisRecord#{record.id} ({kind})",
    content=model_output,
    metadata={"created_at": record.created_at, "kind": kind},
)

# Normalização de RAG -- Document/Governance Advisor (Classe D)
Evidence(
    source_type="document_chunk",
    source_id=chunk.chunk_id,
    source_label=f"Document {chunk.document_id} / Chunk {chunk.chunk_id}",
    content={"text": chunk.text},
    metadata={"document_id": chunk.document_id, "score": chunk.score,
              "created_at": chunk.document_version_created_at},
)
```

`RecommendationEngine.build()` muda apenas a chave de indexação (`item.source_analysis_id` → `item.source_id`) — **nenhuma mudança de lógica**, apenas de nome de campo:

```python
by_id = {item.source_id: item for item in evidence}
cited = [by_id[cited_id] for cited_id in cited_ids if cited_id in by_id]
```

### 2.4 Estratégia de compatibilidade com o Risk Advisor

`Evidence` é um dataclass interno (nunca persistido, nunca serializado para fora da plataforma) — não é um contrato público versionado, é um tipo interno com exatamente **dois pontos produtores** (`AIContextEngine.gather()`, e a nova normalização de RAG) e **um ponto consumidor genérico** (`RecommendationEngine.build()`), além de leitura direta pelo próprio Advisor (`RiskAdvisorAgent.advise()` lê `item.summary`/`item.source_analysis_id`/`item.source_created_at`). "Aditivo e compatível" aqui significa: **comportamento do Risk Advisor byte-for-byte idêntico após a mudança**, verificado pela suíte de testes já existente do Risk Advisor passando sem nenhuma alteração de expectativa — não significa preservar o nome do campo antigo (não há consumidor externo/público que dependa do nome `source_analysis_id`). Impacto de código, apenas nível de nomenclatura de campo, confinado a exatamente 3 arquivos:
- `src/services/ai_foundation/types.py` (definição do dataclass);
- `src/services/ai_foundation/context_engine.py` (produtor);
- `src/services/ai_foundation/recommendation_engine.py` (consumidor);
- `src/agents/risk_advisor/agent.py` (leitor: `item.summary`→`item.content`, `item.source_analysis_id`→`item.source_id`, `item.source_created_at`→`item.metadata["created_at"]`).

**Nenhuma mudança em `AdvisorFramework.run()`** — o portão anti-alucinação (`if not evidence:`) opera sobre a lista, nunca sobre os nomes de campo internos de cada item; permanece byte-for-byte idêntico. **Nenhuma mudança em `ExplanationEngine`** — `len(recommendation.cited_evidence)` não depende de nenhum campo específico de `Evidence`.

### 2.5 Isolamento organizacional

`Evidence` não carrega `organization_id` hoje, e esta revisão recomenda **não adicionar** esse campo — o isolamento é estrutural, garantido nos dois únicos pontos de construção, ambos já tenant-scoped: `AIContextEngine.gather(organization_id, ...)` (filtra por `organization_id` antes de construir qualquer `Evidence`) e a normalização de RAG, que opera sobre um `RagContext` já produzido por `RagPipeline.retrieve(organization_id, ...)`/`KnowledgeRepository.search(organization_id, ...)` — nenhum chunk de outra organização jamais chega a existir na lista de entrada. O Technical Design deve incluir um teste de isolamento explícito (mesmo padrão do Security Hardening Gate, D-045): chunk de uma organização nunca aparece em `Evidence` de outra.

---

## 3. Papel do `AIContextEngine` na normalização/consolidação (aplicação concreta de D-086)

A definição institucional oficial (D-086) já prevê explicitamente "normalizar, consolidar e estruturar evidências para consumo dos Enterprise Advisors" — não apenas coletar `AnalysisRecord`. Esta revisão aplica essa definição concretamente: **o envelope de `ScoredChunk` → `Evidence` (§2.3) é responsabilidade do `AIContextEngine`, não de cada Advisor individualmente.**

**Justificativa:** o Document Advisor e o futuro Governance Advisor (ambos Classe D, `AR-8` §4) precisariam do mesmo código de envelopamento se cada um o implementasse na própria etapa de Montagem de Contexto — duplicação direta, proibida por CLAUDE.md. Centralizar essa normalização em `AIContextEngine` (um método novo, puramente mecânico, sem interpretar `chunk.text`) atende ao mandato de D-086 e evita a duplicação.

**Divulgação explícita do impacto estrutural (per exigência do Founder):** isto **é** uma alteração estrutural pequena e não prevista no Domain Blueprint original (que assumia o envelopamento dentro da Montagem de Contexto de cada Advisor). O impacto concreto:

- `AIContextEngine` ganha um método novo, puro e sem estado adicional: `normalize_rag_evidence(rag_context: RagContext) -> list[Evidence]` — transforma cada `ScoredChunk` em um `Evidence(source_type="document_chunk", ...)` (§2.3), nunca interpreta `chunk.text`, nunca decide relevância (isso já foi decidido pelo `RagPipeline`/ranking).
- `AdvisorFramework` ganha um passthrough fino correspondente: `normalize_rag_evidence(rag_context) -> list[Evidence]`, mesmo padrão de `gather_context()`/`gather_rag_context()` — nenhuma lógica nova no Framework, apenas mais um método de acesso controlado.
- **Nenhuma mudança em `AdvisorFramework.run()`, `RecommendationEngine`, `ExplanationEngine`** além do já descrito em §2.4.
- A Montagem de Contexto do Document Advisor (Domain Blueprint §3) passa a ser: `rag_context = framework.gather_rag_context(...)`; `evidence = framework.normalize_rag_evidence(rag_context)`; `framework.run(document_advisor, session, question, evidence, rag_context)` — mais simples do que o desenho original do Domain Blueprint, que exigia cada Advisor construir `Evidence` manualmente.

Este é o único novo método de framework recomendado por esta revisão. Nenhum outro componente (`RagPipeline`, `KnowledgeRepository`, `VectorRepository`) muda.

---

## 4. Responsabilidades (Knowledge Platform / RAG / AdvisorFramework / Document Advisor)

| Responsabilidade | Componente | Mudança nesta revisão |
|---|---|---|
| Receber upload, criar Document/DocumentVersion | `KnowledgeRepository.ingest()` (rota nova em W5-0) | Nenhuma — rota nova, método zero mudado |
| Chunking, embeddings, indexação, publicar `document.indexed` | `KnowledgeRepository.index()` | Nenhuma |
| Consulta de status | `KnowledgeRepository.get_document()`/`list_versions()` (rota nova) | Aditiva: `chunk_count` por versão |
| Auditoria de upload/indexação/falha | `AuditLog` via `record_audit()` | Nenhuma — reaproveitado |
| Busca semântica | `RagPipeline.retrieve()` | Nenhuma |
| Envelopar chunk em `Evidence` (normalização) | `AIContextEngine.normalize_rag_evidence()` (**novo**) | Novo método, mecânico, sem interpretação de domínio |
| Acesso controlado a essa normalização | `AdvisorFramework.normalize_rag_evidence()` (**novo passthrough**) | Novo, mesmo padrão de `gather_context`/`gather_rag_context` |
| Portão anti-alucinação | `AdvisorFramework.run()` | Nenhuma mudança |
| Filtrar citação por `source_id` | `RecommendationEngine.build()` | Rename de campo apenas |
| Interpretar chunks, montar prompt, interpretar resposta do LLM | `DocumentAdvisorAgent.advise()` | Novo Advisor, mesma forma de `AdvisorContract` |

---

## 5. Riscos

1. **Estado parcial "ingerido, não indexado"** precisa de tratamento explícito na UI/rota de status (§1.2) — não é um risco de arquitetura, é um requisito de Technical Design já endereçado no fluxo acima.
2. **`chunk_count` por versão** exige uma pequena extensão a `DocumentVersionInfo`/`list_versions()` — aditiva, baixo risco, nível Technical Design.
3. **Naming definitivo da permissão RBAC** (`knowledge.document.write`/`.read`, sugestão desta revisão) — decisão de Technical Design, seguindo o padrão `resource.verb` já estabelecido.
4. **Governance Advisor (segundo consumidor futuro de `normalize_rag_evidence()`)** deve reutilizar o mesmo método sem generalizações adicionais — risco de generalização prematura se um terceiro Advisor de Classe D exigir uma forma diferente de normalização; resolver apenas quando esse Advisor real existir (mesmo princípio "Grounded before Generalized").

Nenhum risco listado bloqueia o avanço para Technical Design.

---

## 6. Plano incremental

1. **W5-0 — Document Ingestion (Epic habilitador):** Technical Design próprio → migração aditiva (`chunk_count`, se necessário) → rota `POST /documents` + `GET /documents`/`GET /documents/{id}` + RBAC + auditoria + página administrativa mínima → testes (upload→index→document.indexed→workflow_executions rastreado; falha de indexação preserva Document/DocumentVersion e audita erro sanitizado; tenant isolation) → Executive Review → Encerramento.
2. **Evolução do contrato `Evidence`** (§2, §3) — parte do Technical Design de W5-0 ou de um Technical Design curto e isolado precedente (decisão de sequenciamento fica para a etapa de Technical Design, não desta revisão) — inclui a migração do Risk Advisor com sua suíte de testes existente passando inalterada.
3. **W5-1 — Document Advisor:** Technical Design próprio (prompt, `no_evidence_answer` de domínio, `top_k`) → `DocumentAdvisorAgent` + rota `/document-advisor/ask` → testes (citação real, `no_evidence()`, tenant isolation, citação inventada descartada) → Executive Review → Encerramento do Epic.

---

## 7. Recomendação GO/NO-GO

**GO para Technical Design — de W5-0 primeiro, seguido pela evolução do contrato `Evidence`, seguido pelo Technical Design do Document Advisor (W5-1).**

Ambos os pontos mandatados pelo Founder foram resolvidos com evidência de código, sem introduzir infraestrutura especulativa: Document Ingestion torna-se um Epic habilitador (W5-0) com fluxo funcional completo grounded em métodos já existentes (`ingest()`/`index()`/`get_document()`/`list_versions()`) e mecanismos já existentes (`AuditLog`, `sanitize_error()`, Event/Workflow Pipeline já conectado); o contrato de `Evidence` evolui de forma aditiva e compatível (`source_type`/`source_id`/`source_label`/`content`/`metadata`), preservando o Risk Advisor, sem quebrar `RecommendationEngine`, sem alterar o portão anti-alucinação, com isolamento organizacional estrutural. O único impacto estrutural identificado — um método fino novo (`normalize_rag_evidence`) em `AIContextEngine`/`AdvisorFramework` — foi divulgado explicitamente, per exigência do Founder, e é justificado por evitar duplicação entre os dois futuros Advisors da Classe D.
