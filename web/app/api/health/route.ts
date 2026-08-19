import { NextResponse } from "next/server";

/**
 * W7-5 Etapa 4: the frontend container's own liveness signal, mirroring
 * the backend's `GET /health` (same shape: status + release identity).
 * Unauthenticated on purpose -- this is infrastructure-level health
 * checking (Docker HEALTHCHECK / orchestrator probes), never a BFF proxy
 * to the backend.
 */
export async function GET() {
  return NextResponse.json({
    status: "healthy",
    service: "STRATECH Frontend",
    release: process.env.RELEASE_SHA ?? "unknown",
  });
}
