import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import DocumentsAdminPage from "./page";
import { useAdminDocuments } from "@/lib/hooks/use-admin-documents";
import {
  useUploadAdminDocument,
  useUploadAdminDocumentFromUrl,
  useReindexAdminDocument,
} from "@/lib/hooks/use-admin-document-mutations";
import type { StratechDocument } from "@/lib/domain/document";

vi.mock("@/lib/hooks/use-admin-documents", () => ({
  useAdminDocuments: vi.fn(),
}));
// UploadDocumentDialog, AddDocumentFromUrlDialog and ReindexDocumentButton
// each own a real useMutation() that would otherwise require a real
// QueryClientProvider this test never sets up -- same reason as
// web/app/dashboard/page.test.tsx.
vi.mock("@/lib/hooks/use-admin-document-mutations", () => ({
  useUploadAdminDocument: vi.fn(),
  useUploadAdminDocumentFromUrl: vi.fn(),
  useReindexAdminDocument: vi.fn(),
}));

const mockedDocuments = vi.mocked(useAdminDocuments);
vi.mocked(useUploadAdminDocument).mockReturnValue({
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  data: undefined,
  error: null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);
vi.mocked(useUploadAdminDocumentFromUrl).mockReturnValue({
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  data: undefined,
  error: null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);
vi.mocked(useReindexAdminDocument).mockReturnValue({
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  data: undefined,
  error: null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);

function document(overrides: Partial<StratechDocument>): StratechDocument {
  return {
    documentId: "1",
    sourceName: "Contrato.pdf",
    chunkCount: 12,
    status: "indexed",
    createdAt: "2026-01-01T00:00:00Z",
    ...overrides,
  } as StratechDocument;
}

describe("DocumentsAdminPage", () => {
  // V1 Product & Capability Completion, Pacote E: "Chunks" era jargão
  // técnico exposto ao usuário de negócio -- renomeado para "Trechos
  // indexados", sem alterar o mecanismo interno de chunking.
  it("labels the chunk count column with business-friendly terminology, not the internal jargon", () => {
    mockedDocuments.mockReturnValue({
      data: [document({})],
      isPending: false,
      isError: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentsAdminPage />);
    expect(screen.getByRole("columnheader", { name: "Trechos indexados" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Chunks" })).toBeNull();
  });

  // Pacote E: a coluna "Ações" nunca fica visualmente vazia/quebrada para
  // um documento já indexado (sem ação de retry pendente) -- mostra um
  // traço explícito em vez de nada.
  it("shows an explicit placeholder in Ações for an already-indexed document (no pending action)", () => {
    mockedDocuments.mockReturnValue({
      data: [document({ status: "indexed" })],
      isPending: false,
      isError: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentsAdminPage />);
    expect(screen.queryByRole("button", { name: /reindexar/i })).toBeNull();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  // V1 Product & Capability Completion, Package L (External Document
  // Sources): a "Adicionar por URL" trigger sits alongside the existing
  // manual upload, never replacing it.
  it("offers Adicionar por URL alongside the manual upload trigger", () => {
    mockedDocuments.mockReturnValue({
      data: [document({})],
      isPending: false,
      isError: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentsAdminPage />);
    expect(screen.getByRole("button", { name: /adicionar por url/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /enviar documento/i })).toBeInTheDocument();
  });

  it("still shows the Reindexar action for a failed document", () => {
    mockedDocuments.mockReturnValue({
      data: [document({ status: "failed" })],
      isPending: false,
      isError: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentsAdminPage />);
    expect(screen.getByRole("button", { name: /reindexar/i })).toBeInTheDocument();
  });
});
