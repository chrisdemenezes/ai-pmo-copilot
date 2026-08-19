import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // W7-5 Etapa 4: minimal, reproducible Docker image -- `.next/standalone`
  // copies only the traced files a production `next start` actually needs
  // (including `instrumentation.ts`), instead of shipping the full
  // `node_modules` tree into the image.
  output: "standalone",
  // Local V1 Pilot Hardening Review (F6): the dev-only route indicator
  // defaults to bottom-left, which now collides with the sidebar's "Sair"
  // button pinned to that same corner at md (AppShell/Sidebar). Dev tooling
  // only -- no effect on `next build`/`next start`, no effect on the app's
  // own layout.
  devIndicators: {
    position: "bottom-right",
  },
};

export default nextConfig;
