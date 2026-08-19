import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DocumentApiError,
  getDocument,
  listDocuments,
  reindexDocument,
  uploadDocument,
} from "./document";

afterEach(() => {
  vi.restoreAllMocks();
});

const ROW = {
  document_id: 1,
  source_name: "notes.md",
  project_id: null,
  version_id: 10,
  chunk_count: 2,
  status: "indexed",
  created_at: "2026-07-30T00:00:00Z",
};

describe("listDocuments", () => {
  it("maps the wire shape (snake_case) to the camelCase domain shape", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify([ROW]), { status: 200 })),
    );

    const documents = await listDocuments();

    expect(documents).toEqual([
      {
        documentId: "1",
        sourceName: "notes.md",
        projectId: null,
        versionId: 10,
        chunkCount: 2,
        status: "indexed",
        createdAt: "2026-07-30T00:00:00Z",
      },
    ]);
  });
});

describe("getDocument", () => {
  it("maps versions alongside the document fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            ...ROW,
            versions: [{ version_id: 10, chunk_count: 2, created_at: "2026-07-30T00:00:00Z" }],
          }),
          { status: 200 },
        ),
      ),
    );

    const detail = await getDocument("1");

    expect(detail.versions).toEqual([
      { versionId: 10, chunkCount: 2, createdAt: "2026-07-30T00:00:00Z" },
    ]);
  });
});

describe("error handling", () => {
  it("extracts a plain string detail (e.g. 422 validation)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "File is empty" }), { status: 422 }),
      ),
    );

    await expect(uploadDocument(new File(["x"], "x.md"))).rejects.toMatchObject({
      status: 422,
      message: "File is empty",
    });
  });

  it("extracts the nested detail message from a 502 indexing failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: {
              document_id: 1,
              version_id: 1,
              status: "failed",
              detail: "Indexação falhou; documento foi criado e pode ser reindexado via /reindex",
            },
          }),
          { status: 502 },
        ),
      ),
    );

    await expect(reindexDocument("1")).rejects.toMatchObject({
      status: 502,
      message: "Indexação falhou; documento foi criado e pode ser reindexado via /reindex",
    });
  });

  it("falls back to a generic message when no detail is present", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));

    await expect(listDocuments()).rejects.toBeInstanceOf(DocumentApiError);
  });
});
