import { NextResponse } from "next/server";

import { forwardDomainRequest, institutionalHeaders, readSessionIdentity } from "@/lib/bff/domain-proxy";

/**
 * BFF for Document Ingestion (Wave 5, Epic W5-0) -- same pattern as every
 * other Administration BFF route: browser never sees API_KEY or
 * X-Stratech-* headers.
 *
 * GET (list) has no body, so it reuses `forwardDomainRequest` like every
 * other route. POST (upload) needs a custom handler: the backend route
 * expects `multipart/form-data` with the original boundary preserved --
 * `forwardDomainRequest` always forces `Content-Type: application/json`
 * and reads the body as text, which would corrupt a file upload.
 */

const BACKEND_TIMEOUT_MS = 30_000;

function errorResponse(body: { error: string; detail: string }, status: number) {
  return NextResponse.json(body, { status });
}

export async function GET(request: Request): Promise<NextResponse> {
  return forwardDomainRequest(request, "/api/documents");
}

export async function POST(request: Request): Promise<NextResponse> {
  const backendUrl = process.env.BACKEND_URL;
  const apiKey = process.env.API_KEY;

  if (!backendUrl || !apiKey) {
    return errorResponse(
      { error: "bff_not_configured", detail: "BACKEND_URL ou API_KEY não configurados." },
      503,
    );
  }

  const identity = readSessionIdentity(request);
  if (identity === null) {
    return errorResponse({ error: "unauthorized", detail: "Sessão inválida ou expirada." }, 401);
  }

  const contentType = request.headers.get("content-type");
  if (!contentType || !contentType.startsWith("multipart/form-data")) {
    return errorResponse(
      { error: "invalid_request", detail: "Envio deve ser multipart/form-data." },
      400,
    );
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const bodyBytes = await request.arrayBuffer();
    const backendResponse = await fetch(`${backendUrl}/api/documents`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
        "Content-Type": contentType,
        ...institutionalHeaders(identity),
      },
      body: bodyBytes,
      signal: controller.signal,
      cache: "no-store",
    });

    const responseBody = await backendResponse.json().catch(() => null);
    return NextResponse.json(responseBody, { status: backendResponse.status });
  } catch (reason) {
    if (reason instanceof Error && reason.name === "AbortError") {
      return errorResponse(
        { error: "backend_timeout", detail: "O envio demorou mais que o esperado. Tente novamente." },
        504,
      );
    }
    return errorResponse(
      { error: "backend_unavailable", detail: "Não foi possível contatar o backend." },
      502,
    );
  } finally {
    clearTimeout(timeout);
  }
}
