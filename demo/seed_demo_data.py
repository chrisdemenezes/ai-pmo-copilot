#!/usr/bin/env python3
"""DPS-01 Sprint 2 -- seeds the fictitious demo portfolio via the real API, using
Demo Mode (src/llm/providers/mock_provider.py, MOCK_LLM_RESPONSE_FILE) to produce
schema-conformant structured output with no external LLM credential.

For each project, this script writes the target JSON to $MOCK_LLM_RESPONSE_FILE and
then calls the real endpoint. The backend's MockLLMProvider reads that file fresh on
each request, so the same real ProjectStatusAgent / RiskReviewAgent / AnalysisRepository
path runs as in production -- only the source of the model's text output changes.

If LLM_PROVIDER=anthropic is active instead (real Claude), this script sends the raw
project context and lets the real model decide the output, exactly like production.

Usage:
    python3 demo/seed_demo_data.py
"""
from __future__ import annotations

import json
import os
import sys

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "demo-local-secret-key")
MOCK_LLM_RESPONSE_FILE = os.environ.get("MOCK_LLM_RESPONSE_FILE")
DEMO_MODE = bool(MOCK_LLM_RESPONSE_FILE)

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

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

# (project_name, project_context, target status response, target risk response or None)
PROJECTS: list[tuple[str, str, dict, dict | None]] = [
    (
        SAP_PROJECT,
        SAP_CONTEXT,
        {
            "health_status": "red",
            "key_findings": [
                "Atraso de 6 semanas no conector fiscal do fornecedor de middleware bloqueia os modulos Financeiro e Faturamento",
                "40% dos usuarios-chave ainda nao completaram o treinamento obrigatorio, a 6 semanas do go-live original",
                "Dois dos cinco consultores seniores do fornecedor foram realocados sem substituicao confirmada",
                "92% do orcamento aprovado ja consumido, com 40% do escopo ainda pendente de validacao",
            ],
            "recommendations": [
                "Escalar formalmente o atraso do conector fiscal ao patrocinador executivo do fornecedor",
                "Reavaliar o cronograma de go-live antes da proxima reuniao de escalonamento",
                "Confirmar a substituicao dos consultores seniores realocados como pre-condicao para seguir com os testes de integracao",
            ],
        },
        {
            "risks": [
                {
                    "description": "Atraso do conector fiscal do fornecedor de middleware",
                    "probability": "high",
                    "impact": "high",
                    "mitigation": "Escalar ao patrocinador executivo do fornecedor e negociar entrega parcial do conector",
                },
                {
                    "description": "Usuarios-chave sem treinamento concluido antes do go-live",
                    "probability": "high",
                    "impact": "medium",
                    "mitigation": "Priorizar treinamento dos perfis criticos de Financeiro e Faturamento nas proximas 4 semanas",
                },
                {
                    "description": "Reducao da equipe senior do fornecedor sem substituicao",
                    "probability": "medium",
                    "impact": "high",
                    "mitigation": "Exigir plano de substituicao formal como condicao contratual antes de prosseguir",
                },
                {
                    "description": "Estouro de orcamento antes da conclusao do escopo",
                    "probability": "high",
                    "impact": "high",
                    "mitigation": "Replanejar o escopo remanescente com o patrocinador antes da proxima liberacao de verba",
                },
            ],
            "escalation_recommendation": "Escalar ao comite executivo antes do go-live -- o risco combinado de atraso do fornecedor, lacuna de treinamento e estouro de orcamento compromete a data planejada.",
        },
    ),
    (
        "Migracao de Data Center",
        """
Projeto: Migracao de Data Center. Fase atual: migracao de cargas de trabalho nao
criticas, dentro do cronograma planejado. Um fornecedor de rede reportou um atraso de
5 dias na entrega de um circuito redundante, sem impacto no caminho critico ate o
momento. Equipe completa, sem rotatividade no ultimo trimestre.
""".strip(),
        {
            "health_status": "yellow",
            "key_findings": [
                "Atraso de 5 dias na entrega de um circuito de rede redundante",
                "Sem impacto no caminho critico do cronograma ate o momento",
            ],
            "recommendations": [
                "Monitorar o fornecedor de rede nas proximas 2 semanas",
                "Preparar plano de contingencia caso o atraso se estenda",
            ],
        },
        None,
    ),
    (
        "Portal do Cliente 2.0",
        """
Projeto: Portal do Cliente 2.0. Fase atual: homologacao com usuarios-piloto,
adiantado em relacao ao cronograma original. Todos os marcos das ultimas 8 semanas
foram entregues no prazo. Feedback dos usuarios-piloto majoritariamente positivo.
""".strip(),
        {
            "health_status": "green",
            "key_findings": [
                "Todos os marcos das ultimas 8 semanas entregues no prazo",
                "Feedback dos usuarios-piloto majoritariamente positivo",
            ],
            "recommendations": [
                "Manter o ritmo atual de entregas",
                "Preparar plano de lancamento para producao",
            ],
        },
        None,
    ),
    (
        "Programa de Governanca de Dados",
        """
Projeto: Programa de Governanca de Dados. Fase atual: definicao de politicas de
qualidade de dados, dentro do escopo e cronograma aprovados. Patrocinio executivo
ativo, sem pendencias de decisao ha mais de 30 dias.
""".strip(),
        {
            "health_status": "green",
            "key_findings": [
                "Patrocinio executivo ativo, sem pendencias de decisao ha mais de 30 dias",
                "Nenhum risco em aberto acima de severidade baixa",
            ],
            "recommendations": ["Manter a cadencia atual de governanca"],
        },
        None,
    ),
    (
        "Renovacao de Infraestrutura de Rede",
        """
Projeto: Renovacao de Infraestrutura de Rede. Fase atual: instalacao fisica de
equipamentos, dentro do cronograma. Sem dependencias externas pendentes.
""".strip(),
        {
            "health_status": "green",
            "key_findings": [
                "Instalacao fisica dentro do cronograma",
                "Equipe tecnica completa, sem dependencias externas pendentes",
            ],
            "recommendations": ["Manter o ritmo atual"],
        },
        None,
    ),
    (
        "Implantacao de CRM Regional",
        """
Projeto: Implantacao de CRM Regional. Fase atual: configuracao de fluxos de venda.
Um modulo de relatorios apresentou retrabalho apos revisao de requisitos, adicionando
aproximadamente 2 semanas ao cronograma original.
""".strip(),
        {
            "health_status": "yellow",
            "key_findings": [
                "Retrabalho no modulo de relatorios apos revisao de requisitos",
                "Aproximadamente 2 semanas adicionadas ao cronograma original",
            ],
            "recommendations": [
                "Confirmar o novo cronograma com o patrocinador",
                "Acompanhar de perto a conclusao do modulo de relatorios",
            ],
        },
        None,
    ),
]


