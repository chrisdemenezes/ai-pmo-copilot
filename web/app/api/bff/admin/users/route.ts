import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/**
 * BFF for User Management listing/creation (Wave 2, Enterprise
 * Administration Capability) -- same pattern as the Domain BFF routes
 * (Sprint 5): browser never sees API_KEY or X-Stratech-* headers.
 */
export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/users");
}

export async function POST(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/users");
}
