import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params;
  return forwardDomainRequest(request, `/api/admin/api-keys/${encodeURIComponent(id)}`);
}
