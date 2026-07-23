import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/** Global role catalog (Épico 1) -- needed by the User Management screen
 * to populate the role picker. */
export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/roles");
}
