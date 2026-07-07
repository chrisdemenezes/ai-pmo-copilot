"""First end-to-end PMO workflow.

Reservado intencionalmente para a próxima fase do projeto
(orquestração multi-agente, conforme architecture/05-ai-orchestration-design.md).

Ainda não conectado ao MVP atual (src/api/routes/intelligence.py).
Não remover nem tratar como órfão em futuras reavaliações de débito técnico.
"""

class PMOWorkflow:
    def execute(self, document, ai, repository):
        return repository.save(ai.process(document))
