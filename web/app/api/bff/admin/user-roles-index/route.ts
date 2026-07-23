import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/** Bulk { user_id: [role names] } for the whole organization -- backs the
 * user list's role column and role filter without an N+1 request. */
export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/admin/user-roles-index");
}
