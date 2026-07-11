#!/usr/bin/env python3
"""DPS-01 Sprint 1 -- seeds the fictitious demo portfolio via the real API.

Calls the same three endpoints described in RFC-001 / docs/technical/04-api-design.md
(``/api/projects/analyze``, ``/api/risks/analyze``) with fictitious project text. No
new persistence path: every call goes through the real ProjectStatusAgent /
RiskReviewAgent and the real AnalysisRepository, exactly as production does.

A "project" is not a separate entity to create (see DPS-01 backlog note) -- it comes
into existence the moment the first analysis is saved under that project_name. This
script's only job is to make those calls with convincing, internally consistent text.

Usage:
    python3 demo/seed_demo_data.py
"""
from __future__ import annotations

import os
import sys

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "demo-local-secret-key")

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Protagonist -- the project the whole demo story (DPS-01 S2/S4) revolves around.
SAP_PROJECT = "Implantacao SAP S/4HANA"
SAP_CONTEXT = """
Projeto: Implantacao SAP S/4HANA. Fase atual: testes de integracao, semana 34 de 40
planejadas. O cronograma original previa go-live em 60 dias; o fornecedor de
integracao (middleware de pagamentos) comunicou nesta semana um atraso de pelo menos
6 semanas na entrega do conector fiscal, que bloqueia dois dos tres modulos criticos
(Financeiro e Faturamento). O time de mudanca organizacional reportou que 40% dos
usuarios-chave ainda nao completaram o treinamento obrigatorio. Dois dos cinco
consultores seniores do fornecedor foram realocados para outro cliente na semana
passada, sem substituicao confirmada. O orcamento aprovado ja foi 92% consumido, com
40% do escopo ainda pendente de validacao. O patrocinador executivo pediu uma reuniao
de escalonamento para a proxima semana.
""".strip()

RISK_CONTEXT = SAP_CONTEXT  # risk_review consumes the same real project context.

# Supporting portfolio -- mostly healthy, so W3/W5 read as a real portfolio, not a
# fabricated crisis (see DPS-01 Sec. 4, "Portfolio de apoio").
SUPPORTING_PROJECTS = [
    (
        "Migracao de Data Center",
        """
Projeto: Migracao de Data Center. Fase atual: migracao de cargas de trabalho nao
criticas, dentro do cronograma planejado. Um fornecedor de rede reportou um atraso de
5 dias na entrega de um circuito redundante, sem impacto no caminho critico ate o
momento. Equipe completa, sem rotatividade no ultimo trimestre. Orcamento consumido
proporcional ao progresso fisico.
""".strip(),
    ),
    (
        "Portal do Cliente 2.0",
        """
Projeto: Portal do Cliente 2.0. Fase atual: homologacao com usuarios-piloto,
adiantado em relacao ao cronograma original. Todos os marcos das ultimas 8 semanas
foram entregues no prazo. Feedback dos usuarios-piloto majoritariamente positivo,
sem bloqueios tecnicos abertos.
""".strip(),
    ),
    (
        "Programa de Governanca de Dados",
        """
Projeto: Programa de Governanca de Dados. Fase atual: definicao de politicas de
qualidade de dados, dentro do escopo e cronograma aprovados. Patrocinio executivo
ativo, sem pendencias de decisao ha mais de 30 dias. Nenhum risco em aberto acima de
severidade baixa.
""".strip(),
    ),
    (
        "Renovacao de Infraestrutura de Rede",
        """
Projeto: Renovacao de Infraestrutura de Rede. Fase atual: instalacao fisica de
equipamentos, dentro do cronograma. Sem dependencias externas pendentes. Equipe
tecnica completa.
""".strip(),
    ),
    (
        "Implantacao de CRM Regional",
        """
Projeto: Implantacao de CRM Regional. Fase atual: configuracao de fluxos de venda.
Um modulo de relatorios apresentou retrabalho apos revisao de requisitos, adicionando
aproximadamente 2 semanas ao cronograma original. Sem impacto orcamentario relevante
ate o momento. Time monitorando de perto.
""".strip(),
    ),
]


def _post(path: str, payload: dict) -> dict:
    url = f"{BACKEND_URL}{path}"
    response = httpx.post(url, headers=HEADERS, json=payload, timeout=60.0)
    response.raise_for_status()
    return response.json()


def seed() -> int:
    failures = 0

    print(f"== {SAP_PROJECT} (protagonista) ==")
    for path, payload, kind in [
        (
            "/api/projects/analyze",
            {"project_name": SAP_PROJECT, "project_context": SAP_CONTEXT},
            "status",
        ),
        (
            "/api/risks/analyze",
            {"project_name": SAP_PROJECT, "project_context": RISK_CONTEXT},
            "risk",
        ),
    ]:
        try:
            result = _post(path, payload)
            structured = result.get("model_output", {}).get("structured")
            print(f"  [{kind}] structured={structured} -> {result.get('model_output')}")
            if not structured:
                failures += 1
        except httpx.HTTPStatusError as exc:
            print(f"  [{kind}] HTTP {exc.response.status_code}: {exc.response.text}")
            failures += 1
        except httpx.HTTPError as exc:
            print(f"  [{kind}] request failed: {exc}")
            failures += 1

    for project_name, context in SUPPORTING_PROJECTS:
        print(f"== {project_name} ==")
        try:
            result = _post(
                "/api/projects/analyze",
                {"project_name": project_name, "project_context": context},
            )
            structured = result.get("model_output", {}).get("structured")
            print(f"  [status] structured={structured} -> {result.get('model_output')}")
            if not structured:
                failures += 1
        except httpx.HTTPStatusError as exc:
            print(f"  [status] HTTP {exc.response.status_code}: {exc.response.text}")
            failures += 1
        except httpx.HTTPError as exc:
            print(f"  [status] request failed: {exc}")
            failures += 1

    return failures


if __name__ == "__main__":
    failure_count = seed()
    if failure_count:
        print(f"\n{failure_count} call(s) did not produce structured output.")
        print("See demo/README.md -- Impedimento conhecido (provedor LLM).")
        sys.exit(1)
    print("\nAll calls produced structured output. Check the dashboard:")
    print(f"  curl -H 'X-API-Key: {API_KEY}' {BACKEND_URL}/api/portfolio/summary")
