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
import type { Portfolio } from "@/lib/domain/portfolio";

/**
 * Entrega 2.2 (Sprint 1) -- Situação do Portfólio. Desde a Capability 01
 * (Release 0.2), consome a entidade real Portfolio (lib/domain/portfolio.ts)
 * em vez do mock PortfolioSituation -- primeira substituição progressiva
 * de dado simulado por dado real do Executive Cockpit.
 */
export function PortfolioSituationGrid({
  portfolios,
}: {
  portfolios: Portfolio[];
}) {
  return (
    <>
      <div
        data-testid="portfolio-situation-table"
        className="hidden overflow-hidden rounded-lg border border-border bg-surface shadow-md md:block"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Portfólio</TableHead>
              <TableHead>Saúde</TableHead>
              <TableHead>Progresso</TableHead>
              <TableHead>Programas</TableHead>
              <TableHead>Projetos</TableHead>
              <TableHead>Responsável</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {portfolios.map((portfolio) => (
              <TableRow key={portfolio.id}>
                <TableCell className="font-display font-semibold">{portfolio.name}</TableCell>
                <TableCell>
                  <Badge variant={healthStatusVariant(portfolio.health)}>
                    {healthStatusLabel(portfolio.health)}
                  </Badge>
                </TableCell>
                <TableCell className="w-40">
                  <div className="flex items-center gap-2">
                    <Progress value={portfolio.progressPercentage} className="w-24" />
                    <span className="font-mono text-xs tabular-nums text-ink-muted">
                      {portfolio.progressPercentage}%
                    </span>
                  </div>
                </TableCell>
                <TableCell className="font-mono tabular-nums">{portfolio.programCount}</TableCell>
                <TableCell className="font-mono tabular-nums">{portfolio.projectCount}</TableCell>
                <TableCell className="text-ink-muted">{portfolio.executiveOwner}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div data-testid="portfolio-situation-cards" className="flex flex-col gap-3 md:hidden">
        {portfolios.map((portfolio) => (
          <Card key={portfolio.id}>
            <CardContent className="flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <span className="font-display font-semibold">{portfolio.name}</span>
                <Badge variant={healthStatusVariant(portfolio.health)}>
                  {healthStatusLabel(portfolio.health)}
                </Badge>
              </div>
              <Progress value={portfolio.progressPercentage} />
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-ink-muted">Programas</p>
                  <p className="font-mono tabular-nums">{portfolio.programCount}</p>
                </div>
                <div>
                  <p className="text-xs text-ink-muted">Projetos</p>
                  <p className="font-mono tabular-nums">{portfolio.projectCount}</p>
                </div>
              </div>
              <p className="text-xs text-ink-muted">{portfolio.executiveOwner}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
