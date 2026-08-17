#!/usr/bin/env python3
"""DPS-01 Sprint 2 -- seeds the fictitious demo portfolio via the real API, using
Demo Mode (src/llm/providers/mock_provider.py, MOCK_LLM_RESPONSE_FILE) to produce
schema-conformant structured output with no external LLM credential.

For each project, this script writes the target JSON to $MOCK_LLM_RESPONSE_FILE and
then calls the real endpoint. The backend's MockLLMProvider reads that file fresh on
each request, so the same real ProjectStatusAgent / RiskReviewAgent /
MeetingIntelligenceAgent / AnalysisRepository path runs as in production -- only the
source of the model's text output changes.

If LLM_PROVIDER=anthropic is active instead (real Claude), this script sends the raw
project context and lets the real model decide the output, exactly like production.

Authentication (Founder Decision, "Local V1 Pilot Dataset Completion"): the
/api/*/analyze and /api/documents routes require the same 3 institutional identity
headers (X-Stratech-User-Id / X-Stratech-Organization-Id / X-Stratech-Session-Id)
the real BFF resolves from a session cookie (web/lib/bff/domain-proxy.ts) -- this
script obtains them the same real way a human does: POST /api/auth/login, then reuse
the returned identity on every subsequent call. No bypass, no direct database write,
no special seed-only endpoint.

The bootstrapped Demo Mode user (demo@stratech.local, "Demo Organization") is
deliberately, permanently read-only -- bootstrap_demo_user() re-asserts the `viewer`
role on every backend boot by design (src/services/identity/auth_service.py), and
`viewer` correctly lacks `intelligence.write`/`knowledge.write` (RBAC catalog,
migrations 0010/0020). No API call from any identity can change that without an
existing administrator to grant it, and no administrator exists in "Demo Organization"
out of the box. This script therefore authenticates as the *Administrator* bootstrap
identity instead (STRATECH_ADMIN_EMAIL/STRATECH_ADMIN_PASSWORD ->
bootstrap_administrator(), already implemented, unrelated to this script until now) --
a real `organization_admin` in "Organizacao Principal" (organization_slug of
DEFAULT_ORGANIZATION_NAME, src/database/project_identity.py), the other organization
migration 0008 seeds with the same Enterprise Domain data. See
docs/product/governance/LOCAL-V1-PILOT-DATASET-EXECUTIVE-EVIDENCE.md for the full
mechanical diagnosis.

Usage:
    python3 demo/seed_demo_data.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx


def _load_env_file(path: Path) -> None:
    """Populate os.environ from a simple KEY=VALUE file, without overriding
    variables already set in the real environment. Avoids requiring the
    caller to remember to `source demo/.env` before running this script --
    start-demo.sh already sourced it for the backend/frontend processes, but
    that does not carry over to a separately invoked `python` process."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file(Path(__file__).parent / ".env")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "demo-local-secret-key")
MOCK_LLM_RESPONSE_FILE = os.environ.get("MOCK_LLM_RESPONSE_FILE")
DEMO_MODE = bool(MOCK_LLM_RESPONSE_FILE)

