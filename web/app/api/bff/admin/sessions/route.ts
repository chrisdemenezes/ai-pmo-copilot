import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/**
 * BFF for Sessions (item 5, resolves TD-010) -- same pattern as every other
 * Administration BFF route: the browser never sees API_KEY or X-Stratech-*
 * headers.
 */
export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/sessions");
}
