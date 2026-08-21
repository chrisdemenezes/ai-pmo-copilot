"use client";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Header } from "@/components/shell/header";
import { useAdminDocuments } from "@/lib/hooks/use-admin-documents";
import { ReindexDocumentButton } from "./reindex-document-button";
import { UploadDocumentDialog } from "./upload-document-dialog";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

const STATUS_LABEL: Record<string, string> = {
  indexed: "Indexado",
  ingested_pending_index: "Pendente de indexação",
  failed: "Falhou",
};

function statusVariant(status: string): BadgeProps["variant"] {
  if (status === "indexed") return "ok";
  if (status === "failed") return "danger";
  return "warn";
}

/**
 * Document Ingestion (Wave 5, Epic W5-0) -- interface mínima para entrada
 * e consulta de documentos, per `DOMAIN-BLUEPRINT-DOCUMENT-ADVISOR.md` e
 * `TECHNICAL-DESIGN-W5-0-DOCUMENT-INGESTION.md`. Este Epic é exclusivamente
 * Knowledge Platform -- nenhuma pergunta ao Document Advisor acontece
 * aqui (W5-1, ainda não autorizado).
 */
export default function DocumentsAdminPage() {
  const documents = useAdminDocuments();

  if (documents.isPending) {
    return <DocumentsAdminSkeleton />;
  }

  if (documents.isError) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
        <Header>
          <PageTitle />
        </Header>
        <Card>
          <CardContent className="p-5 text-sm text-danger" role="alert">
            Falha ao carregar documentos.
          </CardContent>
        </Card>
      </main>
    );
  }

  const rows = documents.data ?? [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <PageTitle />
        <UploadDocumentDialog />
      </Header>

      {rows.length === 0 ? (
        <Card>
          <CardContent className="p-5 text-sm text-ink-muted">
            Nenhum documento enviado ainda.
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Trechos indexados</TableHead>
                <TableHead>Enviado em</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((document) => (
                <TableRow key={document.documentId}>
                  <TableCell className="font-medium">{document.sourceName}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(document.status)}>
                      {STATUS_LABEL[document.status] ?? document.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-ink-muted">{document.chunkCount}</TableCell>
                  <TableCell className="text-ink-muted">{formatDate(document.createdAt)}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      {document.status !== "indexed" ? (
                        <ReindexDocumentButton document={document} />
                      ) : (
                        // V1 Product & Capability Completion, Pacote E:
                        // um documento já indexado não tem ação de retry
                        // pendente -- um traço explícito evita que a
                        // coluna pareça quebrada/vazia por engano.
                        <span className="text-sm text-ink-faint" aria-hidden="true">
                          —
                        </span>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </main>
  );
}

function PageTitle() {
  return (
    <div>
      <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
        STRATECH · Administração
      </p>
      <h1 className="font-display text-2xl font-semibold">Documentos</h1>
    </div>
  );
}

function DocumentsAdminSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <PageTitle />
      </Header>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </main>
  );
}
