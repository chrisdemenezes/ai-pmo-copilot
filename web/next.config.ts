import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // W7-5 Etapa 4: minimal, reproducible Docker image -- `.next/standalone`
  // copies only the traced files a production `next start` actually needs
  // (including `instrumentation.ts`), instead of shipping the full
  // `node_modules` tree into the image.
  output: "standalone",
  // Local V1 Pilot Hardening Review (F6) repositioned this indicator to
  // bottom-right to dodge the sidebar's "Sair" button at md. V1 Product &
  // Capability Completion, Pacote C added ThemeToggle to the mobile
  // bottom nav (fixed inset-x-0 bottom-0, full width) -- on mobile there
  // is no corner the indicator can occupy without covering some real
  // interactive element in that bar (confirmed: it now intercepts clicks
  // on "Sair" there). Disabled outright instead of chasing a moving
  // target -- dev tooling only, no effect on `next build`/`next start`,
  // no effect on the app's own layout.
  devIndicators: false,
};

export default nextConfig;
