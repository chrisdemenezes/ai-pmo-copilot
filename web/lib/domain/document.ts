/**
 * Document Ingestion (Wave 5, Epic W5-0) -- repository-shaped accessors
 * over the real backend via the BFF (`/api/bff/admin/documents`), same
 * pattern as `api-key.ts`/`user.ts` (D-011): one module owns the wire
 * shape, nothing above it touches snake_case.
 */

export interface StratechDocument {
  documentId: string;
  sourceName: string;
  projectId: number | null;
  versionId: number;
  chunkCount: number;
  status: string;
  createdAt: string;
}

export interface DocumentVersion {
  versionId: number;
  chunkCount: number;
  createdAt: string;
}

export interface DocumentDetail extends StratechDocument {
  versions: DocumentVersion[];
}

/** Wire shape of DocumentResponse (src/api/routes/knowledge.py). */
interface DocumentApiRow {
  document_id: number;
  source_name: string;
  project_id: number | null;
  version_id: number;
  chunk_count: number;
  status: string;
  created_at: string;
}

interface DocumentVersionApiRow {
  version_id: number;
  chunk_count: number;
  created_at: string;
}

interface DocumentDetailApiRow extends DocumentApiRow {
  versions: DocumentVersionApiRow[];
}

export class DocumentApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "DocumentApiError";
  }
}

function toDocument(row: DocumentApiRow): StratechDocument {
  return {
    documentId: String(row.document_id),
    sourceName: row.source_name,
    projectId: row.project_id,
    versionId: row.version_id,
    chunkCount: row.chunk_count,
    status: row.status,
    createdAt: row.created_at,
  };
}

function toDetail(row: DocumentDetailApiRow): DocumentDetail {
  return {
    ...toDocument(row),
    versions: row.versions.map((version) => ({
      versionId: version.version_id,
      chunkCount: version.chunk_count,
      createdAt: version.created_at,
    })),
  };
}

/** Backend errors are either a plain string (`HTTPException(detail=str)`,
 * ex. 422 validation) or a structured object (502 indexing failure,
 * `{document_id, version_id, status, detail}` -- Technical Design §3.1).
 * Either way, the human-readable message ends up in `.detail`. */
function extractDetailMessage(body: unknown): string | null {
  if (body === null || typeof body !== "object" || !("detail" in body)) return null;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (detail !== null && typeof detail === "object" && "detail" in detail) {
    const nested = (detail as { detail: unknown }).detail;
    if (typeof nested === "string") return nested;
  }
  return null;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = extractDetailMessage(body) ?? `Falha na operação (${response.status}).`;
    throw new DocumentApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export async function listDocuments(): Promise<StratechDocument[]> {
  const response = await fetch("/api/bff/admin/documents");
  const rows = await parseResponse<DocumentApiRow[]>(response);
  return rows.map(toDocument);
}

export async function getDocument(documentId: string): Promise<DocumentDetail> {
  const response = await fetch(`/api/bff/admin/documents/${encodeURIComponent(documentId)}`);
  return toDetail(await parseResponse<DocumentDetailApiRow>(response));
}

export async function uploadDocument(file: File, sourceName?: string): Promise<StratechDocument> {
  const formData = new FormData();
  formData.append("file", file);
  if (sourceName && sourceName.trim().length > 0) {
    formData.append("source_name", sourceName.trim());
  }
  const response = await fetch("/api/bff/admin/documents", { method: "POST", body: formData });
  return toDocument(await parseResponse<DocumentApiRow>(response));
}

export async function reindexDocument(documentId: string): Promise<StratechDocument> {
  const response = await fetch(
    `/api/bff/admin/documents/${encodeURIComponent(documentId)}/reindex`,
    { method: "POST" },
  );
  return toDocument(await parseResponse<DocumentApiRow>(response));
}
