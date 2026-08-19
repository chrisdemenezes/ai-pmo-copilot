import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/**
 * BFF for admin Invitation management (Convites, D-054) -- session-gated,
 * same pattern as the API Keys / Sessions admin BFF routes.
 */
export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/invitations");
}

export async function POST(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/invitations");
}
