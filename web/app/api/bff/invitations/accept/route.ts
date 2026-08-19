import { NextResponse } from "next/server";

import { forwardPublicRequest } from "@/lib/bff/domain-proxy";

/**
 * Public invitation acceptance (Convites, D-054): no session -- the token
 * in the body is the authorization; this is what creates the account.
 * `proxy.ts` exempts this route from the session gate.
 */
export async function POST(request: Request): Promise<NextResponse> {
  return forwardPublicRequest(request, "/api/invitations/accept");
}
