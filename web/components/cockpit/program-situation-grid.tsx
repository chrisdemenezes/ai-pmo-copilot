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
import type { ProgramSituation } from "@/lib/mock/cockpit-data";

/**
 * Entrega 2.2 -- Situação dos Programas (Sprint 1, dados simulados).
 * Mesmo padrão de PortfolioSituationGrid -- Program também não é uma
 * entidade real ainda (Release 0.2).
 */
export function ProgramSituationGrid({ programs }: { programs: ProgramSituation[] }) {
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
              <TableRow key={program.name}>
                <TableCell className="font-display font-semibold">{program.name}</TableCell>
                <TableCell className="text-ink-muted">{program.portfolio}</TableCell>
                <TableCell>
                  <Badge variant={healthStatusVariant(program.health)}>
                    {healthStatusLabel(program.health)}
                  </Badge>
                </TableCell>
                <TableCell className="w-40">
                  <div className="flex items-center gap-2">
                    <Progress value={program.progress} className="w-24" />
                    <span className="font-mono text-xs tabular-nums text-ink-muted">
                      {program.progress}%
                    </span>
                  </div>
                </TableCell>
                <TableCell className="font-mono tabular-nums">{program.projectsCount}</TableCell>
                <TableCell className="text-ink-muted">{program.owner}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div data-testid="program-situation-cards" className="flex flex-col gap-3 md:hidden">
        {programs.map((program) => (
          <Card key={program.name}>
            <CardContent className="flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <span className="font-display font-semibold">{program.name}</span>
                <Badge variant={healthStatusVariant(program.health)}>
                  {healthStatusLabel(program.health)}
                </Badge>
              </div>
              <p className="text-xs text-ink-muted">{program.portfolio}</p>
              <Progress value={program.progress} />
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-ink-muted">Projetos</p>
                  <p className="font-mono tabular-nums">{program.projectsCount}</p>
                </div>
              </div>
              <p className="text-xs text-ink-muted">{program.owner}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
