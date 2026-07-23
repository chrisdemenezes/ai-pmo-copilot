import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

/** Roles the user already has (distinct path from POST .../roles, which
 * assigns a new one) -- needed so the Frontend can offer "assign" vs.
 * "remove" per role, not just a blind assign button. */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params;
  return forwardDomainRequest(request, `/api/admin/users/${encodeURIComponent(id)}/roles`);
}