# Same Administrator bootstrap contract src/main.py's startup already calls
# (bootstrap_identities -> bootstrap_administrator when both are set) -- this
# script only ever *reads* these, never writes/persists them anywhere.
ADMIN_EMAIL = os.environ.get("STRATECH_ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("STRATECH_ADMIN_PASSWORD")
# Deterministic slug of DEFAULT_ORGANIZATION_NAME ("Organizacao Principal",
# src/database/project_identity.py's organization_slug()) -- frozen the same
# way migration 0008's own inline copy of SEED_ORGANIZATIONS is frozen, not
# recomputed here to avoid importing backend internals from this standalone
# script.
ADMIN_ORGANIZATION_SLUG = os.environ.get("ADMIN_ORGANIZATION_SLUG", "organizacao-principal")

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

# Texto verbatim compartilhado por >=3 projetos distintos -- gatilho real do
# Aprendizados Organizacionais (web/lib/organizational-intelligence/
# organizational-learnings.ts, MIN_OCCURRENCES=3, igualdade textual exata).
# Sem esse padrao recorrente, Aprendizados permanece vazio mesmo com Riscos e
# Acoes populados -- achado real desta missao, nao presumido.
RECURRING_RISK_DESCRIPTION = (
    "Dependencia de fornecedor externo sem plano de contingencia formalizado"
)
RECURRING_ACTION_DESCRIPTION = "Atualizar o cronograma consolidado no relatorio executivo mensal"

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
        {
            "risks": [
                {
                    "description": RECURRING_RISK_DESCRIPTION,
                    "probability": "medium",
                    "impact": "high",
                    "mitigation": "Negociar SLA de contingencia e identificar fornecedor alternativo para o circuito redundante",
                },
            ],
            "escalation_recommendation": "Monitorar o fornecedor de rede nas proximas 2 semanas; escalar apenas se o atraso ultrapassar o buffer do cronograma.",
        },
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
        {
            "risks": [
                {
                    "description": RECURRING_RISK_DESCRIPTION,
                    "probability": "medium",
                    "impact": "high",
                    "mitigation": "Formalizar plano de contingencia com o fornecedor de hospedagem antes do lancamento em producao",
                },
            ],
            "escalation_recommendation": "Nenhum escalonamento necessario no momento -- projeto adiantado, risco monitorado como parte do plano de lancamento.",
        },
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
        {
            "risks": [
                {
                    "description": RECURRING_RISK_DESCRIPTION,
                    "probability": "medium",
                    "impact": "high",
                    "mitigation": "Incluir clausula de continuidade de servico na proxima renovacao contratual do fornecedor",
                },
            ],
            "escalation_recommendation": "Nenhum escalonamento necessario no momento -- acompanhar na proxima revisao trimestral de fornecedores.",
        },
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

# (project_name, meeting transcript, target meeting_intelligence response)
# Populates Acoes (web/lib/hooks/use-action-items.ts, kind="meeting"). 3 of
# the 6 meetings share RECURRING_ACTION_DESCRIPTION verbatim, the same
# MIN_OCCURRENCES=3 mechanism as the recurring risk above -- together they
# are what makes Aprendizados non-empty (1 risco recorrente + 1 acao
# recorrente). Decisoes needs no new call: it derives automatically from the
# status ("red"/"yellow") and risk (probability=high/impact=high or
# high/medium or medium/high) analyses already above
# (web/lib/decision-center/decision-queue.ts, web/lib/workspace/risk-momentum.ts).
MEETINGS: list[tuple[str, str, dict]] = [
    (
        SAP_PROJECT,
        """
Reuniao de status semanal, Implantacao SAP S/4HANA. Presentes: Ana Ribeiro (PM),
Rafael Nunes. Pauta: atraso do conector fiscal e impacto no go-live. Decidido
escalar formalmente ao patrocinador do fornecedor ainda esta semana e confirmar a
substituicao dos consultores seniores realocados antes de prosseguir com os testes
de integracao restantes.
""".strip(),
        {
            "action_items": [
                {
                    "description": RECURRING_ACTION_DESCRIPTION,
                    "owner": "Ana Ribeiro",
                    "due_date": "2026-08-24",
                },
                {
                    "description": "Confirmar substituicao dos consultores seniores realocados junto ao fornecedor",
                    "owner": "Rafael Nunes",
                    "due_date": "2026-08-21",
                },
            ],
        },
    ),
    (
        "Migracao de Data Center",
        """
Reuniao de acompanhamento, Migracao de Data Center. Presente: Ana Ribeiro (PM).
Pauta: atraso do circuito redundante. Decidido acompanhar diariamente o status junto
ao fornecedor de rede ate a entrega ser confirmada.
""".strip(),
        {
            "action_items": [
                {
                    "description": "Acompanhar diariamente o status do circuito redundante com o fornecedor de rede",
                    "owner": "Ana Ribeiro",
                    "due_date": "2026-08-20",
                },
            ],
        },
    ),
    (
        "Portal do Cliente 2.0",
        """
Reuniao de homologacao, Portal do Cliente 2.0. Pauta: feedback dos
usuarios-piloto e preparacao do lancamento. Decidido preparar o plano de
lancamento em producao com base no feedback recebido.
""".strip(),
        {
            "action_items": [
                {
                    "description": "Preparar plano de lancamento em producao com base no feedback dos usuarios-piloto",
                    "owner": "Bruno Castro",
                    "due_date": "2026-08-28",
                },
            ],
        },
    ),
    (
        "Programa de Governanca de Dados",
        """
Reuniao de governanca, Programa de Governanca de Dados. Pauta: finalizacao das
politicas de qualidade de dados. Decidido publicar a versao final no portal
interno da organizacao.
""".strip(),
        {
            "action_items": [
                {
                    "description": "Publicar a versao final das politicas de qualidade de dados no portal interno",
                    "owner": "Carla Mendes",
                    "due_date": "2026-09-01",
                },
            ],
        },
    ),
    (
        "Renovacao de Infraestrutura de Rede",
        """
Reuniao de status, Renovacao de Infraestrutura de Rede. Pauta: acompanhamento
mensal do cronograma junto ao patrocinador. Decidido manter o relatorio
executivo mensal atualizado com o cronograma consolidado do projeto.
""".strip(),
        {
            "action_items": [
                {
                    "description": RECURRING_ACTION_DESCRIPTION,
                    "owner": "Diego Souza",
                    "due_date": "2026-08-22",
                },
            ],
        },
    ),
    (
        "Implantacao de CRM Regional",
        """
Reuniao de status, Implantacao de CRM Regional. Pauta: retrabalho no modulo de
relatorios e novo cronograma. Decidido validar o novo cronograma com o
patrocinador e manter o relatorio executivo mensal atualizado.
""".strip(),
        {
            "action_items": [
                {
                    "description": RECURRING_ACTION_DESCRIPTION,
                    "owner": "Carla Mendes",
                    "due_date": "2026-08-25",
                },
                {
                    "description": "Validar o novo cronograma do modulo de relatorios com o patrocinador",
                    "owner": "Carla Mendes",
                    "due_date": "2026-08-19",
                },
            ],
        },
    ),
]

# Documento sintetico minimo para testar a Knowledge Platform (Bloco F do
# roteiro de sessao) -- sem qualquer dado corporativo real, claramente
# identificado como DEMO.
SYNTHETIC_DOCUMENT_PATH = Path(__file__).parent / "synthetic-document.md"
SYNTHETIC_DOCUMENT_SOURCE_NAME = "Nota de Governanca de Fornecedores (DEMO).md"


def _write_mock_response(payload: dict) -> None:
    if not MOCK_LLM_RESPONSE_FILE:
        return
    with open(MOCK_LLM_RESPONSE_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def _login() -> dict[str, str]:
    """Authenticates as the Administrator bootstrap identity via the real
    POST /api/auth/login (the same contract every human login uses,
    src/api/routes/auth.py) and returns the 3 institutional identity headers
    the rest of this script reuses on every subsequent call -- exactly what
    web/lib/bff/domain-proxy.ts's institutionalHeaders() builds server-side
    from a session cookie, just resolved here from a direct login instead."""
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("ERROR: STRATECH_ADMIN_EMAIL / STRATECH_ADMIN_PASSWORD are not set.")
        print(
            "The bootstrapped Demo Mode user (demo@stratech.local) is deliberately "
            "read-only (viewer role, re-asserted on every boot -- see "
            "src/services/identity/auth_service.py) and cannot run analyses or "
            "upload documents. Set STRATECH_ADMIN_EMAIL/STRATECH_ADMIN_PASSWORD in "
            "demo/.env so the backend bootstraps a real Administrator this script "
            "can authenticate as. See demo/README.md."
        )
        sys.exit(1)

    response = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json={
            "organization": ADMIN_ORGANIZATION_SLUG,
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        timeout=30.0,
    )
    if response.status_code != 200:
        print(f"ERROR: login failed for organization={ADMIN_ORGANIZATION_SLUG!r} email={ADMIN_EMAIL!r}")
        print(f"  HTTP {response.status_code}: {response.text}")
        sys.exit(1)

    identity = response.json()
    return {
        "X-API-Key": API_KEY,
        "X-Stratech-User-Id": str(identity["user_id"]),
        "X-Stratech-Organization-Id": str(identity["organization_id"]),
        "X-Stratech-Session-Id": identity["session_id"],
    }


def _post(path: str, payload: dict, identity_headers: dict[str, str]) -> dict:
    headers = {**identity_headers, "Content-Type": "application/json"}
    response = httpx.post(f"{BACKEND_URL}{path}", headers=headers, json=payload, timeout=60.0)
    response.raise_for_status()
    return response.json()


def _upload_synthetic_document(identity_headers: dict[str, str]) -> None:
    if not SYNTHETIC_DOCUMENT_PATH.exists():
        print(f"  [documents] skipped: {SYNTHETIC_DOCUMENT_PATH} not found")
        return
    print("== Documento sintetico ==")
    with open(SYNTHETIC_DOCUMENT_PATH, "rb") as handle:
        try:
            response = httpx.post(
                f"{BACKEND_URL}/api/documents",
                headers=identity_headers,
                files={"file": (SYNTHETIC_DOCUMENT_PATH.name, handle, "text/markdown")},
                data={"source_name": SYNTHETIC_DOCUMENT_SOURCE_NAME},
                timeout=60.0,
            )
        except httpx.HTTPError as exc:
            print(f"  [documents] request failed: {exc}")
            return
    if response.status_code == 201:
        body = response.json()
        print(f"  [documents] status={body.get('status')} chunk_count={body.get('chunk_count')}")
    else:
        print(f"  [documents] HTTP {response.status_code}: {response.text}")


def seed() -> int:
    mode = "Demo Mode (mock + response file)" if DEMO_MODE else "real provider (LLM_PROVIDER)"
    print(f"Seeding via {mode} at {BACKEND_URL}\n")
    identity_headers = _login()
    print(
        f"Authenticated as organization_id={identity_headers['X-Stratech-Organization-Id']} "
        f"user_id={identity_headers['X-Stratech-User-Id']}\n"
    )
    failures = 0

    for project_name, context, status_target, risk_target in PROJECTS:
        print(f"== {project_name} ==")

        if DEMO_MODE:
            _write_mock_response(status_target)
        try:
            result = _post(
                "/api/projects/analyze",
                {"project_name": project_name, "project_context": context},
                identity_headers,
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
                    identity_headers,
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

    for project_name, transcript, action_target in MEETINGS:
        print(f"== {project_name} (reuniao) ==")
        if DEMO_MODE:
            _write_mock_response(action_target)
        try:
            result = _post(
                "/api/meetings/analyze",
                {"project_name": project_name, "transcript": transcript},
                identity_headers,
            )
            structured = result.get("model_output", {}).get("structured")
            action_items = result.get("model_output", {}).get("action_items", [])
            print(f"  [meeting] structured={structured} action_items={len(action_items)}")
            if not structured:
                failures += 1
        except httpx.HTTPStatusError as exc:
            print(f"  [meeting] HTTP {exc.response.status_code}: {exc.response.text}")
            failures += 1
        except httpx.HTTPError as exc:
            print(f"  [meeting] request failed: {exc}")
            failures += 1

    _upload_synthetic_document(identity_headers)

    return failures


if __name__ == "__main__":
    failure_count = seed()
    if failure_count:
        print(f"\n{failure_count} call(s) did not produce structured output.")
        print("See demo/README.md.")
        sys.exit(1)
    print("\nAll calls produced structured output.")
    print(
        f"Check the dashboard: log in at http://localhost:3000/entrar as "
        f"organization={ADMIN_ORGANIZATION_SLUG!r} email={ADMIN_EMAIL!r} "
        f"(GET /api/portfolio/summary itself needs the same institutional identity "
        f"headers as every call above, not just X-API-Key -- there is no single-header "
        f"curl equivalent, see demo/README.md)."
    )
