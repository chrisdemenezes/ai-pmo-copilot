import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedRequest } from "@/lib/bff/test-support";

import { GET, POST } from "./route";

function multipartRequest(body: BodyInit, identity?: { userId: number; organizationId: number }) {
  return authenticatedRequest(
    "http://localhost/x",
    {
      method: "POST",
      headers: { "Content-Type": "multipart/form-data; boundary=test-boundary" },
      body,
    },
    identity,
  );
}

describe("BFF /api/bff/admin/documents", () => {
  beforeEach(() => {
    vi.stubEnv("BACKEND_URL", "http://backend.test");
    vi.stubEnv("API_KEY", "secret-key");
    vi.stubEnv("SESSION_SECRET", "test-secret");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  describe("GET", () => {
    it("returns 401 when there is no session cookie", async () => {
      const response = await GET(new Request("http://localhost/x"));
      expect(response.status).toBe(401);
    });

    it("forwards to /api/documents", async () => {
      const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
      vi.stubGlobal("fetch", fetchMock);

      await GET(authenticatedRequest("http://localhost/x"));

      expect(fetchMock).toHaveBeenCalledWith(
        "http://backend.test/api/documents",
        expect.objectContaining({ method: "GET" }),
      );
    });
  });

  describe("POST (upload)", () => {
    it("returns 503 without leaking the API key when BACKEND_URL or API_KEY are unset", async () => {
      vi.stubEnv("API_KEY", "");
      const response = await POST(multipartRequest("--test-boundary--"));
      expect(response.status).toBe(503);
      expect(JSON.stringify(await response.json())).not.toContain("secret-key");
    });

    it("returns 401 when there is no session cookie", async () => {
      const response = await POST(
        new Request("http://localhost/x", {
          method: "POST",
          headers: { "Content-Type": "multipart/form-data; boundary=test-boundary" },
          body: "--test-boundary--",
        }),
      );
      expect(response.status).toBe(401);
    });

    it("rejects a non-multipart body", async () => {
      const response = await POST(
        authenticatedRequest("http://localhost/x", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        }),
      );
      expect(response.status).toBe(400);
    });

    it("forwards the raw multipart body and preserves the boundary, with institutional headers", async () => {
      const fetchMock = vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({
              document_id: 1,
              source_name: "notes.md",
              project_id: null,
              version_id: 1,
              chunk_count: 1,
              status: "indexed",
              created_at: "2026-07-30T00:00:00Z",
            }),
            { status: 201 },
          ),
        );
      vi.stubGlobal("fetch", fetchMock);

      const response = await POST(
        multipartRequest("--test-boundary--\r\ncontent--test-boundary--", {
          userId: 7,
          organizationId: 3,
        }),
      );

      expect(response.status).toBe(201);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("http://backend.test/api/documents");
      expect(init.method).toBe("POST");
      expect(init.headers["Content-Type"]).toBe("multipart/form-data; boundary=test-boundary");
      expect(init.headers["X-API-Key"]).toBe("secret-key");
      expect(init.headers["X-Stratech-User-Id"]).toBe("7");
      expect(init.headers["X-Stratech-Organization-Id"]).toBe("3");
    });
  });
});
