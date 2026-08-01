import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params;
  return forwardDomainRequest(request, `/api/documents/${encodeURIComponent(id)}`);
}
