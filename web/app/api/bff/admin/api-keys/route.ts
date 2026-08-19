import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/**
 * BFF for API Keys (D-051, Enterprise Administration) -- same pattern as
 * every other Administration BFF route: browser never sees API_KEY or
 * X-Stratech-* headers.
 */
export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/api-keys");
}

export async function POST(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/api-keys");
}
