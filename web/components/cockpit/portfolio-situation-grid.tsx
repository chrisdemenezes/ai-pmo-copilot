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
import type { PortfolioSituation } from "@/lib/mock/cockpit-data";

/**
 * Entrega 2.2 -- Situação do Portfólio (Sprint 1, dados simulados).
 * Portfolio não é uma entidade real ainda (Release 0.2) -- este componente
 * já assume a forma final esperada para quando o dado real existir.
 */
export function PortfolioSituationGrid({
  portfolios,
}: {
  portfolios: PortfolioSituation[];
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
              <TableRow key={portfolio.name}>
                <TableCell className="font-display font-semibold">{portfolio.name}</TableCell>
                <TableCell>
                  <Badge variant={healthStatusVariant(portfolio.health)}>
                    {healthStatusLabel(portfolio.health)}
                  </Badge>
                </TableCell>
                <TableCell className="w-40">
                  <div className="flex items-center gap-2">
                    <Progress value={portfolio.progress} className="w-24" />
                    <span className="font-mono text-xs tabular-nums text-ink-muted">
                      {portfolio.progress}%
                    </span>
                  </div>
                </TableCell>
                <TableCell className="font-mono tabular-nums">{portfolio.programsCount}</TableCell>
                <TableCell className="font-mono tabular-nums">{portfolio.projectsCount}</TableCell>
                <TableCell className="text-ink-muted">{portfolio.owner}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div data-testid="portfolio-situation-cards" className="flex flex-col gap-3 md:hidden">
        {portfolios.map((portfolio) => (
          <Card key={portfolio.name}>
            <CardContent className="flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <span className="font-display font-semibold">{portfolio.name}</span>
                <Badge variant={healthStatusVariant(portfolio.health)}>
                  {healthStatusLabel(portfolio.health)}
                </Badge>
              </div>
              <Progress value={portfolio.progress} />
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-ink-muted">Programas</p>
                  <p className="font-mono tabular-nums">{portfolio.programsCount}</p>
                </div>
                <div>
                  <p className="text-xs text-ink-muted">Projetos</p>
                  <p className="font-mono tabular-nums">{portfolio.projectsCount}</p>
                </div>
              </div>
              <p className="text-xs text-ink-muted">{portfolio.owner}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