def _write_mock_response(payload: dict) -> None:
    if not MOCK_LLM_RESPONSE_FILE:
        return
    with open(MOCK_LLM_RESPONSE_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def _post(path: str, payload: dict) -> dict:
    response = httpx.post(f"{BACKEND_URL}{path}", headers=HEADERS, json=payload, timeout=60.0)
    response.raise_for_status()
    return response.json()


def seed() -> int:
    mode = "Demo Mode (mock + response file)" if DEMO_MODE else "real provider (LLM_PROVIDER)"
    print(f"Seeding via {mode} at {BACKEND_URL}\n")
    failures = 0

    for project_name, context, status_target, risk_target in PROJECTS:
        print(f"== {project_name} ==")

        if DEMO_MODE:
            _write_mock_response(status_target)
        try:
            result = _post(
                "/api/projects/analyze",
                {"project_name": project_name, "project_context": context},
            )
            structured = result.get("model_output", {}).get("structured")
            print(f"  [status] structured={structured} health_status={result.get('model_output', {}).get('health_status')}")
            if not structured:
                failures += 1
        except httpx.HTTPStatusError as exc:
            print(f"  [status] HTTP {exc.response.status_code}: {exc.response.text}")
            failures += 1
        except httpx.HTTPError as exc:
            print(f"  [status] request failed: {exc}")
            failures += 1

        if risk_target is not None:
            if DEMO_MODE:
                _write_mock_response(risk_target)
            try:
                result = _post(
                    "/api/risks/analyze",
                    {"project_name": project_name, "project_context": context},
                )
                structured = result.get("model_output", {}).get("structured")
                risks = result.get("model_output", {}).get("risks", [])
                print(f"  [risk] structured={structured} risks={len(risks)}")
                if not structured:
                    failures += 1
            except httpx.HTTPStatusError as exc:
                print(f"  [risk] HTTP {exc.response.status_code}: {exc.response.text}")
                failures += 1
            except httpx.HTTPError as exc:
                print(f"  [risk] request failed: {exc}")
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
