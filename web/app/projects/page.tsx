"use client";

import { useState } from "react";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/shell/header";
import { usePortfolioSummary } from "@/lib/hooks/use-portfolio-summary";
import { ProjectHealthGrid } from "@/components/dashboard/project-health-grid";

/**
 * TIP-004A -- reuses usePortfolioSummary() and ProjectHealthGrid verbatim
 * (already real, already tested, already linked to /workspace/[projectName]
 * with encodeURIComponent since TIP-004). Zero new backend route, zero new
 * BFF route, zero new data. The only new logic is the client-side search
 * filter, over data already fully loaded -- no speculative backend.
 */
export default function ProjectsPage() {
  const { data, isPending, isError, error, refetch, isFetching } = usePortfolioSummary();
  const [query, setQuery] = useState("");

  if (isPending) {
    return <ProjectsSkeleton />;
  }

  // Same stale-while-revalidate discipline as the Dashboard (FS-001 §6/§10):
  // a failed background poll must not discard a list that already loaded.
  if (isError && !data) {
    throw error;
  }

  const projects = data ?? [];
  const normalizedQuery = query.trim().toLowerCase();
  const filtered = normalizedQuery
    ? projects.filter((project) =>
        project.project_name.toLowerCase().includes(normalizedQuery),
      )
    : projects;

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            Diretório de Projetos
          </p>
          <h1 className="font-display text-2xl font-semibold">Projetos</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Atualizando…" : "Atualizar"}
        </Button>
      </Header>

      {projects.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <div className="relative max-w-sm">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint"
                aria-hidden="true"
              />
              <Input
                type="search"
                placeholder="Buscar projeto…"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="pl-9"
                aria-label="Buscar projeto"
              />
            </div>
            <p className="text-sm text-ink-muted">
              {filtered.length} de {projects.length}{" "}
              {projects.length === 1 ? "projeto" : "projetos"}
            </p>
          </div>

          {filtered.length === 0 ? (
            <NoSearchResults query={query} />
          ) : (
            <ProjectHealthGrid projects={filtered} />
          )}
        </>
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 p-12 text-center">
        <p className="font-medium">Nenhum projeto com análise registrada ainda</p>
        <p className="text-sm text-ink-muted">
          Assim que uma reunião, risco ou status de projeto for analisado, ele aparece aqui
          automaticamente.
        </p>
      </CardContent>
    </Card>
  );
}

function NoSearchResults({ query }: { query: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 p-12 text-center">
        <p className="font-medium">Nenhum projeto encontrado para &quot;{query}&quot;</p>
        <p className="text-sm text-ink-muted">Tente buscar por outro nome de projeto.</p>
      </CardContent>
    </Card>
  );
}

function ProjectsSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-9 w-full max-w-sm" />
      <Skeleton className="h-64" />
    </main>
  );
}
