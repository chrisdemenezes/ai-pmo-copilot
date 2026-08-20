import { describe, expect, it } from "vitest";
import { computeScheduleStatus, scheduleStatusBadgeVariant, SCHEDULE_STATUS_LABEL } from "./schedule-status";

const REFERENCE = new Date("2026-08-20T12:00:00Z");

describe("computeScheduleStatus", () => {
  it("is atrasado when plannedEndDate is in the past and there is no actualEndDate", () => {
    expect(computeScheduleStatus("2026-08-01", null, "Ativo", REFERENCE)).toBe("atrasado");
  });

  it("is no_prazo when plannedEndDate is far in the future", () => {
    expect(computeScheduleStatus("2026-12-01", null, "Ativo", REFERENCE)).toBe("no_prazo");
  });

  it("is atencao when plannedEndDate is within the due-soon threshold", () => {
    expect(computeScheduleStatus("2026-08-24", null, "Ativo", REFERENCE)).toBe("atencao");
  });

  it("is no_prazo for a closed item, even with a past plannedEndDate", () => {
    expect(computeScheduleStatus("2026-08-01", "2026-07-30", "Encerrado", REFERENCE)).toBe(
      "no_prazo",
    );
  });

  it("is not atrasado once actualEndDate is set, even past the planned date", () => {
    // Mirrors Project.isOverdue()'s own guard: actualEndDate !== null means
    // delivery already happened, overdue no longer applies.
    expect(computeScheduleStatus("2026-08-01", "2026-08-15", "Ativo", REFERENCE)).not.toBe(
      "atrasado",
    );
  });

  it("is no_prazo for Planejado status with a distant plannedEndDate", () => {
    expect(computeScheduleStatus("2027-01-01", null, "Planejado", REFERENCE)).toBe("no_prazo");
  });
});

describe("scheduleStatusBadgeVariant", () => {
  it("maps each status to the matching Badge semantic variant", () => {
    expect(scheduleStatusBadgeVariant("atrasado")).toBe("danger");
    expect(scheduleStatusBadgeVariant("atencao")).toBe("warn");
    expect(scheduleStatusBadgeVariant("no_prazo")).toBe("ok");
  });
});

describe("SCHEDULE_STATUS_LABEL", () => {
  it("has a Portuguese label for every status", () => {
    expect(SCHEDULE_STATUS_LABEL.no_prazo).toBe("No prazo");
    expect(SCHEDULE_STATUS_LABEL.atencao).toBe("Atenção");
    expect(SCHEDULE_STATUS_LABEL.atrasado).toBe("Atrasado");
  });
});
