"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/shell/header";
import { AnalyzeProjectDialog } from "@/components/workspace/analyze-project-dialog";
import { useWorkspaceSummary } from "@/lib/hooks/use-workspace-summary";

/** Seção 1 -- Cabeçalho do Projeto. Painel A, independente das demais seções. */
export function WorkspaceHeader({ projectName }: { projectName: string }) {
  const { data, isPending, isError, refetch, isFetching } = useWorkspaceSummary(projectName);

  return (
    <Header>
      <div className="flex min-w-0 flex-col gap-1">
        <Link
          href="/dashboard"
          className="flex w-fit items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"
        >
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          Dashboard
        </Link>
        {isPending ? (
          <Skeleton className="h-8 w-64" />
        ) : isError ? (
          <h1 className="font-display text-2xl font-semibold text-ink" title={projectName}>
            {projectName}
          </h1>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <h1
              className="font-display text-2xl font-semibold text-ink"
              title={data.project_name}
            >
              {data.project_name}
            </h1>
            <Badge variant={healthStatusVariant(data.latest_health_status)}>
              {healthStatusLabel(data.latest_health_status)}
            </Badge>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2">
        <AnalyzeProjectDialog projectName={projectName} />
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </div>
    </Header>
  );
}
