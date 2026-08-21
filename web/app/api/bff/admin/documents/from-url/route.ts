import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/**
 * BFF for External Document Sources (V1 Product & Capability Completion,
 * Package L) -- plain JSON POST, so this reuses `forwardDomainRequest`
 * unlike the multipart file-upload route (`../route.ts`).
 */
export async function POST(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/documents/from-url");
}
