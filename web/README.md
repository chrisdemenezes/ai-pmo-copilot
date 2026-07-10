# AI PMO Copilot — Frontend

Next.js 16 (App Router) + TypeScript + Tailwind CSS v4. Architecture, stack, and rationale are
documented in RFC-001 and `docs/development/01-project-structure.md` at the repository root — read
those before adding a new dependency or route.

## Status

Sprint 1 of 6 (Design System) is delivered. No API integration yet — `web/app/style-guide` is the
only real page, showing every design token and primitive in both light and dark themes.

## Run locally

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). `/style-guide` is the current entry point.

## Design system

Tokens live in `app/globals.css` as CSS custom properties, exposed to Tailwind via `@theme inline`
(Tailwind v4's CSS-first config — there is no `tailwind.config.js`). Primitives in
`components/ui/` are Radix UI wrapped by hand-written components (not the shadcn/ui CLI — its
registry at `ui.shadcn.com` is blocked by this environment's network policy; the same outcome,
Radix + Tailwind owned as our own source rather than a runtime dependency, is achieved by installing
`@radix-ui/react-*` directly).

## Tests

```bash
npm test        # Vitest + React Testing Library, run once
npm run test:watch
```

## Checks before committing

```bash
npx tsc --noEmit
npx eslint .
npm run build
npm test
```
