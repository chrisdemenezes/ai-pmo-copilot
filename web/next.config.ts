import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // W7-5 Etapa 4: minimal, reproducible Docker image -- `.next/standalone`
  // copies only the traced files a production `next start` actually needs
  // (including `instrumentation.ts`), instead of shipping the full
  // `node_modules` tree into the image.
  output: "standalone",
};

export default nextConfig;
