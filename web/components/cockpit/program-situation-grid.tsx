import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Program } from "@/lib/domain/program";
import type { Portfolio } from "@/lib/domain/portfolio";

/**
 * Entrega 2.2 (Sprint 1) -- Situação dos Programas. Desde a Capability 02
 * (Release 0.2), consome a entidade real Program (lib/domain/program.ts) --
 * mesma substituição progressiva já feita para Portfolio na Capability 01.
 */
export function ProgramSituationGrid({
  programs,
  portfolios,
}: {
  programs: Program[];
  portfolios: Portfolio[];
}) {
  const portfolioName = (portfolioId: string) =>
    portfolios.find((portfolio) => portfolio.id === portfolioId)?.name ?? portfolioId;

  return (
    <>
      <div
        data-testid="program-situation-table"
        className="hidden overflow-hidden rounded-lg border border-border bg-surface shadow-md md:block"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Programa</TableHead>
              <TableHead>Portfólio</TableHead>
              <TableHead>Saúde</TableHead>
              <TableHead>Progresso</TableHead>
              <TableHead>Projetos</TableHead>
              <TableHead>Responsável</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {programs.map((program) => (
              <TableRow key={program.id}>
                <TableCell className="font-display font-semibold">{program.name}</TableCell>
                <TableCell className="text-ink-muted">{portfolioName(program.portfolioId)}</TableCell>
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
                <TableCell className="text-ink-muted">{program.programManager}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div data-testid="program-situation-cards" className="flex flex-col gap-3 md:hidden">
        {programs.map((program) => (
          <Card key={program.id}>
            <CardContent className="flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <span className="font-display font-semibold">{program.name}</span>
                <Badge variant={healthStatusVariant(program.health)}>
                  {healthStatusLabel(program.health)}
                </Badge>
              </div>
              <p className="text-xs text-ink-muted">{portfolioName(program.portfolioId)}</p>
              <Progress value={program.progressPercentage} />
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-ink-muted">Projetos</p>
                  <p className="font-mono tabular-nums">{program.projectCount}</p>
                </div>
              </div>
              <p className="text-xs text-ink-muted">{program.programManager}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
