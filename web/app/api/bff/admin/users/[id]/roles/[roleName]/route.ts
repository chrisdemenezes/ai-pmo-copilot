import { NextResponse } from "next/server";

import { forwardDomainRequest } from "@/lib/bff/domain-proxy";

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string; roleName: string }> },
): Promise<NextResponse> {
  const { id, roleName } = await params;
  return forwardDomainRequest(
    request,
    `/api/admin/users/${encodeURIComponent(id)}/roles/${encodeURIComponent(roleName)}`,
  );
}
