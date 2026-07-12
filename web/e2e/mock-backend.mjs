// Standalone HTTP mock of the FastAPI backend, used only by Playwright E2E
// (T9 / TIP-004). Not part of the product's API surface, does not touch
// src/ -- test infrastructure only, mirrors the real, already-tested
// response shapes (docs/technical/04-api-design.md,
// src/api/routes/intelligence.py).
import http from "node:http";
import { URL } from "node:url";

let scenario = "data";

// Per-endpoint scenario for the Workspace's 3 independent panels (TIP-004
// §1) -- lets an E2E test make one panel slow/error while the others
// succeed, to prove none of them blocks the others.
const workspaceScenario = { summary: "data", analyses: "data", detail: "data" };

const SAMPLE = [
  {
    project_name: "Multilift",
    total_analyses: 5,
    open_risks: 3,
    pending_action_items: 2,
    latest_health_status: "red",
  },
  {
    project_name: "Aurora",
    total_analyses: 2,
    open_risks: 0,
    pending_action_items: 1,
    latest_health_status: "green",
  },
  // Real hazard already hit once this Release: a "/" in the project name
  // (curl to /api/projects/{name}/summary broke on an unencoded slash).
  // Kept in the default portfolio so the Workspace's encodeURIComponent
  // chain has a real project to exercise end-to-end.
  {
    project_name: "Implantacao SAP S/4HANA",
    total_analyses: 2,
    open_risks: 1,
    pending_action_items: 1,
    latest_health_status: "yellow",
  },
];

const WORKSPACE_SUMMARY = {
  Aurora: {
    project_name: "Aurora",
    total_analyses: 2,
    open_risks: 0,
    pending_action_items: 1,
    latest_health_status: "green",
  },
  "Implantacao SAP S/4HANA": {
    project_name: "Implantacao SAP S/4HANA",
    total_analyses: 2,
    open_risks: 1,
    pending_action_items: 1,
    latest_health_status: "yellow",
  },
};

const ANALYSES = [
  {
    id: 201,
    kind: "risk",
    project_name: "Aurora",
    created_at: "2026-07-10T14:00:00Z",
    payload: {
      agent: "risk_review",
      project_name: "Aurora",
      model_output: {
        structured: true,
        risks: [
          { description: "Atraso na entrega", probability: "medium", impact: "high", mitigation: "Replanejar sprint" },
        ],
        escalation_recommendation: null,
      },
    },
  },
  {
    id: 202,
    kind: "meeting",
    project_name: "Aurora",
    created_at: "2026-07-09T10:00:00Z",
    payload: {
      agent: "meeting_intelligence",
      project_name: "Aurora",
      model_output: {
        structured: true,
        summary: "Reunião semanal de acompanhamento.",
        decisions: ["Adiar o go-live em 1 semana"],
        action_items: [{ description: "Atualizar cronograma", owner: "Ana", due_date: "2026-07-15" }],
        issues: [],
        dependencies: ["Aprovação do cliente"],
      },
    },
  },
  {
    id: 203,
    kind: "status",
    project_name: "Aurora",
    created_at: "2026-07-08T09:00:00Z",
    payload: {
      agent: "project_status",
      project_name: "Aurora",
      model_output: {
        structured: true,
        health_status: "green",
        key_findings: ["Projeto dentro do prazo"],
        recommendations: ["Manter cadência atual"],
      },
    },
  },
  {
    id: 301,
    kind: "status",
    project_name: "Implantacao SAP S/4HANA",
    created_at: "2026-07-11T08:00:00Z",
    payload: {
      agent: "project_status",
      project_name: "Implantacao SAP S/4HANA",
      model_output: {
        structured: true,
        health_status: "yellow",
        key_findings: ["Atenção ao cronograma de testes"],
        recommendations: ["Revisar plano de testes"],
      },
    },
  },
];

function send(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function applyScenario(res, key) {
  const current = workspaceScenario[key];
  if (current === "timeout") {
    return true; // never respond
  }
  if (current === "unavailable") {
    send(res, 500, { detail: "internal error" });
    return true;
  }
  return false;
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");

  if (req.method === "POST" && url.pathname === "/__control/scenario") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      scenario = JSON.parse(body).scenario;
      res.writeHead(204).end();
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/__control/workspace-scenario") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      const { endpoint, scenario: value } = JSON.parse(body);
      workspaceScenario[endpoint] = value;
      res.writeHead(204).end();
    });
    return;
  }

  if (url.pathname === "/api/portfolio/summary") {
    if (scenario === "timeout") return;
    if (scenario === "unavailable") return send(res, 500, { detail: "internal error" });
    return send(res, 200, scenario === "empty" ? [] : SAMPLE);
  }

  const summaryMatch = url.pathname.match(/^\/api\/projects\/(.+)\/summary$/);
  if (summaryMatch) {
    if (applyScenario(res, "summary")) return;
    const projectName = decodeURIComponent(summaryMatch[1]);
    const found = WORKSPACE_SUMMARY[projectName];
    if (!found) return send(res, 404, { detail: "not found" });
    return send(res, 200, found);
  }

  if (url.pathname === "/api/analyses") {
    if (applyScenario(res, "analyses")) return;
    const projectName = url.searchParams.get("project_name");
    const kind = url.searchParams.get("kind");
    const limit = Number(url.searchParams.get("limit") ?? "20");
    const offset = Number(url.searchParams.get("offset") ?? "0");

    let items = ANALYSES.filter((a) => !projectName || a.project_name === projectName);
    if (kind) items = items.filter((a) => a.kind === kind);
    items = items
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    const page = items.slice(offset, offset + limit).map(({ id, kind: k, project_name, created_at }) => ({
      id,
      kind: k,
      project_name,
      created_at,
    }));
    return send(res, 200, page);
  }

  const detailMatch = url.pathname.match(/^\/api\/analyses\/(\d+)$/);
  if (detailMatch) {
    if (applyScenario(res, "detail")) return;
    const found = ANALYSES.find((a) => a.id === Number(detailMatch[1]));
    if (!found) return send(res, 404, { detail: "Analysis not found" });
    return send(res, 200, found);
  }

  res.writeHead(404).end();
});

const port = Number(process.env.MOCK_BACKEND_PORT ?? 4100);
server.listen(port, () => {
  console.log(`[mock-backend] listening on :${port}`);
});
