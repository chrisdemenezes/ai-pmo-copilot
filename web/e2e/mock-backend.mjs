// Standalone HTTP mock of the FastAPI backend's GET /api/portfolio/summary
// contract, used only by Playwright E2E (T9). Not part of the product's
// API surface, does not touch src/ -- test infrastructure only, mirrors
// the real, already-tested response shape (docs/technical/04-api-design.md).
import http from "node:http";

let scenario = "data";

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
];

const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url === "/__control/scenario") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      scenario = JSON.parse(body).scenario;
      res.writeHead(204).end();
    });
    return;
  }

  if (req.url === "/api/portfolio/summary") {
    if (scenario === "timeout") {
      // Never respond -- exercises the BFF's own AbortController timeout.
      return;
    }
    if (scenario === "unavailable") {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "internal error" }));
      return;
    }
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(scenario === "empty" ? [] : SAMPLE));
    return;
  }

  res.writeHead(404).end();
});

const port = Number(process.env.MOCK_BACKEND_PORT ?? 4100);
server.listen(port, () => {
  console.log(`[mock-backend] listening on :${port}`);
});
