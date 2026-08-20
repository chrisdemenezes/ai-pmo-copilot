import type { DomainStatus } from "@/lib/domain/shared";

/**
 * Local V1 Pilot Findings Review (D-217, Seção 6C) -- schedule/deadline
 * indicator using only data already in the domain model
 * (startDate/plannedEndDate/actualEndDate, present on Portfolio/Program/
 * Project since Capability 01). Not a new business rule: this generalizes
 * the exact boolean logic `Project.isOverdue()` already uses
 * (web/lib/domain/project.ts) into a 3-state label, so it applies
 * uniformly to Portfolio/Program (plain interfaces, no isOverdue() method)
 * without duplicating the rule per type. Always derived at render time --
 * never persisted, same discipline as UrgencyBucket
 * (web/lib/workspace/action-momentum.ts) and ExecutiveFocus.
 */
export type ScheduleStatus = "no_prazo" | "atencao" | "atrasado";

const DUE_SOON_THRESHOLD_DAYS = 7;
const MS_PER_DAY = 1000 * 60 * 60 * 24;

export function computeScheduleStatus(
  plannedEndDate: string,
  actualEndDate: string | null,
  status: DomainStatus,
  referenceDate: Date = new Date(),
): ScheduleStatus {
  // Encerrado (mirrors isOverdue()'s own guard): a closed item is no longer
  // tracked for schedule risk, regardless of when it actually finished.
  if (status === "Encerrado") {
    return "no_prazo";
  }

  const planned = new Date(plannedEndDate);

  if (actualEndDate === null && planned < referenceDate) {
    return "atrasado";
  }

  const daysUntilDue = (planned.getTime() - referenceDate.getTime()) / MS_PER_DAY;
  if (daysUntilDue <= DUE_SOON_THRESHOLD_DAYS) {
    return "atencao";
  }

  return "no_prazo";
}

export const SCHEDULE_STATUS_LABEL: Record<ScheduleStatus, string> = {
  no_prazo: "No prazo",
  atencao: "Atenção",
  atrasado: "Atrasado",
};

export function scheduleStatusBadgeVariant(status: ScheduleStatus): "ok" | "warn" | "danger" {
  if (status === "atrasado") return "danger";
  if (status === "atencao") return "warn";
  return "ok";
}
