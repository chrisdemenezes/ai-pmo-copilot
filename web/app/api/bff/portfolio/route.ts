import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/**
 * BFF for the Enterprise Domain Portfolio API (Wave 2, Sprint 5) -- the
 * browser never sees API_KEY or the X-Stratech-* institutional headers;
 * this route resolves them from the server-side session cookie and
 * forwards to GET /api/portfolios.
 */
export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/portfolios");
}
