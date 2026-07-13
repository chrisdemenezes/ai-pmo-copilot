"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceTimeline } from "@/lib/hooks/use-workspace-timeline";
import { useWorkspaceAnalysisDetail } from "@/lib/hooks/use-workspace-analysis-detail";
import { analysisKindLabel } from "@/lib/workspace/labels";
import type { AnalysisListItem } from "@/lib/workspace/types";

const PAGE_SIZE = 10;

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Seção 8 -- Histórico completo. Painel B, paginado, com drill-down por item. */
export function AnalysisHistory({ projectName }: { projectName: string }) {
  const [page, setPage] = useState(0);
  const [openAnalysisId, setOpenAnalysisId] = useState<number | null>(null);

  const history = useWorkspaceTimeline(projectName, {
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  return (
    <section className="flex flex-col gap-3" aria-labelledby="history-heading">
      <h2 id="history-heading" className="text-sm font-semibold text-ink-muted">
        Histórico completo
      </h2>
      {history.isPending ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : history.isError ? (
        <p className="text-sm text-danger">Não foi possível carregar o histórico.</p>
      ) : history.data.length === 0 && page === 0 ? (
        <p className="text-sm text-ink-muted">Nenhuma análise registrada ainda.</p>
      ) : (
        <>
          <ol className="flex flex-col gap-2">
            {history.data.map((item) => (
              <HistoryRow key={item.id} item={item} onOpen={() => setOpenAnalysisId(item.id)} />
            ))}
          </ol>
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              disabled={page === 0}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((current) => current + 1)}
              disabled={history.data.length < PAGE_SIZE}
            >
              Próxima
            </Button>
          </div>
        </>
      )}

      <AnalysisDetailDialog
        projectName={projectName}
        analysisId={openAnalysisId}
        onClose={() => setOpenAnalysisId(null)}
      />
    </section>
  );
}

function HistoryRow({ item, onOpen }: { item: AnalysisListItem; onOpen: () => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-center justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2 text-left hover:bg-surface-2"
      >
        <span className="text-sm text-ink-muted">{formatDateTime(item.created_at)}</span>
        <Badge variant="outline">{analysisKindLabel(item.kind)}</Badge>
      </button>
    </li>
  );
}

function AnalysisDetailDialog({
  projectName,
  analysisId,
  onClose,
}: {
  projectName: string;
  analysisId: number | null;
  onClose: () => void;
}) {
  const detail = useWorkspaceAnalysisDetail(projectName, analysisId);

  return (
    <Dialog open={analysisId !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {analysisId !== null && detail.data
              ? `${analysisKindLabel(detail.data.kind)} — ${formatDateTime(detail.data.created_at)}`
              : "Análise"}
          </DialogTitle>
        </DialogHeader>
        {detail.isPending ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : detail.isError ? (
          <p className="text-sm text-danger">Não foi possível carregar esta análise.</p>
        ) : detail.data ? (
          <AnalysisDetailBody payload={detail.data.payload} />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function AnalysisDetailBody({
  payload,
}: {
  payload: NonNullable<ReturnType<typeof useWorkspaceAnalysisDetail>["data"]>["payload"];
}) {
  const output = payload.model_output;

  // "structured: true" only means the LLM's raw text was valid JSON
  // (parse_structured_output) -- it never guarantees the parsed object
  // actually matches the schema this branch expects. Confirmed against the
  // real backend (TIP-006): a live call can come back "structured: true"
  // shaped like a different agent's output entirely. Array.isArray, not
  // just "key" in output, so a present-but-wrong-typed field falls through
  // to the raw-JSON fallback instead of crashing.
  if (output.structured === false) {
    return (
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-surface-2 p-3 text-xs">
        {output.raw_output}
      </pre>
    );
  }

  if ("risks" in output && Array.isArray(output.risks)) {
    return (
      <div className="flex max-h-80 flex-col gap-2 overflow-auto text-sm">
        {output.risks.map((risk, index) => (
          <p key={index}>
            {risk.description} — {risk.probability}/{risk.impact}
          </p>
        ))}
      </div>
    );
  }

  if ("action_items" in output && Array.isArray(output.action_items)) {
    return (
      <div className="flex max-h-80 flex-col gap-2 overflow-auto text-sm">
        <p className="font-medium">{output.summary}</p>
        {output.action_items.map((item, index) => (
          <p key={index}>
            {item.description} ({item.owner ?? "sem responsável"})
          </p>
        ))}
      </div>
    );
  }

  if ("key_findings" in output && Array.isArray(output.key_findings)) {
    return (
      <div className="flex max-h-80 flex-col gap-2 overflow-auto text-sm">
        <p>Saúde: {output.health_status}</p>
        {output.key_findings.map((finding, index) => (
          <p key={index}>{finding}</p>
        ))}
      </div>
    );
  }

  return (
    <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-surface-2 p-3 text-xs">
      {JSON.stringify(output, null, 2)}
    </pre>
  );
}
