import { NextResponse } from "next/server";

import { forwardPublicRequest } from "@/lib/bff/domain-proxy";

/**
 * Public invitation preview (Convites, D-054): no session -- the token in
 * the path is the authorization. `proxy.ts` exempts this route from the
 * session gate.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ token: string }> },
): Promise<NextResponse> {
  const { token } = await params;
  return forwardPublicRequest(request, `/api/invitations/${encodeURIComponent(token)}`);
}
