import { Info } from "lucide-react";

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
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Portfolio } from "@/lib/domain/portfolio";
import {
  computeScheduleStatus,
  scheduleStatusBadgeVariant,
  SCHEDULE_STATUS_LABEL,
} from "@/lib/dashboard/schedule-status";

/**
 * V1 Product & Capability Completion, Pacote G: a Human User Session #2
 * (D-222) mostrou que o usuário entende cada selo isoladamente, mas
 * questiona a relação entre eles quando divergem (ex.: um portfólio
 * "Crítico" em saúde mas "No Prazo"). Nenhum algoritmo mudou -- só a
 * explicação de que são duas dimensões independentes por desenho.
 */
function HealthTooltip() {
  return (
    <Tooltip>
      <TooltipTrigger aria-label="O que significa Saúde?">
        <Info className="size-3.5 text-ink-faint" aria-hidden="true" />
      </TooltipTrigger>
      <TooltipContent>
        Visão mais ampla do estado do portfólio (execução, riscos, entregas) --
        independente do cronograma.
      </TooltipContent>
    </Tooltip>
  );
}

function ScheduleTooltip() {
  return (
    <Tooltip>
      <TooltipTrigger aria-label="O que significa Prazo?">
        <Info className="size-3.5 text-ink-faint" aria-hidden="true" />
      </TooltipTrigger>
      <TooltipContent>
        Situação temporal/cronograma apenas -- um portfólio pode estar no prazo
        mesmo com saúde crítica, e vice-versa.
      </TooltipContent>
    </Tooltip>
  );
}

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
              <TableHead>
                <span className="inline-flex items-center gap-1">
                  Saúde
                  <HealthTooltip />
                </span>
              </TableHead>
              <TableHead>
                <span className="inline-flex items-center gap-1">
                  Prazo
                  <ScheduleTooltip />
                </span>
              </TableHead>
              <TableHead>Progresso</TableHead>
              <TableHead>Programas</TableHead>
              <TableHead>Projetos</TableHead>
              <TableHead>Responsável</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {portfolios.map((portfolio) => {
              const scheduleStatus = computeScheduleStatus(
                portfolio.plannedEndDate,
                portfolio.actualEndDate,
                portfolio.status,
              );
              return (
              <TableRow key={portfolio.id}>
                <TableCell className="font-display font-semibold">{portfolio.name}</TableCell>
                <TableCell>
                  <Badge variant={healthStatusVariant(portfolio.health)}>
                    {healthStatusLabel(portfolio.health)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={scheduleStatusBadgeVariant(scheduleStatus)}>
                    {SCHEDULE_STATUS_LABEL[scheduleStatus]}
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
              );
            })}
          </TableBody>
        </Table>
      </div>

      <div data-testid="portfolio-situation-cards" className="flex flex-col gap-3 md:hidden">
        {portfolios.map((portfolio) => {
          const scheduleStatus = computeScheduleStatus(
            portfolio.plannedEndDate,
            portfolio.actualEndDate,
            portfolio.status,
          );
          return (
          <Card key={portfolio.id}>
            <CardContent className="flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <span className="font-display font-semibold">{portfolio.name}</span>
                <div className="flex flex-col items-end gap-1">
                  <Badge variant={healthStatusVariant(portfolio.health)}>
                    {healthStatusLabel(portfolio.health)}
                  </Badge>
                  <Badge variant={scheduleStatusBadgeVariant(scheduleStatus)}>
                    {SCHEDULE_STATUS_LABEL[scheduleStatus]}
                  </Badge>
                </div>
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
          );
        })}
      </div>
    </>
  );
}
