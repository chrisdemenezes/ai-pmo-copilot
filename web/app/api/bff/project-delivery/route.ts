import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/** BFF for the Enterprise Domain Project Delivery API (Wave 2, Sprint 5) -- see portfolio/route.ts. */
export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/projects-delivery");
}
