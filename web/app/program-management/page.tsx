"use client";

import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
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
import { usePortfolios } from "@/lib/hooks/use-portfolios";
import { usePrograms } from "@/lib/hooks/use-programs";
import type { Portfolio } from "@/lib/domain/portfolio";
import type { Program } from "@/lib/domain/program";

/**
 * Program Management (Capability 02, Release 0.2) -- listagem funcional
 * de todos os Programs agrupados por Portfolio pai. Sem CRUD (não
 * solicitado nesta Capability) -- apenas visualização real, consumindo
 * usePortfolios()/usePrograms() (lib/domain), nunca dado mock.
 */
export default function ProgramManagementPage() {
  const portfolios = usePortfolios();
  const programs = usePrograms();

  if (portfolios.isPending || programs.isPending) {
    return <ProgramManagementSkeleton />;
  }

  if (portfolios.isError && !portfolios.data) throw portfolios.error;
  if (programs.isError && !programs.data) throw programs.error;

  const portfolioList = portfolios.data ?? [];
  const programList = programs.data ?? [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            STRATECH · Program Management
          </p>
          <h1 className="font-display text-2xl font-semibold">Programas por Portfólio</h1>
        </div>
      </Header>

      {portfolioList.map((portfolio) => {
        const ownPrograms = programList.filter((program) => program.belongsToPortfolio(portfolio.id));
        return (
          <PortfolioProgramsSection key={portfolio.id} portfolio={portfolio} programs={ownPrograms} />
        );
      })}
    </main>
  );
}

function PortfolioProgramsSection({
  portfolio,
  programs,
}: {
  portfolio: Portfolio;
  programs: Program[];
}) {
  return (
    <section className="flex flex-col gap-3">
      <Card>
        <CardHeader>
          <CardTitle>{portfolio.name}</CardTitle>
          <CardDescription>
            {programs.length} {programs.length === 1 ? "Program" : "Programs"} — {portfolio.executiveOwner}
          </CardDescription>
        </CardHeader>
      </Card>

      {programs.length === 0 ? (
        <Card>
          <CardContent className="p-5 text-sm text-ink-muted">
            Nenhum Program vinculado a este Portfólio ainda.
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Programa</TableHead>
                <TableHead>Saúde</TableHead>
                <TableHead>Progresso</TableHead>
                <TableHead>Projetos</TableHead>
                <TableHead>Sponsor</TableHead>
                <TableHead>Program Manager</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {programs.map((program) => (
                <TableRow key={program.id}>
                  <TableCell className="font-display font-semibold">{program.name}</TableCell>
                  <TableCell>
                    <Badge variant={healthStatusVariant(program.health)}>
                      {healthStatusLabel(program.health)}
                    </Badge>
                  </TableCell>
                  <TableCell className="w-40">
                    <div className="flex items-center gap-2">
                      <Progress value={program.progressPercentage} className="w-24" />
                      <span className="font-mono text-xs tabular-nums text-ink-muted">
                        {program.progressPercentage}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="font-mono tabular-nums">{program.projectCount}</TableCell>
                  <TableCell className="text-ink-muted">{program.sponsor}</TableCell>
                  <TableCell className="text-ink-muted">{program.programManager}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}

function ProgramManagementSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-48" />
      <Skeleton className="h-48" />
    </main>
  );
}
