# AI PMO Copilot — Frontend

Next.js 16 (App Router) + TypeScript + Tailwind CSS v4. Architecture, stack, and rationale are
documented in RFC-001 and `docs/development/01-project-structure.md` at the repository root — read
those before adding a new dependency or route.

## Status

Sprint 1 (Design System) and FS-001 (Dashboard Executivo — Release 0.2) are delivered:

- `web/app/style-guide` — every design token and primitive, light and dark.
- `web/app/dashboard` — first screen wired to real backend data, gated behind a Nível 1 workspace
  session (`web/app/entrar`, `web/proxy.ts`).
- BFF layer (`web/app/api/bff/`) shielding the backend's shared `X-API-Key` from the browser.

## Run locally

```bash
npm install
cp .env.example .env.local   # fill in the values below
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). `/entrar` is the entry point; `/dashboard`
requires a workspace session, `/style-guide` does not.

### Environment variables (`.env.local`)

| Variable | Purpose |
|---|---|
| `BACKEND_URL` | Base URL of the FastAPI backend, called server-side only (BFF → backend) |
| `API_KEY` | Same shared secret the backend expects as `X-API-Key` — never sent to the browser |
| `WORKSPACE_PASSWORD` | Shared password gating the whole BFF (Nível 1 session, RFC-001) — not per-user auth |
| `SESSION_SECRET` | HMAC secret signing the workspace session cookie (`openssl rand -base64 32`) |
| `DISABLE_WORKSPACE_SESSION_GATE` | Emergency kill switch (TIP-001 §7 rollback) — `"true"` disables the session gate without reverting the feature. Unset in normal operation |

See `.env.example` for the same list with inline comments.

## Design system

Tokens live in `app/globals.css` as CSS custom properties, exposed to Tailwind via `@theme inline`
(Tailwind v4's CSS-first config — there is no `tailwind.config.js`). Primitives in
`components/ui/` are Radix UI wrapped by hand-written components (not the shadcn/ui CLI — its
registry at `ui.shadcn.com` is blocked by this environment's network policy; the same outcome,
Radix + Tailwind owned as our own source rather than a runtime dependency, is achieved by installing
`@radix-ui/react-*` directly).

## Dashboard data layer

TanStack Query (`lib/hooks/use-portfolio-summary.ts`) is the only server-state manager — no
Redux/Zustand. `staleTime: 30s` / `refetchInterval: 60s` per RFC-001's Data Freshness Matrix.
`retry: false` on this query specifically (Product Behavior Decision, T9 — see
`docs/releases/mvp-validation.md` Evidence Entry 015): the BFF already has its own 8s timeout, so a
query-level retry only delayed the honest error signal (~8s → ~40s measured with the TanStack Query
default). Not applied to the `QueryClient` global.

## Known limitations (Release 0.2)

- Workspace session is a single shared password, not per-user identity — no logout endpoint exists
  (not in TIP-001's scope); the session simply expires after 12h or via the kill switch above.
- `GET /api/portfolio/summary` has no pagination on the backend — acceptable at MVP volume, flagged
  as a risk in FS-001 §17.
- W4 (Recent Analyses Feed) was adiado to a fast-follow release by the UX Review — not part of this
  screen yet.
- No "atualizado há Xmin" staleness indicator — explicitly deferred in RFC-001 (Pergunta em Aberto).

## Tests

```bash
npm test              # Vitest + React Testing Library, run once
npm run test:watch
npm run test:e2e       # Playwright — spins up a mock backend + next dev automatically
```

E2E tests (`e2e/`) run against `e2e/mock-backend.mjs`, a standalone HTTP mock of the backend's
`GET /api/portfolio/summary` contract — not a new product endpoint, and `src/` is never touched by
these tests. `playwright.config.ts` runs 3 projects (mobile/md/lg, RFC-001's breakpoints).

## Checks before committing

```bash
npx tsc --noEmit
npx eslint .
npm run build
npm test
npm run test:e2e
```
